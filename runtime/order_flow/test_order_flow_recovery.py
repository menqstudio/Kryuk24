import concurrent.futures
import unittest
from unittest.mock import patch
from order_flow import OrderFlow, Principal
from runtime import Runtime
import test_order_flow as scenarios


class RecoveryTests(unittest.TestCase):
    setUp = scenarios.Tests.setUp
    tearDown = scenarios.Tests.tearDown
    command = scenarios.Tests.command
    confirmed = scenarios.Tests.confirmed
    delivered = scenarios.Tests.delivered
    paid = scenarios.Tests.paid
    def test_failed_event_rolls_back_all_writes(self):
        before = self.flow.get(self.oid)
        with patch.object(self.r, 'event', side_effect=RuntimeError('simulated journal failure')):
            with self.assertRaises(RuntimeError):
                self.flow.command(self.oid,self.owner,'fault',0,'QUALIFY',{'evidence':'SAMPLE'})
        self.assertEqual(before,self.flow.get(self.oid))
        with self.r.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM dispatch_write_guard').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM dispatch_commands').fetchone()[0],0)
        result=OrderFlow(Runtime(self.r.path)).command(self.oid,self.owner,'fault',0,'QUALIFY',{'evidence':'SAMPLE'})
        self.assertEqual(result['revision'],1)

    def test_simultaneous_same_command_is_one_event(self):
        def run(_):
            return self.flow.command(self.oid,self.owner,'retry',0,'QUALIFY',{'evidence':'SAMPLE'})
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results=list(pool.map(run,range(4)))
        self.assertTrue(all(result==results[0] for result in results))
        self.assertEqual(sum(e['kind']=='DISPATCH_QUALIFY' for e in self.flow.history(self.oid)),1)

    def test_history_retains_original_and_new_price(self):
        self.delivered()
        self.command('REPRICE',amount=600000,terms='SAMPLE extra work',evidence='SAMPLE',customer_confirmation='SAMPLE yes')
        history=self.flow.history(self.oid)
        quote=next(e for e in history if e['kind']=='DISPATCH_QUOTE')
        reprice=next(e for e in history if e['kind']=='DISPATCH_REPRICE')
        self.assertEqual(quote['data']['payload']['amount'],500000)
        self.assertEqual(reprice['data']['payload']['amount'],600000)

    def test_close_checklist_and_summary_do_not_write(self):
        self.paid()
        before=self.flow.history(self.oid)
        self.assertCountEqual(self.flow.get(self.oid)['closure']['missing'],['commission_settled','feedback_recorded'])
        self.assertFalse(self.flow.get(self.oid)['closure']['can_close'])
        self.assertEqual(self.flow.summary()['orders'],0)
        self.assertEqual(self.flow.summary(test=True)['commission_outstanding_kopecks'],100000)
        self.assertEqual(before,self.flow.history(self.oid))
        self.command('SETTLE_COMMISSION',amount=100000,price_version=1,evidence='SAMPLE')
        self.command('FEEDBACK',state='REQUESTED',evidence='SAMPLE')
        self.assertTrue(self.flow.get(self.oid)['closure']['can_close'])
        self.command('CLOSE',evidence='SAMPLE')
        report=self.flow.summary(test=True)
        self.assertEqual(report['closed_orders'],1)
        self.assertEqual(report['commission_outstanding_kopecks'],0)
        self.assertEqual(report['profit'],'UNKNOWN')

    def test_real_partner_report_preserves_trust_and_owner(self):
        oid=self.r.intake(dict(contact='SAMPLE synthetic real-filter fixture',pickup='A',destination='B',vehicle='car',test=False),'real-filter')['id']
        self.flow.adopt(oid,self.owner,0)
        rev=0
        for action,payload in [('QUALIFY',{'evidence':'SAMPLE'}),('QUOTE',{'amount':500000,'terms':'SAMPLE','evidence':'SAMPLE'}),
                               ('CONFIRM_PRICE',{'price_version':1,'evidence':'SAMPLE'}),('ASSIGN',{'driver':'partner-1','acceptance':'SAMPLE'})]:
            rev=self.flow.command(oid,self.owner,action,rev,action,payload)['revision']
        self.flow.command(oid,self.partner,'reported',rev,'PARTNER_REPORT',{'kind':'PAYMENT','amount':700000,'evidence':'SAMPLE partner says'})
        event=self.flow.history(oid)[-1]
        self.assertEqual(event['data']['trust'],'PARTNER_REPORTED')
        self.assertEqual(self.flow.get(oid)['paid'],0)
        report=self.flow.summary()
        self.assertEqual(report['orders'],1)
        self.assertEqual(report['paid_orders'],0)
        self.assertEqual(self.flow.summary(test=True)['orders'],1)

    def test_zero_rounded_commission_is_supported(self):
        self.paid()
        # Independent synthetic order for a tiny amount; no mutation of financial state.
        oid=self.r.intake(dict(contact='SAMPLE',pickup='A',destination='B',vehicle='car',test=True),'tiny')['id']
        self.flow.adopt(oid,self.owner,0)
        actions=[('QUALIFY',dict(evidence='SAMPLE')),('QUOTE',dict(amount=1,terms='SAMPLE',evidence='SAMPLE')),
                 ('CONFIRM_PRICE',dict(price_version=1,evidence='SAMPLE')),('ASSIGN',dict(driver='partner-1',acceptance='SAMPLE'))]
        actions += [('PROGRESS',dict(status=s,evidence='SAMPLE')) for s in ('EN_ROUTE','ARRIVED','LOADED','TRANSPORTING','DELIVERED')]
        actions += [('VERIFY_JOB',dict(evidence='SAMPLE')),('VERIFY_PAYMENT',dict(amount=1,price_version=1,evidence='SAMPLE')),
                    ('SETTLE_COMMISSION',dict(amount=0,price_version=1,evidence='SAMPLE zero due'))]
        rev=0
        for i,(action,payload) in enumerate(actions):
            rev=self.flow.command(oid,self.owner,str(i),rev,action,payload)['revision']
        self.assertEqual(self.flow.get(oid)['commission_due'],0)


