"""Puts the portal's locations into the installed Nginx file of runtime.kryuk24.ru, or takes them out again.

    python3 nginx_insert.py insert FRAGMENT [--expect SHA256]
    python3 nginx_insert.py remove FRAGMENT

Approved by Gev on 08.10.2026 for the subtree /operator/work/armen/ only.
insert: refuses unless the installed file is the one that was read (--expect), has exactly one catch-all line
of the HTTPS server and no portal location yet. Keeps a private copy first, writes the new file, runs
`nginx -t`; when the test fails the copy is put back and nothing is reloaded. The reload is the caller's step.
remove: takes out exactly the fragment's text; the same test and the same way back.
Changes no other line of the file.
"""
import argparse, hashlib, os, shutil, subprocess, time
from pathlib import Path

TARGET = Path('/etc/nginx/conf.d/kryuk24.conf')
BACKUPS = Path('/root/kryuk24-config-backups')
ANCHOR = ' location / { return 404; }\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stop(text):
    print('STOP:', text)
    raise SystemExit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['insert', 'remove'])
    p.add_argument('fragment')
    p.add_argument('--expect')
    a = p.parse_args()
    fragment = Path(a.fragment).read_text(encoding='utf-8')
    if not fragment.endswith('\n'):
        stop('the fragment must end with a new line')
    before = TARGET.read_bytes()
    text = before.decode('utf-8')
    print('installed file before:', digest(before))
    if a.action == 'insert':
        if a.expect and digest(before) != a.expect:
            stop('the installed file is not the one that was read; read it again')
        if '/operator/work/armen' in text or ':8790' in text:
            stop('the installed file already names the portal')
        if text.count(ANCHOR) != 1:
            stop('the catch-all line of the HTTPS server was not found exactly once')
        for zone in ('zone=kryuk_operator:', 'zone=kryuk_preview:'):
            if text.count(zone) != 1:
                stop('rate limit zone not declared exactly once: ' + zone)
        new = text.replace(ANCHOR, fragment + ANCHOR)
    else:
        if text.count(fragment) != 1:
            stop('the fragment is not in the installed file exactly once')
        new = text.replace(fragment, '')
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    os.chmod(BACKUPS, 0o700)
    copy = BACKUPS / ('kryuk24.conf.before-armen-%s-%s' % (a.action, time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())))
    shutil.copy2(TARGET, copy)
    os.chmod(copy, 0o600)
    if digest(copy.read_bytes()) != digest(before):
        stop('the private copy differs from the installed file')
    print('private copy:', copy, 'mode 600, sha256 equal to the installed file')
    status = TARGET.stat()
    fresh = TARGET.with_name(TARGET.name + '.armen-new')  # not *.conf, so Nginx never reads it
    fresh.write_bytes(new.encode('utf-8'))
    os.chown(fresh, status.st_uid, status.st_gid)
    os.chmod(fresh, status.st_mode & 0o7777)
    os.replace(fresh, TARGET)
    test = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    print((test.stdout + test.stderr).strip())
    if test.returncode != 0:
        shutil.copy2(copy, TARGET)
        again = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        print('put back; installed file now:', digest(TARGET.read_bytes()), '; nginx -t exit', again.returncode)
        stop('nginx -t refused the new file; nothing was reloaded')
    print('installed file after:', digest(TARGET.read_bytes()), '; lines added or removed:', new.count('\n') - text.count('\n'))


if __name__ == '__main__':
    main()
