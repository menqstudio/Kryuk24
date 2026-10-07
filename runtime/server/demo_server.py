"""Loopback-only test adapter. Never deploy this server to Beget or public hosting."""
import argparse, json, secrets
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit
from runtime import Runtime, encode
ROOT=Path(__file__).parent

def server(db,port=8765):
 runtime=Runtime(db); nonce=secrets.token_urlsafe(32)
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'site'),**kw)
  def log_message(self,*a):pass
  def send(self,status,raw,kind='application/json; charset=utf-8'):
   if isinstance(raw,dict):raw=encode(raw).encode()
   self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Robots-Tag','noindex, nofollow');self.send_header('Content-Security-Policy',"default-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'none'");self.end_headers();self.wfile.write(raw)
  def do_GET(self):
   path=urlsplit(self.path).path
   if path in ('/','/index.html'):
    raw=(ROOT/'site/index.html').read_text(encoding='utf-8');raw=raw.replace('</body>',f'<script>window.KRYUK_TEST_NONCE={json.dumps(nonce)}</script><script src="/test-intake.js" defer></script><script src="/whatsapp-handoff.js" defer></script></body>');return self.send(200,raw.encode('utf-8'),'text/html; charset=utf-8')
   if path=='/whatsapp-handoff.js':return self.send(200,(ROOT/'whatsapp-handoff.js').read_bytes(),'text/javascript; charset=utf-8')
   if path=='/handoff-preview':return self.send(200,(ROOT/'handoff-preview.html').read_bytes(),'text/html; charset=utf-8')
   if path=='/test-intake.js':return self.send(200,(ROOT/'test-intake.js').read_bytes(),'text/javascript; charset=utf-8')
   if path=='/test-orders':
    raw=(ROOT/'test-orders.html').read_text(encoding='utf-8').replace('<script>',f'<script>window.KRYUK_TEST_NONCE={json.dumps(nonce)};</script><script>',1)
    return self.send(200,raw.encode('utf-8'),'text/html; charset=utf-8')
   if path=='/test-report':return self.send(200,runtime.report())
   if path.startswith('/.') or any(p.startswith('.') for p in path.split('/') if p):return self.send(404,{'error':'not found'})
   super().do_GET()
  def do_POST(self):
   if self.path not in ('/test-intake','/test-dispatch-decision','/test-match','/test-call'):return self.send(404,{'error':'not found'})
   if self.headers.get('X-Test-Nonce')!=nonce:return self.send(403,{'error':'test session required'})
   origin=self.headers.get('Origin')
   if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.send(403,{'error':'origin mismatch'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=8192:raise ValueError('invalid body size')
    data=json.loads(self.rfile.read(size))
    if not isinstance(data,dict):raise ValueError('object required')
    if self.path=='/test-match':
     order=runtime.get(data['order_id'])
     if order['data'].get('test') is not True:raise ValueError('only TEST orders allowed')
     return self.send(200,runtime.match_whatsapp(order['id'],data['external_ref'],data['evidence'],'LOCAL_TEST_OPERATOR'))
    if self.path=='/test-call':
     data.update(source='PHONE',test=True,actor='LOCAL_TEST_OPERATOR')
     return self.send(201,runtime.record_call(data,self.headers.get('Idempotency-Key')))
    if self.path=='/test-dispatch-decision':
     if set(data)!={'order_id','decision'}:raise ValueError('order_id and decision required')
     order=runtime.get(data['order_id'])
     if order['data'].get('test') is not True:raise ValueError('only TEST orders allowed')
     return self.send(200,runtime.dispatch_decision(order['id'],data['decision'],'LOCAL_TEST_OPERATOR','Local test button; not Armen confirmation'))
    allowed={'contact','pickup','destination','vehicle','message','estimate_display','request_id','channel','form_kind'}
    if set(data)-allowed:raise ValueError('unexpected fields')
    if any(not isinstance(v,str) or len(v)>4000 for v in data.values()):raise ValueError('invalid text')
    if 'request_id' in data:
     if data.get('channel') not in ('wa','tg'):raise ValueError('invalid channel')
     data['flow']='VISITOR_SENDS_WHATSAPP'
    data.update(test=True,source='LOCAL_SITE_TEST',notification_status='NOT_SENT',price_status='NOT_CONFIRMED')
    order=runtime.intake(data,self.headers.get('Idempotency-Key'))
    self.send(201,{'id':order['id'],'status':order['status'],'test':True,'notification_status':'NOT_SENT'})
   except (ValueError,TypeError,LookupError,KeyError) as e:self.send(400,{'error':str(e)})
 return ThreadingHTTPServer(('127.0.0.1',port),Handler)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',default='test-runtime.sqlite');p.add_argument('--port',type=int,default=8765);a=p.parse_args();print(f'TEST ONLY http://127.0.0.1:{a.port} — no messages sent',flush=True);server(a.db,a.port).serve_forever()
