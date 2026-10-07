import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from runtime import Runtime
from order_flow import OrderFlow
from request_flow import RequestFlow
from action_approval import ApprovalStore, digest
from action_executor import SimulationExecutor, SimulationAdapter
from business_service import BusinessService, Identity


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(self.tmp.name+'/db')
        self.orders=OrderFlow(self.r);self.requests=RequestFlow(self.orders)
        self.time=datetime(2026,10,8,tzinfo=timezone.utc)
        self.approvals=ApprovalStore(self.r,'gev',['REPORT_SEND'],lambda:self.time)
        self.executor=SimulationExecutor(self.approvals,SimulationAdapter(self.r,['REPORT_SEND']))
        self.inputs={'SAMPLE queue':digest({'revision':1})}
        self.s=BusinessService(self.requests,self.approvals,self.executor,'gev',lambda _:dict(self.inputs))
        self.d=Identity('dispatcher',frozenset({'DISPATCHER'}))
        self.owner=Identity('gev',frozenset({'OWNER'}))
        self.partner=Identity('partner',frozenset({'PARTNER'}))
        self.preparer=Identity('claude',frozenset({'PREPARER'}))
        self.worker=Identity('worker',frozenset({'EXECUTOR'}))
        self.fields=dict(pickup='SAMPLE pickup',destination='SAMPLE destination',vehicle='SAMPLE car',
                         contact='SAMPLE private contact',evidence='SAMPLE inquiry')
        self.b=dict(action='REPORT_SEND',account='SAMPLE account',target='SAMPLE target',payload={'body':'SAMPLE report'},
                    assets=[],amount=None,inputs=dict(self.inputs),test=True,
                    expires_at=(self.time+timedelta(hours=1)).isoformat())

    def tearDown(self):self.tmp.cleanup()
    def intake(self,ref='sample',test=True):
        r=self.s.receive(self.d,'PHONE',ref,test,'SAMPLE conversation')
        return self.s.convert(self.d,r['id'],0,**self.fields)
    def command(self,oid,action,**payload):
        rev=self.s.order(self.d,oid)['revision']
        return self.s.order_command(self.d,oid,'sample-'+str(rev),rev,action,payload)
    def proposal(self):return self.s.proposal(self.preparer,'SAMPLE proposal',self.b)

    def test_entire_inquiry_order_payment_close_owner_board(self):
        r=self.intake();oid=r['order_id']
        self.command(oid,'QUALIFY',evidence='SAMPLE')
        self.command(oid,'QUOTE',amount=500000,terms='SAMPLE',evidence='SAMPLE')
        self.command(oid,'CONFIRM_PRICE',price_version=1,evidence='SAMPLE customer yes')
        self.command(oid,'ASSIGN',driver='partner',acceptance='SAMPLE')
        for status in ('EN_ROUTE','ARRIVED','LOADED','TRANSPORTING','DELIVERED'):
            self.command(oid,'PROGRESS',status=status,evidence='SAMPLE')
        with self.assertRaises(ValueError):self.command(oid,'CLOSE',evidence='SAMPLE')
        self.command(oid,'VERIFY_JOB',evidence='SAMPLE')
        self.command(oid,'VERIFY_PAYMENT',amount=500000,price_version=1,evidence='SAMPLE')
        self.command(oid,'SETTLE_COMMISSION',amount=100000,price_version=1,evidence='SAMPLE')
        self.command(oid,'FEEDBACK',state='REQUESTED',evidence='SAMPLE')
        self.command(oid,'CLOSE',evidence='SAMPLE')
        board=self.s.board(self.owner,True)
        self.assertEqual(board['counts'],{'requests':1,'managed_orders':1,'closed_orders':1,'conversions_incomplete':0})
        self.assertEqual(board['profit'],'UNKNOWN')
        self.assertNotIn('private contact',str(board));self.assertNotIn('SAMPLE pickup',str(board))
        self.assertEqual(self.s.board(self.owner)['counts']['requests'],0)

    def test_owner_read_only_for_order_facts(self):
        r=self.intake();oid=r['order_id']
        self.assertEqual(self.s.request(self.owner,r['id'])['owner'],'dispatcher')
        self.assertEqual(self.s.order(self.owner,oid)['status'],'NEW')
        with self.assertRaises(PermissionError):self.s.order_command(self.owner,oid,'x',0,'QUALIFY',{'evidence':'SAMPLE'})
        with self.assertRaises(PermissionError):self.s.receive(self.owner,'PHONE','x',True,'SAMPLE')
        with self.assertRaises(PermissionError):self.s.board(Identity('fake',frozenset({'OWNER'})))

    def test_dispatcher_isolation_and_no_self_authorisation(self):
        r=self.intake();other=Identity('other',frozenset({'DISPATCHER'}))
        for fn in (lambda:self.s.request(other,r['id']),lambda:self.s.order(other,r['order_id']),
                   lambda:self.s.board(self.d),lambda:self.s.proposal(self.d,'x',self.b)):
            with self.assertRaises(PermissionError):fn()
        proposal=self.proposal()
        with self.assertRaises(PermissionError):self.s.decide(self.d,proposal['id'],proposal['digest'],'APPROVED','SAMPLE')

    def test_partner_projection_report_does_not_expose_finances(self):
        oid=self.intake()['order_id']
        with self.assertRaises(PermissionError):self.s.order(self.partner,oid)
        self.command(oid,'QUALIFY',evidence='SAMPLE');self.command(oid,'QUOTE',amount=500000,terms='SAMPLE',evidence='SAMPLE')
        self.command(oid,'CONFIRM_PRICE',price_version=1,evidence='SAMPLE')
        self.command(oid,'ASSIGN',driver='partner',acceptance='SAMPLE')
        rev=self.s.order(self.partner,oid)['revision']
        result=self.s.order_command(self.partner,oid,'partner-report',rev,'PARTNER_REPORT',{'kind':'PRICE','amount':700000,'evidence':'SAMPLE'})
        self.assertNotIn('price',result);self.assertNotIn('commission_due',result)
        self.assertEqual(self.s.order(self.d,oid)['price'],500000)
        with self.assertRaises(PermissionError):self.s.order_history(self.partner,oid)
        with self.assertRaises(PermissionError):self.s.order_command(self.partner,oid,'bad',result['revision'],'CLOSE',{'evidence':'SAMPLE'})

    def test_complete_proposal_approval_simulation_report(self):
        d=self.proposal();out=self.s.decide(self.owner,d['id'],d['digest'],'APPROVED','SAMPLE Gev yes')
        self.assertEqual(out['status'],'APPROVED')
        result=self.s.execute_simulation(self.worker,d['id'],'SAMPLE draft-specific key',self.b)
        self.assertEqual(result['status'],'SIMULATION_VERIFIED')
        audit=self.s.action(self.owner,d['id'])
        self.assertEqual(audit['approval']['status'],'RESERVED')
        self.assertFalse(audit['execution']['external_execution_enabled'])
        self.assertEqual(result,self.s.execute_simulation(self.worker,d['id'],'SAMPLE draft-specific key',self.b))

    def test_trusted_fingerprint_changed_after_approval_blocks(self):
        d=self.proposal();self.s.decide(self.owner,d['id'],d['digest'],'APPROVED','SAMPLE')
        self.inputs['SAMPLE queue']=digest({'revision':2})
        out=self.s.execute_simulation(self.worker,d['id'],'SAMPLE key',self.b)
        self.assertEqual(out['status'],'STALE')
        with self.r.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM executor_simulated_effects').fetchone()[0],0)

    def test_stale_proposal_and_bad_identity_denied(self):
        self.inputs['SAMPLE queue']=digest({'revision':2})
        with self.assertRaises(ValueError):self.proposal()
        with self.assertRaises(PermissionError):self.s.board({'actor':'gev','roles':['OWNER']})
        with self.assertRaises(PermissionError):self.s.board(Identity('gev',{'OWNER'}))

    def test_disposition_not_converted_and_test_isolation(self):
        r=self.s.receive(self.d,'PHONE','SAMPLE declined',False,'SAMPLE')
        self.s.dispose(self.d,r['id'],0,'OUT_OF_SCOPE','SAMPLE not supported')
        with self.assertRaises(ValueError):self.s.convert(self.d,r['id'],1,**self.fields)
        board=self.s.board(self.owner)
        self.assertEqual(board['counts']['requests'],1);self.assertEqual(board['counts']['managed_orders'],0)

    def test_order_denials_do_not_disclose_existence(self):
        oid=self.intake()['order_id']
        unauthorized=Identity('other',frozenset({'DISPATCHER'}))
        errors=[]
        for target in (oid, 'missing-order'):
            with self.assertRaises(PermissionError) as caught:self.s.order(unauthorized,target)
            errors.append(str(caught.exception))
        self.assertEqual(errors,['order read denied','order read denied'])
        # A real but unmanaged legacy order also gives the same denial.
        legacy=self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car',test=True),'legacy')['id']
        with self.assertRaisesRegex(PermissionError,'^order read denied$'):self.s.order(unauthorized,legacy)
        with patch.object(self.orders,'get',side_effect=AssertionError('must not query')):
            with self.assertRaises(PermissionError):self.s.order(Identity('no-role',frozenset()),oid)
            with self.assertRaises(PermissionError):self.s.order(Identity('fake',frozenset({'OWNER'})),oid)

if __name__=='__main__':unittest.main()
