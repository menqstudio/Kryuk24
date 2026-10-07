import tempfile, unittest, sqlite3
from pathlib import Path
from runtime import Runtime
from recovery import restore
from report_html import render
class RecoveryReportTests(unittest.TestCase):
 def test_restore_preserves_data_and_refuses_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'source.sqlite';dst=Path(d)/'restored.sqlite'
   r=Runtime(str(src));r.record_call(dict(date='2026-10-06',outcome='COMPLETED',actor='test',evidence='reported',source='PHONE'),'one')
   restore(src,dst)
   self.assertEqual(len(Runtime(str(dst)).report()['call_jobs']),1)
   with self.assertRaises(ValueError):restore(src,dst)
 def test_invalid_snapshot_rejected_without_target(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'other.sqlite';dst=Path(d)/'new.sqlite'
   c=sqlite3.connect(src);c.execute('create table unrelated(x)');c.close()
   with self.assertRaises(ValueError):restore(src,dst)
   self.assertFalse(dst.exists())
 def test_report_excludes_tests_and_customer_details(self):
  report={'orders':[{'id':'secret-id','data':{'test':True,'contact':'PRIVATE PHONE'}}], 'whatsapp_matches':[], 'call_jobs':[{'data':{'test':True,'outcome':'COMPLETED'}},{'data':{'outcome':'COMPLETED','evidence':'PRIVATE ADDRESS'}}]}
  content=render(report)
  self.assertNotIn('PRIVATE',content);self.assertNotIn('secret-id',content)
  self.assertIn('<strong>1</strong>',content);self.assertIn('Тестовые записи исключены',content)
