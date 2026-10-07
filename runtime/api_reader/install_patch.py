"""Adds the API_READ kind to the installed runtime code, or takes it back out.

  python3 install_patch.py --code /opt/kryuk24 check       says what it would do; changes nothing
  python3 install_patch.py --code /opt/kryuk24 apply       needs every file to be exactly the known version
  python3 install_patch.py --code /opt/kryuk24 rollback    puts back the saved files, removes the added ones

The files are written one after another, so a failure in the middle is handled, not assumed away:
  - apply that fails at any write undoes its own work (files, saved copies, added files) and answers REFUSED (exit 2);
  - if that undo cannot finish, or the process is killed, the saved copies stay and the answer is PARTIAL (exit 3).
    rollback then finishes the job: it accepts a half-applied folder and may be repeated until it succeeds;
  - rollback restores every file first and deletes the saved copies last, so its own failure loses nothing.
The services must be restarted only after APPLIED or ROLLED BACK, never after PARTIAL.

What changes in the existing files (exact text replacements, each must be found exactly once):
  ops_work.py    METRICA, WEBMASTER, HOSTING_DEADLINES are planned with kind API_READ from now on (rows that already
                 exist keep their kind: the planner never touches an existing row);
                 machine evidence is accepted for LOCAL_READ and API_READ tasks, still refused for the rest.
  bro_api.py     the browser worker neither sees API_READ tasks as work nor may claim, observe or draft them.
  bro_worker.py  the same for the local adapter bridge.
  test_bro_http.py  one existing test took METRICA as "some other browser task"; it now takes YANDEX_DIRECT.
Added files: bro_api_reader.py, ops_api.py, reader_provision.py.
Not touched: ops_views.py, the database, services, timers.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUFFIX = '.before-api-read'
ADDED = ('bro_api_reader.py', 'ops_api.py', 'reader_provision.py')
BASE = {'ops_work.py': '0c93a77a1e701352cef4ccfc68f3d836e47f357056599392fae1940d675d455d',
        'bro_api.py': '23570810f056a04afc50fbc481bb70aaed59a67ac0c0af886001c84513f058c4',
        'bro_worker.py': '6c194cf99d75a063b41d5495432b11accd709e71bb6de42b86445c496167ec15',
        'test_bro_http.py': '8f6135953991d3a2958e64860588a14737938feea705d84f0a56ffa5740653a8'}
EDITS = {
    'ops_work.py': [
        ("('METRICA','Նպատակների թվեր / Goal counts','BROWSER_READ')", "('METRICA','Նպատակների թվեր / Goal counts','API_READ')"),
        ("('WEBMASTER','Ինդեքսավորում / Indexing','BROWSER_READ')", "('WEBMASTER','Ինդեքսավորում / Indexing','API_READ')"),
        ("('HOSTING_DEADLINES','Վճար և ժամկետներ / Balance and deadlines','BROWSER_READ')",
         "('HOSTING_DEADLINES','Վճար և ժամկետներ / Balance and deadlines','API_READ')"),
        ("if machine and row['kind']!='LOCAL_READ':raise ValueError('machine evidence only for local reads')",
         "if machine and row['kind'] not in ('LOCAL_READ','API_READ'):raise ValueError('machine evidence only for local and API reads')"),
    ],
    'bro_api.py': [
        ("for r in rows if r['job'] in JOBS],", "for r in rows if r['job'] in JOBS and r['kind']!='API_READ'],"),
        ("or row['job'] not in JOBS: raise PermissionError('task outside scope')",
         "or row['job'] not in JOBS or row['kind']=='API_READ': raise PermissionError('task outside scope')"),
    ],
    'bro_worker.py': [
        ("candidates = [t for t in tasks if t['job'] in JOBS and", "candidates = [t for t in tasks if t['job'] in JOBS and t['kind'] != 'API_READ' and"),
    ],
    'test_bro_http.py': [
        ("['tasks'] if t['job']=='METRICA')", "['tasks'] if t['job']=='YANDEX_DIRECT')"),
    ],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patched(name, data):
    text = data.decode('utf-8')
    for old, new in EDITS[name]:
        if text.count(old) != 1:
            raise ValueError('%s: expected text not found exactly once' % name)
        text = text.replace(old, new)
    return text.encode('utf-8')


class Partial(Exception):
    """The code folder is neither the known version nor the patched one. rollback is the way out."""


def put(path, data):
    temporary = path.with_name(path.name + '.new')
    temporary.write_bytes(data)
    os.replace(temporary, path)


def leftovers(code):
    return [code / (name + '.new') for name in (*BASE, *ADDED)]


def plan(code):
    """What apply would write. Raises ValueError unless every file is exactly the known version and nothing is in the way."""
    writes = {}
    for name, expected in BASE.items():
        path = code / name
        if not path.is_file():
            raise ValueError('%s is missing' % name)
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError('%s is not the known version (sha256 %s); nothing was changed' % (name, sha(data)))
        if (code / (name + SUFFIX)).exists():
            raise ValueError('%s%s already exists; nothing was changed' % (name, SUFFIX))
        writes[name] = patched(name, data)
    for name in ADDED:
        if (code / name).exists():
            raise ValueError('%s already exists in the code folder; nothing was changed' % name)
        writes[name] = (HERE / name).read_bytes()
    for path in leftovers(code):
        if path.exists():
            raise ValueError('%s is left from an interrupted run; run rollback first. Nothing was changed' % path.name)
    return writes


def undo(code, originals, made):
    """Takes back a failed apply. Returns the names it could not put right; the saved copies go only when there are none."""
    failed = []
    for name, data in originals.items():
        try:
            if (code / name).read_bytes() != data:
                put(code / name, data)
        except OSError:
            failed.append(name)
    for path in [] if failed else [*made, *leftovers(code)]:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            failed.append(path.name)
    return failed


def apply(code):
    writes = plan(code)
    originals = {name: (code / name).read_bytes() for name in BASE}
    if any(sha(data) != BASE[name] for name, data in originals.items()):
        raise ValueError('a file changed during the check; nothing was changed')
    made = []                                              # what this run created: saved copies and added files
    try:
        for name, data in originals.items():
            with open(code / (name + SUFFIX), 'xb') as backup:
                made.append(code / (name + SUFFIX))
                backup.write(data)
        for name, data in writes.items():
            if name in ADDED:
                made.append(code / name)
            put(code / name, data)
    except BaseException as error:                         # also Ctrl+C: the folder must not stay half-patched
        failed = undo(code, originals, made)
        if failed:
            raise Partial('apply failed (%s) and could not be undone for: %s. Run rollback before anything else'
                          % (type(error).__name__, ', '.join(failed))) from error
        if not isinstance(error, Exception):
            raise
        raise ValueError('apply failed (%s); every file was put back, nothing is changed' % type(error).__name__) from error
    return {name: sha(data) for name, data in writes.items()}


def rollback(code):
    """Back to the known version. Works on a fully applied folder and on one left half-applied or half-rolled-back."""
    backups = {name: code / (name + SUFFIX) for name in BASE}
    restore = {}
    for name, path in backups.items():
        if path.is_file():
            restore[name] = path.read_bytes()
            if sha(restore[name]) != BASE[name]:
                raise ValueError('saved copy of %s is not the known version; nothing was changed' % name)
        elif not (code / name).is_file() or sha((code / name).read_bytes()) != BASE[name]:
            raise ValueError('no saved copy of %s and the file is not the known version; nothing was changed' % name)
    remove = [path for path in [*(code / name for name in ADDED), *leftovers(code)] if path.exists()]
    if not restore and not remove:
        raise ValueError('nothing to roll back: every file is the known version and nothing was added')
    try:
        for name, data in restore.items():
            if not (code / name).is_file() or (code / name).read_bytes() != data:
                put(code / name, data)
        for path in [*remove, *leftovers(code), *(backups[name] for name in restore)]:    # the saved copies go last
            path.unlink(missing_ok=True)
    except OSError as error:
        raise Partial('rollback stopped (%s); the saved copies are kept. Run rollback again' % type(error).__name__) from error
    return {name: sha((code / name).read_bytes()) for name in BASE}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', required=True)
    parser.add_argument('action', choices=('check', 'apply', 'rollback'))
    args = parser.parse_args()
    code = Path(args.code)
    try:
        if args.action == 'check':
            result = {name: sha(data) for name, data in plan(code).items()}
            print('CHECK OK: apply would write these files (sha256):')
        elif args.action == 'apply':
            result = apply(code)
            print('APPLIED. Files now (sha256):')
        else:
            result = rollback(code)
            print('ROLLED BACK. Files now (sha256):')
    except Partial as reason:
        print('PARTIAL: %s' % reason)
        return 3
    except (ValueError, OSError) as reason:
        print('REFUSED: %s' % reason)
        return 2
    for name, digest in result.items():
        print('  %s  %s' % (digest, name))
    return 0


if __name__ == '__main__':
    if os.name == 'nt':
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
