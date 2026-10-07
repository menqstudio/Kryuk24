import tempfile,unittest,sqlite3
from runtime import Runtime
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(self.tmp.name+'/test.db');self.data={'contact':'TEST','pickup':'A','destination':'B','vehicle':'car','test':True}
 def tearDown(self):self.tmp.cleanup()
 def test_duplicate_and_restart(self):
  a=self.r.intake(self.data,'one');self.assertEqual(a['id'],self.r.intake(self.data,'one')['id']);self.assertEqual(Runtime(self.r.path).get(a['id'])['status'],'NEW')
  with self.assertRaises(ValueError):self.r.intake(dict(self.data,vehicle='truck'),'one')
 def test_connection_closed_after_success_and_failure(self):
  with self.r.db() as c:c.execute('SELECT 1')
  with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
  with self.assertRaises(ValueError):
   with self.r.db() as failed:raise ValueError('test failure')
  with self.assertRaises(sqlite3.ProgrammingError):failed.execute('SELECT 1')
 def test_transaction_rollback(self):
  a=self.r.intake(self.data,'rollback')
  with self.assertRaises(ValueError):
   with self.r.db() as c:
    c.execute("UPDATE orders SET status='CLOSED' WHERE id=?",(a['id'],))
    raise ValueError('abort')
  self.assertEqual(self.r.get(a['id'])['status'],'NEW')
 def test_transition_guards(self):
  a=self.r.intake(self.data,'two')
  with self.assertRaises(ValueError):self.r.transition(a['id'],'CLOSED',0,{})
  self.r.transition(a['id'],'QUALIFIED',0,{})
  with self.assertRaises(ValueError):self.r.transition(a['id'],'PRICE_QUOTED',0,{'price':1,'terms':'x','confirmed_by':'dispatcher'})
  with self.assertRaises(ValueError):self.r.transition(a['id'],'PRICE_QUOTED',1,{})
 def test_full_chain(self):
  a=self.r.intake(self.data,'three')
  from runtime import NEXT
  for status in NEXT.values():
   evidence={'price':4000,'terms':'TEST','confirmed_by':'TEST dispatcher','customer_confirmation':'TEST yes','driver':'TEST','driver_acceptance':'TEST yes','time':'TEST','completion_evidence':'TEST delivered','amount':4000,'payment_evidence':'TEST receipt','trust_level':'VERIFIED','feedback_state':'TEST requested','no_open_issue':True}
   a=self.r.transition(a['id'],status,a['revision'],evidence)
  self.assertEqual(a['status'],'CLOSED')
 def test_outbound_disabled(self):
  a=self.r.intake(self.data,'four');m=self.r.draft(a['id'],'TEST recipient','TEST text');self.assertFalse(m['sending_enabled']);self.assertEqual(m['status'],'PENDING_APPROVAL')
 def test_payment_reported_not_verified(self):
  a=self.r.intake(self.data,'five')
  with self.r.db() as c:c.execute("UPDATE orders SET status='DELIVERED' WHERE id=?",(a['id'],))
  with self.assertRaises(ValueError):self.r.transition(a['id'],'PAYMENT_CONFIRMED',0,{'amount':1,'payment_evidence':'driver says','trust_level':'REPORTED'})
if __name__=='__main__':unittest.main()
