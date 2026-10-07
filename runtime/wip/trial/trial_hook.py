"""Hook used only in the supervised trial. It records every raw hook event, then behaves as the case requires.

Modes:
  gate    record, then run the real gate (bro_gate_hook) on the same event
  probe   record; allow only the tools named in --allow (PreToolUse), deny the rest with exit 2
  deny    record; exit 2
  crash   record; die with an unhandled error (exit code 1)
  hang    record; sleep far beyond the hook timeout
  silent  record; exit 0 with no output (no decision at all)

The record (events.jsonl) holds the full raw event, because the trial uses fake pages and an empty profile.
Never use this hook outside the trial.
"""
import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=['gate', 'probe', 'deny', 'crash', 'hang', 'silent'])
    parser.add_argument('--events', required=True)
    parser.add_argument('--policy')
    parser.add_argument('--gate-dir')
    parser.add_argument('--allow', default='')
    args = parser.parse_args()

    raw = sys.stdin.buffer.read()
    try:
        event = json.loads(raw.decode('utf-8'))
    except Exception:
        event = {'unparsed': raw.decode('utf-8', 'replace')[:2000]}
    row = {'ts': datetime.now(timezone.utc).isoformat(), 'mode': args.mode, 'event': event}

    def write(extra):
        with open(args.events, 'a', encoding='utf-8') as f:
            f.write(json.dumps({**row, **extra}, ensure_ascii=False) + '\n')

    if args.mode == 'crash':
        write({'decision': 'crash'})
        raise RuntimeError('trial: deliberate hook crash')
    if args.mode == 'hang':
        write({'decision': 'hang'})
        time.sleep(600)
        return 0
    if args.mode == 'silent':
        write({'decision': 'silent'})
        return 0
    if args.mode == 'deny':
        write({'decision': 'deny'})
        sys.stderr.write('TRIAL HOOK: deny\n')
        return 2
    if args.mode == 'probe':
        if event.get('hook_event_name') != 'PreToolUse':
            write({'decision': 'recorded'})
            return 0
        if event.get('tool_name') in [t for t in args.allow.split(',') if t]:
            write({'decision': 'allow'})
            sys.stdout.write(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                                                                 'permissionDecisionReason': 'trial probe'}}))
            return 0
        write({'decision': 'deny'})
        sys.stderr.write('TRIAL HOOK: tool outside the probe list\n')
        return 2

    # gate: hand the same bytes to the real gate and pass its answer through unchanged
    sys.path.insert(0, args.gate_dir)
    import bro_gate_hook
    out = io.StringIO()
    real_stdin, real_stdout, real_argv = sys.stdin, sys.stdout, sys.argv
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8')
    sys.stdout = out
    sys.argv = ['bro_gate_hook.py', '--policy', args.policy]
    try:
        code = bro_gate_hook.main()
    finally:
        sys.stdin, sys.stdout, sys.argv = real_stdin, real_stdout, real_argv
    write({'decision': 'allow' if code == 0 and event.get('hook_event_name') == 'PreToolUse' else ('recorded' if code == 0 else 'deny'), 'gate_exit': code})
    sys.stdout.write(out.getvalue())
    return code


if __name__ == '__main__':
    sys.exit(main())
