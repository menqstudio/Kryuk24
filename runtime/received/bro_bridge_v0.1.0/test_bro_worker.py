import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ops_work import Operations
from bro_worker import run_one, adapter_call
from runtime import now

class BroTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Operations(Path(self.temp.name) / 'runtime.sqlite')
        self.day = '2026-10-07'
        self.ops.plan(self.day)
    def tearDown(self):
        self.temp.cleanup()
    def response(self, command, request, timeout):
        return dict(task_id=request['task']['id'], status='DONE', source='TEST fixture',
                    observed_at=now(), summary='Սինթետիկ փորձ․ իրական կաբինետ չի ստուգվել։')
    def test_reported_result_saved_and_no_external_messages(self):
        with patch('bro_worker.adapter_call', side_effect=self.response):
            result = run_one(self.ops, self.day, ['TEST'])
        task = self.ops.get(result['task_id'])
        self.assertEqual(task['status'], 'DONE')
        self.assertEqual(task['job'], 'YANDEX_BUSINESS')
        self.assertEqual(self.ops.report()['tasks'][0]['day'], self.day)
        self.assertEqual(self.ops.runtime.report()['notifications'], [])
        obs = next(t for t in self.ops.report()['tasks'] if t['id'] == task['id'])['observations'][0]
        self.assertTrue(obs['actor'].startswith('BRO:'))
        self.assertEqual(obs['trust'], 'OPERATOR_REPORTED')
    def test_failure_blocked_without_raw_secret(self):
        with patch('bro_worker.adapter_call', side_effect=ValueError('SECRET')):
            result = run_one(self.ops, self.day, ['TEST'])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertNotIn('SECRET', str(self.ops.report()))
    def test_blocked_not_automatically_retried(self):
        with patch('bro_worker.adapter_call', side_effect=ValueError('failed')):
            first = run_one(self.ops, self.day, ['TEST'])
            second = run_one(self.ops, self.day, ['TEST'])
        self.assertNotEqual(first['task_id'], second['task_id'])
        with patch('bro_worker.adapter_call', side_effect=self.response):
            retry = run_one(self.ops, self.day, ['TEST'], retry_task=first['task_id'])
        self.assertEqual(retry['status'], 'DONE')
    def test_wrong_task_and_stale_timestamp_rejected(self):
        for field, value in [('task_id', 'WRONG'), ('observed_at', '2000-01-01T00:00:00+00:00')]:
            def bad(command, request, timeout):
                r = self.response(command, request, timeout); r[field] = value; return r
            with patch('bro_worker.adapter_call', side_effect=bad):
                self.assertEqual(run_one(self.ops, self.day, ['TEST'])['status'], 'BLOCKED')
    def test_approval_output_rejected(self):
        with patch('bro_worker.adapter_call', return_value={'status': 'APPROVED'}):
            self.assertEqual(run_one(self.ops, self.day, ['TEST'])['status'], 'BLOCKED')
        with self.ops.runtime.db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM ops_approvals').fetchone()[0], 0)
    def test_report_waits_and_then_becomes_review(self):
        for t in self.ops.report(self.day)['tasks']:
            if t['job'] != 'DAILY_REPORT':
                self.ops.claim(t['id'], 'TEST')
                self.ops.observe(t['id'], 'TEST', 'TEST', now(), 'Փորձ', blocked=True)
        def draft(command, request, timeout):
            self.assertEqual(len(request['daily_evidence']), 9)
            return {'task_id': request['task']['id'], 'status': 'READY_REVIEW',
                    'draft': dict(action='REPORT_DRAFT', account='TEST', destination='Local review',
                                  body='Փորձնական հաշվետվություն', reason='TEST')}
        with patch('bro_worker.adapter_call', side_effect=draft):
            self.assertEqual(run_one(self.ops, self.day, ['TEST'])['status'], 'READY_REVIEW')
            self.assertEqual(run_one(self.ops, self.day, ['TEST'])['status'], 'IDLE')
    def test_timeout_limit_and_missing_config_before_claim(self):
        for cmd, timeout in [([], 300), (['TEST'], 601)]:
            with self.assertRaises(ValueError): run_one(self.ops, self.day, cmd, timeout)
        self.assertEqual(self.ops.report()['counts']['PENDING'], 10)
    def test_real_subprocess_transport_and_timeout(self):
        result = adapter_call([sys.executable, '-c', 'import sys,json; x=json.load(sys.stdin); print(json.dumps(x))'], {'test': True}, 5)
        self.assertEqual(result, {'test': True})
        with self.assertRaisesRegex(ValueError, 'ADAPTER_TIMEOUT'):
            adapter_call([sys.executable, '-c', 'import time; time.sleep(5)'], {}, 1)

if __name__ == '__main__': unittest.main()
