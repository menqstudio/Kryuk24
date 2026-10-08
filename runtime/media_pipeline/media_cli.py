"""Command line of the media pipeline. Prints JSON. Publishes nothing.

Agent commands (queue, claim, fetch, prepare, release) need a worker name and act only on work that worker holds.
Operator commands: intake, reopen, submit, sync, cleanup, storage.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from media_pipeline import MediaPipeline, DEFAULT_LIMIT


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--db', required=True)
    p.add_argument('--media-root', required=True)
    p.add_argument('--limit-bytes', type=int, default=DEFAULT_LIMIT)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('intake'); a.add_argument('--outbox', required=True, help="the portal's outbox folder: the only thing of the portal this reads")
    a = sub.add_parser('queue'); a.add_argument('--status')
    a = sub.add_parser('claim'); a.add_argument('--work', required=True); a.add_argument('--worker', required=True); a.add_argument('--seconds', type=int, default=900)
    a = sub.add_parser('fetch'); a.add_argument('--work', required=True); a.add_argument('--worker', required=True); a.add_argument('--out', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--work', required=True); a.add_argument('--worker', required=True)
    a.add_argument('--masks', help='JSON file: [{"kind":"PLATE","box":[left,top,right,bottom]}, ...]'); a.add_argument('--nothing-to-mask', action='store_true')
    a = sub.add_parser('release'); a.add_argument('--work', required=True); a.add_argument('--worker', required=True); a.add_argument('--reason', required=True)
    a = sub.add_parser('reopen'); a.add_argument('--work', required=True); a.add_argument('--reason', required=True)
    a = sub.add_parser('submit'); a.add_argument('--works', required=True, help='comma separated'); a.add_argument('--day', required=True)
    for name in ('worker', 'platform', 'account', 'body', 'reason'):
        a.add_argument('--' + name, required=True)
    sub.add_parser('sync')
    sub.add_parser('cleanup')
    sub.add_parser('storage')
    args = p.parse_args(argv)
    pipe = MediaPipeline(args.db, args.media_root, limit=args.limit_bytes)
    if args.command == 'intake':
        result = pipe.intake(args.outbox)
    elif args.command == 'queue':
        result = pipe.queue(args.status)
    elif args.command == 'claim':
        result = pipe.claim(args.work, args.worker, args.seconds)
    elif args.command == 'fetch':
        raw = pipe.original_bytes(args.work, args.worker)
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # a new private file, never over an existing one
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        result = {'work': args.work, 'bytes': len(raw), 'out': args.out}
    elif args.command == 'prepare':
        masks = json.loads(Path(args.masks).read_text(encoding='utf-8')) if args.masks else []
        result = pipe.prepare(args.work, args.worker, masks, args.nothing_to_mask)
    elif args.command == 'release':
        result = pipe.release(args.work, args.worker, args.reason)
    elif args.command == 'reopen':
        result = pipe.reopen(args.work, args.reason)
    elif args.command == 'submit':
        task = pipe.submit(args.works.split(','), args.day, args.worker, args.platform, args.account, args.body, args.reason)
        result = {k: task[k] for k in ('id', 'day', 'job', 'status', 'digest')}
        result.update(destination=task['draft']['destination'], assets=task['draft']['assets'], published=False)
    elif args.command == 'sync':
        result = pipe.sync()
    elif args.command == 'cleanup':
        result = pipe.cleanup()
    else:
        result = pipe.storage()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, LookupError, PermissionError, TimeoutError) as e:
        print('REFUSED: %s: %s' % (type(e).__name__, e), file=sys.stderr)
        raise SystemExit(2)
