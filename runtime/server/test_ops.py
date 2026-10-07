import unittest,tempfile,json,threading
from pathlib import Path
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from ops_work import Operations
from runtime import now
from ops_views import dashboard
from ops_local import run_local
import test_secure_server as http_fixture

class OperationsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.ops=Operations(self.root/'db');self.day='2026-10-07';self.ops.plan(self.day)
 def tearDown(self):self.tmp.cleanup()
 def task(self,job):return next(t for t in self.ops.report()['tasks'] if t['job']==job)['id']
 def draft(self):
  tid=self.task('DAILY_REPORT');self.ops.claim(tid,'worker');return self.ops.draft(tid,'worker',dict(action='REPORT_DRAFT',account='TEST',destination='Local file',body='Հաշվետվություն',reason='Review only'))
 def test_plan_persists_and_is_idempotent(self):
  self.assertEqual(self.ops.plan(self.day)['added'],0);self.assertEqual(len(Operations(self.root/'db').report()['tasks']),10)
 def test_parallel_claim_one_owner(self):
  tid=self.task('AVITO')
  def claim(worker):
   try:self.ops.claim(tid,worker);return True
   except ValueError:return False
  with ThreadPoolExecutor(2) as ex:self.assertEqual(sum(ex.map(claim,['one','two'])),1)
 def test_wrong_worker_and_machine_browser_evidence_rejected(self):
  tid=self.task('AVITO');self.ops.claim(tid,'one')
  for worker,machine in [('two',False),('one',True)]:
   with self.assertRaises(ValueError):self.ops.observe(tid,worker,'TEST',now(),'TEST',machine=machine)
  self.assertEqual(self.ops.get(tid)['status'],'CLAIMED')
 def test_missing_timezone_rejected(self):
  tid=self.task('AVITO');self.ops.claim(tid,'one')
  with self.assertRaises(ValueError):self.ops.observe(tid,'one','TEST','2026-10-07T00:00:00','TEST')
 def test_blocked_is_not_done_and_can_retry(self):
  tid=self.task('AVITO');self.ops.claim(tid,'one');self.ops.observe(tid,'one','TEST',now(),'No account connector',blocked=True)
  self.assertEqual(self.ops.get(tid)['status'],'BLOCKED');self.ops.claim(tid,'two')
 def test_expired_read_lease_reclaimed(self):
  tid=self.task('AVITO');self.ops.claim(tid,'one')
  with self.ops.runtime.db() as c:c.execute("UPDATE ops_tasks SET lease_until='2020-01-01T00:00:00+00:00' WHERE id=?",(tid,))
  self.assertEqual(self.ops.claim(tid,'two')['worker'],'two')
 def test_approval_exact_digest_and_explicit_reference(self):
  d=self.draft()
  for digest,actor,reference in [('wrong','GEV','yes'),(d['digest'],'AI','yes'),(d['digest'],'GEV','')]:
   with self.assertRaises(ValueError):self.ops.approve(d['id'],digest,actor,reference)
  self.assertEqual(self.ops.approve(d['id'],d['digest'],'GEV','TEST explicit approval')['status'],'APPROVED')
  self.assertEqual(self.ops.runtime.report()['notifications'],[])
 def test_revision_invalidates_old_approval(self):
  d=self.draft();self.ops.approve(d['id'],d['digest'],'GEV','TEST');self.ops.revise(d['id'],'Changed content')
  with self.assertRaises(ValueError):self.ops.finish_approved(d['id'],d['digest'],'TEST','TEST')
  with self.ops.runtime.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM ops_approvals').fetchone()[0],1)
 def test_result_is_manual_evidence(self):
  d=self.draft();self.ops.approve(d['id'],d['digest'],'GEV','TEST');self.ops.finish_approved(d['id'],d['digest'],'TEST local preview','Viewed file')
  self.assertEqual(self.ops.report()['tasks'][next(i for i,t in enumerate(self.ops.report()['tasks']) if t['id']==d['id'])]['observations'][0]['trust'],'OPERATOR_REPORTED')
 def test_escaped_html_and_offline_report(self):
  tid=self.task('AVITO');self.ops.claim(tid,'one');self.ops.observe(tid,'one','TEST',now(),'<script>alert(1)</script>')
  page=dashboard(self.ops.report(),False);self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
 def test_media_original_review_and_tamper_guard(self):
  image=self.root/'synthetic.png';image.write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC TEST SIGNATURE ONLY')
  original=self.ops.media.original(image,'Synthetic fixture','TEST')
  self.assertEqual(self.ops.media.original(image,'Synthetic fixture','TEST')['id'],original['id'])
  with self.assertRaises(ValueError):self.ops.media.prepared(original['id'],image,'TEST',False)
  asset=self.ops.media.prepared(original['id'],image,'Synthetic reviewed fixture',True)
  tid=self.task('MEDIA_INBOX');self.ops.claim(tid,'worker');d=self.ops.draft(tid,'worker',dict(action='PHOTO_BATCH',account='TEST',destination='Preview only',body='TEST',reason='TEST',assets=[{'id':asset['id'],'sha256':asset['digest']}]))
  path=Path(self.ops.media.verify(asset['id'])['local_path']);path.chmod(0o600);path.write_bytes(b'CHANGED')
  with self.assertRaises(ValueError):self.ops.approve(tid,d['digest'],'GEV','TEST')
 def test_non_image_rejected(self):
  path=self.root/'x';path.write_text('not an image')
  with self.assertRaises(ValueError):self.ops.media.original(path,'TEST','TEST')
 def test_local_worker_leaves_browser_jobs_pending(self):
  result=run_local(self.ops,self.day,1);self.assertFalse(result['browser_jobs_executed'])
  self.assertEqual(self.ops.get(self.task('RUNTIME_HEALTH'))['status'],'BLOCKED');self.assertEqual(self.ops.get(self.task('LOCAL_LEDGER'))['status'],'DONE');self.assertEqual(self.ops.get(self.task('AVITO'))['status'],'PENDING')
 def test_database_recovery_preserves_queue(self):
  from recovery import restore
  import sqlite3
  snapshot=self.root/'snapshot'
  with closing(sqlite3.connect(snapshot)) as dst:
   with self.ops.runtime.db() as src:src.backup(dst)
  with self.assertRaises(sqlite3.ProgrammingError):dst.execute('SELECT 1')
  restore(snapshot,self.root/'restored');self.assertEqual(len(Operations(self.root/'restored').report()['tasks']),10)

class WorkHTTPTests(unittest.TestCase):
 setUp=http_fixture.SecureTests.setUp;tearDown=http_fixture.SecureTests.tearDown;request=http_fixture.SecureTests.request
 def test_private_work_and_media_routes(self):
  import urllib.error
  for path in ['/operator/work','/operator/work/report','/operator/media/ASSET-'+('a'*32)]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.request(path)
   self.assertEqual(e.exception.code,401)
  self.assertEqual(self.request('/operator/work',auth=True).status,200)
 def test_work_post_origin_and_auth(self):
  import urllib.error
  for auth,origin,code in [(False,None,401),(True,'https://evil.example',403)]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.request('/operator/work/plan',{},auth,origin)
   self.assertEqual(e.exception.code,code)
  self.assertEqual(json.load(self.request('/operator/work/plan',{},True))['added'],10)
  self.assertEqual(json.load(self.request('/operator/work/plan',{},True))['added'],0)
  report=json.load(self.request('/operator/work/report',auth=True));tid=report['tasks'][0]['id']
  self.assertEqual(json.load(self.request('/operator/work/claim',{'task_id':tid},True))['status'],'CLAIMED')

class OperationsDailyTests(unittest.TestCase):
 def test_daily_is_idempotent_and_full_backup_preserves_media(self):
  from ops_daily import run
  from ops_backup import backup
  import tarfile
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ops=Operations(root/'db');image=root/'synthetic.png';image.write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC ONLY')
   original=ops.media.original(image,'TEST fixture','TEST permission');ops.media.prepared(original['id'],image,'Synthetic review',True)
   first=run(root/'db',root/'reports','2026-10-07');second=run(root/'db',root/'reports','2026-10-07')
   self.assertEqual((first['added'],second['added']),(10,0));self.assertFalse(first['report_sent']);self.assertTrue(Path(first['report']).is_file())
   result=backup(root/'db',root/'backup.tar.gz');self.assertEqual(result['media_files'],2)
   with tarfile.open(root/'backup.tar.gz') as archive:
    self.assertEqual(len(archive.getnames()),3);self.assertIn('runtime.sqlite',archive.getnames())
    restored=root/'restored.sqlite';restored.write_bytes(archive.extractfile('runtime.sqlite').read())
    restore_ops=Operations(restored);self.assertEqual(len(restore_ops.report()['tasks']),10)
    for row in restore_ops.media.report()['originals']+restore_ops.media.report()['assets']:
     target=root/'media'/row['path'];self.assertEqual(archive.extractfile('media/'+row['path']).read(),target.read_bytes())
   with self.assertRaises(ValueError):backup(root/'db',root/'backup.tar.gz')


class BackupConnectionTests(unittest.TestCase):
 def test_backup_connections_closed_on_success(self):
  self.check_connections(False)
 def test_backup_connections_closed_on_error(self):
  self.check_connections(True)
 def check_connections(self,fail):
  import sqlite3
  from unittest.mock import patch
  from ops_backup import backup
  real_connect=sqlite3.connect;connections=[]
  class TrackedConnection(sqlite3.Connection):
   def execute(self,sql,*args,**kwargs):
    if fail and sql=='PRAGMA integrity_check':raise sqlite3.OperationalError('synthetic integrity read failure')
    return super().execute(sql,*args,**kwargs)
  def tracked(path,*args,**kwargs):
   if Path(str(path)).name=='runtime.sqlite':
    connection=real_connect(path,*args,factory=TrackedConnection,**kwargs);connections.append(connection);return connection
   return real_connect(path,*args,**kwargs)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);Operations(root/'db')
   with patch('ops_backup.sqlite3.connect',side_effect=tracked):
    if fail:
     with self.assertRaises(sqlite3.OperationalError):backup(root/'db',root/'archive.tar.gz')
    else:backup(root/'db',root/'archive.tar.gz')
   self.assertEqual(len(connections),2)
   for connection in connections:
    with self.assertRaises(sqlite3.ProgrammingError):connection.execute('SELECT 1')
   self.assertEqual(list(root.glob('tmp*')),[])
   if fail:self.assertFalse((root/'archive.tar.gz').exists())

if __name__=='__main__':unittest.main()
