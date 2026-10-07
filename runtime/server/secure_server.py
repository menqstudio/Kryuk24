"""Staging capture service. Bind behind an HTTPS reverse proxy; never run demo_server publicly."""
import argparse,mimetypes,base64,hmac,json,os,re,threading,time
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from runtime import Runtime,encode
from staging_site import public_file, render_page
from ops_work import Operations
from ops_views import dashboard
ROOT=Path(__file__).parent

def server(db,password,origins,port=8788,test_mode=True):
 if len(password)<24 or password.startswith('REPLACE_'):raise ValueError('operator password must have at least 24 characters')
 if not origins or any(urlsplit(o).scheme not in ('https','http') or urlsplit(o).netloc=='' or urlsplit(o).path for o in origins):raise ValueError('exact allowed origins required')
 r=Runtime(db);ops=Operations(db);buckets=defaultdict(deque);lock=threading.Lock()
 class H(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def origin_allowed(self):return self.headers.get('Origin') in origins
  def admin(self):
   expected='Basic '+base64.b64encode(('gev:'+password).encode()).decode()
   return hmac.compare_digest(self.headers.get('Authorization',''),expected)
  def reply(self,status,data,kind='application/json; charset=utf-8',auth=False):
   raw=encode(data).encode('utf-8') if isinstance(data,dict) else data if isinstance(data,bytes) else data.encode('utf-8')
   self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
   if urlsplit(self.path).path.startswith('/operator/site/'):
    self.send_header('X-Robots-Tag','noindex, nofollow');self.send_header('Content-Security-Policy',"default-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'")
   if auth:self.send_header('WWW-Authenticate','Basic realm="KRYUK24 operator", charset="UTF-8"')
   if self.origin_allowed():self.send_header('Access-Control-Allow-Origin',self.headers['Origin']);self.send_header('Vary','Origin')
   self.end_headers();self.wfile.write(raw)
  def do_OPTIONS(self):
   if self.path not in ('/capture','/contact-click') or not self.origin_allowed():return self.reply(403,{'error':'origin rejected'})
   self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.headers['Origin']);self.send_header('Vary','Origin');self.send_header('Access-Control-Allow-Methods','POST');self.send_header('Access-Control-Allow-Headers','Content-Type, Idempotency-Key');self.end_headers()
  def do_GET(self):
   route=urlsplit(self.path).path
   if route=='/health':return self.reply(200,{'ok':True,'mode':'STAGING' if test_mode else 'LIVE_CAPTURE','sending_enabled':False})
   if route.startswith('/operator'):
    if not self.admin():return self.reply(401,{'error':'operator login required'},auth=True)
    if route=='/operator/report':return self.reply(200,r.report())
    if route=='/operator/work':return self.reply(200,dashboard(ops.report()),'text/html; charset=utf-8')
    if route=='/operator/work/report':return self.reply(200,ops.report())
    if route.startswith('/operator/media/'):
     try:
      asset=ops.media.verify(route[len('/operator/media/'):]);path=Path(asset['local_path'])
      return self.reply(200,path.read_bytes(),mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
     except (ValueError,OSError):return self.reply(404,{'error':'prepared asset unavailable'})
    if test_mode and route.startswith('/operator/site/'):
     relative=unquote(route[len('/operator/site/'):])
     if relative.endswith('/') or not relative:relative+='index.html'
     file=public_file(ROOT/'site',relative)
     if not file:return self.reply(404,{'error':'not found'})
     if file.suffix=='.html':return self.reply(200,render_page(relative,file.read_text(encoding='utf-8')),'text/html; charset=utf-8')
     return self.reply(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
    if test_mode and route in ('/operator/staging','/operator/staging-preview','/operator/staging-handoff.js','/operator/contact-clicks.js'):
     if route=='/operator/staging':raw=(ROOT/'staging-form.html').read_text(encoding='utf-8');kind='text/html; charset=utf-8'
     elif route=='/operator/staging-preview':raw=(ROOT/'handoff-preview.html').read_text(encoding='utf-8').replace('/test-report','/operator/report').replace('/test-orders','/operator');kind='text/html; charset=utf-8'
     elif route=='/operator/contact-clicks.js':raw=(ROOT/'contact-clicks.js').read_text(encoding='utf-8');kind='text/javascript; charset=utf-8'
     else:raw=(ROOT/'whatsapp-handoff.js').read_text(encoding='utf-8').replace("'/handoff-preview'","'/operator/staging-preview'");kind='text/javascript; charset=utf-8'
     return self.reply(200,raw,kind)
    if route=='/operator':
     html=(ROOT/'test-orders.html').read_text(encoding='utf-8').replace('/test-report','/operator/report').replace('/test-match','/operator/match').replace('/test-call','/operator/call').replace('/test-dispatch-decision','/operator/decision')
     if test_mode:html=html.replace('<a href="/">К форме</a>','<a href="/operator/staging">К закрытому тесту</a>')
     if not test_mode:html=html.replace('order.data.test===true&&','').replace('Тест: ','').replace('тестовый звонок','звонок').replace('Тестовый звонок','Звонок').replace('Тестовое решение записано. Армен не уведомлен.','Сообщенное решение записано.').replace('Реальная отправка отключена. Кнопки ниже — локальная проверка решения диспетчера, не ответ Армена и не заказ машины.','Мессенджер отправляет клиент. Совпадения и решения здесь записывает оператор с источником; это не автоматическая проверка WhatsApp.')
     # Basic auth stays in browser HTTP credentials; no secret embedded in HTML/JS.
     return self.reply(200,html,'text/html; charset=utf-8')
   self.reply(404,{'error':'not found'})
  def do_POST(self):
   if self.path not in ('/capture','/contact-click') and not self.path.startswith('/operator/'):return self.reply(404,{'error':'not found'})
   if not self.origin_allowed():return self.reply(403,{'error':'origin rejected'})
   if self.path.startswith('/operator/') and not self.admin():return self.reply(401,{'error':'operator login required'},auth=True)
   if self.path in ('/capture','/contact-click'):
    # One proxy/worker: trust no forwarded IP headers. Reverse proxy must also rate-limit per visitor.
    with lock:
     t=time.monotonic();q=buckets[self.client_address[0]]
     while q and q[0]<t-60:q.popleft()
     if len(q)>=120:return self.reply(429,{'error':'capture rate limit'})
     q.append(t)
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=8192:raise ValueError('invalid body size')
    if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
    d=json.loads(self.rfile.read(size))
    if not isinstance(d,dict):raise ValueError('object required')
    if self.path=='/contact-click':
     if not test_mode:return self.reply(404,{'error':'staging only'})
     if set(d)!={'event_id','metadata'}:raise ValueError('event_id and metadata only')
     result=r.contact_click(d['event_id'],d['metadata'],test=True)
     return self.reply(201 if result['new'] else 200,result)
    if self.path=='/capture':
     allowed={'request_id','contact','pickup','destination','vehicle','message','estimate_display','channel','form_kind','interaction'}
     if set(d)-allowed or any(not isinstance(v,str) or len(v)>4000 for k,v in d.items() if k!='interaction'):raise ValueError('invalid capture fields')
     if d.get('channel') not in ('wa','tg') or d.get('form_kind') not in ('CALCULATOR','PREBOOKING'):raise ValueError('invalid channel/form')
     if not re.fullmatch(r'K24-[a-f0-9]{32}',d.get('request_id','')):raise ValueError('request ID required')
     if self.headers.get('Idempotency-Key')!=d['request_id']:raise ValueError('key must equal request ID')
     d.update(test=test_mode,source='WEBSITE_CAPTURE',flow='VISITOR_SENDS_WHATSAPP',notification_status='UNVERIFIED',price_status='NOT_CONFIRMED')
     o=r.intake(d,d['request_id']);return self.reply(201,{'id':o['id'],'captured':True,'message_receipt':'UNVERIFIED','test':test_mode})
    if self.path=='/operator/work/plan':
     if d:raise ValueError('empty body required; server chooses current day')
     return self.reply(200,ops.plan())
    if self.path=='/operator/work/claim':
     if set(d)!={'task_id'}:raise ValueError('task_id only')
     return self.reply(200,ops.claim(d['task_id'],'AUTHENTICATED_OPERATOR'))
    if self.path=='/operator/work/observe':
     if set(d)!={'task_id','source','observed_at','summary','blocked'} or not isinstance(d['blocked'],bool):raise ValueError('observation fields required')
     return self.reply(200,ops.observe(d['task_id'],'AUTHENTICATED_OPERATOR',d['source'],d['observed_at'],d['summary'],d['blocked']))
    if self.path=='/operator/work/approve':
     if set(d)!={'task_id','digest','reference'}:raise ValueError('exact draft approval fields required')
     return self.reply(200,ops.approve(d['task_id'],d['digest'],'GEV',d['reference']))
    if self.path=='/operator/match':return self.reply(200,r.match_whatsapp(d['order_id'],d['external_ref'],d['evidence'],'AUTHENTICATED_OPERATOR'))
    if self.path=='/operator/decision':return self.reply(200,r.dispatch_decision(d['order_id'],d['decision'],'AUTHENTICATED_OPERATOR',d.get('evidence') or 'Operator recorded via protected journal; not independent Armen verification'))
    if self.path=='/operator/call':
     d.update(source='PHONE',test=test_mode,actor='AUTHENTICATED_OPERATOR');return self.reply(201,r.record_call(d,self.headers.get('Idempotency-Key')))
    self.reply(404,{'error':'not found'})
   except (ValueError,KeyError,TypeError,LookupError) as e:self.reply(400,{'error':str(e)})
 return ThreadingHTTPServer(('127.0.0.1',port),H)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--port',type=int,default=8788);p.add_argument('--live-capture',action='store_true');a=p.parse_args()
 origins=set(filter(None,os.environ.get('KRYUK_ALLOWED_ORIGINS','').split(',')));password=os.environ.get('KRYUK_OPERATOR_PASSWORD','')
 server(a.db,password,origins,a.port,test_mode=not a.live_capture).serve_forever()
