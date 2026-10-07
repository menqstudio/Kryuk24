"""Bro daily collector over APIs. Deterministic: no model, no browser. Read-only.

Readings (three API sources, four readings, mapped to three existing queue jobs):
  HOSTING_DEADLINES  Beget: balance, days to block, daily and monthly rate
  METRICA            Yandex Metrica: site counter and Yandex Maps card counter, as two separate evidence sections
  WEBMASTER          Yandex Webmaster: summary of the verified host
Listed, not read: YANDEX_DIRECT (access request not approved, API error 58), AVITO (on hold by the owner).

Rules:
  - only the endpoints in ALLOWED are ever requested; HTTPS with certificate verification; redirects are not followed;
    every request has a timeout and a response-size limit; a retry happens only after a timeout, HTTP 429 or 5xx;
  - Yandex is read with GET only. Beget's read method is one POST form to user/getAccountInfo and nothing else;
  - it takes the READ credentials only. A secrets file with an actions token, a mail credential or any unknown key is
    refused: the collector must not be able to act;
  - a secret never goes into a result, a log line or an error text; error bodies of the services are not recorded;
  - a number is reported only when the API returned it in a valid answer. A real zero comes only from such an answer.
    A missing or wrong-typed metric makes that reading BLOCKED; nothing is estimated or carried over;
  - a number is never cut or rounded. NaN, Infinity, a negative count, a count over COUNT_LIMIT, more users than
    visits and goal clicks without a visit are refused (METRIC_INVALID), and the reading is BLOCKED;
  - Metrica counts: with sampled=false every count must be a whole number, a fraction is refused. With sampled=true
    the numbers are the API's estimates: they are kept exactly as returned, marked exact=false, and sample_share
    must be a number above 0 and not above 1;
  - Metrica dates are whole days of the Europe/Moscow calendar: yesterday, and the last seven finished days. Every
    query carries timezone=+03:00, so the days do not depend on the counter's own setting;
  - contact goals are clicks on a button (conversions), not calls, leads or orders. Site and Maps audiences are never
    added together. Beget's days_to_block is the API's estimate, not a guaranteed payment deadline. A zero in the
    Webmaster summary does not by itself prove a site-wide problem.

This file does not talk to the Bro queue. `collect()` returns the readings; `--out` writes them to a new file (dry-run).

  python bro_api_reader.py --secrets <beget.json> --secrets <yandex.json> --out <report.json>
  python bro_api_reader.py --windows-user-store --out <report.json>      local dry-run on the owner's Windows account
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = '0.3.2'
ALLOWED_SECRET_KEYS = {'yandex_read_token', 'beget_login', 'beget_api_password'}
MOSCOW = timezone(timedelta(hours=3))        # Europe/Moscow has been UTC+3 without daylight saving since 2014
MOSCOW_OFFSET = '+03:00'                     # sent to Metrica with every query
MAX_BYTES = 1048576
COUNT_LIMIT = 10 ** 9                        # no count or amount of this client can be above it
CONFIG = {
    'beget_api': 'https://api.beget.com/api',
    'metrica_api': 'https://api-metrika.yandex.net',
    'webmaster_api': 'https://api.webmaster.yandex.net/v4',
    'site_counter': 113277361,
    'site_goals': {'phone_click': 666763225, 'whatsapp_click': 666763625, 'telegram_click': 666763940},
    'maps_counter': 86067232,
    'maps_goals': {'call_click': 223475037, 'route_build': 223475038, 'to_site': 398183355},
    'webmaster_host': 'https:kryuk24.ru:443',
    'timeout': 30, 'retries': 2, 'retry_wait': 2.0, 'require_https': True,
}
NOT_READ = {
    'YANDEX_DIRECT': ('NOT_READY', 'API access request sent on 07.10.2026 is not approved (API error 58)'),
    'AVITO': ('ON_HOLD', 'keys exist; the owner said not to touch Avito yet'),
}


class Blocked(Exception):
    """A reading could not be made. `code` is a short safe label; the text never contains a secret or a service's error body."""

    def __init__(self, code, text):
        super().__init__(text)
        self.code = code


def not_a_number(token):
    raise ValueError(token)                               # NaN and Infinity are not JSON


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def moscow_ranges(now=None):
    """Whole days of the Moscow calendar: yesterday, and the seven finished days ending yesterday."""
    today = (now or datetime.now(timezone.utc)).astimezone(MOSCOW).date()
    yesterday = today - timedelta(days=1)
    return {'yesterday': (yesterday.isoformat(), yesterday.isoformat()),
            'last_7_days': ((today - timedelta(days=7)).isoformat(), yesterday.isoformat())}


def allowed(cfg, url, method):
    """Only these requests exist for the collector."""
    parts = urllib.parse.urlsplit(url)
    base = lambda key: urllib.parse.urlsplit(cfg[key])
    def under(key, path, exact=True):
        b = base(key)
        full = b.path.rstrip('/') + path
        return (parts.scheme, parts.netloc) == (b.scheme, b.netloc) and (parts.path == full if exact else parts.path.startswith(full))
    if method == 'POST':
        return under('beget_api', '/user/getAccountInfo') and not parts.query
    if method != 'GET':
        return False
    if under('metrica_api', '/stat/v1/data') or under('webmaster_api', '/user'):
        return True
    rest = parts.path[len(base('webmaster_api').path.rstrip('/')):] if under('webmaster_api', '/user/', exact=False) else ''
    pieces = rest.strip('/').split('/')                    # user/<id>/hosts  or  user/<id>/hosts/<host>/summary
    return (len(pieces) in (3, 5) and pieces[0] == 'user' and pieces[1].isdigit() and pieces[2] == 'hosts'
            and (len(pieces) == 3 or pieces[4] == 'summary'))


def http_json(cfg, url, headers=None, form=None):
    """One allowed request, JSON back. Retries only after a timeout, HTTP 429 or 5xx."""
    method = 'POST' if form is not None else 'GET'
    host = urllib.parse.urlsplit(url).netloc
    if cfg['require_https'] and not url.startswith('https://'):
        raise Blocked('NOT_HTTPS', 'request refused: not HTTPS')
    if not allowed(cfg, url, method):
        raise Blocked('ENDPOINT_NOT_ALLOWED', 'request refused: endpoint is not on the allowed list')
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    last = None
    for attempt in range(cfg['retries'] + 1):
        if attempt:
            time.sleep(cfg['retry_wait'] * attempt)
        try:
            request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
            with opener.open(request, timeout=cfg['timeout']) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise Blocked('RESPONSE_TOO_LARGE', 'answer from %s is larger than the limit' % host)
            try:
                return json.loads(raw.decode('utf-8'), parse_constant=not_a_number)
            except ValueError:
                raise Blocked('NOT_JSON', 'answer from %s is not JSON' % host) from None
        except urllib.error.HTTPError as error:
            error.close()                                  # the error body is never read; do not leave its socket open
            if 300 <= error.code < 400:
                raise Blocked('REDIRECT_REFUSED', 'redirect from %s was not followed' % host) from None
            last = Blocked('HTTP_%d' % error.code, 'HTTP %d from %s' % (error.code, host))
            if error.code != 429 and error.code < 500:
                raise last from None                       # auth and request errors are not retried
        except Blocked:
            raise
        except (urllib.error.URLError, OSError, TimeoutError):
            last = Blocked('NO_ANSWER', 'no answer from %s in time' % host)
    raise last


def load_secrets(*paths):
    """The collector's own secrets, from one or more JSON files (Beget and Yandex are kept in separate files).

    Any key outside the read set is a refusal, so an actions token cannot ride along. On Linux a file that
    every user of the machine can read is refused too.
    """
    merged = {}
    for path in paths:
        try:
            open_to_all = os.name == 'posix' and os.stat(path).st_mode & 0o007
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise Blocked('SECRETS_UNREADABLE', 'secrets file missing or not JSON') from None
        if open_to_all:
            raise Blocked('SECRETS_OPEN_TO_ALL', 'secrets file is readable by every user of the machine')
        if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
            raise Blocked('SECRETS_FORM', 'secrets file has an unknown form')
        extra = sorted(set(data) - ALLOWED_SECRET_KEYS)
        if extra:
            raise Blocked('SECRETS_NOT_READ_ONLY', 'secrets file holds keys the collector must not have: %s' % ', '.join(extra))
        if set(data) & set(merged):
            raise Blocked('SECRETS_FORM', 'the same key is in two secrets files')
        merged.update(data)
    return merged


def windows_user_store():
    """Local dry-run only: the read token from the user's environment in the registry and the Beget API password file.

    The actions token and the Avito keys live in the same place and are deliberately not read.
    """
    import winreg
    secrets = {'beget_login': 'amo777z0'}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            secrets['yandex_read_token'] = winreg.QueryValueEx(key, 'YANDEX_OAUTH_TOKEN')[0]
    except OSError:
        pass
    path = Path.home() / '.ssh' / 'kryuk24_beget_api_password.txt'
    if path.exists():
        secrets['beget_api_password'] = path.read_text(encoding='utf-8').strip()
    return secrets


def need(secrets, *keys):
    missing = [k for k in keys if not secrets.get(k)]
    if missing:
        raise Blocked('SECRET_MISSING', 'secret not provided: %s' % ', '.join(missing))


def number(source, key, kind, what, low=0, high=COUNT_LIMIT):
    """A value of the expected type from a service answer, or Blocked. bool is not a number here.

    A number must be finite and between `low` and `high` (low=None: any sign down to -high, as for a balance;
    high=None: no upper limit, as for an identifier, which is not a measurement).
    """
    value = source.get(key) if isinstance(source, dict) else None
    if kind is str and isinstance(value, str) and value:
        return value
    if not (kind is int and type(value) is int or kind is float and type(value) in (int, float)):
        raise Blocked('METRIC_MISSING', '%s: %s is missing or has an unknown form' % (what, key))
    if not math.isfinite(value) or (high is not None and abs(value) > high) or (low is not None and value < low):
        raise Blocked('METRIC_INVALID', '%s: %s is not a possible value' % (what, key))
    return kind(value)


def count(value, sampled, what):
    """One Metrica count, never cut or rounded. Unsampled: a whole number or Blocked. Sampled: the estimate as returned."""
    if type(value) not in (int, float):
        raise Blocked('METRIC_MISSING', '%s: totals are missing or have an unknown form' % what)
    if not math.isfinite(value) or not 0 <= value <= COUNT_LIMIT:
        raise Blocked('METRIC_INVALID', '%s: a total is not a possible count' % what)
    if value == int(value):
        return int(value)
    if not sampled:
        raise Blocked('METRIC_INVALID', '%s: a total is a fraction although the answer is not sampled' % what)
    return value


# ---------------- readings
def read_beget(secrets, cfg):
    need(secrets, 'beget_login', 'beget_api_password')
    answer = http_json(cfg, cfg['beget_api'] + '/user/getAccountInfo',
                       form={'login': secrets['beget_login'], 'passwd': secrets['beget_api_password'], 'output_format': 'json'})
    inner = answer.get('answer') if isinstance(answer, dict) else None
    if not isinstance(answer, dict) or answer.get('status') != 'success' or not isinstance(inner, dict) or inner.get('status') != 'success':
        code = answer.get('error_code') if isinstance(answer, dict) else None
        raise Blocked('API_ERROR', 'Beget refused: %s' % (code if isinstance(code, str) and code.isupper() else 'answer status is not success'))
    result = inner.get('result')
    return {'source': 'beget user/getAccountInfo', 'account': secrets['beget_login'],
            'balance': {'value': number(result, 'user_balance', float, 'Beget', low=None), 'unit': 'RUB'},
            'days_to_block': {'value': number(result, 'user_days_to_block', int, 'Beget'), 'unit': 'days',
                              'meaning': "the API's estimate at the current rate, not a guaranteed payment deadline"},
            'rate_per_day': {'value': number(result, 'user_rate_current', float, 'Beget'), 'unit': 'RUB/day'},
            'rate_per_month': {'value': number(result, 'user_rate_month', float, 'Beget'), 'unit': 'RUB/month'},
            'plan': number(result, 'plan_name', str, 'Beget')}


def metrica_totals(secrets, cfg, counter, goals, date1, date2):
    metrics = ['ym:s:visits', 'ym:s:users'] + ['ym:s:goal%dreaches' % g for g in goals.values()]
    query = urllib.parse.urlencode({'ids': counter, 'metrics': ','.join(metrics), 'date1': date1, 'date2': date2, 'accuracy': 'full',
                                    'timezone': MOSCOW_OFFSET})
    answer = http_json(cfg, cfg['metrica_api'] + '/stat/v1/data?' + query, headers={'Authorization': 'OAuth ' + secrets['yandex_read_token']})
    totals = answer.get('totals') if isinstance(answer, dict) else None
    what = 'Metrica counter %s' % counter
    if not isinstance(totals, list) or len(totals) != len(metrics):
        raise Blocked('METRIC_MISSING', '%s: totals are missing or have an unknown form' % what)
    sampled, share = answer.get('sampled'), answer.get('sample_share')
    if type(sampled) is not bool:
        raise Blocked('METRIC_MISSING', '%s: sampling flag is missing' % what)
    if type(share) not in (int, float):
        if sampled:
            raise Blocked('METRIC_MISSING', '%s: the answer is sampled but the sample share is missing' % what)
        share = None
    elif not math.isfinite(share) or not 0 < share <= 1:
        raise Blocked('METRIC_INVALID', '%s: the sample share is not a possible value' % what)
    visits, users, *clicks = (count(t, sampled, what) for t in totals)
    if not sampled and (users > visits or visits == 0 and any(clicks)):
        raise Blocked('METRIC_INVALID', '%s: the totals contradict each other' % what)
    values = {'visits': visits, 'users': users, 'goal_clicks': dict(zip(goals, clicks))}
    return {'date_from': date1, 'date_to': date2, 'timezone': 'Europe/Moscow', 'utc_offset': MOSCOW_OFFSET, 'values': values,
            'units': 'estimated counts' if sampled else 'counts', 'exact': not sampled, 'sampled': sampled, 'sample_share': share}


def read_counter(secrets, cfg, counter_key, goals_key, ranges):
    need(secrets, 'yandex_read_token')
    counter, goals = cfg[counter_key], cfg[goals_key]
    out = {'source': 'metrica stat/v1/data', 'counter': counter, 'goal_ids': goals,
           'meaning': 'goal_clicks are clicks on a contact button (conversions), not calls, leads or orders'}
    for name, (date1, date2) in ranges.items():
        out[name] = metrica_totals(secrets, cfg, counter, goals, date1, date2)
    return out


def read_webmaster(secrets, cfg):
    need(secrets, 'yandex_read_token')
    headers = {'Authorization': 'OAuth ' + secrets['yandex_read_token']}
    user_id = number(http_json(cfg, cfg['webmaster_api'] + '/user', headers=headers), 'user_id', int, 'Webmaster user', low=1, high=None)
    base = '%s/user/%d/hosts' % (cfg['webmaster_api'], user_id)
    listed = http_json(cfg, base, headers=headers)
    hosts = listed.get('hosts') if isinstance(listed, dict) else None
    host = next((h for h in hosts or [] if isinstance(h, dict) and h.get('host_id') == cfg['webmaster_host']), None)
    if host is None:
        raise Blocked('HOST_NOT_LISTED', 'Webmaster does not list the host %s' % cfg['webmaster_host'])
    if host.get('verified') is not True:
        raise Blocked('HOST_NOT_VERIFIED', 'Webmaster host is not verified')
    summary = http_json(cfg, '%s/%s/summary' % (base, urllib.parse.quote(cfg['webmaster_host'], safe='')), headers=headers)
    problems = summary.get('site_problems') if isinstance(summary, dict) else None
    return {'source': 'webmaster hosts/<host>/summary', 'host_id': cfg['webmaster_host'],
            'pages_in_search': {'value': number(summary, 'searchable_pages_count', int, 'Webmaster'), 'unit': 'pages'},
            'pages_excluded': {'value': number(summary, 'excluded_pages_count', int, 'Webmaster'), 'unit': 'pages'},
            'sqi': {'value': number(summary, 'sqi', int, 'Webmaster'), 'unit': 'index'},
            'site_problems': {k: v for k, v in problems.items() if isinstance(k, str) and type(v) is int} if isinstance(problems, dict) else {},
            'meaning': 'a zero here does not by itself prove a site-wide problem'}


def guarded(reader):
    """One reading: OK with evidence, or BLOCKED with a safe code. A bug in the collector is BLOCKED too, never a value."""
    try:
        entry = {'status': 'OK', 'evidence': reader()}
    except Blocked as reason:
        entry = {'status': 'BLOCKED', 'error_code': reason.code, 'reason': str(reason)}
    except Exception as error:
        entry = {'status': 'BLOCKED', 'error_code': 'COLLECTOR_ERROR', 'reason': 'collector error: %s' % type(error).__name__}
    entry['fetched_at'] = utc_now()                       # the moment the answer (or the refusal) was in hand
    return entry


API_JOBS = ('HOSTING_DEADLINES', 'METRICA', 'WEBMASTER')


def no_secret(secrets, value):
    """Last line of defence: something that holds a secret is not handed on."""
    dump = json.dumps(value, ensure_ascii=False)
    leaked = [k for k, v in secrets.items() if k != 'beget_login' and v and v in dump]
    if leaked:
        raise Blocked('SECRET_IN_REPORT', 'a secret appeared in the result (%s); nothing was written' % ', '.join(leaked))
    return value


def read_job(job, secrets, cfg=None, now=None):
    """One queue job's reading. Raises Blocked only when the result itself would hold a secret."""
    cfg = dict(CONFIG, **(cfg or {}))
    if job == 'HOSTING_DEADLINES':
        return no_secret(secrets, guarded(lambda: read_beget(secrets, cfg)))
    if job == 'WEBMASTER':
        return no_secret(secrets, guarded(lambda: read_webmaster(secrets, cfg)))
    if job != 'METRICA':
        raise ValueError('not an API job: %s' % job)
    ranges = moscow_ranges(now)
    site = guarded(lambda: read_counter(secrets, cfg, 'site_counter', 'site_goals', ranges))
    maps = guarded(lambda: read_counter(secrets, cfg, 'maps_counter', 'maps_goals', ranges))
    both = (site['status'], maps['status'])
    return no_secret(secrets, {'status': 'OK' if both == ('OK', 'OK') else ('PARTIAL' if 'OK' in both else 'BLOCKED'),
                               'sections': {'site': site, 'yandex_maps_card': maps},
                               'note': 'the two sections are separate audiences and are never added together',
                               'fetched_at': max(site['fetched_at'], maps['fetched_at'])})


def collect(secrets, cfg=None, now=None):
    started = utc_now()
    jobs = {job: read_job(job, secrets, cfg, now) for job in API_JOBS}
    for job, (status, why) in NOT_READ.items():
        jobs[job] = {'status': status, 'reason': why}
    return {'collector': 'bro_api_reader', 'version': VERSION, 'started': started, 'jobs': jobs, 'finished': utc_now()}


def main():
    parser = argparse.ArgumentParser()
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument('--secrets', action='append')
    where.add_argument('--windows-user-store', action='store_true')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        secrets = windows_user_store() if args.windows_user_store else load_secrets(*args.secrets)
        report = collect(secrets)
    except Blocked as reason:
        print('REFUSED %s: %s' % (reason.code, reason))
        return 2
    with open(args.out, 'x', encoding='utf-8') as f:      # never overwrite an earlier report
        f.write(json.dumps(report, indent=1, ensure_ascii=False))
    for job, entry in report['jobs'].items():
        detail = entry.get('reason') or ''
        if job == 'METRICA':
            detail = ', '.join('%s %s' % (k, v['status']) for k, v in entry['sections'].items())
        print('%-9s %-18s %s' % (entry['status'], job, detail))
    return 0 if all(e['status'] in ('OK', 'NOT_READY', 'ON_HOLD') for e in report['jobs'].values()) else 1


if __name__ == '__main__':
    if os.name == 'nt':
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
