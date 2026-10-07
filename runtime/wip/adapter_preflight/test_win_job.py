"""Synthetic Windows Job Object tests (v3). Only python.exe children that sleep or print; no Claude, no Chrome, no network."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import win_job

PY = sys.executable
HERE = Path(__file__).resolve().parent
ENV = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR') if k in os.environ}

# A process that records its pid, optionally starts one more level with the given creation flags, then sleeps.
TREE = r'''
import os, subprocess, sys, time
folder, depth, flags = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
open(os.path.join(folder, 'pid-%d-%d' % (depth, os.getpid())), 'w').close()
if depth > 0:
    try:
        subprocess.Popen([sys.executable, __file__, folder, str(depth - 1), str(flags)], creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        open(os.path.join(folder, 'spawn-refused-%d' % e.winerror), 'w').close()
time.sleep(120)
'''

# Starts a tree, then floods stdout for ever.
FLOOD = r'''
import os, subprocess, sys
folder = sys.argv[1]
open(os.path.join(folder, 'pid-9-%d' % os.getpid()), 'w').close()
subprocess.Popen([sys.executable, sys.argv[2], folder, '1', '0'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import glob, time
while len(glob.glob(os.path.join(folder, 'pid-*'))) < 3:
    time.sleep(0.05)      # the whole tree is up before the flood starts
while True:
    sys.stdout.write('x' * 65536); sys.stdout.flush()
'''

SUPERVISOR = r'''
import os, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
import win_job
job = win_job.Job()
p = subprocess.Popen([sys.executable, sys.argv[2], sys.argv[3], '2', '0'])
job.assign(p._handle)
time.sleep(1.5)
os._exit(3)   # dies without terminating the job: KILL_ON_JOB_CLOSE must do it
'''

CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


class JobTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.dir.name)
        self.tree = self.folder / 'tree.py'
        self.tree.write_text(TREE, encoding='utf-8')
        self.started = []

    def tearDown(self):
        for pid in self.pids() + [p.pid for p in self.started]:
            if win_job.pid_alive(pid):
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        self.dir.cleanup()

    def pids(self):
        return [int(f.name.rsplit('-', 1)[1]) for f in self.folder.glob('pid-*')]

    def wait_dead(self, pids, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and any(win_job.pid_alive(p) for p in pids):
            time.sleep(0.05)
        return [p for p in pids if win_job.pid_alive(p)]

    def spy_popen(self):
        """Record every process win_job starts, so a test can prove it is gone."""
        real = subprocess.Popen

        def spy(*a, **k):
            p = real(*a, **k)
            self.started.append(p)
            return p
        return mock.patch.object(win_job.subprocess, 'Popen', side_effect=spy)

    # ---------------- v1 behaviour, now with the mandatory environment
    def test_normal_run_returns_output_and_leaves_nothing(self):
        r = win_job.run_in_job([PY, '-c', 'import sys; sys.stdout.write(sys.stdin.read().upper())'], stdin=b'ok', timeout=30, env=ENV)
        self.assertEqual((r['returncode'], r['stdout'], r['timed_out'], r['survivors'], r['cleanup']), (0, b'OK', False, 0, 'job'))

    def test_exit_code_passes_through(self):
        r = win_job.run_in_job([PY, '-c', 'raise SystemExit(7)'], timeout=30, env=ENV)
        self.assertEqual((r['returncode'], r['timed_out'], r['survivors']), (7, False, 0))

    def test_timeout_ends_three_level_tree(self):
        started = time.monotonic()
        r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=3, env=ENV)
        self.assertTrue(r['timed_out']); self.assertIsNone(r['returncode']); self.assertEqual(r['survivors'], 0)
        self.assertLess(time.monotonic() - started, 10)
        pids = self.pids()
        self.assertEqual(len(pids), 3, 'three levels must have started')
        self.assertEqual(self.wait_dead(pids), [])
        self.assertGreaterEqual(len(r['peak_pids']), 4, 'stub + three levels were inside the job')
        self.assertGreaterEqual(len(r['peak_created']), 4, 'a creation time was taken for them')
        self.assertTrue(set(map(int, r['peak_created'])) <= set(r['peak_pids']))
        for times in r['peak_created'].values():
            for when in times:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(when)).total_seconds()
                self.assertTrue(0 <= age < 60, 'created during this test: %s' % when)

    def test_detached_and_new_group_children_are_ended(self):
        flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', str(flags)], timeout=3, env=ENV)
        self.assertEqual(r['survivors'], 0)
        self.assertEqual(len(self.pids()), 3)
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_no_window_children_are_ended(self):
        r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '1', str(CREATE_NO_WINDOW)], timeout=3, env=ENV)
        self.assertEqual(r['survivors'], 0)
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_breakaway_attempt_does_not_escape(self):
        r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '1', str(CREATE_BREAKAWAY_FROM_JOB)], timeout=3, env=ENV)
        self.assertEqual(r['survivors'], 0)
        refused = list(self.folder.glob('spawn-refused-*'))
        pids = self.pids()
        self.assertTrue(refused or len(pids) == 2, 'breakaway child neither refused nor started')
        self.assertEqual(self.wait_dead(pids), [])
        print('\n  breakaway outcome:', 'refused ' + ','.join(f.name for f in refused) if refused else 'started inside job and ended', file=sys.stderr)

    def test_supervisor_death_ends_tree(self):
        sup = self.folder / 'sup.py'
        sup.write_text(SUPERVISOR, encoding='utf-8')
        code = subprocess.run([PY, str(sup), str(HERE), str(self.tree), str(self.folder)], timeout=30).returncode
        self.assertEqual(code, 3)
        pids = self.pids()
        self.assertEqual(len(pids), 3)
        self.assertEqual(self.wait_dead(pids), [])

    def test_process_outside_the_job_survives(self):
        outsider = subprocess.Popen([PY, '-c', 'import time; time.sleep(60)'])
        try:
            r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '1', '0'], timeout=2, env=ENV)
            self.assertEqual(r['survivors'], 0)
            self.assertNotIn(outsider.pid, r['peak_pids'])
            self.assertTrue(win_job.pid_alive(outsider.pid))
        finally:
            outsider.kill(); outsider.wait()

    def test_unreadable_creation_time_is_unknown_never_gone(self):
        # Simulation: the process is real and alive; the reading of its creation time is replaced by "could not be read".
        live = subprocess.Popen([PY, '-c', 'import time; time.sleep(60)'])
        try:
            with mock.patch.object(win_job, '_created', return_value=None):
                self.assertEqual(win_job.pid_state(live.pid, {1}), 'unknown')
                self.assertTrue(win_job.pid_alive(live.pid, {1}), 'never "not alive"')
                self.assertEqual(win_job.pid_state(live.pid), 'alive', 'without recorded times the pid alone decides, as before')
                survivors, how, unidentified = win_job._cleanup(win_job.Job(), None, {live.pid}, wait=0.3, born={live.pid: {1}})
            self.assertEqual((survivors, unidentified), (1, [live.pid]), 'counted as a survivor and named as unidentified')
            self.assertEqual(win_job.pid_state(live.pid, {1}), 'gone', 'time readable and different: another process under the pid')
            survivors, how, unidentified = win_job._cleanup(win_job.Job(), None, {live.pid}, wait=0.3, born={live.pid: {1}})
            self.assertEqual((survivors, unidentified), (0, []))
        finally:
            live.kill(); live.wait()
        self.assertEqual(win_job.pid_state(live.pid, {1}), 'gone')

    def test_result_names_unidentified_pids(self):
        r = win_job.run_in_job([PY, '-c', 'pass'], timeout=30, env=ENV)
        self.assertEqual((r['survivors'], r['unidentified']), (0, []))

    def test_relative_executable_is_refused(self):
        with self.assertRaises(ValueError):
            win_job.run_in_job(['python', '-c', 'pass'], env=ENV)

    # ---------------- 4a. cleaned environment is mandatory
    def test_environment_is_mandatory(self):
        for bad in (None, [], 'SystemRoot=C:\\Windows'):
            with self.assertRaises(ValueError):
                win_job.run_in_job([PY, '-c', 'pass'], env=bad)
        with self.assertRaises(ValueError):
            win_job.run_in_job([PY, '-c', 'pass'], env={'WINDIR': ENV['WINDIR']})          # no SystemRoot

    def test_names_outside_the_allow_list_are_refused(self):
        for name in ('USERPROFILE', 'PATH', 'HOME', 'APPDATA', 'BRO_ANYTHING'):
            with self.assertRaises(ValueError, msg=name):
                win_job.run_in_job([PY, '-c', 'pass'], env={**ENV, name: 'x'})

    def test_secret_like_names_are_refused_even_when_listed(self):
        for name in ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN', 'BRO_PASSWORD', 'MY_SECRET', 'AUTHORIZATION', 'GH_TOKEN', 'SSH_PRIVATE_KEY'):
            with self.assertRaises(ValueError, msg=name):
                win_job.run_in_job([PY, '-c', 'pass'], env={**ENV, name: 'fake'}, extra_env_names=[name])

    def test_parent_environment_does_not_leak(self):
        os.environ['BRO_FAKE_SECRET_VALUE'] = 'fake-value-for-test'
        try:
            r = win_job.run_in_job([PY, '-I', '-c', 'import os, json; print(json.dumps(sorted(os.environ)))'], timeout=30, env=ENV)
        finally:
            del os.environ['BRO_FAKE_SECRET_VALUE']
        names = [n.upper() for n in json.loads(r['stdout'])]
        self.assertNotIn('BRO_FAKE_SECRET_VALUE', names)
        self.assertNotIn('USERPROFILE', names)
        self.assertNotIn('APPDATA', names)

    def test_explicitly_listed_extra_name_is_passed(self):
        r = win_job.run_in_job([PY, '-I', '-c', 'import os; print(os.environ.get("BRO_PROFILE_DIR"))'], timeout=30,
                               env={**ENV, 'BRO_PROFILE_DIR': 'C:\\fake\\profile'}, extra_env_names=['BRO_PROFILE_DIR'])
        self.assertEqual(r['stdout'].strip(), b'C:\\fake\\profile')

    # ---------------- 4b. output limit enforced while the command runs
    def test_flood_is_stopped_during_the_run(self):
        flood = self.folder / 'flood.py'
        flood.write_text(FLOOD, encoding='utf-8')
        started = time.monotonic()
        with self.assertRaises(win_job.OutputLimit) as caught:
            win_job.run_in_job([PY, str(flood), str(self.folder), str(self.tree)], timeout=120, env=ENV, max_output=32768)
        self.assertLess(time.monotonic() - started, 15, 'must not wait for the 120 s timeout')
        result = caught.exception.result
        self.assertEqual((result['survivors'], result['stdout'], result['returncode']), (0, b'', None))
        self.assertEqual(len(self.pids()), 3, 'flooder and its two descendants had started')
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_output_exactly_at_the_limit_is_accepted(self):
        r = win_job.run_in_job([PY, '-c', 'import sys; sys.stdout.write("x" * 1000)'], timeout=30, env=ENV, max_output=1000)
        self.assertEqual(len(r['stdout']), 1000)
        with self.assertRaises(win_job.OutputLimit):
            win_job.run_in_job([PY, '-c', 'import sys; sys.stdout.write("x" * 1001)'], timeout=30, env=ENV, max_output=1000)

    def test_large_stdin_does_not_deadlock(self):
        r = win_job.run_in_job([PY, '-c', 'import sys; print(len(sys.stdin.buffer.read()))'], stdin=b'a' * 500000, timeout=30, env=ENV)
        self.assertEqual(r['stdout'].strip(), b'500000')

    # ---------------- 4c. cleanup when starting or terminating goes wrong
    def test_target_that_cannot_start(self):
        r = win_job.run_in_job([str(self.folder / 'no-such-program.exe')], timeout=30, env=ENV)
        self.assertEqual((r['returncode'], r['survivors'], r['timed_out']), (win_job.TARGET_START_FAILED_EXIT, 0, False))

    def test_assign_failure_leaves_no_process(self):
        with self.spy_popen(), mock.patch.object(win_job.Job, 'assign', side_effect=OSError(5, 'injected')):
            with self.assertRaises(OSError):
                win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=30, env=ENV)
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.wait_dead([self.started[0].pid]), [])
        self.assertEqual(self.pids(), [], 'the real command must never have started')

    def test_release_failure_leaves_no_process(self):
        with self.spy_popen(), mock.patch.object(win_job, '_release', side_effect=OSError(13, 'injected')):
            with self.assertRaises(OSError):
                win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=30, env=ENV)
        self.assertEqual(self.wait_dead([self.started[0].pid]), [])
        self.assertEqual(self.pids(), [])

    def test_terminate_failure_falls_back_and_still_ends_the_tree(self):
        with mock.patch.object(win_job.Job, 'terminate', side_effect=OSError(5, 'injected')):
            r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=3, env=ENV)
        self.assertEqual((r['cleanup'], r['survivors'], r['timed_out']), ('fallback', 0, True))
        self.assertEqual(len(self.pids()), 3)
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_pid_listing_failure_does_not_stop_cleanup(self):
        with mock.patch.object(win_job.Job, 'pids', side_effect=OSError(5, 'injected')):
            r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=3, env=ENV)
        self.assertEqual(r['survivors'], 0)
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_interrupt_during_the_run_still_cleans_up(self):
        calls = {'n': 0}
        real_sleep = time.sleep

        def interrupting(seconds):
            calls['n'] += 1
            if calls['n'] == 40:
                raise KeyboardInterrupt
            real_sleep(seconds)
        with mock.patch.object(win_job.time, 'sleep', side_effect=interrupting):
            with self.assertRaises(KeyboardInterrupt):
                win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=60, env=ENV)
        self.assertGreaterEqual(len(self.pids()), 1)
        self.assertEqual(self.wait_dead(self.pids()), [])

    # ---------------- v3: reader / writer thread errors are failures, never hidden
    def test_normal_run_reports_no_io_errors(self):
        r = win_job.run_in_job([PY, '-c', 'print(1)'], timeout=30, env=ENV)
        self.assertEqual((r['returncode'], r['io_errors']), (0, []))

    def test_output_reader_error_is_a_failure(self):
        for error in (OSError(6, 'injected'), ValueError('injected'), RuntimeError('injected')):
            for f in self.folder.glob('pid-*'):
                f.unlink()
            with mock.patch.object(win_job, '_read_block', side_effect=error):
                with self.assertRaises(win_job.JobIOError) as caught:
                    win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], timeout=60, env=ENV)
            result = caught.exception.result
            self.assertIn('output reader: ' + type(error).__name__, result['io_errors'])
            self.assertEqual((result['returncode'], result['stdout'], result['survivors']), (None, b'', 0))
            self.assertEqual(self.wait_dead(self.pids()), [])

    def test_reader_error_is_not_masked_by_a_clean_exit(self):
        # The command itself ends with code 0 and prints a valid-looking answer; the reader failed.
        with mock.patch.object(win_job, '_read_block', side_effect=OSError(6, 'injected')):
            with self.assertRaises(win_job.JobIOError) as caught:
                win_job.run_in_job([PY, '-c', 'print("{}")'], timeout=30, env=ENV)
        self.assertEqual((caught.exception.result['returncode'], caught.exception.result['stdout']), (None, b''))

    def test_input_writer_error_is_a_failure(self):
        started = time.monotonic()
        with mock.patch.object(win_job, '_write_all', side_effect=OSError(232, 'injected')):
            with self.assertRaises(win_job.JobIOError) as caught:
                win_job.run_in_job([PY, str(self.tree), str(self.folder), '2', '0'], stdin=b'{}', timeout=60, env=ENV)
        self.assertLess(time.monotonic() - started, 20, 'must not wait for the 60 s timeout')
        self.assertIn('input writer: OSError', caught.exception.result['io_errors'])
        self.assertEqual(caught.exception.result['survivors'], 0)
        self.assertEqual(self.wait_dead(self.pids()), [])

    def test_input_that_was_never_read_is_a_failure(self):
        # Real case, nothing injected: the command exits at once and leaves 2 MB of input unread.
        with self.assertRaises(win_job.JobIOError) as caught:
            win_job.run_in_job([PY, '-c', 'print("done without reading")'], stdin=b'a' * 2000000, timeout=30, env=ENV)
        self.assertTrue(any(e.startswith('input writer: ') for e in caught.exception.result['io_errors']))
        self.assertEqual(caught.exception.result['stdout'], b'')

    def test_timeout_result_carries_io_errors_field(self):
        r = win_job.run_in_job([PY, str(self.tree), str(self.folder), '0', '0'], timeout=2, env=ENV)
        self.assertTrue(r['timed_out'])
        self.assertIsNone(r['returncode'])
        self.assertIn('io_errors', r)

    def test_stderr_goes_to_the_given_file_only(self):
        target = self.folder / 'stderr.txt'
        r = win_job.run_in_job([PY, '-c', 'import sys; sys.stderr.write("diagnostic line"); print("out")'], timeout=30, env=ENV, stderr_path=str(target))
        self.assertEqual(r['stdout'].strip(), b'out')
        self.assertEqual(target.read_bytes(), b'diagnostic line')

    def test_bad_limits_are_refused(self):
        for kw in ({'timeout': 0}, {'timeout': 601}, {'timeout': 1.5}, {'max_output': 0}, {'max_output': 2 ** 21}):
            with self.assertRaises(ValueError, msg=kw):
                win_job.run_in_job([PY, '-c', 'pass'], env=ENV, **kw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
