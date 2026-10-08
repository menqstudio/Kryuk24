"""Offline deterministic evaluation of explicitly supplied monitoring observations."""
import argparse
import json
import math
import os
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_INPUT = 65536
MAX_DEPTH = 64
CHECKS = ('health', 'backup', 'hosting', 'certificate')
FIELDS = {
    'health': {'reachable', 'mode', 'sending_enabled'},
    'backup': {'last_success', 'restore_verified'},
    'hosting': {'balance_kopecks', 'daily_cost_kopecks'},
    'certificate': {'not_after'},
}


class ContractError(ValueError):
    pass


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ContractError('timezone-aware ISO timestamp required')
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise ContractError('invalid timestamp') from None
    if result.utcoffset() is None:
        raise ContractError('timestamp timezone required')
    return result.astimezone(timezone.utc)


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ContractError('integer outside allowed range')
    return value


def boolean(value):
    if type(value) is not bool:
        raise ContractError('boolean required')
    return value


def exact(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ContractError('exact fields required')


def policy(value):
    exact(value, {'schema', 'expected_mode', 'expected_sending', 'max_age_seconds',
                  'backup_max_age_seconds', 'hosting_min_days', 'certificate_min_days'})
    integer(value['schema'], 1, 1)
    if value['expected_mode'] not in ('STAGING', 'LIVE'):
        raise ContractError('expected mode required')
    boolean(value['expected_sending'])
    exact(value['max_age_seconds'], set(CHECKS))
    for age in value['max_age_seconds'].values():
        integer(age, 1, 7 * 86400)
    integer(value['backup_max_age_seconds'], 1, 30 * 86400)
    integer(value['hosting_min_days'], 1, 365)
    integer(value['certificate_min_days'], 1, 365)
    return value


def evaluate(document, rules, at):
    """No network, writes, schedules or alerts. Source labels are provenance, not authentication."""
    rules = policy(rules)
    if not isinstance(at, datetime) or at.utcoffset() is None:
        raise ContractError('aware evaluation time required')
    at = at.astimezone(timezone.utc)
    exact(document, {'schema', 'observations'})
    integer(document['schema'], 1, 1)
    observations = document['observations']
    if type(observations) is not dict or set(observations) - set(CHECKS):
        raise ContractError('unknown observation kind')
    rows = []
    for name in CHECKS:
        row = {'check': name, 'status': 'UNKNOWN', 'reason': 'missing_observation'}
        obs = observations.get(name)
        if obs is None:
            rows.append(row)
            continue
        try:
            exact(obs, {'source', 'observed_at', 'values'})
            if not isinstance(obs['source'], str) or not obs['source'].strip() or len(obs['source']) > 120:
                raise ContractError('source required')
            observed = timestamp(obs['observed_at'])
            if observed > at:
                row['reason'] = 'future_observation'
            elif at - observed > timedelta(seconds=rules['max_age_seconds'][name]):
                row['reason'] = 'stale_observation'
            else:
                values = obs['values']
                exact(values, FIELDS[name])
                row.update(_check(name, values, rules, observed, at))
        except (ContractError, TypeError, OverflowError):
            # Do not echo malformed observations: they may contain private values.
            row['reason'] = 'invalid_observation'
        rows.append(row)
    statuses = {row['status'] for row in rows}
    overall = 'ALERT' if 'ALERT' in statuses else ('UNKNOWN' if 'UNKNOWN' in statuses else 'OK')
    return {'schema': 1, 'evaluated_at': at.isoformat(), 'status': overall,
            'checks': rows, 'alerts_sent': False, 'collection_performed': False}


def _check(name, values, rules, observed, at):
    if name == 'health':
        reachable = boolean(values['reachable'])
        mode = values['mode']
        sending = values['sending_enabled']
        if mode is not None and mode not in ('STAGING', 'LIVE'):
            raise ContractError('known mode or unavailable required')
        if sending is not None:
            boolean(sending)
        reasons = []
        if not reachable:
            reasons.append('unreachable')
        if mode is not None and mode != rules['expected_mode']:
            reasons.append('unexpected_mode')
        if sending is not None and sending != rules['expected_sending']:
            reasons.append('unexpected_sending')
        missing = [field for field in ('mode', 'sending_enabled') if values[field] is None]
        return {'status': 'ALERT' if reasons else ('UNKNOWN' if missing else 'OK'),
                'reason': ','.join(reasons) or ('health_details_unavailable' if missing else 'health_matches_policy'),
                'unknown_fields': missing}
    if name == 'backup':
        saved = timestamp(values['last_success'])
        restored = boolean(values['restore_verified'])
        if saved > observed:
            raise ContractError('backup success cannot follow observation')
        if at - saved > timedelta(seconds=rules['backup_max_age_seconds']):
            return {'status': 'ALERT', 'reason': 'backup_overdue'}
        if not restored:
            return {'status': 'UNKNOWN', 'reason': 'restore_unverified'}
        return {'status': 'OK', 'reason': 'backup_recent_restore_reported_verified'}
    if name == 'hosting':
        balance = integer(values['balance_kopecks'], -10**15, 10**15)
        cost = integer(values['daily_cost_kopecks'], 1, 10**12)
        # Avoid float rounding and do not present the estimate as a provider deadline.
        low = balance < rules['hosting_min_days'] * cost
        return {'status': 'ALERT' if low else 'OK', 'reason': 'hosting_below_threshold' if low else 'hosting_above_threshold',
                'estimated_whole_days': max(0, balance // cost)}
    expires = timestamp(values['not_after'])
    remaining = expires - at
    low = remaining < timedelta(days=rules['certificate_min_days'])
    return {'status': 'ALERT' if low else 'OK', 'reason': 'certificate_expired' if remaining <= timedelta(0) else
            ('certificate_near_expiry' if low else 'certificate_above_threshold')}


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ContractError('duplicate JSON key')
        out[key] = value
    return out


def bound_depth(text):
    """Bound nested containers before JSON decoding, ignoring quoted content."""
    depth = 0
    quoted = False
    escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in '[{':
            depth += 1
            if depth > MAX_DEPTH:
                raise ContractError('JSON nesting too deep')
        elif character in ']}':
            depth -= 1


def read_json(path):
    # Nonblocking open prevents a mistakenly supplied FIFO from hanging before
    # we can inspect its type. O_BINARY is needed on Windows descriptors.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContractError('regular JSON file required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_INPUT + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_INPUT:
        raise ContractError('input too large')
    def nonfinite(_):
        raise ContractError('nonfinite JSON number')
    def finite_float(text):
        number = float(text)
        if not math.isfinite(number):
            raise ContractError('nonfinite JSON number')
        return number
    def bounded_integer(text):
        # Largest supported value is 10**15. Bound literals before int(),
        # independently of interpreter-specific integer conversion settings.
        if len(text.lstrip('-')) > 16:
            raise ContractError('JSON integer too large')
        return int(text)
    try:
        text = raw.decode('utf-8')
        bound_depth(text)
        return json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=nonfinite, parse_float=finite_float,
                          parse_int=bounded_integer)
    except (ValueError, RecursionError):
        raise ContractError('invalid JSON') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', required=True)
    parser.add_argument('--policy', required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(read_json(args.observations), read_json(args.policy), datetime.now(timezone.utc))
    except (OSError, ContractError, RecursionError):
        print(json.dumps({'schema': 1, 'status': 'UNKNOWN', 'reason': 'input_rejected', 'alerts_sent': False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return {'OK': 0, 'ALERT': 1, 'UNKNOWN': 2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
