"""Bro adapter gate v3: one script for the PreToolUse and PostToolUse hooks of a headless Claude run.

PreToolUse is the only gate. It allows one vetted call with permissionDecision "allow";
anything else ends with exit code 2 (hard block) and taints the run.
PostToolUse never allows anything. It accepts a result only when it pairs with the pending
PreToolUse by session_id + tool_use_id + tool_name + input, takes facts only from result
structures that are known (strict JSON, no text search), and otherwise taints the run.

v3: a tab that is merely visible in a listing is not a tab of this run. Only a tab whose creation
was bracketed (listing, create, listing with exactly one new blank tab) is owned and may be used.
Duplicate ids, duplicate JSON keys and listings that contradict earlier ones taint the run.

The run must be started default-deny (no allow rule for any browser tool), so a hook that
never starts leaves every call denied.

Usage in settings: command = python.exe, args = [this file, --policy, <policy.json>].
The wrapper asks for the final decision with: --policy <policy.json> --verdict
No secrets are read, written or printed here. Windows only (state lock uses msvcrt).
"""
import argparse
import hashlib
import json
import msvcrt
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

READ_TOOLS = {'get_page_text': {'tabId'},
              'read_page': {'tabId', 'depth', 'filter', 'max_chars', 'ref_id'},
              'find': {'tabId', 'query'}}
BLANK_TABS = {'chrome://newtab/', 'about:blank'}
BROWSER_KEYS = {'deviceId', 'name', 'osPlatform', 'connectedAt', 'isLocal', 'onThisComputer', 'inUse'}
MAX_TABS = 2
LOCK_SECONDS = 5.0
STATE_KEYS = {'v', 'session', 'tainted', 'seq', 'calls', 'pending', 'seen', 'profile', 'tabs', 'visible', 'creating',
              'closed', 'group', 'ctx_seq', 'reads'}


class Deny(Exception):
    pass


class Unknown(Exception):
    """A tool result whose structure is not one of the known ones."""


def new_state():
    # tabs: owned by this run (creation was bracketed). visible: ids in the latest listing, owned or not.
    return {'v': 3, 'session': None, 'tainted': None, 'seq': 0, 'calls': 0, 'pending': None, 'seen': [],
            'profile': {'ok': False, 'seq': None}, 'tabs': {}, 'visible': [], 'creating': None, 'closed': [],
            'group': None, 'ctx_seq': None,
            'reads': {'confirmed': 0, 'awaiting': None, 'last_seq': None}}


def load_policy(path):
    p = json.loads(Path(path).read_text(encoding='utf-8'))
    # trial_origins: local fake pages of the supervised trial. Accepted only for the job named TRIAL.
    trial = p.pop('trial_origins', None)
    # max_connected_browsers: optional and explicit. Absent = no limit on how many browsers are merely connected.
    limit = p.pop('max_connected_browsers', None)
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 10):
        raise ValueError('max_connected_browsers')
    if set(p) != {'job', 'tool_prefix', 'device_id', 'allowed_hosts', 'state_file', 'max_calls'}:
        raise ValueError('policy fields')
    if trial is not None:
        if p['job'] != 'TRIAL' or not isinstance(trial, list) or not trial:
            raise ValueError('trial origins outside a trial')
        for origin in trial:
            if not isinstance(origin, str) or not re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{3,4}', origin):
                raise ValueError('trial origin form')
    p['trial_origins'] = trial or []
    p['max_connected_browsers'] = limit
    if not isinstance(p['allowed_hosts'], list) or not p['allowed_hosts']:
        raise ValueError('allowed_hosts')
    for host in p['allowed_hosts']:
        if not isinstance(host, str) or not re.fullmatch(r'[a-z0-9.-]{3,100}', host):
            raise ValueError('host form')
    if not isinstance(p['device_id'], str) or not re.fullmatch(r'[a-f0-9-]{36}', p['device_id']):
        raise ValueError('device id form')
    if type(p['max_calls']) is not int or not 1 <= p['max_calls'] <= 200:
        raise ValueError('max_calls')
    return p


class Locked:
    """Exclusive lock for the whole read-modify-write of the state file."""

    def __init__(self, state_file):
        self.path = str(state_file) + '.lock'
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        deadline = time.monotonic() + LOCK_SECONDS
        while True:
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    os.close(self.fd)
                    self.fd = None
                    raise TimeoutError('state lock')
                time.sleep(0.02)

    def __exit__(self, *exc):
        if self.fd is not None:
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            finally:
                os.close(self.fd)


def load_state(path):
    path = Path(path)
    if not path.exists():
        return new_state()
    state = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(state, dict) or set(state) != STATE_KEYS or state['v'] != 3:
        raise ValueError('state fields')
    return state


def save_state(path, state):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def input_sha(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def host_allowed(url, policy):
    """True only for https://<exact allowed host>[:443]/... without user info."""
    if not isinstance(url, str) or len(url) > 2000 or any(c in url for c in '\r\n\t\\ '):
        return False
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        return False
    if u.username or u.password:
        return False
    if u.scheme == 'http' and policy['trial_origins']:
        return u.hostname == '127.0.0.1' and port is not None and 'http://127.0.0.1:%d' % port in policy['trial_origins']
    if u.scheme != 'https' or port not in (None, 443):
        return False
    return (u.hostname or '') in policy['allowed_hosts']


def tab_key(value):
    if type(value) is not int or value <= 0:
        raise Deny('tab id form')
    return str(value)


# ---------------------------------------------------------------- result structures

def envelope(response):
    """Return (first text block, is_error) for the known result envelopes; anything else is Unknown."""
    blocks = None
    error = False
    if isinstance(response, str):
        return response, False
    if isinstance(response, dict):
        if 'isError' in response and type(response['isError']) is not bool:
            raise Unknown('isError form')
        error = response.get('isError', False)
        if set(response) <= {'text', 'isError'} and isinstance(response.get('text'), str):
            return response['text'], error
        if set(response) <= {'content', 'isError'} and isinstance(response.get('content'), list):
            blocks = response['content']
    elif isinstance(response, list):
        blocks = response
    if not blocks or any(not isinstance(b, dict) or set(b) != {'type', 'text'} or b['type'] != 'text'
                         or not isinstance(b['text'], str) for b in blocks):
        raise Unknown('result envelope')
    return blocks[0]['text'], error


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise Unknown('duplicate key in a structured result')
    return dict(pairs)


def leading_json(text, kind):
    """The result must START with one JSON value of the expected type. The tail is ignored, never searched."""
    try:
        value, _ = json.JSONDecoder(object_pairs_hook=_no_duplicate_keys).raw_decode(text)
    except ValueError:
        raise Unknown('result is not structured') from None
    if not isinstance(value, kind):
        raise Unknown('result type')
    return value


def parse_browsers(text):
    rows = leading_json(text, list)
    if not rows:
        raise Unknown('no browsers')
    for row in rows:
        if (not isinstance(row, dict) or set(row) - BROWSER_KEYS or not isinstance(row.get('deviceId'), str)
                or ('inUse' in row and type(row['inUse']) is not bool)):
            raise Unknown('browser entry')
    ids = [row['deviceId'] for row in rows]
    if len(ids) != len(set(ids)):
        raise Unknown('duplicate device id')
    return rows


def parse_tabs(text):
    value = leading_json(text, dict)
    if (set(value) != {'availableTabs', 'tabGroupId'} or not isinstance(value['availableTabs'], list)
            or type(value['tabGroupId']) is not int):
        raise Unknown('tab context')
    tabs = {}
    for row in value['availableTabs']:
        if (not isinstance(row, dict) or set(row) != {'tabId', 'title', 'url'} or type(row['tabId']) is not int
                or row['tabId'] <= 0 or not isinstance(row['url'], str) or not isinstance(row['title'], str)):
            raise Unknown('tab entry')
        if str(row['tabId']) in tabs:
            raise Unknown('duplicate tab id')
        tabs[str(row['tabId'])] = row['url']
    return tabs, value['tabGroupId']


# ---------------------------------------------------------------- PreToolUse

def decide(policy, state, payload):
    """Raise Deny, or return normally after registering the call as pending."""
    state['calls'] += 1
    if state['tainted']:
        raise Deny('run is tainted: ' + state['tainted'])
    session, use_id = payload.get('session_id'), payload.get('tool_use_id')
    name, data = payload.get('tool_name'), payload.get('tool_input')
    if not isinstance(session, str) or not session or not isinstance(use_id, str) or not use_id:
        raise Deny('call identity missing')
    if state['session'] is None:
        state['session'] = session
    elif state['session'] != session:
        raise Deny('another session')
    if use_id in state['seen']:
        raise Deny('repeated tool_use_id')
    state['seen'].append(use_id)
    if state['pending'] is not None:
        raise Deny('previous call has no result yet')
    if state['calls'] > policy['max_calls']:
        raise Deny('call budget exceeded')
    if not isinstance(name, str) or not name.startswith(policy['tool_prefix']):
        raise Deny('unknown tool')
    if not isinstance(data, dict):
        raise Deny('input form')
    short = name[len(policy['tool_prefix']):]
    if state['reads']['awaiting'] is not None and short != 'tabs_context_mcp':
        raise Deny('a read is waiting for its tab check')
    if state['creating'] is not None and short != 'tabs_context_mcp':
        raise Deny('a created tab is not identified yet')

    def own(value):
        key = tab_key(value)
        if key not in state['tabs']:
            raise Deny('tab was not created by this run' if key in state['visible'] else 'unknown tab')
        return key

    if short == 'list_connected_browsers':
        if data:
            raise Deny('unexpected input')
    elif short == 'select_browser':
        if data != {'deviceId': policy['device_id']}:
            raise Deny('wrong profile requested')
        if state['profile']['ok']:
            raise Deny('profile change after confirmation')
    elif not state['profile']['ok']:
        raise Deny('profile not confirmed')
    elif short == 'tabs_context_mcp':
        if set(data) - {'createIfEmpty'} or data.get('createIfEmpty') not in (None, False):
            raise Deny('tab creation through context')
    elif short == 'tabs_create_mcp':
        if data:
            raise Deny('unexpected input')
        if len(state['tabs']) >= MAX_TABS:
            raise Deny('tab limit')
        if state['ctx_seq'] != state['seq']:
            raise Deny('no tab listing right before the creation')
    elif short == 'tabs_close_mcp':
        if set(data) != {'tabId'}:
            raise Deny('close input form')
        own(data['tabId'])
    elif short == 'navigate':
        if set(data) != {'tabId', 'url'}:
            raise Deny('navigate needs exactly tabId and url')
        own(data['tabId'])
        if not host_allowed(data['url'], policy):
            raise Deny('host not allowed')
    elif short in READ_TOOLS:
        if 'tabId' not in data or set(data) - READ_TOOLS[short]:
            raise Deny('read input form')
        key = own(data['tabId'])
        if not state['tabs'][key]['host_ok']:
            raise Deny('tab is not on a confirmed allowed host')
        if state['ctx_seq'] != state['seq']:
            raise Deny('tab check is not the call right before this read')
    else:
        raise Deny('tool not in the read-only set')
    state['pending'] = {'id': use_id, 'tool': name, 'input': input_sha(data)}


# ---------------------------------------------------------------- PostToolUse

def record(policy, state, payload):
    """Pair the result with the pending call and record facts from known structures. Raises Deny/Unknown to taint."""
    name, data = payload.get('tool_name'), payload.get('tool_input')
    pending = state['pending']
    if (pending is None or payload.get('session_id') != state['session'] or payload.get('tool_use_id') != pending['id']
            or name != pending['tool'] or not isinstance(data, dict) or input_sha(data) != pending['input']):
        raise Deny('result is unpaired, repeated or old')
    state['pending'] = None
    state['seq'] += 1
    text, failed = envelope(payload.get('tool_response'))
    if failed:
        raise Deny('tool reported an error')
    short = name[len(policy['tool_prefix']):]

    if short == 'list_connected_browsers':
        rows = parse_browsers(text)
        if policy['max_connected_browsers'] is not None and len(rows) > policy['max_connected_browsers']:
            raise Deny('more connected browsers than the policy allows')
        chosen = [row for row in rows if row.get('inUse') is True]
        if len(chosen) > 1:
            raise Deny('more than one browser reported in use')
        ok = len(chosen) == 1 and chosen[0]['deviceId'] == policy['device_id']
        if state['profile']['ok'] and not ok:
            raise Deny('profile changed during the run')
        state['profile'] = {'ok': ok, 'seq': state['seq'] if ok else None}
    elif short == 'select_browser':
        state['profile'] = {'ok': False, 'seq': None}      # no fact taken from this result
    elif short in ('tabs_create_mcp', 'tabs_close_mcp', 'navigate'):
        # No fact is taken from these results. Tabs and hosts are known only from the next tab context.
        state['ctx_seq'] = None
        for tab in state['tabs'].values():
            tab['host_ok'] = False
        if short == 'tabs_create_mcp':
            state['creating'] = {'baseline': list(state['visible'])}
        elif short == 'tabs_close_mcp':
            key = str(data['tabId'])
            state['tabs'].pop(key, None)
            state['closed'].append(key)
    elif short == 'tabs_context_mcp':
        tabs, group = parse_tabs(text)
        if state['group'] is not None and group != state['group']:
            raise Deny('tab group changed during the run')
        state['group'] = group
        if any(key in tabs for key in state['closed']):
            raise Deny('a closed tab is listed again')
        if any(key not in tabs for key in state['tabs']):
            raise Deny('a tab of this run disappeared')
        if state['creating'] is not None:
            # Ownership: exactly one id that was not listed right before the creation, and it is still blank.
            baseline = state['creating']['baseline']
            fresh = [key for key in tabs if key not in baseline]
            if any(key not in tabs for key in baseline) or len(fresh) != 1 or tabs[fresh[0]] not in BLANK_TABS:
                raise Deny('created tab identity not confirmed')
            state['tabs'][fresh[0]] = {'host_ok': False}
            state['creating'] = None
        for key in state['tabs']:
            if tabs[key] not in BLANK_TABS and not host_allowed(tabs[key], policy):
                raise Deny('a tab of this run is outside the allowed hosts')
            state['tabs'][key] = {'host_ok': host_allowed(tabs[key], policy)}
        state['visible'] = list(tabs)
        state['ctx_seq'] = state['seq']
        waiting = state['reads']['awaiting']
        if waiting is not None:
            if not state['tabs'].get(waiting, {}).get('host_ok'):
                raise Deny('tab was not on an allowed host right after the read')
            state['reads']['confirmed'] += 1
            state['reads']['awaiting'] = None
    elif short in READ_TOOLS:
        state['reads']['awaiting'] = str(data['tabId'])
        state['reads']['last_seq'] = state['seq']
    else:
        raise Deny('result of a tool outside the set')


def verdict(state):
    """What the trusted wrapper asks after the run. Only a fully bracketed run is accepted."""
    if state['tainted']:
        return False, 'tainted: ' + state['tainted']
    if state['pending'] is not None:
        return False, 'a call never returned'
    if state['creating'] is not None:
        return False, 'a created tab was never identified'
    if state['reads']['awaiting'] is not None:
        return False, 'a read has no tab check after it'
    if state['reads']['confirmed'] < 1:
        return False, 'nothing was read'
    if not state['profile']['ok'] or state['profile']['seq'] is None or state['profile']['seq'] < state['reads']['last_seq']:
        return False, 'profile was not confirmed again after the last read'
    return True, 'ok'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', required=True)
    parser.add_argument('--verdict', action='store_true')
    args = parser.parse_args()
    try:
        policy = load_policy(args.policy)
    except Exception:
        sys.stderr.write('BRO GATE ERROR: policy\n')
        return 2
    try:
        with Locked(policy['state_file']):
            try:
                state = load_state(policy['state_file'])
            except Exception:
                state = new_state()
                state['tainted'] = 'state unreadable'
                save_state(policy['state_file'], state)
                sys.stderr.write('BRO GATE ERROR: state\n')
                return 2
            if args.verdict:
                ok, reason = verdict(state)
                sys.stdout.write(json.dumps({'accept': ok, 'reason': reason}))
                return 0 if ok else 2
            try:
                payload = json.loads(sys.stdin.buffer.read().decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('payload')
                event = payload.get('hook_event_name')
                if event == 'PreToolUse':
                    decide(policy, state, payload)
                    save_state(policy['state_file'], state)
                    sys.stdout.write(json.dumps({'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                        'permissionDecisionReason': 'Bro gate: read-only call inside policy'}}))
                    return 0
                if event == 'PostToolUse':
                    record(policy, state, payload)
                    save_state(policy['state_file'], state)
                    return 0
                raise Deny('unexpected hook event')
            except Exception as reason:
                label = str(reason) if isinstance(reason, (Deny, Unknown)) else 'gate error'
                state['tainted'] = state['tainted'] or label
                state['pending'] = None if isinstance(reason, (Deny, Unknown)) else state['pending']
                save_state(policy['state_file'], state)
                sys.stderr.write('BRO GATE DENY: ' + label + '\n')
                return 2
    except Exception:
        sys.stderr.write('BRO GATE ERROR: call blocked\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
