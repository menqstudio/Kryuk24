import concurrent.futures
import tempfile
import unittest
from unittest.mock import patch
from runtime import Runtime
from order_flow import OrderFlow, Principal
from request_flow import RequestFlow


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(self.tmp.name + '/db')
        self.flow = OrderFlow(self.r)
        self.requests = RequestFlow(self.flow)
        self.owner = Principal('dispatcher', 'DISPATCHER')

    def tearDown(self):
        self.tmp.cleanup()

    def receive(self, ref='sample-1', test=True):
        return self.requests.receive(self.owner, 'PHONE', ref, test, 'SAMPLE actual conversation')

    def convert(self, rid):
        return self.requests.convert(rid, self.owner, 0, 'SAMPLE A', 'SAMPLE B', 'SAMPLE car', 'SAMPLE contact', 'SAMPLE service requested')

    def test_inquiry_is_not_order_or_click(self):
        row = self.receive()
        self.assertEqual(row['status'], 'OPEN')
        self.assertIsNone(row['order_id'])
        with self.r.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM orders').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM contact_interactions').fetchone()[0], 0)
        with self.assertRaises(ValueError):
            self.requests.receive(self.owner, 'CLICK', 'x', True, 'SAMPLE')

    def test_exact_source_dedup_and_test_separation(self):
        self.assertEqual(self.receive()['id'], self.receive()['id'])
        self.assertNotEqual(self.receive()['id'], self.receive(test=False)['id'])
        with self.assertRaises(ValueError):
            self.requests.receive(self.owner, 'PHONE', 'sample-1', True, 'changed')
        self.assertEqual(self.requests.summary(self.owner)['requests'], 1)
        self.assertEqual(self.requests.summary(self.owner, True)['requests'], 1)

    def test_owner_authority_read_and_write(self):
        rid = self.receive()['id']
        for p in (Principal('other', 'DISPATCHER'), Principal('partner', 'PARTNER')):
            for operation in (lambda: self.requests.get(rid, p), lambda: self.requests.history(rid, p),
                              lambda: self.requests.dispose(rid, p, 0, 'DECLINED', 'SAMPLE')):
                with self.assertRaises(PermissionError):
                    operation()

    def test_disposition_and_duplicate_contract(self):
        a = self.receive('a')['id']; b = self.receive('b')['id']
        with self.assertRaises(ValueError):
            self.requests.dispose(a, self.owner, 0, 'DUPLICATE', 'SAMPLE', a)
        real = self.receive('real', False)['id']
        with self.assertRaises(ValueError):
            self.requests.dispose(a, self.owner, 0, 'DUPLICATE', 'SAMPLE', real)
        self.requests.dispose(a, self.owner, 0, 'DUPLICATE', 'SAMPLE same inquiry', b)
        with self.assertRaises(ValueError):self.convert(a)
        self.assertEqual(self.requests.history(a, self.owner)[-1]['kind'], 'DUPLICATE')

    def test_conversion_reuses_runtime_and_enrols_owner(self):
        rid = self.receive()['id']; result = self.convert(rid)
        self.assertEqual(result, self.convert(rid))
        order = self.flow.get(result['order_id'])
        self.assertEqual(order['owner'], self.owner.actor)
        self.assertEqual(order['status'], 'NEW')
        self.assertFalse(order['closure']['can_close'])
        with self.r.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM orders').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM notifications').fetchone()[0], 1)
        self.assertEqual([e['kind'] for e in self.requests.history(rid, self.owner)], ['RECEIVED', 'CONVERSION_STARTED', 'CONVERTED'])

    def test_recover_after_intake_before_adopt(self):
        rid = self.receive()['id']
        with patch.object(self.flow, 'adopt', side_effect=RuntimeError('SAMPLE crash')):
            with self.assertRaises(RuntimeError):self.convert(rid)
        self.assertEqual(self.requests.get(rid, self.owner)['status'], 'CONVERTING')
        with self.assertRaises(ValueError):self.requests.dispose(rid, self.owner, 1, 'DECLINED', 'SAMPLE')
        self.requests = RequestFlow(OrderFlow(Runtime(self.r.path)))
        self.assertEqual(self.convert(rid)['status'], 'CONVERTED')
        with self.r.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM orders').fetchone()[0], 1)

    def test_recover_after_adopt_before_link(self):
        rid = self.receive()['id']; event = self.requests._event
        def fail(c, request, kind, p, data):
            if kind == 'CONVERTED':raise RuntimeError('SAMPLE journal failure')
            return event(c, request, kind, p, data)
        with patch.object(self.requests, '_event', side_effect=fail):
            with self.assertRaises(RuntimeError):self.convert(rid)
        self.assertEqual(self.requests.get(rid, self.owner)['status'], 'CONVERTING')
        self.assertEqual(self.convert(rid)['status'], 'CONVERTED')
        self.assertEqual(len(self.requests.history(rid, self.owner)), 3)

    def test_changed_conversion_payload_rejected(self):
        rid = self.receive()['id']; self.convert(rid)
        with self.assertRaises(ValueError):
            self.requests.convert(rid, self.owner, 0, 'changed', 'SAMPLE B', 'SAMPLE car', 'SAMPLE contact', 'SAMPLE service requested')
        with self.assertRaises(ValueError):
            self.requests.receive(self.owner, 'PHONE', 'x', 'false', 'SAMPLE')

    def test_concurrent_conversion_once(self):
        rid = self.receive()['id']
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda _: self.convert(rid), range(4)))
        self.assertEqual(len({r['order_id'] for r in results}), 1)
        self.assertEqual(len(self.requests.history(rid, self.owner)), 3)

    def test_receive_audit_failure_rolls_back(self):
        with patch.object(self.requests, '_event', side_effect=RuntimeError('SAMPLE')):
            with self.assertRaises(RuntimeError):self.receive()
        self.assertEqual(self.requests.summary(self.owner, True)['requests'], 0)

if __name__ == '__main__':unittest.main()
