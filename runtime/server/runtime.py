"""Local KRYUK24 intake prototype. No external sending or payments."""
import re
import argparse, hashlib, hmac, json, math, os, sqlite3, uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contact_metrics import validate_metadata, daily_summary

NEXT = {'NEW':'QUALIFIED','QUALIFIED':'PRICE_QUOTED','PRICE_QUOTED':'CUSTOMER_CONFIRMED','CUSTOMER_CONFIRMED':'DRIVER_ASSIGNED','DRIVER_ASSIGNED':'EN_ROUTE','EN_ROUTE':'ARRIVED','ARRIVED':'LOADED','LOADED':'TRANSPORTING','TRANSPORTING':'DELIVERED','DELIVERED':'PAYMENT_CONFIRMED','PAYMENT_CONFIRMED':'CLOSED'}
def now(): return datetime.now(timezone.utc).isoformat()
def encode(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
class Runtime:
 def __init__(self,path):
  self.path=path
  with self.db() as c:
   c.executescript('''CREATE TABLE IF NOT EXISTS contact_interactions(id TEXT PRIMARY KEY, order_id TEXT UNIQUE, digest TEXT, data TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,idem TEXT UNIQUE, digest TEXT,data TEXT,status TEXT,revision INTEGER,created TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,order_id TEXT,kind TEXT,data TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,order_id TEXT,recipient TEXT,body TEXT,status TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,order_id TEXT UNIQUE,recipient TEXT,body TEXT,status TEXT,attempts INTEGER,receipt TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS dispatch_decisions(order_id TEXT PRIMARY KEY,decision TEXT,actor TEXT,evidence TEXT,trust_level TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS matches(order_id TEXT PRIMARY KEY,external_ref TEXT UNIQUE,evidence TEXT,actor TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS call_jobs(id TEXT PRIMARY KEY,idem TEXT UNIQUE,data TEXT,created TEXT);''')
 @contextmanager
 def db(self):
  c=sqlite3.connect(self.path,timeout=10)
  try:
   c.row_factory=sqlite3.Row
   c.execute('PRAGMA journal_mode=WAL')
   with c:
    yield c
  finally:
   c.close()
 def event(self,c,oid,kind,data):c.execute('INSERT INTO events(order_id,kind,data,created) VALUES(?,?,?,?)',(oid,kind,encode(data),now()))
 def get(self,oid):
  with self.db() as c:
   row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
   if not row:raise LookupError('order not found')
   out=dict(row);out['data']=json.loads(out['data']);out.pop('digest');out.pop('idem');return out
 def intake(self,data,key):
  if not isinstance(data,dict):raise ValueError('object required')
  for f in ('contact','pickup','destination','vehicle'):
   if not isinstance(data.get(f),str) or not data[f].strip() or len(data[f])>500:raise ValueError('required text: '+f)
  if not isinstance(key,str) or not 1<=len(key)<=128:raise ValueError('Idempotency-Key required (1..128 chars)')
  requested=data.get('request_id')
  if requested is not None and (not isinstance(requested,str) or not re.fullmatch(r'K24-[a-f0-9]{32}',requested)):raise ValueError('invalid request_id')
  if 'interaction' in data:
   metadata=validate_metadata(data['interaction'])
   if metadata['channel']!=data.get('channel') or metadata['position']!='form':raise ValueError('form interaction mismatch')
  raw=encode(data);digest=hashlib.sha256(raw.encode()).hexdigest();oid=requested or uuid.uuid4().hex
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT id,digest FROM orders WHERE idem=?',(key,)).fetchone()
   if old:
    if old['digest']!=digest:raise ValueError('idempotency key reused with different request')
    oid=old['id']
   else:
    if c.execute('SELECT id FROM orders WHERE id=?',(oid,)).fetchone():raise ValueError('request ID already exists with another key')
    c.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?)',(oid,key,digest,raw,'NEW',0,now()));self.event(c,oid,'ORDER_RECEIVED',{'source':data.get('source','UNKNOWN'),'test':data.get('test',False)})
    # Same transaction as intake: a new request cannot lose its notification task.
    if data.get('flow')=='VISITOR_SENDS_WHATSAPP':self.event(c,oid,'WHATSAPP_HANDOFF_REQUESTED',{'delivery':'UNVERIFIED'})
    else:self.enqueue(c,oid,data)
    if 'interaction' in data:self.insert_contact(c,oid,data['interaction'],data.get('test',False),oid)
  return self.get(oid)
 def insert_contact(self,c,event_id,metadata,test,order_id=None):
  clean=validate_metadata(metadata);clean['test']=bool(test)
  raw=encode(clean);digest=hashlib.sha256(raw.encode()).hexdigest()
  old=c.execute('SELECT digest FROM contact_interactions WHERE id=?',(event_id,)).fetchone()
  if old:
   if old['digest']!=digest:raise ValueError('contact ID reused with different metadata')
   return False
  c.execute('INSERT INTO contact_interactions VALUES(?,?,?,?,?)',(event_id,order_id,digest,raw,now()))
  return True
 def contact_click(self,event_id,metadata,test=True):
  if not isinstance(event_id,str) or not re.fullmatch(r'CLICK-[a-f0-9]{32}',event_id):raise ValueError('contact event ID required')
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');created=self.insert_contact(c,event_id,metadata,test)
  return {'id':event_id,'recorded':True,'new':created,'test':bool(test),'meaning':'CLICK_INTENT_ONLY'}
 def enqueue(self,c,oid,data):
  body=('ТЕСТ — НЕ ВЫЕЗЖАТЬ\n' if data.get('test') else '')+'Новая заявка КРЮК24: '+oid+'\n'+ '\n'.join(f'{k}: {data[k]}' for k in ('contact','pickup','destination','vehicle'))+'\nЦена и время подачи не подтверждены.'
  c.execute('INSERT OR IGNORE INTO notifications VALUES(?,?,?,?,?,0,?,?)',(uuid.uuid4().hex,oid,'ARMEN_UNCONFIGURED',body,'BLOCKED_NO_CONNECTOR','',now()))
  self.event(c,oid,'NOTIFICATION_QUEUED',{'status':'BLOCKED_NO_CONNECTOR'})
 def dispatch_decision(self,oid,decision,actor,evidence):
  if decision not in ('ACCEPTED','DECLINED'):raise ValueError('decision must be ACCEPTED or DECLINED')
  if any(not isinstance(x,str) or not x.strip() or len(x)>2000 for x in (actor,evidence)):raise ValueError('actor and source evidence required')
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT data FROM orders WHERE id=?',(oid,)).fetchone()
   if not r:raise LookupError('order not found')
   old=c.execute('SELECT * FROM dispatch_decisions WHERE order_id=?',(oid,)).fetchone()
   if old:
    if (old['decision'],old['actor'],old['evidence'])!=(decision,actor,evidence):raise ValueError('decision already recorded; explicit correction required')
    return dict(old)
   test=json.loads(r['data']).get('test') is True
   trust='TEST_ONLY' if test else 'OPERATOR_REPORTED'
   c.execute('INSERT INTO dispatch_decisions VALUES(?,?,?,?,?,?)',(oid,decision,actor,evidence,trust,now()))
   self.event(c,oid,'DISPATCH_DECISION_RECORDED',{'decision':decision,'actor':actor,'evidence':evidence,'trust_level':trust})
   return dict(c.execute('SELECT * FROM dispatch_decisions WHERE order_id=?',(oid,)).fetchone())
 def match_whatsapp(self,oid,external_ref,evidence,actor):
  if any(not isinstance(x,str) or not x.strip() or len(x)>2000 for x in (external_ref,evidence,actor)):raise ValueError('reference, evidence and actor required')
  if not re.search(r'(?<![A-Za-z0-9-])'+re.escape(oid)+r'(?![A-Za-z0-9-])',evidence):raise ValueError('evidence must contain exact request ID; probable match is not confirmation')
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not c.execute('SELECT id FROM orders WHERE id=?',(oid,)).fetchone():raise LookupError('order not found')
   old=c.execute('SELECT * FROM matches WHERE order_id=?',(oid,)).fetchone()
   if old:
    if (old['external_ref'],old['evidence'],old['actor'])!=(external_ref,evidence,actor):raise ValueError('match already recorded')
    return dict(old)
   if c.execute('SELECT order_id FROM matches WHERE external_ref=?',(external_ref,)).fetchone():raise ValueError('message already matched to another request')
   c.execute('INSERT INTO matches VALUES(?,?,?,?,?)',(oid,external_ref,evidence,actor,now()))
   self.event(c,oid,'WHATSAPP_RECEIPT_OBSERVED',{'external_ref':external_ref,'actor':actor,'trust_level':'OPERATOR_OBSERVED'})
   return dict(c.execute('SELECT * FROM matches WHERE order_id=?',(oid,)).fetchone())
 def record_call(self,data,key):
  if not isinstance(data,dict) or data.get('source')!='PHONE':raise ValueError('source must be PHONE')
  if not isinstance(key,str) or not 1<=len(key)<=128:raise ValueError('idempotency key required')
  if data.get('outcome') not in ('INQUIRY','ACCEPTED','COMPLETED','DECLINED','UNKNOWN'):raise ValueError('invalid outcome')
  if any(not isinstance(data.get(f),str) or not data[f].strip() or len(data[f])>2000 for f in ('date','evidence','actor')):raise ValueError('date, evidence and actor required')
  try:datetime.strptime(data['date'],'%Y-%m-%d')
  except ValueError:raise ValueError('date must be YYYY-MM-DD')
  amount=data.get('amount')
  if amount is not None and (isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or not 0<amount<10000000):raise ValueError('invalid amount')
  raw=encode(data)
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM call_jobs WHERE idem=?',(key,)).fetchone()
   if old:
    if old['data']!=raw:raise ValueError('key reused with different call job')
    return {'id':old['id'],'data':json.loads(old['data']),'trust_level':'OPERATOR_REPORTED'}
   cid='CALL-'+uuid.uuid4().hex;c.execute('INSERT INTO call_jobs VALUES(?,?,?,?)',(cid,key,raw,now()))
  return {'id':cid,'data':data,'trust_level':'OPERATOR_REPORTED'}
 def transition(self,oid,status,revision,evidence):
  if not isinstance(evidence,dict):raise ValueError('evidence object required')
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
   if not r:raise LookupError('order not found')
   if revision!=r['revision']:raise ValueError('stale revision')
   if status!=NEXT.get(r['status']):raise ValueError('invalid transition')
   required={'PRICE_QUOTED':['price','terms','confirmed_by'],'CUSTOMER_CONFIRMED':['customer_confirmation'],'DRIVER_ASSIGNED':['driver','driver_acceptance'],'EN_ROUTE':['time'],'ARRIVED':['time'],'DELIVERED':['completion_evidence'],'PAYMENT_CONFIRMED':['amount','payment_evidence','trust_level'],'CLOSED':['feedback_state','no_open_issue']}.get(status,[])
   if any(not evidence.get(f) for f in required):raise ValueError('missing evidence: '+','.join(required))
   if status in ('PRICE_QUOTED','PAYMENT_CONFIRMED'):
    n=evidence.get('price' if status=='PRICE_QUOTED' else 'amount')
    if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or not 0<n<10000000:raise ValueError('invalid amount')
   if status=='PAYMENT_CONFIRMED' and evidence['trust_level']!='VERIFIED':raise ValueError('payment closure requires VERIFIED evidence')
   if status=='CLOSED' and evidence['no_open_issue'] is not True:raise ValueError('open issue prevents closure')
   c.execute('UPDATE orders SET status=?,revision=revision+1 WHERE id=?',(status,oid));self.event(c,oid,status,evidence)
  return self.get(oid)
 def draft(self,oid,recipient,body):
  self.get(oid)
  if not isinstance(recipient,str) or not recipient.strip() or not isinstance(body,str) or not body.strip() or len(body)>10000:raise ValueError('recipient and body required')
  mid=uuid.uuid4().hex
  with self.db() as c:
   c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(mid,oid,recipient,body,'PENDING_APPROVAL',now()));self.event(c,oid,'MESSAGE_DRAFTED',{'message_id':mid})
  return {'id':mid,'status':'PENDING_APPROVAL','sending_enabled':False}
 def report(self):
  with self.db() as c:
   orders=[dict(r) for r in c.execute('SELECT id,status,revision,created,data FROM orders ORDER BY created')]
   for r in orders:r['data']=json.loads(r['data'])
   messages=[dict(r) for r in c.execute('SELECT id,order_id,status,created FROM messages')]
   notifications=[dict(r) for r in c.execute('SELECT * FROM notifications ORDER BY created')]
   matches=[dict(r) for r in c.execute('SELECT * FROM matches')]
   calls=[dict(r) for r in c.execute('SELECT id,data,created FROM call_jobs ORDER BY created')]
   for r in calls:r['data']=json.loads(r['data']);r['trust_level']='OPERATOR_REPORTED'
   decisions=[dict(r) for r in c.execute('SELECT * FROM dispatch_decisions')]
   contacts=[dict(r) for r in c.execute('SELECT id,order_id,data,created FROM contact_interactions ORDER BY created DESC')]
   for row in contacts:row['data']=json.loads(row['data'])
  return {'contact_interactions':contacts,'contact_daily':daily_summary(contacts),'contact_daily_test':daily_summary([x for x in contacts if x['data'].get('test') is True],True),'contact_timezone':'Europe/Moscow','orders':orders,'messages':messages,'notifications':notifications,'dispatch_decisions':decisions,'whatsapp_matches':matches,'call_jobs':calls,'external_connectors':'NOT_CONNECTED','sending_enabled':False,'generated':now()}

def serve(runtime,token,port):
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass # Do not log contact/address or credentials.
  def reply(self,status,data):
   raw=encode(data).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def authorized(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
  def do_GET(self):
   if self.path=='/health':return self.reply(200,{'status':'ok','mode':'LOCAL_PROTOTYPE','sending_enabled':False})
   if not self.authorized():return self.reply(401,{'error':'unauthorized'})
   try:
    if self.path=='/report':return self.reply(200,runtime.report())
    if self.path.startswith('/orders/'):return self.reply(200,runtime.get(self.path.split('/')[-1]))
    self.reply(404,{'error':'not found'})
   except LookupError as e:self.reply(404,{'error':str(e)})
  def do_POST(self):
   if not self.authorized():return self.reply(401,{'error':'unauthorized'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=32768:raise ValueError('body size invalid')
    data=json.loads(self.rfile.read(size));parts=self.path.strip('/').split('/')
    if self.path=='/call-jobs':return self.reply(201,runtime.record_call(data,self.headers.get('Idempotency-Key')))
    if len(parts)==3 and parts[0]=='orders' and parts[2]=='whatsapp-match':return self.reply(200,runtime.match_whatsapp(parts[1],data['external_ref'],data['evidence'],data['actor']))
    if self.path=='/orders':return self.reply(201,runtime.intake(data,self.headers.get('Idempotency-Key')))
    if len(parts)==3 and parts[0]=='orders' and parts[2]=='transition':return self.reply(200,runtime.transition(parts[1],data['status'],data['revision'],data.get('evidence',{})))
    if len(parts)==3 and parts[0]=='orders' and parts[2]=='messages':return self.reply(201,runtime.draft(parts[1],data['recipient'],data['body']))
    if len(parts)==3 and parts[0]=='orders' and parts[2]=='dispatch-decision':return self.reply(200,runtime.dispatch_decision(parts[1],data['decision'],data['actor'],data['evidence']))
    self.reply(404,{'error':'not found'})
   except LookupError as e:self.reply(404,{'error':str(e)})
   except (ValueError,KeyError,TypeError) as e:self.reply(400,{'error':str(e)})
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',default='runtime.sqlite');p.add_argument('--port',type=int,default=8787);a=p.parse_args();token=os.environ.get('KRYUK_API_TOKEN','')
 if len(token)<24:raise SystemExit('Set KRYUK_API_TOKEN to a random secret of at least 24 characters; do not put it in site code.')
 serve(Runtime(a.db),token,a.port)
