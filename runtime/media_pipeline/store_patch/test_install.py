"""install.sh in its rehearsal mode: a temporary code folder, no services, no ownership. Linux (bash, coreutils).

What it shows: the checksum gates, both files changing together, the kept copies, the way back, a second run, a
failed self-test putting both originals back.

The second class runs the script in its real mode with stand-ins for systemctl, curl, runuser, id, stat, install,
pgrep, ps and sleep put first in PATH. It shows what the script ASKS for and what it does with each answer: which
unit it restarts, as whom the self-test runs, that a one-shot unit started from outside at any moment of the install
does not start, what happens when the service dies or stops answering with the new files, and what happens when a
step of putting the originals back fails. It does not show that the real systemd or the real service behave like
the stand-ins: that is tried on the server by trial_on_server.sh, in a temporary place.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parents[1] / 'server'
OLD = {'ops_media.py': '5ca3e4dea8b0b11040a4a85ff0985c4c881ac80348abfaf7c8058cca2dbbda4c', 'ops_work.py': 'd1e6a2dfa653f40ddbf886c170e8c0d143b1750ad59c1703c647313f7e8818d6'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipIf(os.name == 'nt' and not os.environ.get('KRYUK_TEST_INSTALL_ON_WINDOWS'), 'the install script is a Linux script')
class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.code = Path(self.tmp.name) / 'code'
        self.code.mkdir()
        for name in ('ops_media.py', 'ops_work.py', 'runtime.py', 'contact_metrics.py'):
            shutil.copyfile(SERVER / name, self.code / name)
        self.package = Path(self.tmp.name) / 'package'
        shutil.copytree(HERE, self.package, ignore=shutil.ignore_patterns('__pycache__'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args, package=None, code=None):
        env = {**os.environ, 'KRYUK_CODE_DIR': str(code or self.code), 'KRYUK_INSTALL_REHEARSAL': '1', 'KRYUK_PYTHON': sys.executable}
        done = subprocess.run([os.environ.get('KRYUK_BASH', 'bash'), str((package or self.package) / 'install.sh'), *args], env=env, capture_output=True, text=True, timeout=180)
        return done.returncode, done.stdout + done.stderr

    def state(self):
        return {name: ('original' if sha(self.code / name) == OLD[name] else 'new' if sha(self.code / name) == sha(HERE / name) else 'other') for name in OLD}

    def kept(self):
        return sorted(f.name for f in self.code.glob('*.before-store-lock'))

    def test_the_recorded_files_are_the_ones_the_script_expects(self):
        self.assertEqual({name: sha(SERVER / name) for name in OLD}, OLD)
        text = (HERE / 'install.sh').read_text(encoding='utf-8')
        for name in OLD:
            self.assertIn(OLD[name], text)
            self.assertIn(sha(HERE / name), text, 'install.sh names the checksum of the ' + name + ' beside it')

    def test_install_status_second_run_rollback_and_install_again(self):
        code, out = self.run_script('status')
        self.assertEqual((code, self.state()), (0, {'ops_media.py': 'original', 'ops_work.py': 'original'}), out)
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn('SELFTEST OK', out)
        self.assertIn('INSTALLED at', out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'new', 'ops_work.py': 'new'}, ['ops_media.py.before-store-lock', 'ops_work.py.before-store-lock']))
        self.assertEqual({name: sha(self.code / (name + '.before-store-lock')) for name in OLD}, OLD, 'the kept copies are the originals')
        code, out = self.run_script()
        self.assertEqual((code, 'ALREADY INSTALLED' in out), (0, True), out)
        code, out = self.run_script('rollback')
        self.assertEqual((code, 'ROLLED BACK' in out), (0, True), out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, []))
        code, out = self.run_script('rollback')
        self.assertEqual((code, 'no kept copy' in out), (1, True), out)
        code, out = self.run_script()
        self.assertEqual((code, self.state()['ops_work.py']), (0, 'new'), out)

    def test_it_refuses_installed_files_it_was_not_made_from(self):
        shutil.copyfile(HERE / 'ops_media.py', self.code / 'ops_media.py')            # one new, one original
        code, out = self.run_script()
        self.assertEqual((code, 'not both the originals' in out, self.kept()), (1, True, []), out)
        self.assertEqual(self.state(), {'ops_media.py': 'new', 'ops_work.py': 'original'}, 'nothing was changed')
        shutil.copyfile(SERVER / 'ops_media.py', self.code / 'ops_media.py')
        with (self.code / 'ops_work.py').open('ab') as f:
            f.write(b'\n# changed on the server by somebody\n')
        before = sha(self.code / 'ops_work.py')
        code, out = self.run_script()
        self.assertEqual((code, sha(self.code / 'ops_work.py'), self.kept()), (1, before, []), out)

    def test_it_refuses_new_files_that_are_not_the_reviewed_ones(self):
        with (self.package / 'ops_work.py').open('ab') as f:
            f.write(b'\n# not what was reviewed\n')
        code, out = self.run_script()
        self.assertEqual((code, 'not the reviewed one' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, []))

    def test_a_failed_self_test_puts_both_originals_back(self):
        (self.package / 'selftest.py').write_text("import sys\nprint('SELFTEST FAILED: on purpose')\nsys.exit(1)\n")
        code, out = self.run_script()
        self.assertEqual((code, 'Putting both originals back' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, []), out)

    def test_a_kept_copy_in_the_way_stops_it_and_a_rehearsal_is_refused_on_the_real_folder(self):
        (self.code / 'ops_media.py.before-store-lock').write_text('left by something else')
        code, out = self.run_script()
        self.assertEqual((code, 'already exists' in out, self.state()['ops_media.py']), (1, True, 'original'), out)
        code, out = self.run_script(code='/opt/kryuk24')
        self.assertEqual((code, 'not run on the real code folder' in out), (1, True), out)


HOLD = '90-kryuk-store-lock-install.conf'
ONESHOTS = ['kryuk-api-read.service', 'kryuk-backup.service', 'kryuk-operations.service']
STANDINS = {
    'systemctl': r"""#!/usr/bin/env bash
# A stand-in for systemd: answers from files in $KRYUK_STANDIN and writes every call into its log.
# A one-shot unit that is running is "activating". A unit whose loaded drop-in holds a condition on a file
# that exists is not started (as ConditionPathExists=!file does); a drop-in counts only after daemon-reload.
S="$KRYUK_STANDIN"; echo "systemctl $*" >> "$S/log"
NAME=90-kryuk-store-lock-install.conf
new() { grep -q 'LOCKING=1' "$KRYUK_CODE_DIR/ops_media.py"; }
listed() { grep -qx "$2" "$S/$1" 2>/dev/null; }
u="${@: -1}"
case "$1" in
  is-active) if listed active "$u"; then [ "$2" = --quiet ] || echo active; exit 0; else [ "$2" = --quiet ] || echo inactive; exit 3; fi;;
  is-enabled) echo enabled;;
  show) case "$3" in
      User) cat "$S/user";;
      ActiveState) if listed running "$u"; then echo activating; elif listed active "$u"; then echo active; else echo inactive; fi;;
      DropInPaths) if listed loaded "$u"; then echo "$KRYUK_HOLD_DIR/$u.d/$NAME"; fi;;
      NeedDaemonReload) if listed stale "$u"; then echo yes; else echo no; fi;;
      TriggeredBy) case "$u" in kryuk-operations.service) echo kryuk-operations.timer;; kryuk-backup.service) echo kryuk-backup.timer;; esac;;
      NextElapseUSecRealtime) cat "$S/next-$u" 2>/dev/null || echo "Fri 2036-01-04 00:04:57 UTC";;
      *) echo "stand-in: unexpected systemctl $*" >&2; exit 64;;
    esac;;
  daemon-reload) [ -e "$S/reload-fails" ] && exit 1
    : > "$S/loaded"
    for d in "$KRYUK_HOLD_DIR"/*.d; do [ -e "$d/$NAME" ] && basename "$d" .d >> "$S/loaded"; done
    exit 0;;
  start) if listed loaded "$u" && [ -e "$KRYUK_HOLD_DIR/$u.d/$NAME" ]; then echo "start $u: skipped by its condition" >> "$S/log"; exit 0; fi
    echo "$u" >> "$S/running"
    if new; then echo "start $u: STARTED with the new files on the disk" >> "$S/log"; else echo "start $u: STARTED with the original files on the disk" >> "$S/log"; fi;;
  restart) [ -e "$S/restart-fails" ] && exit 1
    grep -vx "$u" "$S/active" > "$S/active.next" || true; mv "$S/active.next" "$S/active"
    if [ -e "$S/dies-with-new" ] && new; then exit 0; fi
    echo "$u" >> "$S/active";;
  *) echo "stand-in: unexpected systemctl $*" >&2; exit 64;;
esac
""",
    # something outside tries to start a one-shot unit at this moment (a timer, a person)
    'outside': r"""#!/usr/bin/env bash
if [ -e "$KRYUK_STANDIN/try-start" ]; then systemctl start kryuk-operations.service; fi
""",
    'curl': r"""#!/usr/bin/env bash
S="$KRYUK_STANDIN"; echo "curl ${@: -1}" >> "$S/log"; outside
grep -qx kryuk-capture.service "$S/active" 2>/dev/null || exit 7
if [ -e "$S/silent-with-new" ] && grep -q 'LOCKING=1' "$KRYUK_CODE_DIR/ops_media.py"; then exit 22; fi
if [ -e "$S/silent-always" ]; then exit 22; fi
echo '{"ok":true,"stand-in":true}'
""",
    'runuser': r"""#!/usr/bin/env bash
S="$KRYUK_STANDIN"; echo "runuser $1 $2" >> "$S/log"; outside
shift 4   # -u USER -- /usr/bin/python3
exec "$KRYUK_PYTHON" "$@"
""",
    'id': '#!/usr/bin/env bash\ncat "$KRYUK_STANDIN/uid"\n',
    'stat': '#!/usr/bin/env bash\ncat "$KRYUK_STANDIN/owner"\n',
    'install': r"""#!/usr/bin/env bash
# the real install without the owner; fails on purpose for a source named in the file install-fails
S="$KRYUK_STANDIN"; outside
args=(); while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2;; *) args+=("$1"); shift;; esac; done
if [ -s "$S/install-fails" ]; then
  case "${args[*]}" in *"$(cat "$S/install-fails")"*) echo "install ${args[*]: -2}: FAILED on purpose" >> "$S/log"; exit 1;; esac
fi
exec /usr/bin/install "${args[@]}"
""",
    'pgrep': '#!/usr/bin/env bash\n[ -s "$KRYUK_STANDIN/processes" ] || exit 1\ncut -d" " -f1 "$KRYUK_STANDIN/processes"\n',
    'ps': r"""#!/usr/bin/env bash
# ps -o unit= -p PID, ps -o args= -p PID: from the file "processes" (lines: PID UNIT)
line="$(grep "^${@: -1} " "$KRYUK_STANDIN/processes")"
case "$2" in unit=) echo "${line#* }";; *) echo "a stand-in process";; esac
""",
    'sleep': '#!/usr/bin/env bash\nexit 0\n',
}
ORIGINALS = {'ops_media.py': 'original', 'ops_work.py': 'original'}
NEW = {'ops_media.py': 'new', 'ops_work.py': 'new'}


@unittest.skipIf(os.name == 'nt' and not os.environ.get('KRYUK_TEST_INSTALL_ON_WINDOWS'), 'the install script is a Linux script')
class RealModeWithStandIns(Install):
    """The real branches of the script: units, users, the hold, restart, health. Every outside command is a stand-in."""

    def setUp(self):
        super().setUp()
        self.standin = Path(self.tmp.name) / 'standin'
        self.hold = Path(self.tmp.name) / 'run-systemd-system'
        self.standin.mkdir()
        self.hold.mkdir()
        for name, text in STANDINS.items():
            (self.standin / name).write_text(text, encoding='utf-8', newline='\n')
            os.chmod(self.standin / name, 0o755)
        self.normal()
        self.answer(log='')

    def normal(self):
        self.answer(active='kryuk-capture.service\n', user='kryuk-run\n', uid='0\n', owner='root:root 644\n', running='', loaded='', stale='',
                    processes='101 kryuk-capture.service\n102 kryuk-bro-api.service\n', install_fails='')
        for name in ('silent-with-new', 'silent-always', 'dies-with-new', 'restart-fails', 'reload-fails', 'try-start', 'next-kryuk-backup.timer'):
            (self.standin / name).unlink(missing_ok=True)

    def answer(self, **files):
        for name, text in files.items():
            (self.standin / name.replace('_', '-')).write_text(text, encoding='utf-8', newline='\n')

    def environment(self, code=None):
        env = {**os.environ, 'KRYUK_CODE_DIR': str(code or self.code), 'KRYUK_PYTHON': sys.executable, 'KRYUK_STANDIN': str(self.standin),
               'KRYUK_HOLD_DIR': self.hold.as_posix(), 'PATH': str(self.standin) + os.pathsep + os.environ['PATH']}
        env.pop('KRYUK_INSTALL_REHEARSAL', None)
        return env

    def run_script(self, *args, package=None, code=None):
        done = subprocess.run([os.environ.get('KRYUK_BASH', 'bash'), str((package or self.package) / 'install.sh'), *args], env=self.environment(code),
                              capture_output=True, text=True, timeout=180)
        return done.returncode, done.stdout + done.stderr

    def outside_start(self):
        """Somebody starts a one-shot unit now; what the stand-in systemd did with it."""
        before = len(self.log('start '))
        subprocess.run([os.environ.get('KRYUK_BASH', 'bash'), str(self.standin / 'systemctl'), 'start', 'kryuk-operations.service'], env=self.environment(), check=True, timeout=60)
        return self.log('start ')[before:]

    def log(self, word):
        return [line for line in (self.standin / 'log').read_text(encoding='utf-8').splitlines() if line.startswith(word)]

    def verbs(self):            # what the script told systemd to do, questions left out
        return [line.split()[1] for line in self.log('systemctl') if line.split()[1] not in ('is-active', 'is-enabled', 'show')]

    def restarts(self):
        return [line for line in self.log('systemctl restart')]

    def held(self):             # the hold as it is on the disk and as the stand-in systemd has it loaded
        return sorted(f.parent.name[:-2] for f in self.hold.glob('*.d/' + HOLD)), sorted((self.standin / 'loaded').read_text().split())

    FREE = ([], [])
    HELD = (ONESHOTS, ONESHOTS)

    # ---- the ordinary way
    def test_a_kept_copy_in_the_way_stops_it_and_a_rehearsal_is_refused_on_the_real_folder(self):
        (self.code / 'ops_media.py.before-store-lock').write_text('left by something else')
        code, out = self.run_script()
        self.assertEqual((code, 'already exists' in out, self.verbs()), (1, True, []), out)

    def test_it_restarts_one_service_and_runs_the_self_test_as_the_user_of_that_service(self):
        code, out = self.run_script()
        self.assertEqual((code, self.state()), (0, NEW), out)
        self.assertEqual(self.verbs(), ['daemon-reload', 'restart', 'daemon-reload'], 'hold, one restart, release; nothing else')
        self.assertEqual(self.restarts(), ['systemctl restart kryuk-capture.service'])
        self.assertEqual(self.log('runuser'), ['runuser -u kryuk-run'])
        self.assertIn('health: OK', out)
        self.assertEqual(self.held(), self.FREE)
        code, out = self.run_script('rollback')
        self.assertEqual((code, self.state(), self.kept(), self.held()), (0, ORIGINALS, [], self.FREE), out)
        self.assertEqual(self.restarts(), ['systemctl restart kryuk-capture.service'] * 2)

    def test_a_service_that_stops_answering_with_the_new_files_gets_its_originals_back(self):
        self.answer(silent_with_new='')
        code, out = self.run_script()
        self.assertEqual((code, 'does not answer with the new files. Putting both originals back' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept(), self.held()), (ORIGINALS, [], self.FREE), out)
        self.assertEqual(self.restarts(), ['systemctl restart kryuk-capture.service'] * 2, 'with the new files, then with the originals')
        self.assertIn('restore: both installed files are the originals', out)
        self.assertIn('health: OK {"ok":true,"stand-in":true}', out.split('Putting both originals back')[1], 'it answers again with the originals')

    def test_a_service_that_dies_with_the_new_files_gets_its_originals_back(self):
        self.answer(dies_with_new='')
        code, out = self.run_script()
        self.assertEqual((code, 'did not restart with the new files. Putting both originals back' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept(), self.held()), (ORIGINALS, [], self.FREE), out)
        self.assertEqual((self.standin / 'active').read_text().split(), ['kryuk-capture.service'], 'running again')

    def test_it_changes_nothing_when_a_precondition_is_not_met(self):
        soon = time.strftime('%a %Y-%m-%d %H:%M:%S UTC', time.gmtime(time.time() + 120))
        for answers, words in (({'running': 'kryuk-operations.service\n'}, 'kryuk-operations.service is running now (state: activating)'),
                               ({'active': ''}, 'kryuk-capture.service is not running'),
                               ({'owner': 'kryuk:kryuk 664\n'}, 'is not root:root 644'),
                               ({'user': '\n'}, 'has no user of its own'),
                               ({'uid': '1000\n'}, 'run with sudo'),
                               ({'processes': '101 kryuk-capture.service\n777 session-4.scope\n'}, 'process 777 runs code of'),
                               ({'next_kryuk_backup.timer': soon + '\n'}, 'kryuk-backup.timer fires in'),
                               ({'stale': 'kryuk-backup.service\n'}, 'was changed and not loaded'),
                               ({'reload_fails': ''}, 'could not be held'),
                               ({'silent_always': ''}, 'does not answer before anything was changed')):
            self.normal()
            self.answer(**answers)
            code, out = self.run_script()
            # a hold that could not be confirmed gone is the one case here that needs a person
            self.assertEqual((code, words in out), (2 if 'reload_fails' in answers else 1, True), out)
            self.assertEqual((self.state(), self.kept(), self.restarts()), (ORIGINALS, [], []), words)
            self.assertEqual(self.held()[0], [], words + ': no hold file is left')

    # ---- the hold
    def test_a_one_shot_unit_started_from_outside_at_any_moment_of_the_install_does_not_start(self):
        """GPT's review of 195c896: a start after the check must not put the original importer beside the new code."""
        self.assertEqual(self.outside_start(), ['start kryuk-operations.service: STARTED with the original files on the disk'], 'without a hold it starts')
        self.answer(running='', try_start='')
        code, out = self.run_script()
        self.assertEqual((code, self.state()), (0, NEW), out)
        tried = self.log('start ')[1:]
        self.assertGreaterEqual(len(tried), 6, 'before the files, at each file, at the self-test, after the restart')
        self.assertEqual(set(tried), {'start kryuk-operations.service: skipped by its condition'})
        self.assertEqual(self.held(), self.FREE)
        (self.standin / 'try-start').unlink()
        self.assertEqual(self.outside_start(), ['start kryuk-operations.service: STARTED with the new files on the disk'], 'after the install it starts again, with the new code')

    def test_the_same_holds_while_an_install_fails_and_while_a_rollback_runs(self):
        self.answer(try_start='', silent_with_new='')
        code, out = self.run_script()
        self.assertEqual((code, self.state(), self.held()), (1, ORIGINALS, self.FREE), out)
        self.normal()
        self.assertEqual(self.run_script()[0], 0)
        self.answer(try_start='')
        code, out = self.run_script('rollback')
        self.assertEqual((code, self.state(), self.held()), (0, ORIGINALS, self.FREE), out)
        self.assertGreaterEqual(len(self.log('start ')), 8)
        self.assertEqual(set(self.log('start ')), {'start kryuk-operations.service: skipped by its condition'})

    def test_rollback_waits_for_a_running_one_shot_unit(self):
        self.assertEqual(self.run_script()[0], 0)
        self.answer(running='kryuk-backup.service\n')
        code, out = self.run_script('rollback')
        self.assertEqual((code, 'kryuk-backup.service is running now' in out, self.state(), self.held()), (1, True, NEW, self.FREE), out)
        self.assertEqual(len(self.kept()), 2, 'the kept copies stay')

    # ---- putting the originals back, one step failing (GPT's review of 195c896)
    def unresolved(self, out, state, restarts):
        self.assertIn('STOP: the originals could not be put back', out)
        self.assertIn('was NOT restarted', out)
        self.assertIn('STAY HELD', out)
        self.assertEqual(self.state(), state, out)
        self.assertEqual(self.kept(), ['ops_media.py.before-store-lock', 'ops_work.py.before-store-lock'], 'both kept copies stay')
        self.assertEqual({name: sha(self.code / (name + '.before-store-lock')) for name in OLD}, OLD)
        self.assertEqual(len(self.restarts()), restarts, 'no restart on a pair that was not confirmed')
        self.assertEqual(self.held(), self.HELD, 'nothing that loads these files may start in this state')
        self.assertEqual(sorted(f.name for f in self.code.glob('*.store-lock-part')), [])

    def test_a_failed_install_whose_first_restore_step_fails_stops_with_both_new_files_and_touches_nothing_more(self):
        self.answer(silent_with_new='', install_fails='ops_work.py.before-store-lock')
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn('restore: ops_work.py could not be put back; the next file was not touched', out)
        self.unresolved(out, NEW, restarts=1)
        self.assertEqual(self.outside_start(), ['start kryuk-operations.service: skipped by its condition'])
        self.normal()
        self.answer(loaded='\n'.join(ONESHOTS) + '\n')
        code, out = self.run_script('status')
        self.assertEqual((code, out.count(', HELD')), (0, 3), out)
        code, out = self.run_script('rollback')     # a person, after looking: the way back still works
        self.assertEqual((code, self.state(), self.kept(), self.held()), (0, ORIGINALS, [], self.FREE), out)

    def test_a_failed_install_whose_second_restore_step_fails_stops_with_a_pair_that_works(self):
        self.answer(silent_with_new='', install_fails='ops_media.py.before-store-lock')
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn('restore: ops_media.py could not be put back', out)
        self.unresolved(out, {'ops_media.py': 'new', 'ops_work.py': 'original'}, restarts=1)

    def test_a_rollback_whose_first_or_second_step_fails_stops_the_same_way_and_can_be_run_again(self):
        for source, state in (('ops_work.py.before-store-lock', NEW), ('ops_media.py.before-store-lock', {'ops_media.py': 'new', 'ops_work.py': 'original'})):
            self.normal()
            self.answer(log='')
            self.assertEqual(self.run_script()[0], 0)
            self.answer(install_fails=source)
            code, out = self.run_script('rollback')
            self.assertEqual(code, 2, out)
            self.unresolved(out, state, restarts=1)     # the one restart is the install's
            self.normal()
            self.answer(loaded='\n'.join(ONESHOTS) + '\n')
            code, out = self.run_script('rollback')
            self.assertEqual((code, self.state(), self.kept(), self.held()), (0, ORIGINALS, [], self.FREE), out)

    def test_originals_back_but_a_service_that_does_not_come_up_is_left_to_a_person_with_the_copies_kept(self):
        self.answer(restart_fails='')
        code, out = self.run_script()
        self.assertEqual((code, 'did not restart with the new files' in out, 'the originals are back, but the service did not restart' in out), (2, True, True), out)
        self.assertEqual((self.state(), len(self.kept()), self.held()), (ORIGINALS, 2, self.HELD), out)

    def test_rollback_refuses_a_kept_copy_that_is_not_the_original_and_release_takes_a_left_hold_away(self):
        self.assertEqual(self.run_script()[0], 0)
        with (self.code / 'ops_work.py.before-store-lock').open('ab') as f:
            f.write(b'\n# not the original any more\n')
        code, out = self.run_script('rollback')
        self.assertEqual((code, 'is not the original: nothing was changed' in out, self.state(), self.restarts()), (1, True, NEW, ['systemctl restart kryuk-capture.service']), out)
        for unit in ONESHOTS:                       # a hold left by a killed run
            (self.hold / (unit + '.d')).mkdir()
            (self.hold / (unit + '.d') / HOLD).write_text('[Unit]\n')
        self.answer(loaded='\n'.join(ONESHOTS) + '\n')
        code, out = self.run_script('release')
        self.assertEqual((code, 'released (can start again)' in out, self.held()), (0, True, self.FREE), out)
        self.assertEqual(sorted(p.name for p in self.hold.iterdir()), [], 'the empty folders are gone too')


class Order(unittest.TestCase):
    def test_the_new_store_works_with_the_original_work_file_and_not_the_other_way_round(self):
        """Why ops_media.py goes in first and comes out last."""
        with tempfile.TemporaryDirectory() as tmp:
            for kind, media, work, expected in (('media-first', HERE, SERVER, 0), ('work-first', SERVER, HERE, 1)):
                code = Path(tmp) / kind
                code.mkdir()
                for name in ('runtime.py', 'contact_metrics.py'):
                    shutil.copyfile(SERVER / name, code / name)
                shutil.copyfile(media / 'ops_media.py', code / 'ops_media.py')
                shutil.copyfile(work / 'ops_work.py', code / 'ops_work.py')
                done = subprocess.run([sys.executable, '-B', str(HERE / 'selftest.py'), str(code)], capture_output=True, text=True, timeout=120)
                self.assertEqual(done.returncode, expected, kind + ': ' + done.stdout + done.stderr)
        text = (HERE / 'install.sh').read_text(encoding='utf-8')
        self.assertIn('FILES="ops_media.py ops_work.py"', text)
        self.assertIn('BACK="ops_work.py ops_media.py"', text)


class SelfTest(unittest.TestCase):
    def test_the_self_test_passes_on_the_patched_files_and_fails_on_the_installed_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind, source in (('patched', HERE), ('installed', SERVER)):
                code = Path(tmp) / kind
                code.mkdir()
                for name in ('runtime.py', 'contact_metrics.py'):
                    shutil.copyfile(SERVER / name, code / name)
                for name in OLD:
                    shutil.copyfile(source / name, code / name)
                done = subprocess.run([sys.executable, '-B', str(HERE / 'selftest.py'), str(code)], capture_output=True, text=True, timeout=120)
                self.assertEqual((done.returncode, done.stdout.split(':')[0]), (0, 'SELFTEST OK') if kind == 'patched' else (1, 'SELFTEST FAILED'), done.stdout + done.stderr)


if __name__ == '__main__':
    unittest.main()
