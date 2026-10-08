"""Backup before the media pipeline is installed, and the way back after it. Publishes nothing, restores nothing by itself.

    python media_rollback.py backup   --db DB --to FILE
    python media_rollback.py snapshot --db DB
    python media_rollback.py rollback --db DB --media-root FOLDER --outbox FOLDER --archive FILE

backup    an online copy of the database (SQLite's own backup), checked for integrity, with every table's row count
          and content fingerprint of the copy printed. The target must not exist; mode 600.
snapshot  row count and content fingerprint of every table: run before and after, compare.
rollback  takes the pipeline out again and keeps what must not be lost:
          - it runs alone: under the pipeline's lock (no intake, processing, submit or clean-up at the same time) and
            inside one write transaction of the database, from reading the history to dropping the tables. What it
            archives is exactly what it removes;
          - the whole history of accepted work (the four pipeline tables, every inbox original a work used and the
            pipeline's variants) is written to the archive file first; the file is removed again if the step fails;
          - an original leaves the inbox only when this pipeline made it AND the portal's outbox still holds the same
            bytes (sha256) AND nothing else in the inbox uses it. An original the inbox had before the pipeline, from
            any other source, is never removed, nor its row. An original that is the only copy stays;
          - work whose publication is recorded keeps its original, its final variant and the approval records;
          - it refuses while anything of this pipeline is before Gev. That is read from the tasks themselves (a draft
            in review or approved that names a variant of this pipeline), not only from the works' own status, and a
            submit that was cut off counts too;
          - the four pipeline tables are dropped. No other table is altered; from `ops_originals` and `ops_assets`
            only rows this pipeline made are taken, and only as described above.
          A second run finds nothing to do. A run cut off after the database step leaves files behind, never a hole.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from media_lock import PipelineLock

TABLES = ('media_work', 'media_work_sources', 'media_work_assets', 'media_work_events')
TRUST = 'AGENT_DECLARED_MASKS'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def connect(db, readonly=False):
    c = sqlite3.connect('file:' + Path(db).as_posix() + ('?mode=ro' if readonly else ''), uri=True, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    return c


def snapshot(db):
    """{table: [rows, fingerprint of the content in rowid order]} for every table of the database."""
    c = connect(db, readonly=True)
    try:
        result = {}
        for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            h, rows = hashlib.sha256(), 0
            for row in c.execute('SELECT * FROM "%s" ORDER BY rowid' % name):
                h.update(repr(tuple(row)).encode('utf-8', 'surrogatepass'))
                rows += 1
            result[name] = [rows, h.hexdigest()]
        return result
    finally:
        c.close()


def backup(db, target):
    target = Path(target)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # never over an existing copy
    os.close(fd)
    source, copy = connect(db, readonly=True), sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    os.chmod(target, 0o600)
    check = sqlite3.connect(target)
    try:
        integrity = check.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        check.close()
    tables = snapshot(target)
    if integrity != 'ok':
        raise ValueError('the copy failed its integrity check: ' + str(integrity))
    return {'file': str(target), 'bytes': target.stat().st_size, 'sha256': sha256(target), 'integrity': integrity, 'tables': tables}


def rollback(db, media_root, outbox, archive, lock_wait=30.0):
    root, outbox, archive = Path(media_root).resolve(), Path(outbox), Path(archive)
    with PipelineLock(root, lock_wait):
        c = connect(db)
        written = False
        try:
            c.execute('BEGIN IMMEDIATE')   # from here to the commit nobody else writes to this database
            have = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(TABLES) <= have:
                c.execute('ROLLBACK')
                return {'done': False, 'reason': 'the pipeline tables are not there: nothing to roll back'}
            works = [dict(r) for r in c.execute('SELECT * FROM media_work ORDER BY rowid')]
            ours = {r['id'] for r in c.execute('SELECT id FROM ops_assets WHERE review_trust=?', (TRUST,))}
            named, open_tasks = set(), []
            for t in c.execute('SELECT id,status,draft FROM ops_tasks WHERE draft IS NOT NULL'):
                ids = {a['id'] for a in json.loads(t['draft']).get('assets', [])}
                named |= ids
                if t['status'] in ('READY_REVIEW', 'APPROVED') and ids & ours:
                    open_tasks.append(t['id'])
            waiting = [w['id'] for w in works if w['status'] in ('SUBMITTING', 'IN_REVIEW', 'APPROVED')]
            if waiting or open_tasks:
                raise ValueError('something of this pipeline is before Gev or on its way to him; he decides first. works: %s; tasks whose draft names a variant of this pipeline: %s'
                                 % (', '.join(waiting) or 'none', ', '.join(open_tasks) or 'none'))
            used = sorted({w['original_id'] for w in works})
            history = {name: [dict(r) for r in c.execute('SELECT * FROM %s ORDER BY rowid' % name)] for name in TABLES}
            history['ops_originals'] = [dict(r) for o in used for r in c.execute('SELECT * FROM ops_originals WHERE id=?', (o,))]
            history['ops_assets'] = [dict(r) for r in c.execute('SELECT * FROM ops_assets WHERE review_trust=? ORDER BY rowid', (TRUST,))]
            raw = json.dumps(history, ensure_ascii=False, sort_keys=True, indent=1).encode('utf-8')
            fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # the history first; never over an older archive
            written = True
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            result = {'done': True, 'archive': str(archive), 'archive_sha256': hashlib.sha256(raw).hexdigest(), 'history_rows': {k: len(v) for k, v in history.items()},
                      'originals_removed': [], 'originals_kept_only_copy': [], 'originals_kept_still_used': [], 'originals_kept_not_made_by_the_pipeline': [],
                      'kept_published': [], 'variants_removed': 0, 'variants_kept_named_by_a_draft': 0}
            doomed = []
            for w in works:
                if w['status'] == 'PUBLISHED':
                    result['kept_published'].append(w['id'])
                    continue
                for a in c.execute('SELECT id,path FROM ops_assets WHERE original_id=? AND review_trust=?', (w['original_id'], TRUST)).fetchall():
                    if a['id'] in named:
                        result['variants_kept_named_by_a_draft'] += 1
                        continue
                    c.execute('DELETE FROM ops_assets WHERE id=?', (a['id'],))
                    doomed.append(root / a['path'])
                    result['variants_removed'] += 1
                original = c.execute('SELECT path FROM ops_originals WHERE id=?', (w['original_id'],)).fetchone()
                if not original:
                    continue
                if not w['owns_original']:
                    result['originals_kept_not_made_by_the_pipeline'].append(w['digest'])   # the inbox had it before: not ours to take
                    continue
                files = [s['source_file'] for s in c.execute('SELECT source_file FROM media_work_sources WHERE work_id=?', (w['id'],))]
                elsewhere = any((outbox / name).is_file() and not (outbox / name).is_symlink() and sha256(outbox / name) == w['digest'] for name in files)
                still_used = c.execute('SELECT 1 FROM ops_assets WHERE original_id=?', (w['original_id'],)).fetchone()
                if elsewhere and not still_used:
                    c.execute('DELETE FROM ops_originals WHERE id=?', (w['original_id'],))
                    doomed.append(root / original['path'])
                    result['originals_removed'].append(w['digest'])
                else:
                    result['originals_kept_only_copy' if not elsewhere else 'originals_kept_still_used'].append(w['digest'])
            for name in TABLES:
                c.execute('DROP TABLE %s' % name)
            c.execute('COMMIT')
        except BaseException:
            if c.in_transaction:
                c.execute('ROLLBACK')
            if written:
                archive.unlink()   # nothing was removed, so there is no history to keep apart: no stray archive in the way of the next run
            raise
        finally:
            c.close()
        # Files go after the database step is committed, still under the lock: a run cut off here leaves files nobody
        # names, never a missing one.
        for path in doomed:
            if path.is_file() and not path.is_symlink():
                os.chmod(path, 0o600)
                path.unlink()
        shutil.rmtree(root / 'tmp', ignore_errors=True)
        return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('backup'); a.add_argument('--db', required=True); a.add_argument('--to', required=True)
    a = sub.add_parser('snapshot'); a.add_argument('--db', required=True)
    a = sub.add_parser('rollback'); a.add_argument('--db', required=True); a.add_argument('--media-root', required=True)
    a.add_argument('--outbox', required=True); a.add_argument('--archive', required=True)
    args = p.parse_args(argv)
    if args.command == 'backup':
        result = backup(args.db, args.to)
    elif args.command == 'snapshot':
        result = snapshot(args.db)
    else:
        result = rollback(args.db, args.media_root, args.outbox, args.archive)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TimeoutError) as e:
        print('REFUSED: %s: %s' % (type(e).__name__, e), file=sys.stderr)
        raise SystemExit(2)
