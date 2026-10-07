import base64, concurrent.futures, hashlib, json, os, socket, sys, tempfile, threading, unittest, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ops_work import Operations
from bro_api import Queue, server
from bro_pull import Transport, adapter_call, run_one

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.db=Path(self.tmp.name)/'test.sqlite'; self.ops=Operations(self.db)
  self.time=datetime.now(timezone.utc); self.q=Queue(self.db,lambda:self.time)
  self.ops.plan(self.q.day()); self.task=next(t for t in self.ops.report(self.q.day())['tasks'] if t['job']=='YANDEX_BUSINESS')
  self.pw=uuid.uuid4().hex; self.s=server(self.q,{'username':'bro-win','password_sha256':hashlib.sha256(self.pw.encode()).hexdigest()},0)
  threading.Thread(target=self.s.serve_forever,daemon=True).start(); self.addCleanup(self.s.server_close); self.addCleanup(self.s.shutdown)
  self.origin='http://127.0.0.1:'+str(self.s.server_port); self.auth='Basic '+base64.b64encode(('bro-win:'+self.pw).encode()).decode()
 def http(self,route,d=None,auth=None,method=None):
  req=Request(self.origin+route,None if d is None else json.dumps(d).encode(),headers={'Authorization':self.auth if auth is None else auth,'Content-Type':'application/json'},method=method)
  try:
   with urlopen(req,timeout=3) as r:return r.status,json.load(r)
  except HTTPError as e:return e.code,json.load(e)
 def payload(self,task=None):return {'task_id':(task or self.task)['id'],'day':self.q.day(),'run_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex}
 def claim(self,task=None):
  d=self.payload(task); status,r=self.http('/bro/v1/claim',d); self.assertEqual(status,200); return d,r
 def obs(self,d,r):return {**d,'request_id':uuid.uuid4().hex,'revision':r['revision'],'source':'fixture','observed_at':self.time.isoformat(),'summary':'Փորձնական արդյունք','blocked':False}
 def test_simultaneous_claim(self):
  with concurrent.futures.ThreadPoolExecutor(8) as pool:results=list(pool.map(lambda _:self.http('/bro/v1/claim',self.payload())[0],range(8)))
  self.assertEqual(results.count(200),1); self.assertEqual(results.count(409),7)
 def test_run_unique(self):
  d,r=self.claim(); other=next(t for t in self.ops.report(self.q.day())['tasks'] if t['job']=='METRICA')
  d.update(task_id=other['id'],request_id=uuid.uuid4().hex)
  self.assertEqual(self.http('/bro/v1/claim',d)[0],409)
 def test_malformed_types(self):
  d,r=self.claim(); o=self.obs(d,r); o['observed_at']={}
  self.assertEqual(self.http('/bro/v1/observe',o)[0],409)
  o=self.obs(d,r); o['task_id']={}; self.assertEqual(self.http('/bro/v1/observe',o)[0],409)
 def test_wrong_run(self):
  d,r=self.claim(); o=self.obs(d,r); o['run_id']=uuid.uuid4().hex; self.assertEqual(self.http('/bro/v1/observe',o)[0],403)
 def test_wrong_principal(self):
  d,r=self.claim()
  with self.assertRaises(PermissionError):self.q.apply('other','observe',self.obs(d,r))
 def test_expiry(self):
  d,r=self.claim(); self.time+=timedelta(seconds=601); self.assertEqual(self.http('/bro/v1/observe',self.obs(d,r))[0],403)
 def test_old_attempt_after_reclaim(self):
  d,r=self.claim(); self.time+=timedelta(seconds=601); _,nr=self.claim(); self.assertGreater(nr['revision'],r['revision'])
  self.assertEqual(self.http('/bro/v1/observe',self.obs(d,r))[0],403); self.assertEqual(self.http('/bro/v1/claim',d)[0],403)
 def test_duplicate_claim(self):
  d,r=self.claim(); self.assertEqual(self.http('/bro/v1/claim',d),(200,r))
  with self.q.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM ops_events WHERE kind='CLAIMED'").fetchone()[0],1)
 def test_duplicate_observe_and_conflict(self):
  d,r=self.claim(); o=self.obs(d,r); first=self.http('/bro/v1/observe',o); self.assertEqual(first[0],200); self.assertEqual(self.http('/bro/v1/observe',o),first)
  with self.q.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM ops_observations').fetchone()[0],1)
  o['summary']='different'; self.assertEqual(self.http('/bro/v1/observe',o)[0],409)
 def test_forbidden_routes(self):
  for route in ('/operator','/operator/work/approve','/orders','/bro/v1/plan','/bro/v1/message','/bro/v1/queue?day=2020-01-01','/bro/v1/../operator'):
   self.assertEqual(self.http(route)[0],403,route)
  self.assertEqual(self.http('/bro/v1/queue',method='DELETE')[0],403)
 def test_auth(self):
  for auth in ('','Basic broken','Basic '+base64.b64encode(b'gev:owner').decode()):self.assertEqual(self.http('/bro/v1/queue',auth=auth)[0],401)
 def test_cross_day(self):
  d,r=self.claim(); self.time+=timedelta(days=1); self.assertEqual(self.http('/bro/v1/observe',self.obs(d,r))[0],403)
  self.assertEqual(self.http('/bro/v1/claim',d)[0],403); self.assertEqual(self.http('/bro/v1/queue')[1]['tasks'],[])
  d.update(day=self.q.day(),request_id=uuid.uuid4().hex); self.assertEqual(self.http('/bro/v1/claim',d)[0],403)
 def test_local_and_blocked(self):
  local=next(t for t in self.ops.report(self.q.day())['tasks'] if t['job']=='LOCAL_LEDGER'); self.assertEqual(self.http('/bro/v1/claim',self.payload(local))[0],403)
  d,r=self.claim(); o=self.obs(d,r); o['blocked']=True; self.assertEqual(self.http('/bro/v1/observe',o)[0],200)
  d['request_id']=uuid.uuid4().hex; self.assertEqual(self.http('/bro/v1/claim',d)[0],409)
 def test_minimization(self):
  _,data=self.http('/bro/v1/queue'); self.assertFalse(any(t['job']=='LOCAL_LEDGER' for t in data['tasks']))
  for t in data['tasks']:self.assertEqual(set(t),{'id','day','job','kind','status','revision','lease_expired'})
  self.assertNotIn('observations',json.dumps(data)); self.assertNotIn('media',data)
 def report(self,ready=False):
  if ready:
   with self.q.db() as c:c.execute("UPDATE ops_tasks SET status='DONE' WHERE job!='DAILY_REPORT'")
  return next(t for t in self.ops.report(self.q.day())['tasks'] if t['job']=='DAILY_REPORT')
 def test_report_dependency(self):self.assertEqual(self.http('/bro/v1/claim',self.payload(self.report()))[0],409)
 def test_report_duplicate_and_preservation(self):
  d,r=self.claim(self.report(True)); p={**d,'request_id':uuid.uuid4().hex,'revision':r['revision'],'body':'Հաշվետվություն','reason':'Քննարկում'}
  first=self.http('/bro/v1/draft',p); self.assertEqual(first[0],200); self.assertEqual(self.http('/bro/v1/draft',p),first)
  saved=self.ops.get(d['task_id']); self.assertEqual(saved['status'],'READY_REVIEW'); self.assertEqual(saved['draft']['action'],'REPORT_DRAFT')
  with self.q.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM ops_events WHERE kind='DRAFT_READY'").fetchone()[0],1)
  Queue(self.db).listing(); self.assertEqual(self.ops.get(d['task_id']),saved)
 def test_draft_scope_extra_fields(self):
  d,r=self.claim(); p={**d,'request_id':uuid.uuid4().hex,'revision':r['revision'],'body':'test','reason':'test'}; self.assertEqual(self.http('/bro/v1/draft',p)[0],403)
  o=self.obs(d,r); o['machine']=True; self.assertEqual(self.http('/bro/v1/observe',o)[0],409)
 def test_revision_timestamp(self):
  d,r=self.claim(); o=self.obs(d,r); o['revision']-=1; self.assertEqual(self.http('/bro/v1/observe',o)[0],403)
  o=self.obs(d,r); o['observed_at']=(self.time-timedelta(seconds=60)).isoformat(); self.assertEqual(self.http('/bro/v1/observe',o)[0],409)
 def test_subprocess_environment(self):
  script=Path(self.tmp.name)/'env.py'; script.write_text('import os,json; print(json.dumps(dict(os.environ)))')
  with patch.dict(os.environ,{'BRO_PASSWORD':'SECRET','GEV_TOKEN':'SECRET','AWS_SECRET_ACCESS_KEY':'SECRET','CUSTOM_TOKEN':'SECRET'}):result=adapter_call([sys.executable,str(script)],{},3)
  for k in ('BRO_PASSWORD','GEV_TOKEN','AWS_SECRET_ACCESS_KEY','CUSTOM_TOKEN','PATH','HOME','USERPROFILE'):self.assertNotIn(k,result)
 def test_http_timeout_same_request(self):
  t=Transport('https://example.invalid','bro','pw',1)
  with patch.object(t.opener,'open',side_effect=URLError(socket.timeout())) as m:
   with self.assertRaises(ValueError):t.call('claim',{'request_id':'same'})
   self.assertEqual(m.call_count,2); self.assertEqual(m.call_args_list[0].args[0].data,m.call_args_list[1].args[0].data)
 def test_https_redirect(self):
  for origin in ('http://example.com','https://user:pw@example.com','https://example.com/operator','https://example.com/?x=1'):
   with self.assertRaises(ValueError):Transport(origin,'bro','pw')
  t=Transport('https://example.com','bro','pw')
  with patch.object(t.opener,'open',side_effect=HTTPError('https://example.com',302,'redirect',{},None)) as m:
   with self.assertRaises(ValueError):t.call('queue')
   self.assertEqual(m.call_count,1)
 def test_client_lost_response_recovery(self):
  q=self.q; q.clock=lambda:datetime.now(timezone.utc)
  class T:
   lost=True
   def call(self,route,d=None):
    if route=='queue':return q.listing()
    result=q.apply('bro-win',route,d)
    if route=='observe' and self.lost:self.lost=False; raise ValueError('lost')
    return result
  t=T(); journal=Path(self.tmp.name)/'run.json'; calls=[]
  def adapter(req):
   calls.append(1);return {'task_id':req['task']['id'],'status':'DONE','source':'fixture','observed_at':datetime.now(timezone.utc).isoformat(),'summary':'Փորձ'}
  with self.assertRaises(ValueError):run_one(t,journal,adapter)
  self.assertEqual(run_one(t,journal,adapter)['status'],'DONE'); self.assertEqual(len(calls),1)
  with q.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM ops_observations').fetchone()[0],1)
 def test_adapter_disabled(self):
  with self.assertRaises(ValueError):run_one(None,'unused')
 def test_missing_db(self):
  with self.assertRaises(ValueError):Queue(Path(self.tmp.name)/'missing')
if __name__=='__main__':unittest.main()
