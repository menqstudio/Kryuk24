"""Tests of the API_READ queue work against the real queue code (fixtures/server_base, the files installed on the
server on 07.10.2026) and a local stand-in for the three services. No real service, no real secret."""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE_FILES = HERE / 'fixtures' / 'server_base'
sys.path.insert(0, str(HERE))
import install_patch
import reader_provision
from test_bro_api_reader import Fake, PASSWORD, SECRETS, TOKEN


def code_folder():
    folder = Path(tempfile.mkdtemp())
    for path in BASE_FILES.glob('*.py'):
        shutil.copy(path, folder / path.name)
    return folder


CODE = code_folder()
APPLIED = install_patch.apply(CODE)
sys.path.insert(0, str(CODE))
import bro_api          # noqa: E402  the patched copies
import bro_worker       # noqa: E402
import ops_api          # noqa: E402
import ops_work         # noqa: E402

API = ('HOSTING_DEADLINES', 'METRICA', 'WEBMASTER')


class Patch(unittest.TestCase):
    def test_apply_needs_the_exact_known_files_and_rollback_restores_them(self):
        code = code_folder()
        before = {p.name: p.read_bytes() for p in code.iterdir()}
        self.assertEqual(set(install_patch.plan(code)), set(install_patch.BASE) | set(install_patch.ADDED))
        self.assertEqual({p.name: p.read_bytes() for p in code.iterdir()}, before, 'check changes nothing')
        result = install_patch.apply(code)
        self.assertEqual(result, APPLIED)
        for name in install_patch.BASE:
            self.assertEqual((code / (name + install_patch.SUFFIX)).read_bytes(), before[name])
            self.assertNotEqual((code / name).read_bytes(), before[name])
        self.assertIn(b"'API_READ'", (code / 'ops_work.py').read_bytes())
        self.assertEqual((code / 'ops_api.py').read_bytes(), (HERE / 'ops_api.py').read_bytes())
        with self.assertRaises(ValueError):
            install_patch.apply(code)                      # a second apply finds changed files and refuses
        install_patch.rollback(code)
        self.assertEqual({p.name: p.read_bytes() for p in code.iterdir()}, before, 'rollback gives back every byte')
        with self.assertRaises(ValueError):
            install_patch.rollback(code)

    def test_a_changed_file_stops_everything(self):
        code = code_folder()
        (code / 'bro_worker.py').write_bytes((code / 'bro_worker.py').read_bytes() + b'\n# local edit\n')
        before = {p.name: p.read_bytes() for p in code.iterdir()}
        with self.assertRaises(ValueError) as caught:
            install_patch.apply(code)
        self.assertIn('bro_worker.py is not the known version', str(caught.exception))
        self.assertEqual({p.name: p.read_bytes() for p in code.iterdir()}, before)
        r = subprocess.run([sys.executable, str(HERE / 'install_patch.py'), '--code', str(code), 'check'], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn(b'REFUSED', r.stdout)

    def folder(self, code):
        return {p.name: p.read_bytes() for p in code.iterdir()}

    def failing_replace(self, fail):
        # os.replace as the installer sees it; fail(n) says whether the n-th file write breaks (disk full, permission)
        real, calls = os.replace, []
        def replace(source, target):
            calls.append(Path(target).name)
            if fail(len(calls)):
                raise OSError(28, 'No space left on device')
            return real(source, target)
        return patch.object(install_patch.os, 'replace', replace), calls

    def test_apply_that_fails_at_any_write_leaves_the_folder_exactly_as_it_was(self):
        writes = len(install_patch.BASE) + len(install_patch.ADDED)
        self.assertEqual(writes, 7)
        for nth in range(1, writes + 1):                   # 2 and 3 are the second and third file; 5 to 7 are the added ones
            code = code_folder()
            before = self.folder(code)
            patcher, calls = self.failing_replace(lambda n: n == nth)
            with patcher, self.assertRaises(ValueError) as caught:
                install_patch.apply(code)
            self.assertIn('every file was put back', str(caught.exception), nth)
            self.assertGreaterEqual(len(calls), nth)
            self.assertEqual(self.folder(code), before, 'write %d failed: no half patch, no saved copy, no added file, no .new file' % nth)
            self.assertEqual(install_patch.apply(code), APPLIED, 'and a later apply on the same folder works')

    def test_apply_that_cannot_undo_says_partial_and_rollback_restores_every_byte(self):
        for nth in (2, 3):
            code = code_folder()
            before = self.folder(code)
            patcher, calls = self.failing_replace(lambda n: n >= nth)      # the undo cannot write either
            with patcher, self.assertRaises(install_patch.Partial) as caught:
                install_patch.apply(code)
            self.assertIn('Run rollback', str(caught.exception))
            state = self.folder(code)
            self.assertNotEqual(state['ops_work.py'], before['ops_work.py'], 'the folder really is half-patched')
            self.assertEqual(state['test_bro_http.py'], before['test_bro_http.py'])
            for name in install_patch.BASE:
                self.assertEqual(state[name + install_patch.SUFFIX], before[name], 'every saved copy is kept')
            with self.assertRaises(ValueError):
                install_patch.apply(code)                  # a new apply refuses a half-patched folder
            self.assertEqual(self.folder(code), state)
            r = subprocess.run([sys.executable, str(HERE / 'install_patch.py'), '--code', str(code), 'rollback'], capture_output=True, timeout=60)
            self.assertEqual((r.returncode, r.stdout[:11]), (0, b'ROLLED BACK'))
            self.assertEqual(self.folder(code), before, 'rollback gives back every byte of a half-patched folder')

    def test_rollback_that_fails_in_the_middle_can_be_repeated(self):
        for nth in (1, 2, 3):
            code = code_folder()
            before = self.folder(code)
            install_patch.apply(code)
            patcher, calls = self.failing_replace(lambda n: n == nth)
            with patcher, self.assertRaises(install_patch.Partial):
                install_patch.rollback(code)
            for name in install_patch.BASE:
                self.assertEqual((code / (name + install_patch.SUFFIX)).read_bytes(), before[name], 'saved copies are deleted last')
            install_patch.rollback(code)
            self.assertEqual(self.folder(code), before)

    def test_a_real_apply_process_killed_in_the_middle_is_recovered_by_rollback(self):
        # A real subprocess runs apply and is killed (SIGKILL / TerminateProcess) while it stands inside its 3rd file write.
        # Only the pause is arranged: the child's os.replace says where it is and then waits to be killed.
        driver = ('import os, sys, time; sys.path.insert(0, sys.argv[1]); import install_patch\n'
                  'from pathlib import Path\n'
                  'real, calls = os.replace, []\n'
                  'def replace(source, target):\n'
                  '    calls.append(target)\n'
                  '    if len(calls) == 3:\n'
                  '        Path(sys.argv[3]).write_text("inside write 3")\n'
                  '        time.sleep(120)\n'
                  '    return real(source, target)\n'
                  'install_patch.os.replace = replace\n'
                  'install_patch.apply(Path(sys.argv[2]))\n')
        code = code_folder()
        before = self.folder(code)
        marker = Path(tempfile.mkdtemp()) / 'marker'
        child = subprocess.Popen([sys.executable, '-c', driver, str(HERE), str(code), str(marker)])
        try:
            for _ in range(600):
                if marker.exists() or child.poll() is not None:
                    break
                time.sleep(0.1)
            self.assertTrue(marker.exists(), 'the child reached its third write')
            self.assertIsNone(child.poll(), 'and is still running')
        finally:
            child.kill()
            child.wait(timeout=60)
        self.assertNotEqual(child.returncode, 0)
        state = self.folder(code)
        self.assertNotEqual(state['ops_work.py'], before['ops_work.py'], 'two files are already patched')
        self.assertNotEqual(state['bro_api.py'], before['bro_api.py'])
        self.assertEqual(state['bro_worker.py'], before['bro_worker.py'], 'the third is not')
        self.assertIn('bro_worker.py.new', state, 'its temporary file is left behind')
        self.assertNotIn('ops_api.py', state)
        with self.assertRaises(ValueError):
            install_patch.apply(code)                      # a new apply refuses what the killed one left
        self.assertEqual(self.folder(code), state)
        r = subprocess.run([sys.executable, str(HERE / 'install_patch.py'), '--code', str(code), 'rollback'], capture_output=True, timeout=60)
        self.assertEqual((r.returncode, r.stdout[:11]), (0, b'ROLLED BACK'), r.stdout)
        self.assertEqual(self.folder(code), before, 'rollback gives back every byte after a real kill')
        self.assertEqual(install_patch.apply(code), APPLIED)

    def test_a_folder_arranged_as_if_apply_died_early_is_recovered_by_rollback(self):
        # Simulated, no process is killed: the files are arranged by hand as an apply would leave them
        # if it died while writing the saved copies.
        code = code_folder()
        before = self.folder(code)
        for name in list(install_patch.BASE)[:2]:
            (code / (name + install_patch.SUFFIX)).write_bytes(before[name])
        (code / 'bro_api.py.new').write_bytes(b'half a file')
        with self.assertRaises(ValueError):
            install_patch.apply(code)
        install_patch.rollback(code)
        self.assertEqual(self.folder(code), before)
        code = code_folder()
        install_patch.apply(code)
        (code / ('ops_work.py' + install_patch.SUFFIX)).write_bytes(b'not the original')
        state = self.folder(code)
        with self.assertRaises(ValueError):
            install_patch.rollback(code)                   # a saved copy that is not the known version is never written back
        self.assertEqual(self.folder(code), state)

    def test_command_line_refuses_a_folder_with_something_in_the_way_and_changes_nothing(self):
        code = code_folder()
        (code / 'bro_worker.py.new').write_bytes(b'left from an interrupted run')
        before = self.folder(code)
        for action in ('check', 'apply'):
            r = subprocess.run([sys.executable, str(HERE / 'install_patch.py'), '--code', str(code), action], capture_output=True, timeout=60)
            self.assertEqual((r.returncode, r.stdout[:8]), (2, b'REFUSED:'), r.stdout)
            self.assertIn(b'run rollback first', r.stdout)
            self.assertEqual(self.folder(code), before)

    def test_ops_views_is_not_part_of_the_patch(self):
        self.assertNotIn('ops_views.py', set(install_patch.BASE) | set(install_patch.ADDED))
        self.assertEqual(sorted(install_patch.BASE), ['bro_api.py', 'bro_worker.py', 'ops_work.py', 'test_bro_http.py'])


class Queue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:%d' % cls.server.server_address[1]
        cls.cfg = {'beget_api': base + '/beget', 'metrica_api': base + '/metrica', 'webmaster_api': base + '/webmaster',
                   'timeout': 5, 'retry_wait': 0.01, 'require_https': False}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.db = self.folder / 'runtime.sqlite'
        self.ops = ops_work.Operations(self.db)
        self.day = ops_api.today()
        self.ops.plan(self.day)
        Fake.mode, Fake.seen = {}, []

    def tasks(self):
        return {t['job']: t for t in self.ops.report(self.day)['tasks']}

    def run_api(self, **mode):
        Fake.mode = mode
        return {r['job']: r for r in ops_api.run_api(self.ops, self.day, dict(SECRETS), self.cfg)['results']}

    def rows(self, table):
        with sqlite3.connect(self.db) as c:
            return c.execute('SELECT * FROM %s ORDER BY rowid' % table).fetchall()

    def test_new_days_are_planned_with_the_api_kind(self):
        kinds = {job: t['kind'] for job, t in self.tasks().items()}
        self.assertEqual({j for j, k in kinds.items() if k == 'API_READ'}, set(API))
        self.assertEqual((kinds['YANDEX_BUSINESS'], kinds['YANDEX_DIRECT'], kinds['AVITO'], kinds['LOCAL_LEDGER'], kinds['DAILY_REPORT']),
                         ('BROWSER_READ', 'BROWSER_READ', 'BROWSER_READ', 'LOCAL_READ', 'PREPARE'), 'no new Maps job, nothing else moved')
        self.assertEqual(len(kinds), 10)

    def test_all_three_jobs_done_with_machine_evidence_and_a_second_run_adds_nothing(self):
        results = self.run_api()
        self.assertEqual({j: r['outcome'] for j, r in results.items()}, dict.fromkeys(API, 'DONE'))
        tasks = self.tasks()
        for job in API:
            task = tasks[job]
            self.assertEqual((task['status'], task['worker'], task['lease_until']), ('DONE', None, None))
            (obs,) = task['observations']
            self.assertEqual((obs['trust'], obs['source']), ('MACHINE_OBSERVED', ops_api.SOURCES[job]))
            self.assertRegex(obs['actor'], r'^API_READ:[a-f0-9]{32}$')
            entry = json.loads(obs['summary'])
            self.assertEqual((entry['status'], entry['fetched_at']), ('OK', obs['observed_at']))
        metrica = json.loads(tasks['METRICA']['observations'][0]['summary'])
        self.assertEqual(set(metrica['sections']), {'site', 'yandex_maps_card'}, 'two evidence sections in the one METRICA job')
        self.assertEqual(metrica['sections']['site']['evidence']['yesterday']['values']['visits'], 15)
        self.assertEqual(json.loads(tasks['HOSTING_DEADLINES']['observations'][0]['summary'])['evidence']['days_to_block']['value'], 41)
        self.assertEqual({j for j, t in tasks.items() if t['status'] != 'PENDING'}, set(API), 'every other task is untouched')
        observations, events = self.rows('ops_observations'), self.rows('ops_events')
        again = self.run_api()
        self.assertEqual({j: r['outcome'] for j, r in again.items()}, dict.fromkeys(API, 'NOT_CLAIMABLE'))
        self.assertEqual((self.rows('ops_observations'), self.rows('ops_events')), (observations, events), 'a repeated run writes nothing')

    def test_a_task_planned_before_the_api_kind_is_left_alone(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE ops_tasks SET kind='BROWSER_READ' WHERE job='METRICA'")     # as today's real rows are
        results = self.run_api()
        self.assertEqual(set(results), {'HOSTING_DEADLINES', 'WEBMASTER'})
        metrica = self.tasks()['METRICA']
        self.assertEqual((metrica['status'], metrica['revision'], metrica['observations']), ('PENDING', 0, []))

    def test_partial_metrica_keeps_the_good_section_and_is_blocked_then_done_on_a_later_run(self):
        results = self.run_api(metrica='maps403')
        self.assertEqual((results['METRICA']['outcome'], results['METRICA']['reading']), ('BLOCKED', 'PARTIAL'))
        task = self.tasks()['METRICA']
        self.assertEqual(task['status'], 'BLOCKED')
        entry = json.loads(task['observations'][0]['summary'])
        self.assertEqual(entry['sections']['site']['evidence']['last_7_days']['values']['visits'], 15)
        self.assertEqual((entry['sections']['yandex_maps_card']['status'], entry['sections']['yandex_maps_card']['error_code']), ('BLOCKED', 'HTTP_403'))
        self.assertNotIn('evidence', entry['sections']['yandex_maps_card'])
        results = self.run_api()
        self.assertEqual(set(results) and results['METRICA']['outcome'], 'DONE')
        task = self.tasks()['METRICA']
        self.assertEqual((task['status'], len(task['observations'])), ('DONE', 2))

    def test_real_zero_is_recorded_and_a_missing_metric_is_blocked_without_a_number(self):
        self.run_api(metrica='zero')
        entry = json.loads(self.tasks()['METRICA']['observations'][0]['summary'])
        self.assertEqual(entry['sections']['site']['evidence']['yesterday']['values']['visits'], 0)
        self.assertEqual(self.tasks()['METRICA']['status'], 'DONE')
        self.setUp()
        results = self.run_api(metrica='short', beget='no_days', webmaster='no_sqi')
        self.assertEqual({j: (r['outcome'], r['error_code']) for j, r in results.items() if j != 'METRICA'},
                         {'HOSTING_DEADLINES': ('BLOCKED', 'METRIC_MISSING'), 'WEBMASTER': ('BLOCKED', 'METRIC_MISSING')})
        for job in API:
            summary = self.tasks()[job]['observations'][0]['summary']
            self.assertNotIn('"value"', summary, job)
            self.assertNotIn('"values"', summary, job)

    def test_service_error_text_and_secrets_never_reach_the_database(self):
        self.run_api(beget='refuse', metrica='http403')
        dump = json.dumps([self.rows(t) for t in ('ops_tasks', 'ops_observations', 'ops_events')], ensure_ascii=False)
        self.assertNotIn(TOKEN, dump)
        self.assertNotIn(PASSWORD, dump)
        self.assertNotIn('forbidden', dump, "the service's own error body is not recorded")
        self.assertEqual(json.loads(self.tasks()['HOSTING_DEADLINES']['observations'][0]['summary'])['error_code'], 'API_ERROR')
        self.setUp()
        results = self.run_api(webmaster='leak')
        self.assertEqual((results['WEBMASTER']['outcome'], results['WEBMASTER']['error_code']), ('BLOCKED', 'SECRET_IN_REPORT'))
        self.assertNotIn(TOKEN, json.dumps(self.rows('ops_observations')))

    def test_two_runs_at_once_record_every_task_exactly_once(self):
        outcomes, errors = [], []
        def one():
            try:
                outcomes.append(ops_api.run_api(ops_work.Operations(self.db), self.day, dict(SECRETS), self.cfg)['results'])
            except Exception as error:                     # pragma: no cover - shown by the assertion below
                errors.append(repr(error))
        threads = [threading.Thread(target=one) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(errors, [])
        tasks = self.tasks()
        for job in API:
            self.assertEqual((tasks[job]['status'], len(tasks[job]['observations'])), ('DONE', 1), job)
            got = sorted(r['outcome'] for run in outcomes for r in run if r['job'] == job)
            self.assertEqual(got.count('DONE'), 1, job)
            self.assertTrue(set(got) <= {'DONE', 'CLAIM_LOST', 'NOT_CLAIMABLE'}, got)

    def test_expired_lease_passes_to_a_new_attempt_and_the_late_result_is_refused(self):
        real, state = ops_api.R.read_job, {}
        def slow(job, secrets, cfg=None, now=None):
            entry = real(job, secrets, cfg, now)
            if job == 'METRICA' and not state:
                state['first'] = self.tasks()['METRICA']['worker']
                with sqlite3.connect(self.db) as c:        # the first attempt's lease runs out while it is still reading
                    c.execute("UPDATE ops_tasks SET lease_until=? WHERE job='METRICA'", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
                state['second'] = {r['job']: r for r in ops_api.run_api(ops_work.Operations(self.db), self.day, dict(SECRETS), self.cfg)['results']}
            return entry
        with patch.object(ops_api.R, 'read_job', slow):
            first = {r['job']: r for r in ops_api.run_api(self.ops, self.day, dict(SECRETS), self.cfg)['results']}
        self.assertEqual(state['second']['METRICA']['outcome'], 'DONE')
        self.assertEqual(first['METRICA']['outcome'], 'LEASE_LOST', 'the stale result is not written')
        task = self.tasks()['METRICA']
        (obs,) = task['observations']
        self.assertNotEqual(obs['actor'], state['first'])
        self.assertEqual(task['status'], 'DONE')
        with self.assertRaises(ValueError):                # and the queue itself refuses a resend under the old name
            self.ops.observe(task['id'], state['first'], 'x', ops_work.now(), 'x', machine=True)
        self.assertEqual(len(self.tasks()['METRICA']['observations']), 1)

    def test_lease_is_long_enough_and_still_inside_the_queue_limit(self):
        cfg = ops_api.R.CONFIG
        worst = 4 * ((cfg['retries'] + 1) * cfg['timeout'] + sum(cfg['retry_wait'] * n for n in range(1, cfg['retries'] + 1)))
        self.assertLess(worst, ops_api.LEASE)
        self.assertLessEqual(ops_api.LEASE, 1800)

    def test_machine_evidence_is_still_refused_for_browser_tasks(self):
        task = self.tasks()['YANDEX_BUSINESS']
        self.ops.claim(task['id'], 'someone')
        with self.assertRaises(ValueError):
            self.ops.observe(task['id'], 'someone', 'x', ops_work.now(), 'x', machine=True)

    def test_only_the_current_day_can_be_read(self):
        yesterday = (datetime.now(ops_api.YEREVAN).date() - timedelta(days=1)).isoformat()
        self.ops.plan(yesterday)
        for call in (lambda: ops_api.run_api(self.ops, yesterday, dict(SECRETS), self.cfg), lambda: ops_api.dry_run(self.db, yesterday, dict(SECRETS), self.cfg)):
            with self.assertRaises(ValueError):
                call()
        self.assertEqual(Fake.seen, [])
        self.assertEqual(self.rows('ops_observations'), [])

    def test_browser_worker_cannot_see_or_claim_api_tasks(self):
        queue = bro_api.Queue(self.db, clock=lambda: datetime.now(timezone.utc))
        listing = queue.listing()
        self.assertEqual({t['job'] for t in listing['tasks']}, {'YANDEX_BUSINESS', 'YANDEX_DIRECT', 'DAILY_REPORT'})
        self.assertTrue(set(API) <= {s['job'] for s in listing['daily_statuses']}, 'their status is still shown')
        tasks = self.tasks()
        request = lambda job, n: {'request_id': '%032x' % n, 'run_id': '%032x' % (n + 100), 'task_id': tasks[job]['id'], 'day': queue.day()}
        if queue.day() == self.day:                        # Yerevan day on both sides
            for n, job in enumerate(API):
                with self.assertRaises(PermissionError):
                    queue.apply('bro-win', 'claim', request(job, n))
            self.assertEqual(queue.apply('bro-win', 'claim', request('YANDEX_BUSINESS', 9))['status'], 'CLAIMED')
        self.assertEqual({j: self.tasks()[j]['status'] for j in API}, dict.fromkeys(API, 'PENDING'))

    def test_local_adapter_bridge_never_takes_api_tasks(self):
        def adapter(command, request, timeout):
            return dict(task_id=request['task']['id'], status='BLOCKED', source='TEST fixture', observed_at=ops_work.now(), summary='TEST')
        taken = []
        with patch('bro_worker.adapter_call', side_effect=adapter):
            for _ in range(10):
                result = bro_worker.run_one(self.ops, self.day, ['TEST'])
                if result['status'] == 'IDLE':
                    break
                taken.append(self.ops.get(result['task_id'])['job'])
        self.assertEqual(sorted(taken), ['YANDEX_BUSINESS', 'YANDEX_DIRECT'])
        self.assertEqual({j: self.tasks()[j]['status'] for j in API}, dict.fromkeys(API, 'PENDING'))

    def test_dry_run_reads_for_real_and_writes_nothing(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE ops_tasks SET kind='BROWSER_READ',status='DONE' WHERE job='WEBMASTER'")
        c = sqlite3.connect(self.db, isolation_level=None)
        c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        c.close()
        before = (self.db.read_bytes(), self.rows('ops_tasks'), self.rows('ops_observations'), self.rows('ops_events'))
        Fake.mode = {'metrica': 'maps403'}
        result = ops_api.dry_run(self.db, self.day, dict(SECRETS), self.cfg)
        self.assertEqual((self.db.read_bytes(), self.rows('ops_tasks'), self.rows('ops_observations'), self.rows('ops_events')), before)
        got = {r['job']: r for r in result['results']}
        self.assertEqual((got['HOSTING_DEADLINES']['would_write'], got['HOSTING_DEADLINES']['would_set']), (True, 'DONE'))
        self.assertEqual((got['METRICA']['would_write'], got['METRICA']['would_set'], got['METRICA']['reading']['status']), (True, 'BLOCKED', 'PARTIAL'))
        self.assertEqual(got['WEBMASTER']['would_write'], False)
        self.assertIn('BROWSER_READ', got['WEBMASTER']['why'])
        self.assertEqual(got['WEBMASTER']['reading']['status'], 'OK')
        self.assertTrue(Fake.seen, 'the readings were really made')
        self.assertNotIn(TOKEN, json.dumps(result))

    def test_command_line_needs_an_explicit_mode_and_refuses_secrets_that_can_act(self):
        bad = self.folder / 'bad.json'
        bad.write_text(json.dumps(dict(SECRETS, yandex_actions_token='y0_x')), encoding='utf-8')
        if os.name == 'posix':
            os.chmod(bad, 0o640)
        run = lambda *extra: subprocess.run([sys.executable, str(CODE / 'ops_api.py'), '--db', str(self.db), '--secrets', str(bad), *extra],
                                            capture_output=True, timeout=60, cwd=str(CODE))
        self.assertEqual(run().returncode, 2, 'neither --dry-run nor --write: nothing happens')
        self.assertNotEqual(run('--dry-run', '--write').returncode, 0)
        r = run('--write')
        self.assertEqual(r.returncode, 2)
        self.assertIn(b'SECRETS_NOT_READ_ONLY', r.stdout)
        self.assertEqual(self.rows('ops_observations'), [])
        self.assertNotIn(TOKEN.encode(), r.stdout + r.stderr)


class Provision(unittest.TestCase):
    def test_two_separate_files_that_the_collector_can_load(self):
        folder = Path(tempfile.mkdtemp()) / 'readers'
        self.assertEqual(reader_provision.provision(dict(SECRETS), folder), ['beget-read.json', 'yandex-read.json'])
        self.assertEqual(json.loads((folder / 'beget-read.json').read_text()), {'beget_login': 'amo777z0', 'beget_api_password': PASSWORD})
        self.assertEqual(json.loads((folder / 'yandex-read.json').read_text()), {'yandex_read_token': TOKEN})
        self.assertEqual(ops_api.R.load_secrets(folder / 'beget-read.json', folder / 'yandex-read.json'), SECRETS)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['beget-read.json', 'yandex-read.json'])
        if os.name == 'posix':
            self.assertEqual([oct(p.stat().st_mode & 0o777) for p in (folder, folder / 'beget-read.json', folder / 'yandex-read.json')], ['0o750', '0o640', '0o640'])
            os.chmod(folder / 'yandex-read.json', 0o644)
            with self.assertRaises(ops_api.R.Blocked) as caught:
                ops_api.R.load_secrets(folder / 'yandex-read.json')
            self.assertEqual(caught.exception.code, 'SECRETS_OPEN_TO_ALL')
        reader_provision.provision(dict(SECRETS, yandex_read_token='y0_SECOND'), folder)       # replacing works
        self.assertEqual(json.loads((folder / 'yandex-read.json').read_text()), {'yandex_read_token': 'y0_SECOND'})

    def test_anything_that_can_act_or_looks_wrong_is_refused_and_nothing_is_printed(self):
        folder = Path(tempfile.mkdtemp()) / 'readers'
        for data in (dict(SECRETS, yandex_actions_token='y0_ACTIONS'), dict(SECRETS, mail_app_password='x'), {'yandex_read_token': TOKEN},
                     dict(SECRETS, beget_api_password='two words'), dict(SECRETS, yandex_read_token=''), [1]):
            with self.assertRaises(ValueError) as caught:
                reader_provision.provision(data, folder)
            self.assertNotIn('y0_ACTIONS', str(caught.exception))
            self.assertNotIn(TOKEN, str(caught.exception))
        self.assertFalse(folder.exists() and list(folder.iterdir()))
        for payload, code, word in ((json.dumps(SECRETS), 0, b'written: beget-read.json, yandex-read.json'),
                                    (json.dumps(dict(SECRETS, yandex_actions_token='y0_ACTIONS')), 2, b'REFUSED'), ('{', 2, b'REFUSED')):
            r = subprocess.run([sys.executable, str(HERE / 'reader_provision.py'), '--dir', str(folder)], input=payload.encode(), capture_output=True, timeout=60)
            self.assertEqual(r.returncode, code)
            self.assertIn(word, r.stdout)
            for secret in (TOKEN, PASSWORD, 'y0_ACTIONS'):
                self.assertNotIn(secret.encode(), r.stdout + r.stderr)

    def test_secrets_are_not_accepted_on_the_command_line(self):
        source = (HERE / 'reader_provision.py').read_text(encoding='utf-8')
        self.assertEqual(source.count('add_argument('), 2)
        self.assertIn("add_argument('--dir'", source)
        self.assertIn("add_argument('--group')", source)
        self.assertIn('sys.stdin.isatty()', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
