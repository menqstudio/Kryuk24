"""install.sh in its rehearsal mode: a temporary code folder, no services, no ownership. Linux (bash, coreutils).

What it shows: the checksum gates, both files changing together, the kept copies, the way back, a second run, a
failed self-test putting both originals back.

The second class runs the script in its real mode with stand-ins for systemctl, curl, runuser, id, stat, install and
sleep put first in PATH. It shows what the script ASKS for and what it does with each answer (which unit it restarts,
as whom the self-test runs, what happens when the service dies or stops answering with the new files). It does not
show that the real systemctl or the real service behave like the stand-ins: that exists only on the server.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
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


STANDINS = {
    'systemctl': r"""#!/usr/bin/env bash
# a stand-in: answers from files in $KRYUK_STANDIN, writes every call into its log
S="$KRYUK_STANDIN"; echo "systemctl $*" >> "$S/log"
new() { grep -q 'LOCKING=1' "$KRYUK_CODE_DIR/ops_media.py"; }
active() { grep -qx "$1" "$S/active" 2>/dev/null; }
case "$1" in
  is-active) u="${@: -1}"; if active "$u"; then [ "$2" = --quiet ] || echo active; exit 0; else [ "$2" = --quiet ] || echo inactive; exit 3; fi;;
  is-enabled) echo enabled;;
  show) cat "$S/user";;
  restart) [ -e "$S/restart-fails" ] && exit 1
    grep -vx "$2" "$S/active" > "$S/active.next" || true; mv "$S/active.next" "$S/active"
    if [ -e "$S/dies-with-new" ] && new; then exit 0; fi
    echo "$2" >> "$S/active";;
  *) echo "stand-in: unexpected systemctl $*" >&2; exit 64;;
esac
""",
    'curl': r"""#!/usr/bin/env bash
S="$KRYUK_STANDIN"; echo "curl ${@: -1}" >> "$S/log"
grep -qx kryuk-capture.service "$S/active" 2>/dev/null || exit 7
if [ -e "$S/silent-with-new" ] && grep -q 'LOCKING=1' "$KRYUK_CODE_DIR/ops_media.py"; then exit 22; fi
echo '{"ok":true,"stand-in":true}'
""",
    'runuser': r"""#!/usr/bin/env bash
S="$KRYUK_STANDIN"; echo "runuser $1 $2" >> "$S/log"
shift 4   # -u USER -- /usr/bin/python3
exec "$KRYUK_PYTHON" "$@"
""",
    'id': '#!/usr/bin/env bash\ncat "$KRYUK_STANDIN/uid"\n',
    'stat': '#!/usr/bin/env bash\ncat "$KRYUK_STANDIN/owner"\n',
    'install': r"""#!/usr/bin/env bash
args=(); while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2;; *) args+=("$1"); shift;; esac; done
exec /usr/bin/install "${args[@]}"
""",
    'sleep': '#!/usr/bin/env bash\nexit 0\n',
}


@unittest.skipIf(os.name == 'nt' and not os.environ.get('KRYUK_TEST_INSTALL_ON_WINDOWS'), 'the install script is a Linux script')
class RealModeWithStandIns(Install):
    """The real branches of the script: units, users, restart, health. Every outside command is a stand-in."""

    def setUp(self):
        super().setUp()
        self.standin = Path(self.tmp.name) / 'standin'
        self.standin.mkdir()
        for name, text in STANDINS.items():
            (self.standin / name).write_text(text, encoding='utf-8', newline='\n')
            os.chmod(self.standin / name, 0o755)
        self.answer(active='kryuk-capture.service\n', user='kryuk-run\n', uid='0\n', owner='root:root 644\n', log='')

    def answer(self, **files):
        for name, text in files.items():
            (self.standin / name.replace('_', '-')).write_text(text, encoding='utf-8', newline='\n')

    def run_script(self, *args, package=None, code=None):
        env = {**os.environ, 'KRYUK_CODE_DIR': str(code or self.code), 'KRYUK_PYTHON': sys.executable, 'KRYUK_STANDIN': str(self.standin),
               'PATH': str(self.standin) + os.pathsep + os.environ['PATH']}
        env.pop('KRYUK_INSTALL_REHEARSAL', None)
        done = subprocess.run([os.environ.get('KRYUK_BASH', 'bash'), str((package or self.package) / 'install.sh'), *args], env=env, capture_output=True, text=True, timeout=180)
        return done.returncode, done.stdout + done.stderr

    def log(self, word):
        return [line for line in (self.standin / 'log').read_text(encoding='utf-8').splitlines() if line.startswith(word)]

    def changing_calls(self):   # every call of the stand-in systemctl that is not a question
        return [line for line in self.log('systemctl') if line.split()[1] not in ('is-active', 'is-enabled', 'show')]

    def test_a_kept_copy_in_the_way_stops_it_and_a_rehearsal_is_refused_on_the_real_folder(self):
        (self.code / 'ops_media.py.before-store-lock').write_text('left by something else')
        code, out = self.run_script()
        self.assertEqual((code, 'already exists' in out, self.changing_calls()), (1, True, []), out)

    def test_it_restarts_one_service_and_runs_the_self_test_as_the_user_of_that_service(self):
        code, out = self.run_script()
        self.assertEqual((code, self.state()), (0, {'ops_media.py': 'new', 'ops_work.py': 'new'}), out)
        self.assertEqual(self.changing_calls(), ['systemctl restart kryuk-capture.service'], 'one restart of one service and nothing else')
        self.assertEqual(self.log('runuser'), ['runuser -u kryuk-run'])
        self.assertIn('health: OK', out)
        code, out = self.run_script('rollback')
        self.assertEqual((code, self.state(), self.kept()), (0, {'ops_media.py': 'original', 'ops_work.py': 'original'}, []), out)
        self.assertEqual(self.changing_calls(), ['systemctl restart kryuk-capture.service'] * 2)

    def test_a_service_that_stops_answering_with_the_new_files_gets_its_originals_back(self):
        self.answer(silent_with_new='')
        code, out = self.run_script()
        self.assertEqual((code, 'does not answer with the new files. Putting both originals back' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, []), out)
        self.assertEqual(self.changing_calls(), ['systemctl restart kryuk-capture.service'] * 2, 'with the new files, then with the originals')
        self.assertEqual(out.strip().splitlines()[-3], 'health: OK {"ok":true,"stand-in":true}', 'it answers again with the originals')

    def test_a_service_that_dies_with_the_new_files_gets_its_originals_back(self):
        self.answer(dies_with_new='')
        code, out = self.run_script()
        self.assertEqual((code, 'did not restart with the new files. Putting both originals back' in out), (1, True), out)
        self.assertEqual((self.state(), self.kept()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, []), out)
        self.assertEqual((self.standin / 'active').read_text().split(), ['kryuk-capture.service'], 'running again')

    def test_it_changes_nothing_while_a_one_shot_unit_runs_or_the_service_is_down_or_the_owner_is_wrong(self):
        for answers, words in (({'active': 'kryuk-capture.service\nkryuk-operations.service\n'}, 'kryuk-operations.service is running now'),
                               ({'active': ''}, 'kryuk-capture.service is not running'),
                               ({'owner': 'kryuk:kryuk 664\n'}, 'is not root:root 644'),
                               ({'user': '\n'}, 'has no user of its own'),
                               ({'uid': '1000\n'}, 'run with sudo')):
            self.answer(active='kryuk-capture.service\n', user='kryuk-run\n', uid='0\n', owner='root:root 644\n')
            self.answer(**answers)
            code, out = self.run_script()
            self.assertEqual((code, words in out), (1, True), out)
            self.assertEqual((self.state(), self.kept(), self.changing_calls()), ({'ops_media.py': 'original', 'ops_work.py': 'original'}, [], []), words)

    def test_rollback_waits_for_a_running_one_shot_unit(self):
        self.assertEqual(self.run_script()[0], 0)
        self.answer(active='kryuk-capture.service\nkryuk-backup.service\n')
        code, out = self.run_script('rollback')
        self.assertEqual((code, 'kryuk-backup.service is running now' in out, self.state()['ops_work.py']), (1, True, 'new'), out)
        self.assertEqual(len(self.kept()), 2, 'the kept copies stay')


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
