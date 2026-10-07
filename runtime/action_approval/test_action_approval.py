import concurrent.futures
import copy
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from runtime import Runtime
from action_approval import ApprovalStore, ApprovalPrincipal, digest


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(self.tmp.name + '/db')
        self.time = datetime(2026, 10, 8, tzinfo=timezone.utc)
        self.s = ApprovalStore(self.r, 'gev', ['REPORT_SEND'], lambda: self.time)
        self.preparer = ApprovalPrincipal('claude', 'PREPARER')
        self.owner = ApprovalPrincipal('gev', 'APPROVER')
        self.executor = ApprovalPrincipal('worker', 'EXECUTOR')
        self.b = dict(action='REPORT_SEND', account='SAMPLE-account', target='SAMPLE-recipient',
                      payload={'body':'SAMPLE report'}, assets=[{'id':'SAMPLE-asset','sha256':'a'*64}],
                      amount=None, inputs={'SAMPLE-task-revisions':digest({'task':1})},
                      expires_at=(self.time + timedelta(hours=1)).isoformat(), test=True)

    def tearDown(self):self.tmp.cleanup()
    def draft(self):return self.s.draft(self.preparer, 'sample', self.b)
    def approve(self):
        d=self.draft();return self.s.decide(d['id'], self.owner, d['digest'], 'APPROVED', self.b['inputs'], 'SAMPLE user decision')
    def claim(self, did, key='sample-execution'):
        return self.s.claim(did, self.executor, key, self.b, self.b['inputs'])

    def test_immutable_contract_and_replay(self):
        d=self.draft();self.assertEqual(d,self.draft())
        with self.r.db() as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE action_approval_drafts SET bundle='{}'")
        self.b['target']='other'
        with self.assertRaises(ValueError):self.draft()

    def test_only_gevs_trusted_role_can_decide(self):
        d=self.draft()
        for p in (self.preparer,self.executor,ApprovalPrincipal('other','APPROVER')):
            with self.assertRaises(PermissionError):self.s.decide(d['id'],p,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        with self.assertRaises(ValueError):self.claim(d['id'])

    def test_stale_at_approval_is_terminal(self):
        d=self.draft()
        changed={'SAMPLE-task-revisions':digest({'task':2})}
        out=self.s.decide(d['id'],self.owner,d['digest'],'APPROVED',changed,'SAMPLE')
        self.assertEqual(out['status'],'STALE')
        with self.assertRaises(ValueError):self.claim(d['id'])

    def test_expiry_at_approval_boundary(self):
        d=self.draft();self.time+=timedelta(hours=1)
        out=self.s.decide(d['id'],self.owner,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        self.assertEqual(out['status'],'EXPIRED')

    def test_full_binding_prevents_changed_execution(self):
        d=self.approve()
        for key,value in [('account','other'),('target','other'),('payload',{'body':'changed'}),
                          ('assets',[]),('amount',{'currency':'RUB','kopecks':100}),('test',False),
                          ('expires_at',(self.time+timedelta(hours=2)).isoformat())]:
            b=copy.deepcopy(self.b);b[key]=value
            with self.assertRaises(ValueError):self.s.claim(d['id'],self.executor,'x',b,b['inputs'])
        self.assertEqual(self.s.inspect(d['id'],self.owner)['status'],'APPROVED')

    def test_stale_and_expired_before_reservation(self):
        d=self.approve()
        out=self.s.claim(d['id'],self.executor,'x',self.b,{'SAMPLE-task-revisions':'b'*64})
        self.assertEqual(out['status'],'STALE');self.assertFalse(out['new_reservation'])
        b=copy.deepcopy(self.b);d=self.s.draft(self.preparer,'second',b)
        self.s.decide(d['id'],self.owner,d['digest'],'APPROVED',b['inputs'],'SAMPLE')
        self.time+=timedelta(hours=1)
        self.assertEqual(self.claim(d['id'])['status'],'EXPIRED')

    def test_reject_and_revoke_block_execution(self):
        d=self.draft();self.s.decide(d['id'],self.owner,d['digest'],'REJECTED',self.b['inputs'],'SAMPLE')
        with self.assertRaises(ValueError):self.claim(d['id'])
        d=self.s.draft(self.preparer,'other',self.b)
        self.s.decide(d['id'],self.owner,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        self.s.revoke(d['id'],self.owner,'SAMPLE revoked')
        with self.assertRaises(ValueError):self.claim(d['id'])

    def test_concurrent_one_reservation_and_no_second_grant(self):
        d=self.approve()
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results=list(pool.map(lambda _:self.claim(d['id']),range(4)))
        self.assertEqual(sum(x['new_reservation'] for x in results),1)
        self.assertTrue(all(x['execution_result']=='UNKNOWN' for x in results))
        with self.assertRaises(ValueError):self.claim(d['id'],'another')
        with self.assertRaises(ValueError):self.s.revoke(d['id'],self.owner,'SAMPLE')
        self.assertEqual([e['kind'] for e in self.s.inspect(d['id'],self.owner)['history']],['DRAFTED','APPROVED','RESERVED'])

    def test_restart_replay_is_reconciliation_only(self):
        d=self.approve();self.claim(d['id'])
        self.s=ApprovalStore(Runtime(self.r.path),'gev',['REPORT_SEND'],lambda:self.time)
        self.assertFalse(self.claim(d['id'])['new_reservation'])

    def test_fail_closed_types_allowlist_digest(self):
        for key,value in [('amount',{'currency':'RUB','kopecks':True}),('test','false'),
                          ('expires_at','2026-10-08T01:00:00'),('inputs',{}),('payload',{'x':float('nan')})]:
            b=copy.deepcopy(self.b);b[key]=value
            with self.assertRaises(ValueError):self.s.draft(self.preparer,'bad',b)
        deny=ApprovalStore(self.r,'gev')
        with self.assertRaises(PermissionError):deny.draft(self.preparer,'deny',self.b)
        d=self.draft()
        with self.assertRaises(ValueError):self.s.decide(d['id'],self.owner,'0'*64,'APPROVED',self.b['inputs'],'SAMPLE')

    def test_audit_failure_rolls_back_approval_and_reservation(self):
        d=self.draft()
        with patch.object(self.s,'event',side_effect=RuntimeError('SAMPLE failure')):
            with self.assertRaises(RuntimeError):self.s.decide(d['id'],self.owner,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        self.assertEqual(self.s.inspect(d['id'],self.owner)['status'],'PENDING')
        d=self.approve()
        with patch.object(self.s,'event',side_effect=RuntimeError('SAMPLE failure')):
            with self.assertRaises(RuntimeError):self.claim(d['id'])
        self.assertEqual(self.s.inspect(d['id'],self.owner)['status'],'APPROVED')

if __name__=='__main__':unittest.main()
