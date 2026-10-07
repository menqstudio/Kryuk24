"""Tests of the API collector against a local stand-in for the three services. No real service is contacted."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bro_api_reader as R

HERE = Path(__file__).resolve().parent
TOKEN, PASSWORD = 'y0_TESTTOKENTESTTOKENTESTTOKENTESTTOKEN', 'TestBegetApiPassword1234567890'
SECRETS = {'yandex_read_token': TOKEN, 'beget_login': 'amo777z0', 'beget_api_password': PASSWORD}
HOST_ID = 'https:kryuk24.ru:443'
MAPS = 'ids=86067232'
USER = 1130000065432101                      # a Yandex user id is far above any count limit


class Fake(BaseHTTPRequestHandler):
    mode = {}
    seen = []
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def answer(self, code, body, headers=()):
        raw = json.dumps(body).encode() if not isinstance(body, bytes) else body
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(raw)
        except OSError:
            pass                                           # the collector gave up on this answer (timeout, size limit)

    def handle_any(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length).decode() if length else ''
        with Fake.lock:
            Fake.seen.append((self.command, self.path.split('?')[0], self.headers.get('Authorization'), body, self.path))
            nth = sum(1 for x in Fake.seen if x[4] == self.path)
        m, path = Fake.mode, self.path
        if path.startswith('/beget/user/getAccountInfo'):
            if m.get('beget') == 'refuse':
                return self.answer(200, {'status': 'error', 'error_code': 'AUTH_ERROR', 'error_text': 'bad ' + PASSWORD})
            if m.get('beget') == 'inner_error':
                return self.answer(200, {'status': 'success', 'answer': {'status': 'error', 'errors': [{'error_text': 'no ' + PASSWORD}]}})
            if m.get('beget') == 'http500':
                return self.answer(500, {'error': PASSWORD})
            if m.get('beget') == 'redirect':
                return self.answer(302, {}, [('Location', '/beget/elsewhere')])
            result = {'user_balance': 1965.56, 'user_days_to_block': 41, 'user_rate_current': 49.1, 'user_rate_month': 1473, 'plan_name': 'Blog'}
            if m.get('beget') == 'no_days':
                del result['user_days_to_block']
            if m.get('beget') == 'days_as_text':
                result['user_days_to_block'] = '41'
            if m.get('beget') == 'zero':
                result.update(user_balance=0, user_days_to_block=0)
            result.update(m.get('beget_result') or {})
            return self.answer(200, {'status': 'success', 'answer': {'status': 'success', 'result': result}})
        if path.startswith('/metrica/stat/v1/data'):
            kind = m.get('metrica')
            if kind == 'maps403' and MAPS in path or kind == 'http403':
                return self.answer(403, {'message': 'forbidden ' + TOKEN})
            if kind == 'not_json':
                return self.answer(200, b'<html>')
            if kind == 'huge':
                return self.answer(200, b'{"pad": "' + b'x' * (R.MAX_BYTES + 10) + b'"}')
            if kind == 'busy_once' and nth == 1:
                return self.answer(429, {'message': 'quota'})
            if kind == 'slow_once' and nth == 1:
                time.sleep(1.5)
            totals = [15.0, 11.0, 1.0, 2.0, 3.0]
            if kind == 'zero':
                totals = [0.0] * 5
            if kind == 'short':
                totals = totals[:3]
            if kind == 'text':
                totals[0] = '15'
            if kind == 'totals':
                totals = m['totals']
            body = {'totals': totals, 'sampled': False, 'sample_share': 1.0}
            if kind == 'no_sampled':
                del body['sampled']
            if kind == 'sampled':
                body.update(sampled=True, sample_share=0.1)
            body.update(m.get('metrica_body') or {})
            if 'metrica_raw' in m:                         # text that json.dumps would not write: NaN, Infinity, 1e999
                return self.answer(200, m['metrica_raw'].encode())
            return self.answer(200, body)
        if path == '/webmaster/user':
            return self.answer(200, {'user_id': m.get('webmaster_user', USER)})
        if path == '/webmaster/user/%d/hosts' % USER:
            hosts = [{'host_id': HOST_ID, 'unicode_host_url': 'https://kryuk24.ru/', 'verified': m.get('webmaster') != 'unverified'}]
            return self.answer(200, {'hosts': [] if m.get('webmaster') == 'no_host' else hosts})
        if path.startswith('/webmaster/user/%d/hosts/' % USER) and path.endswith('/summary'):
            summary = {'searchable_pages_count': 1, 'excluded_pages_count': 0, 'sqi': 0, 'site_problems': {'POSSIBLE_PROBLEM': 1}}
            summary.update(m.get('webmaster_summary') or {})
            if m.get('webmaster') == 'leak':
                summary['site_problems'] = {TOKEN: 1}
            if m.get('webmaster') == 'no_sqi':
                del summary['sqi']
            return self.answer(200, summary)
        return self.answer(404, {})

    do_GET = do_POST = do_PUT = do_DELETE = handle_any


class Case(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = 'http://127.0.0.1:%d' % cls.server.server_address[1]
        cls.cfg = {'beget_api': cls.base + '/beget', 'metrica_api': cls.base + '/metrica', 'webmaster_api': cls.base + '/webmaster',
                   'timeout': 5, 'retry_wait': 0.01, 'require_https': False}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def read(self, secrets=None, cfg=None, **mode):
        Fake.mode, Fake.seen = mode, []
        return R.collect(dict(SECRETS if secrets is None else secrets), dict(self.cfg, **(cfg or {})))['jobs']

    def clean(self, jobs):
        dump = json.dumps(jobs, ensure_ascii=False)
        self.assertNotIn(TOKEN, dump)
        self.assertNotIn(PASSWORD, dump, 'even when the service echoes the secret in its error text')

    def test_everything_read_and_only_allowed_requests_sent(self):
        j = self.read()
        self.assertEqual({k: v['status'] for k, v in j.items()},
                         {'HOSTING_DEADLINES': 'OK', 'METRICA': 'OK', 'WEBMASTER': 'OK', 'YANDEX_DIRECT': 'NOT_READY', 'AVITO': 'ON_HOLD'})
        beget = j['HOSTING_DEADLINES']['evidence']
        self.assertEqual(beget['balance'], {'value': 1965.56, 'unit': 'RUB'})
        self.assertEqual((beget['days_to_block']['value'], beget['rate_per_month']['value'], beget['plan']), (41, 1473.0, 'Blog'))
        self.assertIn('estimate', beget['days_to_block']['meaning'])
        site, maps = (j['METRICA']['sections'][k]['evidence'] for k in ('site', 'yandex_maps_card'))
        self.assertEqual(site['yesterday']['values'], {'visits': 15, 'users': 11, 'goal_clicks': {'phone_click': 1, 'whatsapp_click': 2, 'telegram_click': 3}})
        self.assertEqual((site['counter'], maps['counter']), (113277361, 86067232))
        self.assertEqual(set(maps['last_7_days']['values']['goal_clicks']), {'call_click', 'route_build', 'to_site'})
        self.assertEqual((site['yesterday']['timezone'], site['yesterday']['sampled'], site['yesterday']['sample_share']), ('Europe/Moscow', False, 1.0))
        self.assertNotIn('visits', j['METRICA'], 'site and Maps are never added into one number')
        self.assertEqual(j['WEBMASTER']['evidence']['pages_in_search'], {'value': 1, 'unit': 'pages'})
        self.assertTrue(all('fetched_at' in e for e in (j['HOSTING_DEADLINES'], j['WEBMASTER'], *j['METRICA']['sections'].values())))
        methods = {(m, p) for m, p, _, _, _ in Fake.seen}
        self.assertEqual({m for m, p in methods if not p.startswith('/beget')}, {'GET'}, 'Yandex is only ever read with GET')
        self.assertEqual([(m, p) for m, p in methods if p.startswith('/beget')], [('POST', '/beget/user/getAccountInfo')])
        self.assertTrue(all(a == 'OAuth ' + TOKEN for m, p, a, b, f in Fake.seen if not p.startswith('/beget')))
        self.assertNotIn('direct', json.dumps(Fake.seen).lower(), 'Direct is not contacted while it is not ready')
        self.assertNotIn('avito', json.dumps(Fake.seen).lower(), 'Avito is not contacted while it is on hold')
        self.clean(j)

    def test_real_zero_is_reported_as_zero(self):
        j = self.read(metrica='zero', beget='zero')
        site = j['METRICA']['sections']['site']
        self.assertEqual(site['status'], 'OK')
        self.assertEqual(site['evidence']['yesterday']['values'], {'visits': 0, 'users': 0, 'goal_clicks': {'phone_click': 0, 'whatsapp_click': 0, 'telegram_click': 0}})
        self.assertEqual(j['HOSTING_DEADLINES']['evidence']['days_to_block']['value'], 0)

    def test_missing_or_wrong_typed_metric_is_blocked_never_zero(self):
        for mode, job in (({'beget': 'no_days'}, 'HOSTING_DEADLINES'), ({'beget': 'days_as_text'}, 'HOSTING_DEADLINES'),
                          ({'metrica': 'short'}, 'METRICA'), ({'metrica': 'text'}, 'METRICA'), ({'metrica': 'no_sampled'}, 'METRICA'),
                          ({'webmaster': 'no_sqi'}, 'WEBMASTER')):
            j = self.read(**mode)
            entry = j[job] if job != 'METRICA' else j[job]['sections']['site']
            self.assertEqual((j[job]['status'], entry['status'], entry['error_code']), ('BLOCKED', 'BLOCKED', 'METRIC_MISSING'), mode)
            self.assertNotIn('evidence', entry, 'a blocked reading carries no value at all')
            self.clean(j)

    def test_service_errors_block_one_reading_and_leave_the_others(self):
        for mode, job, code in (({'beget': 'refuse'}, 'HOSTING_DEADLINES', 'API_ERROR'), ({'beget': 'inner_error'}, 'HOSTING_DEADLINES', 'API_ERROR'),
                                ({'beget': 'redirect'}, 'HOSTING_DEADLINES', 'REDIRECT_REFUSED'), ({'beget': 'http500'}, 'HOSTING_DEADLINES', 'HTTP_500'),
                                ({'metrica': 'http403'}, 'METRICA', 'HTTP_403'), ({'metrica': 'not_json'}, 'METRICA', 'NOT_JSON'),
                                ({'metrica': 'huge'}, 'METRICA', 'RESPONSE_TOO_LARGE'),
                                ({'webmaster': 'no_host'}, 'WEBMASTER', 'HOST_NOT_LISTED'), ({'webmaster': 'unverified'}, 'WEBMASTER', 'HOST_NOT_VERIFIED')):
            j = self.read(**mode)
            entry = j[job] if job != 'METRICA' else j[job]['sections']['site']
            self.assertEqual((j[job]['status'], entry.get('error_code')), ('BLOCKED', code), mode)
            other = 'WEBMASTER' if job != 'WEBMASTER' else 'HOSTING_DEADLINES'
            self.assertEqual(j[other]['status'], 'OK', mode)
            self.clean(j)
        self.assertIn('AUTH_ERROR', self.read(beget='refuse')['HOSTING_DEADLINES']['reason'])

    def test_retry_only_after_timeout_429_or_5xx(self):
        count = lambda prefix: len([x for x in Fake.seen if x[1].startswith(prefix)])
        j = self.read(metrica='busy_once')
        self.assertEqual(j['METRICA']['status'], 'OK', '429 once, then the answer')
        self.assertEqual(count('/metrica'), 8, 'four queries, each asked twice')
        j = self.read(cfg={'timeout': 0.5}, metrica='slow_once')
        self.assertEqual(j['METRICA']['status'], 'OK', 'timeout once, then the answer')
        j = self.read(beget='http500')
        self.assertEqual(count('/beget'), 3, 'one try and two retries, then it gives up')
        j = self.read(metrica='http403')
        self.assertEqual(count('/metrica'), 2, 'an auth error is not retried: one request per counter')
        j = self.read(beget='redirect')
        self.assertEqual(count('/beget'), 1, 'a redirect is neither followed nor retried')

    def test_partial_metrica_keeps_the_good_section_but_the_job_is_not_ok(self):
        j = self.read(metrica='maps403')
        m = j['METRICA']
        self.assertEqual((m['status'], m['sections']['site']['status'], m['sections']['yandex_maps_card']['status']), ('PARTIAL', 'OK', 'BLOCKED'))
        self.assertEqual(m['sections']['site']['evidence']['yesterday']['values']['visits'], 15)
        self.assertNotIn('evidence', m['sections']['yandex_maps_card'])
        self.clean(j)

    def test_sampling_metadata_is_kept(self):
        day = self.read(metrica='sampled')['METRICA']['sections']['site']['evidence']['yesterday']
        self.assertEqual((day['sampled'], day['sample_share']), (True, 0.1))

    def test_every_metrica_query_carries_the_moscow_offset(self):
        self.read()
        sent = [x[4] for x in Fake.seen if x[1] == '/metrica/stat/v1/data']
        self.assertEqual(len(sent), 4, 'two counters, two ranges')
        ranges = R.moscow_ranges()
        for raw in sent:
            self.assertIn('timezone=%2B03%3A00', raw, 'the plus sign travels encoded, not as a space')
            query = urllib.parse.parse_qs(raw.split('?', 1)[1], strict_parsing=True)
            self.assertEqual(sorted(query), ['accuracy', 'date1', 'date2', 'ids', 'metrics', 'timezone'])
            self.assertEqual((query['timezone'], query['accuracy']), (['+03:00'], ['full']))
            self.assertIn((query['date1'][0], query['date2'][0]), ranges.values())
        self.assertEqual({urllib.parse.parse_qs(raw.split('?', 1)[1])['ids'][0] for raw in sent}, {'113277361', '86067232'})
        day = self.read()['METRICA']['sections']['site']['evidence']['yesterday']
        self.assertEqual((day['timezone'], day['utc_offset']), ('Europe/Moscow', '+03:00'), 'what is recorded is what was asked')
        self.assertEqual(R.MOSCOW.utcoffset(None).total_seconds(), 3 * 3600)

    def test_a_fraction_is_never_cut_and_impossible_numbers_are_blocked(self):
        site = lambda **mode: self.read(metrica=mode.pop('metrica', 'totals'), **mode)['METRICA']['sections']['site']
        for label, totals in (('fraction, not sampled', [15.5, 11.0, 1.0, 2.0, 3.0]), ('fraction in a goal', [15.0, 11.0, 1.0, 2.9, 3.0]),
                              ('negative', [15.0, -1.0, 1.0, 2.0, 3.0]), ('over the limit', [1e12, 11.0, 1.0, 2.0, 3.0]),
                              ('more users than visits', [15.0, 16.0, 1.0, 2.0, 3.0]), ('clicks without a visit', [0.0, 0.0, 0.0, 1.0, 0.0]),
                              ('true is not a number', [True, 11.0, 1.0, 2.0, 3.0])):
            entry = site(totals=totals)
            self.assertEqual(entry['status'], 'BLOCKED', label)
            self.assertEqual(entry['error_code'], 'METRIC_MISSING' if label == 'true is not a number' else 'METRIC_INVALID', label)
            self.assertNotIn('evidence', entry, label)
        for label, raw, code in (('NaN', '{"totals":[NaN,11.0,1.0,2.0,3.0],"sampled":false,"sample_share":1.0}', 'NOT_JSON'),
                                 ('Infinity', '{"totals":[15.0,Infinity,1.0,2.0,3.0],"sampled":false,"sample_share":1.0}', 'NOT_JSON'),
                                 ('-Infinity', '{"totals":[15.0,11.0,-Infinity,2.0,3.0],"sampled":false,"sample_share":1.0}', 'NOT_JSON'),
                                 ('overflow to infinity', '{"totals":[1e999,11.0,1.0,2.0,3.0],"sampled":false,"sample_share":1.0}', 'METRIC_INVALID'),
                                 ('NaN share', '{"totals":[15.0,11.0,1.0,2.0,3.0],"sampled":false,"sample_share":NaN}', 'NOT_JSON')):
            entry = site(metrica='raw', metrica_raw=raw)
            self.assertEqual((entry['status'], entry['error_code']), ('BLOCKED', code), label)
            self.assertNotIn('evidence', entry, label)
        whole = site(totals=[15, 11.0, 1, 2.0, 3])['evidence']['yesterday']
        self.assertEqual(whole['values'], {'visits': 15, 'users': 11, 'goal_clicks': {'phone_click': 1, 'whatsapp_click': 2, 'telegram_click': 3}})
        self.assertTrue(all(type(v) is int for v in (whole['values']['visits'], whole['values']['users'], *whole['values']['goal_clicks'].values())))
        self.assertEqual((whole['exact'], whole['units']), (True, 'counts'))

    def test_sampled_numbers_are_kept_as_returned_and_marked_as_estimates(self):
        site = lambda **body: self.read(metrica='totals', totals=[152.7, 110.0, 10.4, 2.0, 3.0], metrica_body=body)['METRICA']['sections']['site']
        day = site(sampled=True, sample_share=0.1)['evidence']['yesterday']
        self.assertEqual(day['values'], {'visits': 152.7, 'users': 110, 'goal_clicks': {'phone_click': 10.4, 'whatsapp_click': 2, 'telegram_click': 3}})
        self.assertEqual((day['exact'], day['units'], day['sampled'], day['sample_share']), (False, 'estimated counts', True, 0.1))
        for label, body, code in (('no share', {'sampled': True, 'sample_share': None}, 'METRIC_MISSING'), ('share 0', {'sampled': True, 'sample_share': 0}, 'METRIC_INVALID'),
                                  ('share above 1', {'sampled': True, 'sample_share': 1.5}, 'METRIC_INVALID'), ('negative share', {'sampled': True, 'sample_share': -0.1}, 'METRIC_INVALID')):
            entry = site(**body)
            self.assertEqual((entry['status'], entry.get('error_code')), ('BLOCKED', code), label)
        self.assertEqual(site(sampled=False, sample_share=1.0)['error_code'], 'METRIC_INVALID', 'the same fractions without sampling are refused')

    def test_impossible_beget_and_webmaster_numbers_are_blocked(self):
        for label, mode, job in (('negative days', {'beget_result': {'user_days_to_block': -3}}, 'HOSTING_DEADLINES'),
                                 ('negative rate', {'beget_result': {'user_rate_current': -1.5}}, 'HOSTING_DEADLINES'),
                                 ('absurd balance', {'beget_result': {'user_balance': 1e15}}, 'HOSTING_DEADLINES'),
                                 ('days as a fraction', {'beget_result': {'user_days_to_block': 41.5}}, 'HOSTING_DEADLINES'),
                                 ('negative pages', {'webmaster_summary': {'searchable_pages_count': -1}}, 'WEBMASTER'),
                                 ('absurd pages', {'webmaster_summary': {'excluded_pages_count': 10 ** 12}}, 'WEBMASTER')):
            entry = self.read(**mode)[job]
            self.assertEqual(entry['status'], 'BLOCKED', label)
            self.assertEqual(entry['error_code'], 'METRIC_MISSING' if label == 'days as a fraction' else 'METRIC_INVALID', label)
            self.assertNotIn('evidence', entry, label)
        for label, user in (('zero', 0), ('negative', -5), ('fraction', 42.0), ('text', str(USER))):
            entry = self.read(webmaster_user=user)['WEBMASTER']
            self.assertEqual((entry['status'], 'evidence' in entry), ('BLOCKED', False), label)
            self.assertFalse([x for x in Fake.seen if x[1].startswith('/webmaster/user/')], 'no request is built from a bad user id')
        self.assertEqual(self.read()['WEBMASTER']['status'], 'OK', 'a real user id is far above the count limit and is fine')
        self.assertTrue([x for x in Fake.seen if x[1] == '/webmaster/user/%d/hosts' % USER])
        owed = self.read(beget_result={'user_balance': -120.5})['HOSTING_DEADLINES']
        self.assertEqual((owed['status'], owed['evidence']['balance']['value']), ('OK', -120.5), 'a debt is a possible balance and is not cut')

    def test_ranges_are_whole_moscow_days_across_month_and_year(self):
        at = lambda *a: R.moscow_ranges(datetime(*a, tzinfo=timezone.utc))
        self.assertEqual(at(2026, 10, 7, 11, 0), {'yesterday': ('2026-10-06', '2026-10-06'), 'last_7_days': ('2026-09-30', '2026-10-06')})
        self.assertEqual(at(2026, 10, 31, 21, 30)['yesterday'], ('2026-10-31', '2026-10-31'), '00:30 in Moscow is already the next day')
        self.assertEqual(at(2026, 10, 31, 20, 59)['yesterday'], ('2026-10-30', '2026-10-30'))
        self.assertEqual(at(2027, 1, 1, 5, 0), {'yesterday': ('2026-12-31', '2026-12-31'), 'last_7_days': ('2026-12-25', '2026-12-31')})
        self.assertEqual(at(2028, 3, 1, 5, 0)['yesterday'], ('2028-02-29', '2028-02-29'))
        self.read()
        asked = {x[4].split('date1=')[1].split('&accuracy')[0] for x in Fake.seen if 'date1=' in x[4]}
        r = R.moscow_ranges()
        self.assertEqual(asked, {'%s&date2=%s' % pair for pair in r.values()}, 'the collector asks for exactly these ranges')

    def test_only_the_allowed_endpoints_can_be_requested(self):
        cfg = dict(R.CONFIG, **self.cfg)
        ok = lambda url, method: R.allowed(cfg, self.base + url, method)
        self.assertTrue(ok('/beget/user/getAccountInfo', 'POST'))
        self.assertTrue(ok('/metrica/stat/v1/data?ids=1', 'GET'))
        self.assertTrue(ok('/webmaster/user', 'GET') and ok('/webmaster/user/42/hosts', 'GET') and ok('/webmaster/user/42/hosts/https%3Akryuk24.ru%3A443/summary', 'GET'))
        for url, method in (('/beget/user/toggleSsh', 'POST'), ('/beget/user/getAccountInfo', 'GET'), ('/beget/user/getAccountInfo?x=1', 'POST'),
                            ('/metrica/stat/v1/data', 'POST'), ('/metrica/management/v1/counter/1', 'GET'), ('/metrica/management/v1/counter/1/goals', 'POST'),
                            ('/webmaster/user/42/hosts', 'POST'), ('/webmaster/user/42/hosts/x/verification', 'GET'),
                            ('/webmaster/user/42/hosts/x/recrawl/queue', 'GET'), ('/webmaster/user/42/hosts/x/summary/more', 'GET'),
                            ('/webmaster/user/42/hosts', 'DELETE'), ('/elsewhere', 'GET')):
            self.assertFalse(ok(url, method), (url, method))
        Fake.seen = []
        for url, form in (('/beget/user/toggleSsh', {'a': 1}), ('/metrica/management/v1/counters', None)):
            with self.assertRaises(R.Blocked) as caught:
                R.http_json(cfg, self.base + url, form=form)
            self.assertEqual(caught.exception.code, 'ENDPOINT_NOT_ALLOWED')
        self.assertEqual(Fake.seen, [], 'a refused request never leaves the collector')
        with self.assertRaises(R.Blocked) as caught:
            R.http_json(dict(cfg, require_https=True), self.base + '/webmaster/user')
        self.assertEqual(caught.exception.code, 'NOT_HTTPS')
        self.assertTrue(R.CONFIG['require_https'] and all(R.CONFIG[k].startswith('https://') for k in ('beget_api', 'metrica_api', 'webmaster_api')))

    def test_missing_secret_blocks_only_the_readings_that_need_it(self):
        j = self.read(secrets={'beget_login': 'amo777z0', 'beget_api_password': PASSWORD})
        self.assertEqual((j['HOSTING_DEADLINES']['status'], j['METRICA']['status'], j['WEBMASTER']['status']), ('OK', 'BLOCKED', 'BLOCKED'))
        self.assertEqual(j['WEBMASTER']['error_code'], 'SECRET_MISSING')
        self.assertFalse([x for x in Fake.seen if not x[1].startswith('/beget')], 'no request is sent without the token')

    def test_report_with_a_secret_in_it_is_never_returned(self):
        with self.assertRaises(R.Blocked) as caught:
            self.read(webmaster='leak')
        self.assertEqual(caught.exception.code, 'SECRET_IN_REPORT')
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_secrets_file_with_anything_beyond_the_read_set_is_refused(self):
        folder = Path(tempfile.mkdtemp())
        good = folder / 'good.json'
        good.write_text(json.dumps(SECRETS), encoding='utf-8')
        os.chmod(good, 0o600)
        self.assertEqual(R.load_secrets(good), SECRETS)
        for label, content in (('actions token', dict(SECRETS, yandex_actions_token='y0_x')), ('mail password', dict(SECRETS, mail_app_password='x')),
                               ('avito secret', dict(SECRETS, avito_client_secret='x')), ('not strings', dict(SECRETS, beget_login=5)), ('a list', [1])):
            path = folder / 'bad.json'
            path.write_text(json.dumps(content), encoding='utf-8')
            os.chmod(path, 0o600)
            with self.assertRaises(R.Blocked, msg=label) as caught:
                R.load_secrets(path)
            self.assertNotIn('y0_x', str(caught.exception))
        (folder / 'broken.json').write_text('{', encoding='utf-8')
        for path in (folder / 'broken.json', folder / 'missing.json'):
            with self.assertRaises(R.Blocked):
                R.load_secrets(path)

    def test_command_line_refuses_bad_secrets_and_writes_nothing(self):
        folder = Path(tempfile.mkdtemp())
        bad = folder / 'bad.json'
        bad.write_text(json.dumps(dict(SECRETS, yandex_actions_token='y0_x')), encoding='utf-8')
        os.chmod(bad, 0o600)
        out = folder / 'report.json'
        r = subprocess.run([sys.executable, str(HERE / 'bro_api_reader.py'), '--secrets', str(bad), '--out', str(out)], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn(b'REFUSED SECRETS_NOT_READ_ONLY', r.stdout)
        self.assertFalse(out.exists())
        self.assertNotIn(TOKEN.encode(), r.stdout + r.stderr)

    def test_windows_store_reader_never_takes_the_actions_token(self):
        source = (HERE / 'bro_api_reader.py').read_text(encoding='utf-8')
        body = source.split('def windows_user_store')[1].split('\ndef ')[0]
        self.assertIn("'YANDEX_OAUTH_TOKEN'", body)
        self.assertNotIn("QueryValueEx(key, 'YANDEX_ACTIONS_TOKEN')", source)
        self.assertNotIn('AVITO_CLIENT_SECRET', source)
        self.assertEqual(R.ALLOWED_SECRET_KEYS, {'yandex_read_token', 'beget_login', 'beget_api_password'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
