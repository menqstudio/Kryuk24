"""Negative permission and regression tests for the gate (v3), with fake secret and fake browser targets.

Runs the hook exactly as Claude Code would: a separate process, JSON on stdin, exit code and stdout read back.
No Claude, no Chrome, no network. All paths, hosts, device ids, session ids and tab ids are made up.
"""
import concurrent.futures
import json
import msvcrt
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name('bro_gate_hook.py')
P = 'mcp__claude-in-chrome__'
DEVICE = '11111111-2222-3333-4444-555555555555'
OTHER = '99999999-8888-7777-6666-555555555555'
THIRD = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
HOST = 'webmaster.example.test'
GOOD = 'https://' + HOST + '/site/indexing'
BLANK = 'chrome://newtab/'
SESSION = 'fake-session-1'
MINE = 4242          # the tab this run creates
THEIRS = 9001        # a tab that was already open


def browsers(device=DEVICE, second_in_use=False, tail=' 2 browsers are connected; "Browser 2" is the one picked last and will be used.'):
    rows = [{'deviceId': THIRD, 'name': 'Browser 1', 'osPlatform': 'Windows', 'connectedAt': 1, 'isLocal': True},
            {'deviceId': device, 'name': 'Browser 2', 'osPlatform': 'Windows', 'connectedAt': 2, 'isLocal': True, 'inUse': True}]
    if second_in_use:
        rows[0]['inUse'] = True
    return json.dumps(rows, separators=(',', ':')) + tail


def context(tabs, group=7, tail='\n\nTab Context:\n- Available tabs:\n'):
    return json.dumps({'availableTabs': [{'tabId': t, 'title': 'x', 'url': url} for t, url in tabs], 'tabGroupId': group},
                      separators=(',', ':')) + tail


class Gate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.state = root / 'state.json'
        self.policy = root / 'policy.json'
        self.policy.write_text(json.dumps({
            'job': 'WEBMASTER', 'tool_prefix': P, 'device_id': DEVICE,
            'allowed_hosts': [HOST], 'state_file': str(self.state), 'max_calls': 40}), encoding='utf-8')
        self.n = 0

    def tearDown(self):
        self.dir.cleanup()

    # ---- plumbing
    def run_hook(self, payload=None, raw=None, extra=()):
        body = raw if raw is not None else json.dumps(payload).encode()
        r = subprocess.run([sys.executable, str(HOOK), '--policy', str(self.policy), *extra], input=body, capture_output=True, timeout=30)
        return r.returncode, r.stdout.decode()

    def pre(self, tool, data, use_id=None, session=SESSION, prefix=P):
        self.n += 1
        self.last_id = use_id or 'toolu_fake_%d' % self.n
        code, out = self.run_hook({'hook_event_name': 'PreToolUse', 'session_id': session, 'tool_use_id': self.last_id,
                                   'tool_name': prefix + tool, 'tool_input': data})
        return code == 0 and json.loads(out)['hookSpecificOutput']['permissionDecision'] == 'allow'

    def post(self, tool, data, response, use_id=None, session=SESSION):
        code, _ = self.run_hook({'hook_event_name': 'PostToolUse', 'session_id': session, 'tool_use_id': use_id or self.last_id,
                                 'tool_name': P + tool, 'tool_input': data, 'tool_response': response})
        return code == 0

    def call(self, tool, data, response):
        self.assertTrue(self.pre(tool, data), 'pre ' + tool)
        return self.post(tool, data, response)

    def denied(self, tool, data, prefix=P):
        return not self.pre(tool, data, prefix=prefix)

    def tainted(self):
        return json.loads(self.state.read_text(encoding='utf-8'))['tainted']

    def verdict(self):
        code, out = self.run_hook(raw=b'', extra=('--verdict',))
        return json.loads(out)['accept'] if out else False

    def fresh(self):
        self.state.unlink(missing_ok=True)

    # ---- building blocks of the allowed path
    def confirm(self, **kw):
        return self.call('list_connected_browsers', {}, {'text': browsers(**kw), 'isError': False})

    def listing(self, tabs, **kw):
        return self.call('tabs_context_mcp', {}, {'text': context(tabs, **kw), 'isError': False})

    def create(self):
        return self.call('tabs_create_mcp', {}, {'text': 'anything at all', 'isError': False})

    def own_tab(self, before=(), tab=MINE):
        """Listing, create, listing with exactly one new blank tab: the only way a tab becomes ours."""
        self.assertTrue(self.listing(list(before)))
        self.assertTrue(self.create())
        return self.listing(list(before) + [(tab, BLANK)])

    def open_and_land(self, landed=GOOD, before=()):
        self.assertTrue(self.confirm())
        self.assertTrue(self.own_tab(before))
        self.assertTrue(self.call('navigate', {'tabId': MINE, 'url': GOOD}, {'text': 'Navigated to ' + GOOD, 'isError': False}))
        return self.listing(list(before) + [(MINE, landed)])

    # ================= allowed path and the verdict
    def test_happy_path_and_verdict(self):
        self.assertTrue(self.open_and_land())
        self.assertFalse(self.verdict(), 'nothing read yet')
        self.assertTrue(self.call('get_page_text', {'tabId': MINE}, {'text': 'page text', 'isError': False}))
        self.assertFalse(self.verdict(), 'read without the tab check after it')
        self.assertTrue(self.listing([(MINE, GOOD)]))
        self.assertFalse(self.verdict(), 'profile not confirmed again after the last read')
        self.assertTrue(self.call('find', {'tabId': MINE, 'query': 'pages in search'}, {'text': 'x', 'isError': False}))
        self.assertTrue(self.listing([(MINE, GOOD)]))
        self.assertTrue(self.confirm())
        self.assertTrue(self.verdict())
        self.assertTrue(self.call('tabs_close_mcp', {'tabId': MINE}, {'text': 'Closed', 'isError': False}))
        self.assertTrue(self.listing([]))
        self.assertIsNone(self.tainted())

    def test_result_envelopes_that_are_accepted(self):
        for wrap in (lambda t: t, lambda t: {'text': t}, lambda t: [{'type': 'text', 'text': t}],
                     lambda t: {'content': [{'type': 'text', 'text': t}, {'type': 'text', 'text': 'second block ignored'}], 'isError': False}):
            self.fresh()
            self.assertTrue(self.call('list_connected_browsers', {}, wrap(browsers())))
            self.assertFalse(self.denied('tabs_context_mcp', {}))

    # ================= v3: visible is not owned
    def test_tab_that_was_already_open_cannot_be_read_closed_or_navigated(self):
        for tool, data in (('get_page_text', {'tabId': THEIRS}), ('read_page', {'tabId': THEIRS}), ('find', {'tabId': THEIRS, 'query': 'x'}),
                           ('tabs_close_mcp', {'tabId': THEIRS}), ('navigate', {'tabId': THEIRS, 'url': GOOD})):
            self.fresh(); self.assertTrue(self.confirm())
            self.assertTrue(self.listing([(THEIRS, GOOD)]), 'an allowed tab is visible')
            self.assertTrue(self.denied(tool, data), tool)
            self.assertIn('not created by this run', self.tainted())
            self.assertFalse(self.verdict())

    def test_already_open_tab_stays_foreign_after_this_run_creates_its_own(self):
        for tool, data in (('get_page_text', {'tabId': THEIRS}), ('tabs_close_mcp', {'tabId': THEIRS}), ('navigate', {'tabId': THEIRS, 'url': GOOD})):
            self.fresh(); self.assertTrue(self.open_and_land(before=[(THEIRS, GOOD)]))
            self.assertTrue(self.denied(tool, data), tool)
        self.fresh(); self.assertTrue(self.open_and_land(before=[(THEIRS, GOOD)]))
        self.assertTrue(self.call('get_page_text', {'tabId': MINE}, {'text': 'x', 'isError': False}), 'own tab still works')

    def test_listing_alone_never_makes_a_tab_ours(self):
        self.assertTrue(self.confirm())
        for _ in range(3):
            self.assertTrue(self.listing([(MINE, GOOD)]))
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))

    def test_tab_that_appears_without_a_creation_is_foreign(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.listing([(MINE, GOOD), (THEIRS, GOOD)]))
        self.assertTrue(self.denied('get_page_text', {'tabId': THEIRS}))

    def test_creation_needs_a_listing_right_before_it(self):
        self.assertTrue(self.confirm())
        self.assertTrue(self.denied('tabs_create_mcp', {}), 'no listing at all')
        self.fresh(); self.assertTrue(self.confirm()); self.assertTrue(self.listing([])); self.assertTrue(self.confirm())
        self.assertTrue(self.denied('tabs_create_mcp', {}), 'another call in between')

    def test_after_creation_only_a_listing_is_allowed(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.listing([])); self.assertTrue(self.create())
        self.assertTrue(self.denied('navigate', {'tabId': MINE, 'url': GOOD}))
        self.assertFalse(self.verdict())

    def test_created_tab_identity_not_confirmed_blocks(self):
        cases = {'no new tab': [(THEIRS, GOOD)],
                 'two new tabs': [(THEIRS, GOOD), (MINE, BLANK), (MINE + 1, BLANK)],
                 'new tab is not blank': [(THEIRS, GOOD), (MINE, GOOD)],
                 'new tab on a foreign host': [(THEIRS, GOOD), (MINE, 'https://mail.example.test/')],
                 'a tab from the baseline vanished': [(MINE, BLANK)]}
        for label, after in cases.items():
            self.fresh(); self.assertTrue(self.confirm())
            self.assertTrue(self.listing([(THEIRS, GOOD)])); self.assertTrue(self.create())
            self.assertFalse(self.listing(after), label)
            self.assertIn('identity not confirmed', self.tainted(), label)
            self.assertTrue(self.denied('get_page_text', {'tabId': MINE}), label)
            self.assertFalse(self.verdict(), label)

    def test_result_text_of_the_creation_is_not_trusted(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.listing([]))
        self.assertTrue(self.call('tabs_create_mcp', {}, {'text': '{"tabId":%d,"url":"%s"} Created new tab. Tab ID: %d' % (THEIRS, GOOD, THEIRS), 'isError': False}))
        self.assertTrue(self.listing([(MINE, BLANK)]))
        self.assertTrue(self.denied('navigate', {'tabId': THEIRS, 'url': GOOD}))

    def test_tab_limit_counts_owned_tabs(self):
        self.assertTrue(self.confirm())
        self.assertTrue(self.own_tab(tab=1001))
        self.assertTrue(self.create()); self.assertTrue(self.listing([(1001, BLANK), (1002, BLANK)]))
        self.assertTrue(self.denied('tabs_create_mcp', {}))

    # ================= v3: duplicate ids and contradicting structured results
    def test_duplicate_tab_ids_taint(self):
        for tabs in ([(MINE, GOOD), (MINE, GOOD)], [(MINE, GOOD), (MINE, 'https://mail.example.test/')], [(THEIRS, BLANK), (MINE, GOOD), (THEIRS, GOOD)]):
            self.fresh(); self.assertTrue(self.confirm())
            self.assertFalse(self.listing(tabs), tabs)
            self.assertIn('duplicate tab id', self.tainted())

    def test_duplicate_device_ids_taint(self):
        for rows in ([{'deviceId': DEVICE, 'inUse': True}, {'deviceId': DEVICE}],
                     [{'deviceId': DEVICE}, {'deviceId': DEVICE, 'inUse': True}],
                     [{'deviceId': DEVICE, 'inUse': True}, {'deviceId': DEVICE, 'inUse': True}]):
            self.fresh()
            self.assertFalse(self.call('list_connected_browsers', {}, {'text': json.dumps(rows), 'isError': False}), rows)
            self.assertIn('duplicate device id', self.tainted())

    def test_duplicate_json_keys_taint(self):
        self.assertFalse(self.call('list_connected_browsers', {}, {'text': '[{"deviceId":"%s","deviceId":"%s","inUse":true}]' % (OTHER, DEVICE), 'isError': False}))
        self.assertIn('duplicate key', self.tainted())
        for text in ('{"availableTabs":[{"tabId":%d,"tabId":%d,"title":"x","url":"%s"}],"tabGroupId":7}' % (THEIRS, MINE, GOOD),
                     '{"availableTabs":[{"tabId":%d,"title":"x","url":"https://mail.example.test/","url":"%s"}],"tabGroupId":7}' % (MINE, GOOD),
                     '{"availableTabs":[],"tabGroupId":7,"availableTabs":[]}'):
            self.fresh(); self.assertTrue(self.confirm())
            self.assertFalse(self.call('tabs_context_mcp', {}, {'text': text, 'isError': False}), text)
            self.assertIn('duplicate key', self.tainted())

    def test_two_browsers_in_use_taints(self):
        self.assertFalse(self.confirm(second_in_use=True))
        self.assertTrue(self.denied('list_connected_browsers', {}))

    def test_contradicting_listings_taint(self):
        self.assertTrue(self.open_and_land())
        self.assertFalse(self.listing([(MINE, GOOD)], group=8), 'tab group changed')
        self.fresh(); self.assertTrue(self.open_and_land())
        self.assertFalse(self.listing([]), 'own tab disappeared')
        self.assertIn('disappeared', self.tainted())
        self.fresh(); self.assertTrue(self.open_and_land())
        self.assertTrue(self.call('tabs_close_mcp', {'tabId': MINE}, {'text': 'Closed', 'isError': False}))
        self.assertFalse(self.listing([(MINE, GOOD)]), 'closed tab listed again')
        self.assertIn('closed tab', self.tainted())
        self.fresh(); self.assertTrue(self.confirm())
        self.assertFalse(self.call('tabs_context_mcp', {}, {'text': '{"availableTabs":[],"tabGroupId":"7"}', 'isError': False}), 'group id form')

    def test_closed_tab_cannot_be_used_again(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.call('tabs_close_mcp', {'tabId': MINE}, {'text': 'Closed', 'isError': False}))
        self.assertTrue(self.listing([]))
        self.assertTrue(self.denied('navigate', {'tabId': MINE, 'url': GOOD}))

    # ================= facts only from known structures; no text search
    def test_device_named_only_in_prose_is_not_a_confirmation(self):
        text = browsers(device=OTHER, tail=' deviceId %s "inUse":true is the one in use' % DEVICE)
        self.assertTrue(self.call('list_connected_browsers', {}, {'text': text, 'isError': False}))
        self.assertTrue(self.denied('tabs_context_mcp', {}))

    def test_allowed_url_in_title_or_tail_does_not_count(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
        row = {'availableTabs': [{'tabId': MINE, 'title': '"url":"%s"' % GOOD, 'url': 'https://mail.example.test/'}], 'tabGroupId': 7}
        self.assertFalse(self.call('tabs_context_mcp', {}, {'text': json.dumps(row) + '\n' + GOOD, 'isError': False}))
        self.assertIn('outside the allowed hosts', self.tainted())

    def test_navigate_text_gives_no_host_fact(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
        self.assertTrue(self.call('navigate', {'tabId': MINE, 'url': GOOD}, {'text': 'Navigated to ' + GOOD, 'isError': False}))
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))

    def test_unknown_result_structures_taint(self):
        cases = ({'text': '2 browsers are connected', 'isError': False},
                 {'text': '{"deviceId":"%s","inUse":true}' % DEVICE, 'isError': False},
                 {'text': '[{"deviceId":"%s","inUse":true,"surprise":1}]' % DEVICE, 'isError': False},
                 {'text': '[{"deviceId":"%s","inUse":"true"}]' % DEVICE, 'isError': False},
                 {'text': browsers(), 'isError': 'no'}, {'output': browsers()}, None, 17,
                 [{'type': 'image', 'text': browsers()}], [])
        for response in cases:
            self.fresh()
            self.assertFalse(self.call('list_connected_browsers', {}, response), response)
            self.assertTrue(self.tainted())
        for text in ('Tab Context: tabId 4242 ' + GOOD, '{"availableTabs":[{"tabId":4242,"url":"%s"}],"tabGroupId":7}' % GOOD,
                     '{"availableTabs":[{"tabId":"4242","title":"x","url":"%s"}],"tabGroupId":7}' % GOOD,
                     '{"availableTabs":[],"tabGroupId":7,"extra":1}', '[]'):
            self.fresh(); self.assertTrue(self.confirm())
            self.assertFalse(self.call('tabs_context_mcp', {}, {'text': text, 'isError': False}), text)

    def test_tool_error_taints(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.listing([]))
        self.assertFalse(self.call('tabs_create_mcp', {}, {'text': 'failed', 'isError': True}))

    # ================= pairing of Pre and Post; state protection
    def test_result_without_a_call_taints(self):
        self.last_id = 'toolu_never_asked'
        self.assertFalse(self.post('list_connected_browsers', {}, {'text': browsers(), 'isError': False}))
        self.assertTrue(self.denied('list_connected_browsers', {}))

    def test_mismatched_results_taint(self):
        for kw in ({'use_id': 'toolu_other'}, {'session': 'another-session'}):
            self.fresh(); self.assertTrue(self.pre('list_connected_browsers', {}))
            self.assertFalse(self.post('list_connected_browsers', {}, {'text': browsers(), 'isError': False}, **kw), kw)
        self.fresh(); self.assertTrue(self.pre('list_connected_browsers', {}))
        self.assertFalse(self.post('tabs_context_mcp', {}, {'text': context([]), 'isError': False}), 'other tool')
        self.fresh(); self.assertTrue(self.open_and_land())
        self.assertTrue(self.pre('get_page_text', {'tabId': MINE}))
        self.assertFalse(self.post('get_page_text', {'tabId': MINE + 1}, {'text': 'x', 'isError': False}), 'other input')

    def test_duplicate_and_old_results_taint(self):
        self.assertTrue(self.confirm())
        self.assertFalse(self.post('list_connected_browsers', {}, {'text': browsers(), 'isError': False}), 'same result twice')
        self.fresh(); self.assertTrue(self.confirm()); old = self.last_id
        self.assertTrue(self.pre('tabs_context_mcp', {}))
        self.assertFalse(self.post('list_connected_browsers', {}, {'text': browsers(), 'isError': False}, use_id=old), 'old result during another call')

    def test_reused_call_id_and_other_session_denied(self):
        self.assertTrue(self.confirm())
        self.assertFalse(self.pre('list_connected_browsers', {}, use_id=self.last_id))
        self.fresh(); self.assertTrue(self.confirm())
        self.assertFalse(self.pre('list_connected_browsers', {}, session='another-session'))
        self.fresh()
        code, _ = self.run_hook({'hook_event_name': 'PreToolUse', 'tool_name': P + 'list_connected_browsers', 'tool_input': {}})
        self.assertEqual(code, 2, 'no session_id / tool_use_id')

    def test_second_call_while_first_has_no_result_denied(self):
        self.assertTrue(self.pre('list_connected_browsers', {}))
        self.assertFalse(self.pre('list_connected_browsers', {}))

    def test_parallel_calls_do_not_corrupt_state(self):
        def one(i):
            body = json.dumps({'hook_event_name': 'PreToolUse', 'session_id': SESSION, 'tool_use_id': 'toolu_par_%d' % i,
                               'tool_name': P + 'list_connected_browsers', 'tool_input': {}}).encode()
            return subprocess.run([sys.executable, str(HOOK), '--policy', str(self.policy)], input=body, capture_output=True, timeout=60).returncode
        with concurrent.futures.ThreadPoolExecutor(12) as pool:
            codes = list(pool.map(one, range(12)))
        state = json.loads(self.state.read_text(encoding='utf-8'))
        self.assertEqual(codes.count(0), 1, 'exactly one of the simultaneous calls may pass')
        self.assertEqual(state['calls'], 12, 'no lost update')
        self.assertEqual(len(state['seen']), 2, 'first call registered, second registered and denied, the rest stopped at the taint')
        self.assertTrue(state['tainted'])

    def test_held_lock_blocks_instead_of_racing(self):
        self.assertTrue(self.confirm())
        fd = os.open(str(self.state) + '.lock', os.O_RDWR | os.O_CREAT)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            self.assertFalse(self.pre('tabs_context_mcp', {}))
        finally:
            os.lseek(fd, 0, os.SEEK_SET); msvcrt.locking(fd, msvcrt.LK_UNLCK, 1); os.close(fd)

    # ================= host and profile around the read
    def test_read_needs_the_tab_check_right_before_it(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.confirm())                     # another call slipped in between
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))

    def test_after_a_read_only_the_tab_check_is_allowed(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.call('get_page_text', {'tabId': MINE}, {'text': 'x', 'isError': False}))
        self.assertTrue(self.denied('find', {'tabId': MINE, 'query': 'x'}))

    def test_tab_moved_during_the_read_invalidates_the_run(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.call('get_page_text', {'tabId': MINE}, {'text': 'x', 'isError': False}))
        self.assertFalse(self.listing([(MINE, 'https://passport.example.test/auth')]))
        self.assertFalse(self.verdict())

    def test_redirect_before_the_read_blocks_the_read(self):
        self.assertFalse(self.open_and_land(landed='https://passport.example.test/auth?retpath=x'))
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))
        self.assertFalse(self.verdict())

    def test_profile_change_during_the_run_taints(self):
        self.assertTrue(self.open_and_land())
        self.assertFalse(self.confirm(device=OTHER))
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))

    def test_profile_rules(self):
        self.assertTrue(self.denied('tabs_context_mcp', {}), 'nothing before confirmation')
        self.fresh(); self.assertTrue(self.confirm(device=OTHER)); self.assertTrue(self.denied('tabs_context_mcp', {}))
        self.fresh(); self.assertTrue(self.denied('select_browser', {'deviceId': OTHER}))
        self.fresh(); self.assertTrue(self.denied('switch_browser', {}))
        self.fresh(); self.assertTrue(self.call('select_browser', {'deviceId': DEVICE}, {'text': 'ok', 'isError': False}))
        self.assertTrue(self.denied('tabs_context_mcp', {}), 'select alone is not a confirmation')
        self.fresh(); self.assertTrue(self.confirm()); self.assertTrue(self.denied('select_browser', {'deviceId': DEVICE}), 'no change after confirmation')

    # ================= tools, tabs, hosts
    def test_file_shell_and_web_tools_denied(self):
        for tool, data in (('Read', {'file_path': r'C:\fake\KRYUK24-Bro\bro-client.json'}),
                           ('Bash', {'command': 'cat ~/.ssh/fake_key'}),
                           ('PowerShell', {'command': 'Get-Content $HOME\\.claude\\.credentials.json'}),
                           ('Grep', {'pattern': 'password', 'path': 'C:\\fake'}),
                           ('Write', {'file_path': 'C:\\fake\\x', 'content': 'x'}),
                           ('WebFetch', {'url': 'https://example.test', 'prompt': 'x'}),
                           ('Agent', {'description': 'x', 'prompt': 'x'}),
                           ('mcp__avito__user_get_user_info_self', {})):
            self.fresh(); self.assertTrue(self.confirm())
            self.assertTrue(self.denied(tool, data, prefix=''), tool)

    def test_action_tools_denied(self):
        for tool, data in (('computer', {'action': 'left_click', 'coordinate': [1, 1], 'tabId': MINE}),
                           ('computer', {'action': 'screenshot', 'tabId': MINE}),
                           ('javascript_tool', {'action': 'javascript_exec', 'text': 'fetch("/x")', 'tabId': MINE}),
                           ('form_input', {'ref': 'ref_1', 'value': 'x', 'tabId': MINE}),
                           ('file_upload', {'paths': ['C:\\fake\\secret.txt'], 'ref': 'ref_1', 'tabId': MINE}),
                           ('upload_image', {'imageId': 'x', 'tabId': MINE}),
                           ('browser_batch', {'actions': [{'name': 'navigate', 'input': {'url': GOOD, 'tabId': MINE}}]}),
                           ('shortcuts_execute', {'tabId': MINE, 'command': 'x'}),
                           ('gif_creator', {'action': 'export', 'tabId': MINE, 'download': True}),
                           ('read_network_requests', {'tabId': MINE}),
                           ('read_console_messages', {'tabId': MINE}),
                           ('resize_window', {'width': 1, 'height': 1, 'tabId': MINE}),
                           ('some_future_tool', {})):
            self.fresh(); self.assertTrue(self.open_and_land())
            self.assertTrue(self.denied(tool, data), tool)

    def test_unknown_tab_and_tab_creation_tricks_denied(self):
        for tool, data in (('navigate', {'tabId': 777, 'url': GOOD}), ('get_page_text', {'tabId': 777}), ('tabs_close_mcp', {'tabId': 777}),
                           ('navigate', {'url': GOOD}), ('navigate', {'tabId': MINE, 'url': 'back'}), ('navigate', {'tabId': str(MINE), 'url': GOOD}),
                           ('tabs_context_mcp', {'createIfEmpty': True})):
            self.fresh(); self.assertTrue(self.open_and_land())
            self.assertTrue(self.denied(tool, data), (tool, data))

    def test_hosts_denied(self):
        for url in ('https://web.whatsapp.example.test/', 'https://runtime.example.test/operator/work',
                    'http://' + HOST + '/', 'file:///C:/fake/KRYUK24-Bro/bro-client.json',
                    'javascript:alert(1)', 'chrome://settings/passwords', 'data:text/html,x',
                    'https://' + HOST + '.evil.test/', 'https://evil.test/?x=' + HOST,
                    'https://user:pw@' + HOST + '/', 'https://' + HOST + ':8443/',
                    'https://' + HOST + '@evil.test/', HOST, '', 'https://[::1]/', 'https://' + HOST + '/\n'):
            self.fresh(); self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
            self.assertTrue(self.denied('navigate', {'tabId': MINE, 'url': url}), url)

    def test_one_denial_stops_the_run(self):
        self.assertTrue(self.open_and_land())
        self.assertTrue(self.denied('computer', {'action': 'left_click', 'coordinate': [1, 1], 'tabId': MINE}))
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}))
        self.assertFalse(self.verdict())

    # ================= the gate itself failing
    def test_broken_input_policy_and_state_block(self):
        self.assertEqual(self.run_hook(raw=b'not json')[0], 2)
        self.fresh(); self.state.write_text('{broken', encoding='utf-8')
        self.assertTrue(self.denied('list_connected_browsers', {}))
        self.assertTrue(self.tainted())
        self.fresh(); self.state.write_text(json.dumps({'v': 2, 'tainted': None, 'profile': {'ok': True}, 'tabs': {str(MINE): {'host_ok': True}}}), encoding='utf-8')
        self.assertTrue(self.denied('get_page_text', {'tabId': MINE}), 'state of an older format is not trusted')
        self.fresh()
        self.assertEqual(self.run_hook({'hook_event_name': 'Stop', 'session_id': SESSION, 'tool_use_id': 'x', 'tool_name': P + 'list_connected_browsers', 'tool_input': {}})[0], 2)
        self.policy.write_text('{}', encoding='utf-8')
        self.assertEqual(self.run_hook({'hook_event_name': 'PreToolUse'})[0], 2)

    def test_call_budget(self):
        self.assertTrue(all(self.confirm() for _ in range(40)))
        self.assertFalse(self.pre('list_connected_browsers', {}))

    # ================= trial-only local origins
    def trial_policy(self, job, origins):
        self.policy.write_text(json.dumps({
            'job': job, 'tool_prefix': P, 'device_id': DEVICE, 'allowed_hosts': [HOST],
            'state_file': str(self.state), 'max_calls': 40, 'trial_origins': origins}), encoding='utf-8')

    def test_local_trial_origin_only_for_the_trial_job(self):
        self.trial_policy('TRIAL', ['http://127.0.0.1:8765'])
        self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
        self.assertTrue(self.call('navigate', {'tabId': MINE, 'url': 'http://127.0.0.1:8765/facts'}, {'text': 'x', 'isError': False}))
        self.assertTrue(self.listing([(MINE, 'http://127.0.0.1:8765/facts')]))
        self.assertTrue(self.call('get_page_text', {'tabId': MINE}, {'text': 'x', 'isError': False}))
        self.assertFalse(self.listing([(MINE, 'http://127.0.0.1:8766/foreign')]), 'other local port is foreign')
        for url in ('http://127.0.0.1:8766/', 'http://localhost:8765/', 'http://127.0.0.1/', 'http://127.0.0.1:8765@evil.test/',
                    'http://evil.test:8765/', 'http://user:pw@127.0.0.1:8765/'):
            self.fresh(); self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
            self.assertTrue(self.denied('navigate', {'tabId': MINE, 'url': url}), url)

    def test_trial_origins_refused_for_any_real_job(self):
        for job, origins in (('WEBMASTER', ['http://127.0.0.1:8765']), ('TRIAL', ['http://192.168.1.5:8765']), ('TRIAL', ['https://127.0.0.1:8765']),
                             ('TRIAL', ['http://127.0.0.1:80']), ('TRIAL', []), ('TRIAL', 'http://127.0.0.1:8765')):
            self.fresh(); self.trial_policy(job, origins)
            self.assertTrue(self.denied('list_connected_browsers', {}), (job, origins))

    def test_plain_http_stays_denied_without_trial_origins(self):
        self.assertTrue(self.confirm()); self.assertTrue(self.own_tab())
        self.assertTrue(self.denied('navigate', {'tabId': MINE, 'url': 'http://127.0.0.1:8765/facts'}))

    # ================= explicit limit on connected browsers (used by the trial policy)
    def limit_policy(self, value):
        self.policy.write_text(json.dumps({
            'job': 'WEBMASTER', 'tool_prefix': P, 'device_id': DEVICE, 'allowed_hosts': [HOST],
            'state_file': str(self.state), 'max_calls': 40, 'max_connected_browsers': value}), encoding='utf-8')

    def test_without_the_key_two_connected_browsers_are_still_accepted(self):
        # Production behaviour is unchanged: the pinned browser is in use, another one is merely connected.
        self.assertTrue(self.confirm())
        self.assertTrue(self.listing([]))

    def test_limit_of_one_rejects_a_second_connected_browser_even_when_the_pinned_one_is_in_use(self):
        self.limit_policy(1)
        self.assertFalse(self.confirm(), 'two browsers listed, the pinned one in use')
        self.assertIn('more connected browsers', self.tainted())
        self.assertTrue(self.denied('tabs_context_mcp', {}))
        self.assertFalse(self.verdict())

    def test_limit_of_one_accepts_a_single_browser(self):
        self.limit_policy(1)
        one = json.dumps([{'deviceId': DEVICE, 'name': 'Only', 'inUse': True}])
        self.assertTrue(self.call('list_connected_browsers', {}, {'text': one, 'isError': False}))
        self.assertTrue(self.listing([]))

    def test_bad_limit_values_block(self):
        for value in (0, 11, '1', 1.0, True, [1]):
            self.fresh(); self.limit_policy(value)
            self.assertTrue(self.denied('list_connected_browsers', {}), value)

    def test_verdict_of_an_empty_run_is_reject(self):
        self.assertFalse(self.verdict())


if __name__ == '__main__':
    unittest.main()
