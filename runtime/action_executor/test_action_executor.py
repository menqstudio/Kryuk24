import concurrent.futures
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from runtime import Runtime
from action_approval import ApprovalStore, ApprovalPrincipal, digest
from action_executor import SimulationExecutor, SimulationAdapter


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(self.tmp.name+'/db')
        self.time=datetime(2026,10,8,tzinfo=timezone.utc)
        self.a=ApprovalStore(self.r,'gev',['REPORT_SEND'],lambda:self.time)
        self.owner=ApprovalPrincipal('gev','APPROVER');self.p=ApprovalPrincipal('worker','EXECUTOR')
        self.preparer=ApprovalPrincipal('claude','PREPARER')
        self.b=dict(action='REPORT_SEND',account='SAMPLE account',target='SAMPLE target',payload={'body':'SAMPLE'},
                    assets=[],amount=None,inputs={'SAMPLE task':digest({'revision':1})},
                    expires_at=(self.time+timedelta(hours=1)).isoformat(),test=True)
        self.adapter=SimulationAdapter(self.r,['REPORT_SEND']);self.e=SimulationExecutor(self.a,self.adapter)
        self.d=self.a.draft(self.preparer,'SAMPLE draft',self.b)
        self.a.decide(self.d['id'],self.owner,self.d['digest'],'APPROVED',self.b['inputs'],'SAMPLE approval')

    def tearDown(self):self.tmp.cleanup()
    def execute(self):return self.e.execute(self.d['id'],self.p,'SAMPLE execution',self.b,self.b['inputs'])
    def reconcile(self):return self.e.reconcile(self.d['id'],self.p,'SAMPLE execution',self.b)

    def test_success_readback_and_replay_no_second_attempt(self):
        with patch.object(self.adapter,'perform',wraps=self.adapter.perform) as fn:
            out=self.execute();self.assertEqual(out['status'],'SIMULATION_VERIFIED')
            self.assertEqual(out,self.execute());self.assertEqual(fn.call_count,1)
        self.assertEqual(out['trust'],'SIMULATED_ONLY');self.assertFalse(out['external_execution_enabled'])
        self.assertFalse(out['retry_allowed'])

    def test_response_lost_after_effect_reconciles_without_retry(self):
        original=self.adapter.perform
        def lost(k,b):original(k,b);raise TimeoutError('SAMPLE secret must not leak')
        with patch.object(self.adapter,'perform',side_effect=lost) as fn:
            self.assertEqual(self.execute()['status'],'UNKNOWN')
            self.assertEqual(self.execute()['status'],'UNKNOWN');self.assertEqual(fn.call_count,1)
        self.assertEqual(self.reconcile()['status'],'SIMULATION_VERIFIED')
        history=self.e.inspect(self.d['id'],self.owner)['history']
        self.assertNotIn('secret',str(history))

    def test_no_effect_unknown_does_not_blindly_retry(self):
        with patch.object(self.adapter,'perform',side_effect=ConnectionError('SAMPLE')):
            self.assertEqual(self.execute()['status'],'UNKNOWN')
        with patch.object(self.adapter,'perform',side_effect=AssertionError('must never retry')):
            self.assertEqual(self.execute()['status'],'UNKNOWN')
            self.assertEqual(self.reconcile()['status'],'UNKNOWN')

    def test_expired_stale_and_revoked_never_perform(self):
        self.time+=timedelta(hours=1)
        with patch.object(self.adapter,'perform',side_effect=AssertionError('forbidden')):
            self.assertEqual(self.execute()['status'],'EXPIRED')
        # New draft with future deadline, but changed source facts.
        self.b['expires_at']=(self.time+timedelta(hours=1)).isoformat()
        d=self.a.draft(self.preparer,'SAMPLE second',self.b)
        self.a.decide(d['id'],self.owner,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        out=self.e.execute(d['id'],self.p,'other',self.b,{'SAMPLE task':'f'*64})
        self.assertEqual(out['status'],'STALE')
        d=self.a.draft(self.preparer,'SAMPLE third',self.b)
        self.a.decide(d['id'],self.owner,d['digest'],'APPROVED',self.b['inputs'],'SAMPLE')
        self.a.revoke(d['id'],self.owner,'SAMPLE')
        with self.assertRaises(ValueError):self.e.execute(d['id'],self.p,'third',self.b,self.b['inputs'])

    def test_no_real_actions_even_with_approval(self):
        b=copy.deepcopy(self.b);b['test']=False
        d=self.a.draft(self.preparer,'SAMPLE real-contract-denial',b)
        self.a.decide(d['id'],self.owner,d['digest'],'APPROVED',b['inputs'],'SAMPLE')
        with self.assertRaises(PermissionError):self.e.execute(d['id'],self.p,'real',b,b['inputs'])
        self.assertEqual(self.a.inspect(d['id'],self.owner)['status'],'APPROVED')

    def test_response_mismatch_is_not_success(self):
        original=self.adapter.perform
        def forged(k,b):out=original(k,b);out['bundle_digest']='0'*64;return out
        with patch.object(self.adapter,'perform',side_effect=forged):
            self.assertEqual(self.execute()['status'],'UNKNOWN')
        self.assertEqual(self.reconcile()['status'],'SIMULATION_VERIFIED')

    def test_concurrent_execute_one_effect(self):
        with patch.object(self.adapter,'perform',wraps=self.adapter.perform) as fn:
            with concurrent.futures.ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:self.execute(),range(4)))
            self.assertEqual(fn.call_count,1)
        self.assertTrue(all(x['status'] in ('UNKNOWN','SIMULATION_VERIFIED') for x in results))
        self.assertEqual(self.reconcile()['status'],'SIMULATION_VERIFIED')
        with self.r.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM executor_simulated_effects').fetchone()[0],1)

    def test_reserved_without_journal_recovery_never_executes(self):
        self.a.claim(self.d['id'],self.p,'SAMPLE execution',self.b,self.b['inputs'])
        with patch.object(self.adapter,'perform',side_effect=AssertionError('must not perform')):
            self.assertEqual(self.execute()['status'],'UNKNOWN')
            self.assertEqual(self.reconcile()['status'],'UNKNOWN')

    def test_restart_after_effect_before_verification_commit(self):
        event=self.e.event
        def failed(c,did,kind,data):
            if kind=='SIMULATION_VERIFIED':raise RuntimeError('SAMPLE audit crash')
            return event(c,did,kind,data)
        with patch.object(self.e,'event',side_effect=failed):self.assertEqual(self.execute()['status'],'UNKNOWN')
        r=Runtime(self.r.path);a=ApprovalStore(r,'gev',['REPORT_SEND'],lambda:self.time)
        self.e=SimulationExecutor(a,SimulationAdapter(r,['REPORT_SEND']))
        self.assertEqual(self.reconcile()['status'],'SIMULATION_VERIFIED')

    def test_actor_payload_and_key_isolation(self):
        wrong=copy.deepcopy(self.b);wrong['target']='wrong'
        with self.assertRaises(ValueError):self.e.execute(self.d['id'],self.p,'x',wrong,wrong['inputs'])
        self.execute()
        with self.assertRaises(PermissionError):self.e.reconcile(self.d['id'],ApprovalPrincipal('other','EXECUTOR'),'SAMPLE execution',self.b)
        with self.assertRaises(PermissionError):self.e.inspect(self.d['id'],self.preparer)
        with self.assertRaises(PermissionError):self.e.execute(self.d['id'],self.p,'other',self.b,self.b['inputs'])

    def test_journal_failure_before_perform_no_side_effect(self):
        with patch.object(self.e,'event',side_effect=RuntimeError('SAMPLE')):
            with self.assertRaises(RuntimeError):self.execute()
        self.assertIsNone(self.adapter.lookup('SAMPLE execution'))
        self.assertEqual(self.execute()['status'],'UNKNOWN')
        self.assertEqual(self.reconcile()['status'],'UNKNOWN')

if __name__=='__main__':unittest.main()
