import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from monitor import ContractError, evaluate, read_json

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)
RULES = {'schema': 1, 'expected_mode': 'STAGING', 'expected_sending': False,
         'max_age_seconds': dict.fromkeys(('health', 'backup', 'hosting', 'certificate'), 3600),
         'backup_max_age_seconds': 86400, 'hosting_min_days': 7, 'certificate_min_days': 14}


def sample():
    values = {'health': {'reachable': True, 'mode': 'STAGING', 'sending_enabled': False},
              'backup': {'last_success': (NOW-timedelta(hours=2)).isoformat(), 'restore_verified': True},
              'hosting': {'balance_kopecks': 70000, 'daily_cost_kopecks': 10000},
              'certificate': {'not_after': (NOW+timedelta(days=14)).isoformat()}}
    return {'schema': 1, 'observations': {k: {'source': 'SAMPLE fixture only', 'observed_at': NOW.isoformat(), 'values': v}
                                        for k, v in values.items()}}


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.doc = sample()
        self.rules = copy.deepcopy(RULES)

    def run_check(self, name):
        result = evaluate(self.doc, self.rules, NOW)
        return next(r for r in result['checks'] if r['check'] == name)

    def test_healthy_boundary_and_no_external_effects(self):
        before = copy.deepcopy(self.doc)
        result = evaluate(self.doc, self.rules, NOW)
        self.assertEqual(result['status'], 'OK')
        self.assertFalse(result['alerts_sent'])
        self.assertFalse(result['collection_performed'])
        self.assertEqual(before, self.doc)

    def test_missing_all_is_unknown(self):
        result = evaluate({'schema': 1, 'observations': {}}, self.rules, NOW)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(len(result['checks']), 4)

    def test_stale_each_source_is_not_healthy(self):
        for name in self.doc['observations']:
            with self.subTest(name=name):
                old = self.doc['observations'][name]['observed_at']
                self.doc['observations'][name]['observed_at'] = (NOW-timedelta(seconds=3601)).isoformat()
                self.assertEqual(self.run_check(name)['reason'], 'stale_observation')
                self.doc['observations'][name]['observed_at'] = old

    def test_future_observation_is_unknown(self):
        self.doc['observations']['health']['observed_at'] = (NOW+timedelta(microseconds=1)).isoformat()
        self.assertEqual(self.run_check('health')['status'], 'UNKNOWN')

    def test_naive_timestamp_is_unknown(self):
        self.doc['observations']['health']['observed_at'] = '2026-10-08T00:00:00'
        self.assertEqual(self.run_check('health')['status'], 'UNKNOWN')

    def test_timezone_offsets_are_normalized(self):
        self.doc['observations']['health']['observed_at'] = '2026-10-08T04:00:00+04:00'
        self.assertEqual(self.run_check('health')['status'], 'OK')

    def test_unreachable_unexpected_mode_and_sending(self):
        values = self.doc['observations']['health']['values']
        values.update(reachable=False, mode='LIVE', sending_enabled=True)
        result = self.run_check('health')
        self.assertEqual(result['status'], 'ALERT')
        self.assertIn('unreachable', result['reason'])

    def test_reachable_wrong_mode_and_sending_are_alerts(self):
        self.doc['observations']['health']['values'].update(mode='LIVE', sending_enabled=True)
        row = self.run_check('health')
        self.assertEqual(row['status'], 'ALERT')
        self.assertIn('unexpected_mode', row['reason'])
        self.assertIn('unexpected_sending', row['reason'])

    def test_known_unreachable_with_no_response_details_is_alert(self):
        self.doc['observations']['health']['values'].update(reachable=False, mode=None, sending_enabled=None)
        self.assertEqual(self.run_check('health')['status'], 'ALERT')
        self.doc['observations']['health']['values']['reachable'] = True
        self.assertEqual(self.run_check('health')['status'], 'UNKNOWN')

    def test_partial_health_evidence_preserves_known_violation(self):
        values = self.doc['observations']['health']['values']
        values.update(mode=None, sending_enabled=True)
        row = self.run_check('health')
        self.assertEqual(row['status'], 'ALERT')
        self.assertEqual(row['reason'], 'unexpected_sending')
        self.assertEqual(row['unknown_fields'], ['mode'])
        values.update(mode='LIVE', sending_enabled=None)
        self.assertEqual(self.run_check('health')['reason'], 'unexpected_mode')
        values['mode'] = 'STAGING'
        self.assertEqual(self.run_check('health')['status'], 'UNKNOWN')

    def test_boolean_strings_cannot_pass(self):
        self.doc['observations']['health']['values']['sending_enabled'] = 'false'
        self.assertEqual(self.run_check('health')['status'], 'UNKNOWN')

    def test_backup_overdue_and_unverified_restore(self):
        values = self.doc['observations']['backup']['values']
        values['restore_verified'] = False
        self.assertEqual(self.run_check('backup')['reason'], 'restore_unverified')
        values['last_success'] = (NOW-timedelta(days=2)).isoformat()
        self.assertEqual(self.run_check('backup')['status'], 'ALERT')

    def test_future_backup_success_is_invalid(self):
        self.doc['observations']['backup']['values']['last_success'] = (NOW+timedelta(seconds=1)).isoformat()
        self.assertEqual(self.run_check('backup')['status'], 'UNKNOWN')

    def test_hosting_kopeck_boundary_not_float_rounding(self):
        self.doc['observations']['hosting']['values']['balance_kopecks'] = 69999
        self.assertEqual(self.run_check('hosting')['status'], 'ALERT')
        self.assertEqual(self.run_check('hosting')['estimated_whole_days'], 6)

    def test_invalid_cost_and_balance_types(self):
        for field, value in [('daily_cost_kopecks', 0), ('balance_kopecks', -10**15-1),
                             ('balance_kopecks', True), ('balance_kopecks', 70000.0)]:
            with self.subTest(field=field, value=value):
                doc = sample()
                doc['observations']['hosting']['values'][field] = value
                self.assertEqual(evaluate(doc, self.rules, NOW)['checks'][2]['status'], 'UNKNOWN')

    def test_negative_balance_is_alert_with_zero_runway(self):
        self.doc['observations']['hosting']['values']['balance_kopecks'] = -1
        row = self.run_check('hosting')
        self.assertEqual(row['status'], 'ALERT')
        self.assertEqual(row['estimated_whole_days'], 0)

    def test_more_balance_never_worsens_hosting_status(self):
        previous = False
        for balance in [-10000, -1, 0, 1, 69999, 70000, 70001, 10**15]:
            self.doc['observations']['hosting']['values']['balance_kopecks'] = balance
            healthy = self.run_check('hosting')['status'] == 'OK'
            self.assertFalse(previous and not healthy)
            previous = healthy

    def test_expired_and_near_expiry_certificate(self):
        values = self.doc['observations']['certificate']['values']
        values['not_after'] = NOW.isoformat()
        self.assertEqual(self.run_check('certificate')['reason'], 'certificate_expired')
        values['not_after'] = (NOW+timedelta(days=14, microseconds=-1)).isoformat()
        self.assertEqual(self.run_check('certificate')['reason'], 'certificate_near_expiry')

    def test_alert_does_not_hide_unknown_checks(self):
        self.doc['observations']['health']['values']['reachable'] = False
        del self.doc['observations']['backup']
        result = evaluate(self.doc, self.rules, NOW)
        self.assertEqual(result['status'], 'ALERT')
        self.assertEqual(result['checks'][1]['status'], 'UNKNOWN')

    def test_extra_private_data_is_rejected_without_echo(self):
        self.doc['observations']['health']['values']['secret'] = 'DO-NOT-ECHO'
        result = evaluate(self.doc, self.rules, NOW)
        self.assertEqual(result['checks'][0]['status'], 'UNKNOWN')
        self.assertNotIn('DO-NOT-ECHO', json.dumps(result))

    def test_unknown_observation_kind_and_schema_rejected(self):
        self.doc['observations']['typo'] = {}
        with self.assertRaises(ContractError):
            evaluate(self.doc, self.rules, NOW)
        with self.assertRaises(ContractError):
            evaluate({'schema': True, 'observations': {}}, self.rules, NOW)

    def test_policy_cannot_disable_checks_with_zero_age(self):
        self.rules['max_age_seconds']['health'] = 0
        with self.assertRaises(ContractError):
            evaluate(self.doc, self.rules, NOW)

    def test_json_duplicate_nonfinite_invalid_utf8_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.json'
            for raw in [b'{"schema":1,"schema":2}', b'{"v":NaN}', b'{"v":1e999}',
                        b'{"v":-1e999}', b'{"v":'+b'9'*5000+b'}', b'\xff', b' '*65537]:
                path.write_bytes(raw)
                with self.assertRaises(ContractError):
                    read_json(path)

    def test_depth_limit_is_independent_of_interpreter_recursion_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'deep.json'
            path.write_text('['*65+'0'+']'*65, encoding='utf-8')
            with self.assertRaises(ContractError):
                read_json(path)
            # Quoted braces, escaped quotes and backslashes are not nesting.
            value = {'text': '['*100+'"\\'+']'*100}
            path.write_text(json.dumps(value), encoding='utf-8')
            self.assertEqual(read_json(path), value)

    def test_malformed_values_never_escape_evaluation(self):
        variants = [None, [], {}, True, False, 0, 1, -1, 'wrong', '', 1.2]
        for name, obs in self.doc['observations'].items():
            for field in obs['values']:
                for bad in variants:
                    with self.subTest(check=name, field=field, value=bad):
                        doc = sample()
                        doc['observations'][name]['values'][field] = bad
                        result = evaluate(doc, self.rules, NOW)
                        self.assertEqual(len(result['checks']), 4)

    def test_evaluation_is_replay_deterministic(self):
        self.assertEqual(evaluate(self.doc, self.rules, NOW), evaluate(self.doc, self.rules, NOW))

    def test_cli_long_integer_is_unknown_not_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            observations = Path(directory)/'observations.json'
            rules = Path(directory)/'rules.json'
            observations.write_text('{"schema":'+('9'*5000)+',"observations":{}}', encoding='utf-8')
            rules.write_text(json.dumps(RULES), encoding='utf-8')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('monitor.py')),
                                     '--observations', str(observations), '--policy', str(rules)],
                                    capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'UNKNOWN')
        self.assertEqual(result.stderr, '')

    def test_nonregular_input_is_rejected_without_hanging(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'not-a-file'
            if hasattr(os, 'mkfifo'):
                os.mkfifo(path)
            else:
                path.mkdir()
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('monitor.py')),
                                     '--observations', str(path), '--policy', str(path)],
                                    capture_output=True, text=True, encoding='utf-8', timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'UNKNOWN')
            self.assertEqual(result.stderr, '')

    def test_cli_rejects_missing_file_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('monitor.py')),
                                     '--observations', str(Path(directory)/'missing'), '--policy', str(Path(directory)/'missing')],
                                    capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'UNKNOWN')
        self.assertEqual(result.stderr, '')

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            observations = Path(directory)/'Դիտարկումներ.json'
            rules = Path(directory)/'policy.json'
            rules.write_text(json.dumps(RULES), encoding='utf-8')
            current = datetime.now(timezone.utc)
            doc = sample()
            for obs in doc['observations'].values():
                obs['observed_at'] = current.isoformat()
            doc['observations']['backup']['values']['last_success'] = current.isoformat()
            doc['observations']['certificate']['values']['not_after'] = (current+timedelta(days=30)).isoformat()
            for state, code in [('OK', 0), ('ALERT', 1), ('UNKNOWN', 2)]:
                changed = copy.deepcopy(doc)
                if state == 'ALERT':
                    changed['observations']['hosting']['values']['balance_kopecks'] = 0
                if state == 'UNKNOWN':
                    del changed['observations']['backup']
                observations.write_text(json.dumps(changed, ensure_ascii=False), encoding='utf-8')
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('monitor.py')),
                                         '--observations', str(observations), '--policy', str(rules)],
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, code)
                self.assertEqual(json.loads(result.stdout)['status'], state)
                self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
