import tempfile,unittest
from runtime import Runtime
class HandoffTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(self.tmp.name+'/db');self.data=dict(contact='NOT_PROVIDED',pickup='A',destination='B',vehicle='car',test=True,flow='VISITOR_SENDS_WHATSAPP',request_id='K24-'+'a'*32)
 def tearDown(self):self.tmp.cleanup()
 def test_browser_id_is_preserved_and_no_notification_queued(self):
  a=self.r.intake(self.data,'one');self.assertEqual(a['id'],self.data['request_id']);self.assertEqual(self.r.report()['notifications'],[]);self.assertEqual(self.r.report()['whatsapp_matches'],[])
 def test_reject_invalid_id(self):
  with self.assertRaises(ValueError):self.r.intake(dict(self.data,request_id='bad'),'two')
 def test_exact_match_and_no_lifecycle_jump(self):
  a=self.r.intake(self.data,'one');m=self.r.match_whatsapp(a['id'],'chat-message-1','Observed '+a['id'],'TEST');self.assertEqual(m,self.r.match_whatsapp(a['id'],'chat-message-1','Observed '+a['id'],'TEST'));self.assertEqual(self.r.get(a['id'])['status'],'NEW')
 def test_probable_match_rejected(self):
  a=self.r.intake(self.data,'one')
  with self.assertRaises(ValueError):self.r.match_whatsapp(a['id'],'chat-message-1','Same address','TEST')
 def test_one_message_cannot_match_two_requests(self):
  a=self.r.intake(self.data,'one');b=self.r.intake(dict(self.data,request_id='K24-'+'b'*32),'two');self.r.match_whatsapp(a['id'],'message','Observed '+a['id'],'TEST')
  with self.assertRaises(ValueError):self.r.match_whatsapp(b['id'],'message','Observed '+b['id'],'TEST')
 def test_phone_jobs_separate_idempotent_unknown_money(self):
  data=dict(date='2026-10-06',source='PHONE',outcome='COMPLETED',amount=None,evidence='TEST owner statement',actor='TEST');a=self.r.record_call(data,'call');self.assertEqual(a,self.r.record_call(data,'call'));r=self.r.report();self.assertEqual(r['orders'],[]);self.assertEqual(len(r['call_jobs']),1);self.assertIsNone(r['call_jobs'][0]['data']['amount'])
if __name__=='__main__':unittest.main()
