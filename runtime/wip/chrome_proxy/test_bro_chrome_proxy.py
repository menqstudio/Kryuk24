"""Tests of the Bro Chrome proxy with a stand-in upstream. No Claude, no Chrome, no network.

What "reached Chrome" means here: a tools/call line in the stand-in's own log. A refusal counts only when that log
shows no such line.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE_DIR = HERE.parent / 'adapter_preflight'
DEVICE = '11111111-2222-3333-4444-555555555555'
ORIGIN = 'http://127.0.0.1:18765'

FAKE_GATES = {
    'crash': 'import sys; sys.exit(1)',
    'hang': 'import time; time.sleep(600)',
    'silent': 'import sys; sys.exit(0)',
    'allow_but_exit_1': 'import sys, json; print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}})); sys.exit(1)',
    'says_deny_exit_0': 'import sys, json; print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny"}})); sys.exit(0)',
    'garbage_exit_0': 'print("allow")',
    'allow_pre_fail_post': ('import sys, json\n'
                            'e = json.loads(sys.stdin.buffer.read())\n'
                            'if e["hook_event_name"] == "PostToolUse": sys.exit(2)\n'
                            'print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))'),
}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.log, self.audit_path = self.dir / 'upstream.log', self.dir / 'audit.jsonl'
        self.proc = None

    def tearDown(self):
        self.stop()
        self.tmp.cleanup()

    def stop(self):
        if self.proc is not None:
            self.proc.stdin.close()
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(20)
            self.proc.stdout.close()
            self.proc = None

    def policy(self, **change):
        data = {'job': 'TRIAL', 'tool_prefix': 'mcp__claude-in-chrome__', 'device_id': DEVICE, 'allowed_hosts': ['trial.invalid'],
                'trial_origins': [ORIGIN], 'max_connected_browsers': 1, 'state_file': str(self.dir / 'gate_state.json'), 'max_calls': 40}
        data.update(change)
        path = self.dir / 'policy.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def fake_gate(self, kind):
        folder = self.dir / ('gate_' + kind)
        folder.mkdir()
        (folder / 'bro_gate_hook.py').write_text(FAKE_GATES[kind], encoding='utf-8')
        return folder

    def start(self, policy=None, gate_dir=GATE_DIR, mode='ok', audit=None, upstream=None, gate_timeout=20, upstream_timeout=20):
        argv = [sys.executable, str(HERE / 'bro_chrome_proxy.py'), '--policy', str(policy or self.dir / 'no-policy.json'), '--gate-dir', str(gate_dir),
                '--audit', str(audit or self.audit_path), '--gate-timeout', str(gate_timeout), '--upstream-timeout', str(upstream_timeout), '--']
        argv += upstream or [sys.executable, str(HERE / 'fake_upstream.py'), '--log', str(self.log), '--mode', mode, '--device', DEVICE]
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.n = 0
        return self.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 't', 'version': '0'}})

    def rpc(self, method, params=None):
        self.n += 1
        self.proc.stdin.write((json.dumps({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params or {}}) + '\n').encode())
        self.proc.stdin.flush()
        reply = json.loads(self.proc.stdout.readline().decode('utf-8'))
        self.assertEqual(reply.get('id'), self.n)
        return reply

    def call(self, name, **arguments):
        return self.rpc('tools/call', {'name': name, 'arguments': arguments})['result']

    def reached(self):
        """The tool calls the stand-in Chrome really received."""
        if not self.log.exists():
            return []
        rows = [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]
        return [r['params']['name'] for r in rows if r['method'] == 'tools/call']

    def audit(self):
        return [json.loads(line) for line in self.audit_path.read_text(encoding='utf-8').splitlines()] if self.audit_path.exists() else []

    def assert_refused(self, result, text='BRO PROXY: denied'):
        self.assertIs(result.get('isError'), True)
        self.assertEqual(result['content'], [{'type': 'text', 'text': text}])

    # ---------------- what the proxy offers
    def test_only_the_nine_read_only_tools_are_listed(self):
        self.start(self.policy())
        names = [t['name'] for t in self.rpc('tools/list')['result']['tools']]
        self.assertEqual(sorted(names), sorted(['list_connected_browsers', 'select_browser', 'tabs_context_mcp', 'tabs_create_mcp', 'tabs_close_mcp',
                                                'navigate', 'get_page_text', 'read_page', 'find']))
        self.assertEqual(self.reached(), [], 'listing tools calls nothing')

    def test_tool_outside_the_set_is_refused_without_asking_the_gate(self):
        self.start(self.policy())
        for name in ('computer', 'javascript_tool', 'form_input', 'no_such_tool', '', None):
            self.assert_refused(self.rpc('tools/call', {'name': name, 'arguments': {}})['result'])
        self.assert_refused(self.rpc('tools/call', {'name': 'navigate', 'arguments': 'not an object'})['result'])
        self.assertEqual(self.reached(), [])
        self.assertFalse((self.dir / 'gate_state.json').exists(), 'the gate was never run')
        self.assertTrue(all(r['decision'] == 'deny' for r in self.audit()))

    # ---------------- no policy, broken policy, broken gate: nothing reaches Chrome
    def test_missing_or_broken_policy_refuses_before_chrome(self):
        broken = self.dir / 'broken.json'
        broken.write_text('{not json', encoding='utf-8')
        incomplete = self.dir / 'incomplete.json'
        incomplete.write_text(json.dumps({'job': 'TRIAL'}), encoding='utf-8')
        for label, policy in (('missing', None), ('not JSON', broken), ('incomplete', incomplete)):
            self.start(policy)
            for name in ('list_connected_browsers', 'tabs_context_mcp', 'tabs_create_mcp'):
                self.assert_refused(self.call(name))
            self.stop()
            self.assertEqual(self.reached(), [], label)
        self.assertTrue(all(r['phase'] == 'pre' and r['decision'] == 'deny' and r['gate_exit'] == 2 for r in self.audit()))

    def test_gate_that_is_missing_crashes_hangs_or_does_not_say_allow_refuses_before_chrome(self):
        situations = [('gate file missing', self.dir / 'no-such-folder', 20)]
        situations += [(kind, self.fake_gate(kind), 2 if kind == 'hang' else 20) for kind in
                       ('crash', 'hang', 'silent', 'allow_but_exit_1', 'says_deny_exit_0', 'garbage_exit_0')]
        for label, gate_dir, timeout in situations:
            self.start(self.policy(), gate_dir=gate_dir, gate_timeout=timeout)
            self.assert_refused(self.call('list_connected_browsers'))
            self.assert_refused(self.call('tabs_context_mcp'))
            self.stop()
            self.assertEqual(self.reached(), [], label)

    def test_audit_log_that_cannot_be_written_refuses_before_chrome(self):
        self.start(self.policy(), audit=self.dir / 'no-such-folder' / 'audit.jsonl')
        self.assert_refused(self.call('list_connected_browsers'))
        self.assertEqual(self.reached(), [])

    # ---------------- the real gate decides
    def test_allowed_call_goes_through_once_and_is_recorded(self):
        self.start(self.policy())
        result = self.call('list_connected_browsers')
        self.assertNotIn('isError', result)
        self.assertEqual(json.loads(result['content'][0]['text'])[0]['deviceId'], DEVICE)
        self.assertEqual(self.reached(), ['list_connected_browsers'])
        rows = self.audit()
        self.assertEqual([(r['phase'], r['decision'], r['gate_exit']) for r in rows], [('pre', 'allow', 0), ('post', 'recorded', 0)])
        self.assertEqual(rows[0]['event']['tool_use_id'], rows[1]['event']['tool_use_id'])
        self.assertEqual(rows[0]['event']['tool_name'], 'mcp__claude-in-chrome__list_connected_browsers')
        self.assertEqual(rows[1]['event']['tool_response'], result['content'])

    def test_full_read_of_an_allowed_page_and_refusal_of_a_foreign_one(self):
        self.start(self.policy())
        for name, arguments in (('list_connected_browsers', {}), ('tabs_context_mcp', {}), ('tabs_create_mcp', {}), ('tabs_context_mcp', {}),
                                ('navigate', {'tabId': 5001, 'url': ORIGIN + '/facts'}), ('tabs_context_mcp', {}), ('get_page_text', {'tabId': 5001}),
                                ('tabs_context_mcp', {})):
            result = self.call(name, **arguments)
            self.assertNotIn('isError', result, (name, result))
        self.assertIn('PAGE TEXT FROM FAKE CHROME', json.dumps(result) + json.dumps(self.audit()[-3]))
        before = len(self.reached())
        self.assert_refused(self.call('navigate', tabId=5001, url='http://127.0.0.1:18766/foreign'))
        self.assertEqual(len(self.reached()), before, 'the foreign navigation never reached Chrome')
        self.assert_refused(self.call('list_connected_browsers'))
        self.assertEqual(len(self.reached()), before, 'after a refusal the run is tainted: nothing else passes')

    def test_wrong_browser_stops_the_run_at_the_list(self):
        self.start(self.policy(device_id='99999999-8888-7777-6666-555555555555'))
        self.call('list_connected_browsers')              # the list is the only thing that may be read
        for name in ('tabs_context_mcp', 'tabs_create_mcp', 'navigate'):
            self.assertIs(self.call(name).get('isError'), True, name)
        self.assertEqual(self.reached()[:1], ['list_connected_browsers'])
        self.assertNotIn('tabs_create_mcp', self.reached())
        self.assertNotIn('navigate', self.reached())

    def test_answer_is_withheld_when_the_gate_taints_the_run_while_recording_it(self):
        self.start(self.policy())
        self.call('list_connected_browsers')
        state = self.dir / 'gate_state.json'
        data = json.loads(state.read_text(encoding='utf-8'))
        self.assertFalse(data['tainted'])
        self.stop()
        # the same proxy rule, seen directly: a tainted or unreadable state means "do not pass the answer on"
        sys.path.insert(0, str(HERE))
        import bro_chrome_proxy
        proxy = bro_chrome_proxy.Proxy(type('A', (), {'policy': str(self.dir / 'policy.json'), 'upstream_timeout': 1})(), ['x'])
        self.assertIs(proxy.tainted(), False)
        state.write_text(json.dumps(dict(data, tainted='profile changed')), encoding='utf-8')
        self.assertIs(proxy.tainted(), True)
        state.write_text('{broken', encoding='utf-8')
        self.assertIs(proxy.tainted(), True)
        state.unlink()
        self.assertIs(proxy.tainted(), True)

    # ---------------- after the call
    def test_answer_the_gate_does_not_accept_is_withheld(self):
        self.start(self.policy(), gate_dir=self.fake_gate('allow_pre_fail_post'))
        self.assert_refused(self.call('get_page_text', tabId=1), 'BRO PROXY: result withheld')
        self.assertEqual(self.reached(), ['get_page_text'])
        self.assertEqual([(r['phase'], r['decision']) for r in self.audit()], [('pre', 'allow'), ('post', 'withheld')])
        self.assertNotIn('PAGE TEXT', self.proc_output_so_far())

    def proc_output_so_far(self):
        return json.dumps(self.rpc('ping'))

    def test_dead_or_silent_upstream_is_a_refusal_not_a_crash(self):
        for mode, timeout in (('dead', 20), ('mute', 2)):
            self.start(self.policy(), mode=mode, upstream_timeout=timeout)
            self.assertEqual(self.rpc('tools/list')['result']['tools'], [], mode + ': no upstream, no tools')
            self.assert_refused(self.call('list_connected_browsers'), 'BRO PROXY: result withheld')
            self.assertEqual(self.rpc('ping')['result'], {}, 'the proxy is still alive')
            self.stop()
            (self.dir / 'gate_state.json').unlink()
        self.start(self.policy(), upstream=[str(self.dir / 'no-such-program.exe')])
        self.assert_refused(self.call('list_connected_browsers'), 'BRO PROXY: result withheld')

    def test_unknown_method_is_an_error_and_notifications_get_no_answer(self):
        self.start(self.policy())
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\nnot json at all\n[1,2]\n')
        self.proc.stdin.flush()
        self.assertEqual(self.rpc('resources/list')['error']['code'], -32601)


if __name__ == '__main__':
    unittest.main(verbosity=2)
