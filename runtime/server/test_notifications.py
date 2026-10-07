import tempfile,unittest
from runtime import Runtime
class NotificationTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(self.tmp.name+'/db.sqlite');self.data=dict(contact='TEST',pickup='A',destination='B',vehicle='car',test=True)
 def tearDown(self):self.tmp.cleanup()
 def test_queue_is_durable_unique_and_blocked(self):
  a=self.r.intake(self.data,'one');self.r.intake(self.data,'one');r=Runtime(self.r.path).report();self.assertEqual(len(r['notifications']),1);n=r['notifications'][0];self.assertEqual(n['order_id'],a['id']);self.assertEqual(n['status'],'BLOCKED_NO_CONNECTOR');self.assertEqual(n['attempts'],0);self.assertIn('НЕ ВЫЕЗЖАТЬ',n['body']);self.assertEqual(r['dispatch_decisions'],[])
 def test_acceptance_is_not_customer_confirmation(self):
  a=self.r.intake(self.data,'two');d=self.r.dispatch_decision(a['id'],'ACCEPTED','TEST','test click');self.assertEqual(d['trust_level'],'TEST_ONLY');self.assertEqual(self.r.get(a['id'])['status'],'NEW');self.assertEqual(self.r.report()['notifications'][0]['status'],'BLOCKED_NO_CONNECTOR')
 def test_decision_is_idempotent_and_cannot_be_overwritten(self):
  a=self.r.intake(self.data,'three');d=self.r.dispatch_decision(a['id'],'DECLINED','TEST','test click');self.assertEqual(d,self.r.dispatch_decision(a['id'],'DECLINED','TEST','test click'))
  with self.assertRaises(ValueError):self.r.dispatch_decision(a['id'],'ACCEPTED','TEST','test click')
 def test_non_test_report_is_not_verified(self):
  data=dict(self.data,test=False);a=self.r.intake(data,'four');d=self.r.dispatch_decision(a['id'],'ACCEPTED','Gev','Armen said yes');self.assertEqual(d['trust_level'],'OPERATOR_REPORTED')
 def test_decision_requires_evidence(self):
  a=self.r.intake(self.data,'five')
  with self.assertRaises(ValueError):self.r.dispatch_decision(a['id'],'ACCEPTED','TEST','')
if __name__=='__main__':unittest.main()
