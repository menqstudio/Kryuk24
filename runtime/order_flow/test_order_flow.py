import concurrent.futures
import sqlite3
import tempfile
import unittest
from runtime import Runtime
from order_flow import OrderFlow, Principal


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(self.tmp.name + '/db')
        self.flow = OrderFlow(self.r)
        self.owner = Principal('dispatcher-1', 'DISPATCHER')
        self.partner = Principal('partner-1', 'PARTNER')
        self.oid = self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car',test=True), 'sample')['id']
        self.flow.adopt(self.oid, self.owner, 0)
        self.counter = 0

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, action, **payload):
        self.counter += 1
        return self.flow.command(self.oid, self.owner, str(self.counter), self.flow.get(self.oid)['revision'], action, payload)

    def confirmed(self):
        self.command('QUALIFY', evidence='SAMPLE qualification')
        self.command('QUOTE', amount=500000,terms='SAMPLE agreed scope',evidence='SAMPLE quote')
        self.command('CONFIRM_PRICE',price_version=1,evidence='SAMPLE customer yes')

    def delivered(self):
        self.confirmed()
        self.command('ASSIGN',driver='partner-1',acceptance='SAMPLE acceptance')
        for status in ('EN_ROUTE','ARRIVED','LOADED','TRANSPORTING','DELIVERED'):
            self.command('PROGRESS',status=status,evidence='SAMPLE '+status)

    def paid(self):
        self.delivered()
        self.command('VERIFY_JOB', evidence='SAMPLE customer delivery attestation')
        self.command('VERIFY_PAYMENT',amount=500000,price_version=1,evidence='SAMPLE payment evidence')

    def test_full_flow_restart_and_closure(self):
        self.paid()
        self.command('SETTLE_COMMISSION',amount=100000,price_version=1,evidence='SAMPLE settlement')
        self.command('FEEDBACK',state='REQUESTED',evidence='SAMPLE feedback request')
        self.command('CLOSE',evidence='SAMPLE dispatcher closure')
        saved=OrderFlow(Runtime(self.r.path)).get(self.oid)
        self.assertEqual(saved['status'],'CLOSED')
        self.assertEqual(saved['owner'],'dispatcher-1')
        self.assertEqual(saved['verification'],'TEST_ONLY')
        with self.assertRaises(ValueError):self.command('OPEN_ISSUE',evidence='SAMPLE')

    def test_job_done_is_not_closed(self):
        self.delivered()
        with self.assertRaises(ValueError):self.command('CLOSE',evidence='SAMPLE')
        self.assertEqual(self.flow.get(self.oid)['status'],'DELIVERED')

    def test_partner_cannot_set_price_payment_or_close(self):
        self.delivered()
        before=self.flow.get(self.oid)
        result=self.flow.command(self.oid,self.partner,'report',before['revision'],'PARTNER_REPORT',
                                 dict(kind='PRICE',amount=700000,evidence='SAMPLE partner says'))
        self.assertEqual(result['price'],500000)
        self.assertEqual(result['commission_due'],100000)
        for action in ('REPRICE','VERIFY_PAYMENT','CLOSE'):
            with self.assertRaises(PermissionError):self.flow.command(self.oid,self.partner,action,result['revision'],action,{})
        with self.r.db() as c:
            event=c.execute("SELECT data FROM events WHERE kind='DISPATCH_PARTNER_REPORT'").fetchone()
            self.assertIn('TEST_ONLY',event['data'])

    def test_reprice_customer_confirmation_and_current_version(self):
        self.delivered()
        with self.assertRaises(ValueError):self.command('REPRICE',amount=700000,terms='SAMPLE',evidence='SAMPLE',customer_confirmation='')
        self.command('REPRICE',amount=700000,terms='SAMPLE',evidence='SAMPLE',customer_confirmation='SAMPLE customer yes')
        self.assertEqual(self.flow.get(self.oid)['commission_due'],140000)
        self.command('VERIFY_JOB',evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command('VERIFY_PAYMENT',amount=700000,price_version=1,evidence='SAMPLE')
        self.command('VERIFY_PAYMENT',amount=700000,price_version=2,evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command('REPRICE',amount=800000,terms='SAMPLE',evidence='SAMPLE',customer_confirmation='SAMPLE')

    def test_payment_and_commission_must_match(self):
        self.delivered()
        with self.assertRaises(ValueError):self.command('VERIFY_PAYMENT',amount=500000,price_version=1,evidence='SAMPLE')
        self.command('VERIFY_JOB',evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command('VERIFY_PAYMENT',amount=400000,price_version=1,evidence='SAMPLE')
        self.command('VERIFY_PAYMENT',amount=500000,price_version=1,evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command('SETTLE_COMMISSION',amount=99999,price_version=1,evidence='SAMPLE')

    def test_issue_blocks_close_and_resolution_is_audited(self):
        self.paid()
        self.command('SETTLE_COMMISSION',amount=100000,price_version=1,evidence='SAMPLE')
        self.command('FEEDBACK',state='DECLINED',evidence='SAMPLE')
        self.command('OPEN_ISSUE',evidence='SAMPLE complaint')
        with self.assertRaises(ValueError):self.command('CLOSE',evidence='SAMPLE')
        self.command('RESOLVE_ISSUE',evidence='SAMPLE resolved')
        self.assertEqual(self.command('CLOSE',evidence='SAMPLE')['status'],'CLOSED')

    def test_idempotency_and_transaction_rollback(self):
        a=self.flow.command(self.oid,self.owner,'same',0,'QUALIFY',{'evidence':'SAMPLE'})
        self.assertEqual(a,self.flow.command(self.oid,self.owner,'same',0,'QUALIFY',{'evidence':'SAMPLE'}))
        with self.assertRaises(ValueError):self.flow.command(self.oid,self.owner,'same',0,'QUALIFY',{'evidence':'other'})
        before=self.flow.get(self.oid)
        with self.assertRaises(ValueError):self.command('QUOTE',amount=500000,terms='',evidence='SAMPLE')
        self.assertEqual(before,self.flow.get(self.oid))

    def test_two_concurrent_writers_only_one_wins(self):
        def write(key):
            try:return self.flow.command(self.oid,self.owner,key,0,'QUALIFY',{'evidence':'SAMPLE'})['revision']
            except ValueError:return 'stale'
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(write,['a','b']))
        self.assertCountEqual(results,[1,'stale'])

    def test_legacy_transition_cannot_bypass_managed_guard(self):
        with self.assertRaises(sqlite3.IntegrityError):self.r.transition(self.oid,'QUALIFIED',0,{})
        self.assertEqual(self.flow.get(self.oid)['revision'],0)
        other=self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car',test=True),'legacy')['id']
        self.assertEqual(self.r.transition(other,'QUALIFIED',0,{})['status'],'QUALIFIED')

    def test_owner_and_partner_isolation(self):
        for principal in (Principal('other','DISPATCHER'),Principal('partner-1','PARTNER'),Principal('ai','AI')):
            with self.assertRaises(PermissionError):self.flow.command(self.oid,principal,'x',0,'QUALIFY',{'evidence':'SAMPLE'})

    def test_eta_call_and_strict_input(self):
        with self.assertRaises(ValueError):self.command('ETA',time='2026-10-08T12:00:00',evidence='SAMPLE')
        self.command('ETA',time='2026-10-08T12:00:00+03:00',evidence='SAMPLE')
        self.command('CALL_STATUS',state='REACHED',evidence='SAMPLE')
        self.command('QUALIFY',evidence='SAMPLE')
        for amount in (True,False,0,-1,1.5,'500000'):
            with self.assertRaises(ValueError):self.command('QUOTE',amount=amount,terms='SAMPLE',evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command('QUOTE',amount=500000,terms='SAMPLE',evidence='SAMPLE',trust='VERIFIED')

    def test_no_guess_for_existing_nonnew_or_missing_test(self):
        other=self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car',test=True),'old')['id']
        self.r.transition(other,'QUALIFIED',0,{})
        with self.assertRaises(ValueError):self.flow.adopt(other,self.owner,1)
        ambiguous=self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car'),'ambiguous')['id']
        with self.assertRaises(ValueError):self.flow.adopt(ambiguous,self.owner,0)

if __name__ == '__main__':
    unittest.main()
