"""API_READ jobs of the daily queue: the server reads Beget, Metrica and Webmaster itself. No model, no browser.

Uses the queue's own chain and nothing else: claim -> lease -> observe (ops_work.Operations).
  - every attempt claims under its own unique worker name, so a result from an old or expired attempt is refused
    by the queue ("active owned lease required") and is never written;
  - a task that is DONE is not claimable, so a second run writes nothing: no duplicates;
  - evidence is written as MACHINE_OBSERVED, which the queue allows only for LOCAL_READ and API_READ tasks;
  - a partial Metrica reading keeps the good section in the observation, but the task becomes BLOCKED, not DONE;
  - only today's tasks (Yerevan day, as the planner counts) with kind API_READ are touched. Tasks planned before
    this kind existed keep their old kind and are left alone.

  python3 ops_api.py --db <runtime.sqlite> --secrets <beget-read.json> --secrets <yandex-read.json> --dry-run
  python3 ops_api.py --db <runtime.sqlite> --secrets <beget-read.json> --secrets <yandex-read.json> --write

--dry-run opens the database read-only, makes the real readings and prints what it would write. It writes nothing.
"""
import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bro_api_reader as R

KIND = 'API_READ'
LEASE = 600                 # seconds; the slowest reading (four Metrica queries with retries) stays below it
SUMMARY_LIMIT = 3900        # the queue refuses a summary over 4000 characters
YEREVAN = timezone(timedelta(hours=4))
SOURCES = {'HOSTING_DEADLINES': 'Beget API: user/getAccountInfo',
           'METRICA': 'Yandex Metrica API: stat/v1/data, site counter and Yandex Maps card counter',
           'WEBMASTER': 'Yandex Webmaster API v4: summary of the verified host'}


def today():
    return datetime.now(YEREVAN).date().isoformat()


def reading(job, secrets, cfg):
    """(entry, summary text, blocked). The text is what goes into the observation; it never holds a secret."""
    try:
        entry = R.read_job(job, secrets, cfg)
    except R.Blocked as reason:
        entry = {'status': 'BLOCKED', 'error_code': reason.code, 'reason': str(reason), 'fetched_at': R.utc_now()}
    text = json.dumps(entry, ensure_ascii=False, separators=(',', ':'))
    if len(text) > SUMMARY_LIMIT:
        entry = {'status': 'BLOCKED', 'error_code': 'SUMMARY_TOO_LARGE', 'fetched_at': entry['fetched_at'],
                 'reason': 'the reading does not fit into one observation; nothing from it was recorded'}
        text = json.dumps(entry, ensure_ascii=False, separators=(',', ':'))
    return entry, text, entry['status'] != 'OK'


def run_api(ops, day, secrets, cfg=None):
    """Claim, read and record every claimable API_READ task of the day. Returns what happened to each."""
    if day != today():
        raise ValueError('only the current day can be read: the readings are "yesterday" and "last 7 days" counted from now')
    results = []
    for task in ops.report(day)['tasks']:
        if task['kind'] != KIND or task['job'] not in R.API_JOBS:
            continue
        result = {'job': task['job'], 'task_id': task['id']}
        results.append(result)
        if task['status'] not in ('PENDING', 'BLOCKED') and not task['lease_expired']:
            result.update(outcome='NOT_CLAIMABLE', task_status=task['status'])
            continue
        worker = 'API_READ:' + uuid.uuid4().hex
        try:
            ops.claim(task['id'], worker, LEASE)
        except ValueError:
            result.update(outcome='CLAIM_LOST')            # another attempt won the atomic claim
            continue
        entry, text, blocked = reading(task['job'], secrets, cfg)
        try:
            saved = ops.observe(task['id'], worker, SOURCES[task['job']], entry['fetched_at'], text, blocked=blocked, machine=True)
        except ValueError:
            result.update(outcome='LEASE_LOST')            # the lease ended or passed to another attempt; nothing was written
            continue
        result.update(outcome=saved['status'], reading=entry['status'], error_code=entry.get('error_code'))
    return {'day': day, 'worker': 'API_READ', 'results': results, 'external_writes': False}


def dry_run(db, day, secrets, cfg=None):
    """The real readings and what would be written, with the database opened read-only."""
    if day != today():
        raise ValueError('only the current day can be read')
    connection = sqlite3.connect('file:%s?mode=ro' % Path(db).as_posix(), uri=True)
    try:
        rows = {r[0]: r[1:] for r in connection.execute('SELECT job,id,kind,status,lease_until FROM ops_tasks WHERE day=?', (day,))}
    finally:
        connection.close()
    results = []
    for job in R.API_JOBS:
        entry, text, blocked = reading(job, secrets, cfg)
        result = {'job': job, 'reading': entry, 'summary_characters': len(text), 'would_set': 'BLOCKED' if blocked else 'DONE'}
        if job not in rows:
            result.update(would_write=False, why='no task for this job today')
        else:
            task_id, kind, status, lease_until = rows[job]
            expired = status == 'CLAIMED' and datetime.fromisoformat(lease_until) <= datetime.now(timezone.utc)
            result.update(task_id=task_id, task_kind=kind, task_status=status)
            if kind != KIND:
                result.update(would_write=False, why='the task was planned with kind %s, before API_READ; it is left alone' % kind)
            elif status not in ('PENDING', 'BLOCKED') and not expired:
                result.update(would_write=False, why='the task is %s, not claimable' % status)
            else:
                result.update(would_write=True)
        results.append(result)
    return {'day': day, 'dry_run': True, 'database_opened': 'read-only', 'results': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--secrets', action='append', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('existing database required')
    try:
        secrets = R.load_secrets(*args.secrets)
    except R.Blocked as reason:
        print(json.dumps({'refused': reason.code, 'reason': str(reason)}))
        return 2
    if args.dry_run:
        result = dry_run(args.db, today(), secrets)
        good = all(r['reading']['status'] == 'OK' for r in result['results'])
    else:
        from ops_work import Operations
        result = run_api(Operations(args.db), today(), secrets)
        good = all(r['outcome'] in ('DONE', 'NOT_CLAIMABLE') for r in result['results'])
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
