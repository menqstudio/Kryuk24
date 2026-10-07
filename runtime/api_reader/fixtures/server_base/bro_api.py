"""STAGING-only worker sidecar. Bind loopback; HTTPS and Basic gate at Nginx."""
import argparse, base64, hashlib, hmac, json, re, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TZ = timezone(timedelta(hours=4))
JOBS = {'YANDEX_BUSINESS','YANDEX_DIRECT','METRICA','WEBMASTER','HOSTING_DEADLINES','DAILY_REPORT'}
ROUTES = {'/bro/v1/queue':'GET','/bro/v1/claim':'POST','/bro/v1/observe':'POST','/bro/v1/draft':'POST'}
def utc(): return datetime.now(timezone.utc)
def encode(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def ident(v):
    if not isinstance(v,str) or not re.fullmatch(r'[a-f0-9]{32}',v): raise ValueError('invalid identifier')
    return v

def fields(d, names):
    if not isinstance(d,dict) or set(d)!=set(names.split()): raise ValueError('invalid fields')
def text(v, maximum):
    if not isinstance(v,str) or not v.strip() or len(v)>maximum: raise ValueError('invalid text')
    return v.strip()

class Queue:
    def __init__(self, path, clock=utc):
        self.path=str(path); self.clock=clock
        if not Path(path).is_file(): raise ValueError('existing database required')
        with self.db() as c:
            required={'ops_tasks','ops_observations','ops_events'}
            if not required <= {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}: raise ValueError('operations schema required')
            c.executescript('''CREATE TABLE IF NOT EXISTS bro_receipts(
            principal TEXT, request_id TEXT, day TEXT, digest TEXT, response TEXT,
            PRIMARY KEY(principal,request_id));
            CREATE TABLE IF NOT EXISTS bro_runs(principal TEXT,run_id TEXT,task_id TEXT,
            PRIMARY KEY(principal,run_id));''')
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=10); c.row_factory=sqlite3.Row
        try:
            with c: yield c
        finally: c.close()
    def day(self): return self.clock().astimezone(TZ).date().isoformat()
    def safe(self,row):
        # Fixed structured metadata only. No ledger, draft, free-text title or observations.
        return {k:row[k] for k in ('id','day','job','kind','status','revision')}
    def listing(self):
        with self.db() as c:
            rows=c.execute('SELECT * FROM ops_tasks WHERE day=? ORDER BY rowid',(self.day(),)).fetchall()
        return {'day':self.day(),'tasks':[{**self.safe(r),'lease_expired':r['status']=='CLAIMED' and datetime.fromisoformat(r['lease_until'])<=self.clock()} for r in rows if r['job'] in JOBS],
                'daily_statuses':[{'job':r['job'],'status':r['status']} for r in rows if r['job'] in JOBS | {'LOCAL_LEDGER','RUNTIME_HEALTH','AVITO','MEDIA_INBOX'}],
                'adapter_connected':False,'sending':False}
    def apply(self,principal,route,d):
        names={'claim':'request_id run_id task_id day',
               'observe':'request_id run_id task_id day revision source observed_at summary blocked',
               'draft':'request_id run_id task_id day revision body reason'}
        fields(d,names[route]); ident(d['request_id']); ident(d['run_id'])
        if not isinstance(d['task_id'],str) or not re.fullmatch(r'WORK-[a-f0-9]{32}',d['task_id']): raise ValueError('invalid task')
        if d['day']!=self.day(): raise PermissionError('current day required')
        digest=hashlib.sha256(encode({'route':route,'data':d}).encode()).hexdigest()
        worker='BRO:'+principal+':'+d['run_id']
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            receipt=c.execute('SELECT * FROM bro_receipts WHERE principal=? AND request_id=?',(principal,d['request_id'])).fetchone()
            if receipt:
                if receipt['digest']!=digest: raise ValueError('idempotency conflict')
                row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(d['task_id'],)).fetchone()
                response=json.loads(receipt['response'])
                # Old claim responses must never revive a superseded attempt.
                if route=='claim' and (not row or row['worker']!=worker or row['revision']!=response['revision'] or row['status']!='CLAIMED' or datetime.fromisoformat(row['lease_until'])<=self.clock()): raise PermissionError('stale claim')
                return response
            row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(d['task_id'],)).fetchone()
            if not row or row['day']!=self.day() or row['job'] not in JOBS: raise PermissionError('task outside scope')
            if route=='claim':
                expired=row['status']=='CLAIMED' and datetime.fromisoformat(row['lease_until'])<=self.clock()
                if row['status']!='PENDING' and not expired: raise ValueError('not claimable')
                if row['job']=='DAILY_REPORT' and c.execute("SELECT 1 FROM ops_tasks WHERE day=? AND job!='DAILY_REPORT' AND status NOT IN ('DONE','BLOCKED','READY_REVIEW','APPROVED')",(self.day(),)).fetchone(): raise ValueError('daily work incomplete')
                if c.execute('SELECT 1 FROM bro_runs WHERE principal=? AND run_id=?',(principal,d['run_id'])).fetchone(): raise ValueError('run already used')
                c.execute('INSERT INTO bro_runs VALUES(?,?,?)',(principal,d['run_id'],row['id']))
                until=(self.clock()+timedelta(seconds=600)).isoformat()
                c.execute("UPDATE ops_tasks SET status='CLAIMED',worker=?,lease_until=?,revision=revision+1 WHERE id=?",(worker,until,row['id']))
                event='CLAIMED'; data={'worker':worker,'expires':until,'bro_http':True}
            else:
                if type(d['revision']) is not int or row['status']!='CLAIMED' or row['worker']!=worker or row['revision']!=d['revision'] or datetime.fromisoformat(row['lease_until'])<=self.clock(): raise PermissionError('active owned attempt required')
                if route=='observe':
                    source=text(d['source'],500); summary=text(d['summary'],3800)
                    observed=datetime.fromisoformat(text(d['observed_at'],100))
                    if observed.tzinfo is None or not datetime.fromisoformat(row['lease_until'])-timedelta(seconds=600)<=observed<=self.clock(): raise ValueError('invalid observation time')
                    if type(d['blocked']) is not bool: raise ValueError('blocked must be boolean')
                    if row['job']=='DAILY_REPORT' and not d['blocked']: raise ValueError('report requires draft')
                    c.execute('INSERT INTO ops_observations VALUES(?,?,?,?,?,?,?,?)',('OBS-'+uuid.uuid4().hex,row['id'],source,observed.isoformat(),'Bro-ի հաղորդած արդյունք՝ '+summary,'OPERATOR_REPORTED',worker,self.clock().isoformat()))
                    event='BLOCKED' if d['blocked'] else 'DONE'; data={'source':source,'trust':'OPERATOR_REPORTED','bro_http':True}
                    c.execute('UPDATE ops_tasks SET status=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?',(event,row['id']))
                else:
                    if row['job']!='DAILY_REPORT': raise PermissionError('report task only')
                    normalized={'action':'REPORT_DRAFT','account':'KRYUK24','destination':'INTERNAL_REVIEW','body':text(d['body'],10000),'reason':text(d['reason'],1000),'assets':[]}
                    raw=encode(normalized); draft_hash=hashlib.sha256(raw.encode()).hexdigest()
                    c.execute("UPDATE ops_tasks SET status='READY_REVIEW',draft=?,digest=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?",(raw,draft_hash,row['id']))
                    event='DRAFT_READY'; data={'digest':draft_hash,'external_execution':False,'bro_http':True}
            c.execute('INSERT INTO ops_events(task_id,kind,data,created) VALUES(?,?,?,?)',(row['id'],event,encode(data),self.clock().isoformat()))
            saved=c.execute('SELECT * FROM ops_tasks WHERE id=?',(row['id'],)).fetchone(); response=self.safe(saved)
            if route=='claim': response['lease_until']=saved['lease_until']
            if route=='draft': response['digest']=saved['digest']
            c.execute('INSERT INTO bro_receipts VALUES(?,?,?,?,?)',(principal,d['request_id'],self.day(),digest,encode(response)))
            return response

def server(queue,credentials,port=8789):
    # Credential file maps one dedicated username to SHA256(random 32+ byte password).
    fields(credentials,'username password_sha256')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',credentials['username']) or not re.fullmatch(r'[a-f0-9]{64}',credentials['password_sha256']): raise ValueError('invalid credentials')
    class H(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,status,data):
            raw=encode(data).encode(); self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(raw)))
            if status==401: self.send_header('WWW-Authenticate','Basic realm="KRYUK24 operator"')
            self.end_headers(); self.wfile.write(raw)
        def handle_request(self):
            self.connection.settimeout(12)
            try:
                auth=self.headers.get('Authorization','')
                user,pw=base64.b64decode(auth[6:],validate=True).decode().split(':',1) if auth.startswith('Basic ') else ('','')
                authorized=hmac.compare_digest(user,credentials['username']) and hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(),credentials['password_sha256'])
            except (ValueError,UnicodeError): authorized=False
            if not authorized: return self.reply(401,{'error':'worker authentication required'})
            if self.path not in ROUTES or ROUTES[self.path]!=self.command: return self.reply(403,{'error':'outside worker scope'})
            try:
                if self.command=='GET': return self.reply(200,queue.listing())
                if self.headers.get('Transfer-Encoding') or self.headers.get_content_type()!='application/json': raise ValueError('JSON required')
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=32768: raise ValueError('body size')
                raw=self.rfile.read(length)
                if len(raw)!=length: raise ValueError('truncated body')
                d=json.loads(raw); result=queue.apply(user,self.path.rsplit('/',1)[1],d)
                return self.reply(200,result)
            except PermissionError: return self.reply(403,{'error':'attempt or day outside scope'})
            except (ValueError,TypeError,KeyError): return self.reply(409,{'error':'invalid or conflicting request'})
            except sqlite3.Error: return self.reply(503,{'error':'database unavailable'})
        do_GET=handle_request; do_POST=handle_request; do_PUT=handle_request
        do_DELETE=handle_request; do_PATCH=handle_request; do_OPTIONS=handle_request
    return ThreadingHTTPServer(('127.0.0.1',port),H)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--db',required=True); p.add_argument('--credentials',required=True); p.add_argument('--port',type=int,default=8789)
    a=p.parse_args(); server(Queue(a.db),json.loads(Path(a.credentials).read_text()),a.port).serve_forever()
if __name__=='__main__': main()
