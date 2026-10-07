"""Rehearsal before the real database folder is touched: can two service users share one SQLite database in WAL mode
through a group, with both units keeping UMask=0077? Works only in a throwaway folder under /tmp, which it removes.

  sudo python3 db_share_check.py --owner kryuk-run --reader kryuk-api-read --group kryuk-db --outsider nobody

The folder gets the layout planned for /var/lib/kryuk24: owner <owner>, group <group>, group rwx + setgid; the
database file is owner <owner>, group <group>, mode 0660. Every step runs as the named user with that user's real
groups and umask 077. Exit 0 only if every step says PASS.

Without root (--same-user) the steps run as the current user. That exercises this script and shows the file modes,
but proves nothing about two users.
"""
import argparse
import grp
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

WRITE = '''
import os, sqlite3, sys, time
os.umask(0o077)
c = sqlite3.connect(sys.argv[1], timeout=10)
c.execute('PRAGMA journal_mode=WAL')
c.execute('CREATE TABLE IF NOT EXISTS t(who TEXT)')
c.execute('INSERT INTO t VALUES (?)', (sys.argv[2],))
c.commit()
if len(sys.argv) > 3:
    print('HOLDING', flush=True)
    time.sleep(float(sys.argv[3]))
print(c.execute('SELECT count(*) FROM t').fetchone()[0], flush=True)
c.close()
'''
READ_ONLY = '''
import sqlite3, sys
c = sqlite3.connect('file:%s?mode=ro' % sys.argv[1], uri=True)
print(c.execute('SELECT count(*) FROM t').fetchone()[0], flush=True)
c.close()
'''


def identity(name, same_user):
    if same_user:
        return {}
    entry = pwd.getpwnam(name)
    return {'user': entry.pw_uid, 'group': entry.pw_gid, 'extra_groups': os.getgrouplist(name, entry.pw_gid)}


def start(who, same_user, code, *args):
    return subprocess.Popen([sys.executable, '-c', code, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            cwd='/', **identity(who, same_user))


def run(who, same_user, code, *args):
    child = start(who, same_user, code, *args)
    out, err = child.communicate(timeout=60)
    return child.returncode, out.strip(), (err.strip().splitlines() or [''])[-1]


def listing(folder):
    rows = []
    for name in sorted(os.listdir(folder)):
        s = os.stat(os.path.join(folder, name))
        rows.append('%s %s:%s %s' % (name, pwd.getpwuid(s.st_uid).pw_name, grp.getgrgid(s.st_gid).gr_name, oct(stat.S_IMODE(s.st_mode))))
    return '; '.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner', required=True)
    parser.add_argument('--reader', required=True)
    parser.add_argument('--group', required=True)
    parser.add_argument('--outsider')
    parser.add_argument('--same-user', action='store_true')
    args = parser.parse_args()
    same = args.same_user
    if not same and os.geteuid() != 0:
        print('REFUSED: run as root, or use --same-user (which proves nothing about two users)')
        return 2
    gid = grp.getgrnam(args.group).gr_gid
    folder = tempfile.mkdtemp(prefix='kryuk-db-share.', dir='/tmp')
    db = os.path.join(folder, 'runtime.sqlite')
    failed = []

    def step(label, ok, detail):
        print('%s  %s  %s' % ('PASS' if ok else 'FAIL', label, detail))
        if not ok:
            failed.append(label)

    try:
        os.chown(folder, -1 if same else pwd.getpwnam(args.owner).pw_uid, gid)
        os.chmod(folder, 0o2770)
        code, out, err = run(args.owner, same, WRITE, db, 'owner')
        step('1 owner creates the database', code == 0, err or listing(folder))
        os.chown(db, -1, gid)
        os.chmod(db, 0o660)
        code, out, err = run(args.reader, same, WRITE, db, 'reader')
        step('2 reader writes when nobody else has it open', (code, out) == (0, '2'), err or listing(folder))
        holder = start(args.reader, same, WRITE, db, 'reader-holding', '4')
        holder.stdout.readline()                           # the reader now holds the database open: -wal and -shm are its files
        held = listing(folder)
        code, out, err = run(args.owner, same, WRITE, db, 'owner-while-reader-holds')
        step('3 owner writes into files the reader created', code == 0 and '-wal' in held, err or held)
        holder.communicate(timeout=60)
        holder = start(args.owner, same, WRITE, db, 'owner-holding', '4')
        holder.stdout.readline()
        held = listing(folder)
        code, out, err = run(args.reader, same, WRITE, db, 'reader-while-owner-holds')
        step('4 reader writes into files the owner created', code == 0 and '-wal' in held, err or held)
        code, out, err = run(args.reader, same, READ_ONLY, db)
        step('5 reader opens read-only (the dry-run) while the owner holds it', code == 0, err or 'rows %s' % out)
        holder.communicate(timeout=60)
        code, out, err = run(args.owner, same, WRITE, db, 'owner-last')
        step('6 every write is there', (code, out) == (0, '7'), err or 'rows %s' % out)
        if args.outsider and not same:
            code, out, err = run(args.outsider, same, READ_ONLY, db)
            step('7 a user outside the group cannot open it', code != 0, err or 'it could: rows %s' % out)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print('removed %s: %s' % (folder, not os.path.exists(folder)))
    if same:
        print('SAME-USER RUN: the script works; nothing is proven about two users')
    print('RESULT: %s' % ('FAIL (%s)' % ', '.join(failed) if failed else 'PASS'))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
