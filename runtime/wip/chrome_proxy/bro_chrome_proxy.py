"""Bro Chrome proxy: a mandatory layer between Claude and the Chrome tools.

Why it exists. In the supervised trial (T2, 07.10.2026) Claude Code ran two Chrome tools with no hook and no allow rule.
A hook therefore cannot be the only gate: when the hook is absent, some calls still reach Chrome. This proxy puts the
decision into the path of the call itself. Claude is given THIS program as its only MCP server; the real Chrome tools
are reachable only through it.

    Claude Code  --stdio MCP-->  bro_chrome_proxy.py  --stdio MCP-->  upstream Chrome MCP server  -->  Chrome

Rules:
  - only the nine read-only tools exist here; any other name is refused without asking anybody;
  - before a call is forwarded, the gate (bro_gate_hook.py, unchanged) is run on a PreToolUse event built from the call.
    The call is forwarded only when the gate exits 0 AND prints permissionDecision "allow";
  - no policy file, a broken policy, a missing, crashing, hanging or silent gate, an audit log that cannot be written:
    each of them ends in a refusal BEFORE anything is sent upstream;
  - after the upstream answer the gate is run on a PostToolUse event. If it does not accept the answer, or has
    tainted the run while recording it, or its state cannot be read, the answer is withheld from Claude;
  - every decision is appended to an audit log with the raw event.

The proxy never talks to the network and starts exactly one child: the upstream command given after "--".

  python bro_chrome_proxy.py --policy <policy.json> --gate-dir <folder with bro_gate_hook.py> --audit <events.jsonl>
                             [--gate-timeout 20] [--upstream-timeout 120] -- <upstream command> [args...]
"""
import argparse
import json
import queue
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

READ_ONLY = ('list_connected_browsers', 'select_browser', 'tabs_context_mcp', 'tabs_create_mcp', 'tabs_close_mcp',
             'navigate', 'get_page_text', 'read_page', 'find')
GATE_PREFIX = 'mcp__claude-in-chrome__'       # the tool names the gate and its policies are written for
SERVER_INFO = {'name': 'bro-chrome-proxy', 'version': '0.1.0'}


class UpstreamError(Exception):
    pass


class Upstream:
    """The real Chrome MCP server as a child process, spoken to with newline-delimited JSON-RPC."""

    def __init__(self, argv, timeout):
        self.argv, self.timeout = argv, timeout
        self.process, self.lines, self.next_id = None, queue.Queue(), 0

    def start(self):
        if self.process is not None:
            return
        try:
            self.process = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as error:
            raise UpstreamError('upstream did not start: %s' % type(error).__name__) from None
        threading.Thread(target=self._read, daemon=True).start()
        self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': SERVER_INFO})
        self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _send(self, message):
        try:
            self.process.stdin.write((json.dumps(message) + '\n').encode('utf-8'))
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise UpstreamError('upstream pipe closed') from None

    def request(self, method, params):
        if self.process is None:
            raise UpstreamError('upstream not started')
        self.next_id += 1
        wanted = self.next_id
        self._send({'jsonrpc': '2.0', 'id': wanted, 'method': method, 'params': params})
        while True:
            try:
                line = self.lines.get(timeout=self.timeout)
            except queue.Empty:
                raise UpstreamError('upstream did not answer in time') from None
            if line is None:
                raise UpstreamError('upstream ended')
            try:
                message = json.loads(line.decode('utf-8'))
            except ValueError:
                continue
            if isinstance(message, dict) and message.get('id') == wanted and 'method' not in message:
                if 'result' not in message or not isinstance(message['result'], dict):
                    raise UpstreamError('upstream returned an error')
                return message['result']

    def stop(self):
        if self.process is not None:
            try:
                self.process.kill()
                self.process.wait(10)
            except OSError:
                pass
            for stream in (self.process.stdin, self.process.stdout):
                try:
                    stream.close()
                except OSError:
                    pass


class Proxy:
    def __init__(self, args, upstream_argv):
        self.args = args
        self.upstream = Upstream(upstream_argv, args.upstream_timeout)
        self.session = 'bro-proxy-' + uuid.uuid4().hex
        self.calls = 0

    # ---------------- the gate, exactly as a hook would run it
    def gate(self, event):
        """(exit code or None, stdout, stderr label). None = the gate could not be run or did not finish."""
        argv = [sys.executable, str(Path(self.args.gate_dir) / 'bro_gate_hook.py'), '--policy', self.args.policy]
        try:
            done = subprocess.run(argv, input=json.dumps(event).encode('utf-8'), capture_output=True, timeout=self.args.gate_timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            return None, '', type(error).__name__
        return done.returncode, done.stdout.decode('utf-8', 'replace'), done.stderr.decode('utf-8', 'replace').strip()[:200]

    @staticmethod
    def allowed(code, out):
        """Only an exit code 0 together with an explicit "allow" counts. Everything else is a refusal."""
        if code != 0:
            return False
        try:
            return json.loads(out)['hookSpecificOutput']['permissionDecision'] == 'allow'
        except (ValueError, KeyError, TypeError):
            return False

    def tainted(self):
        """False only when the gate's state file can be read and says the run is not tainted. Anything else is True."""
        try:
            state_file = json.loads(Path(self.args.policy).read_text(encoding='utf-8'))['state_file']
            return bool(json.loads(Path(state_file).read_text(encoding='utf-8'))['tainted'])
        except (OSError, ValueError, KeyError, TypeError):
            return True

    def audit(self, row):
        """Append to the audit log. Returns False when the record could not be written: then nothing may proceed."""
        try:
            with open(self.args.audit, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), **row}, ensure_ascii=False) + '\n')
            return True
        except OSError:
            return False

    @staticmethod
    def refusal(text):
        return {'content': [{'type': 'text', 'text': 'BRO PROXY: ' + text}], 'isError': True}

    # ---------------- one tool call
    def call(self, params):
        name = params.get('name') if isinstance(params, dict) else None
        data = params.get('arguments', {}) if isinstance(params, dict) else None
        self.calls += 1
        use_id = 'proxy_%04d_%s' % (self.calls, uuid.uuid4().hex[:12])
        if name not in READ_ONLY or not isinstance(data, dict):
            self.audit({'phase': 'refused', 'decision': 'deny', 'reason': 'tool outside the read-only set or bad input', 'tool': str(name)[:80]})
            return self.refusal('denied')
        base = {'session_id': self.session, 'tool_use_id': use_id, 'tool_name': GATE_PREFIX + name, 'tool_input': data,
                'permission_mode': 'proxy', 'cwd': str(Path.cwd())}
        pre = dict(base, hook_event_name='PreToolUse')
        code, out, label = self.gate(pre)
        ok = self.allowed(code, out)
        if not self.audit({'phase': 'pre', 'decision': 'allow' if ok else 'deny', 'gate_exit': code, 'gate_says': label, 'event': pre}) or not ok:
            return self.refusal('denied')          # nothing was sent upstream

        failure = None
        try:
            self.upstream.start()
            result = self.upstream.request('tools/call', {'name': name, 'arguments': data})
            content = result.get('content')
            response = {'content': content, 'isError': True} if result.get('isError') is True else content
        except UpstreamError as error:
            failure, result = str(error), None
            response = {'text': 'upstream failure', 'isError': True}
        post = dict(base, hook_event_name='PostToolUse', tool_response=response)
        code, _, label = self.gate(post)
        # A hook can only record after the fact. Here the answer is still in our hands: if the gate has tainted the run
        # while recording it (wrong browser, unknown form, ...), or its state cannot be read, the answer is not passed on.
        accepted = code == 0 and failure is None and self.tainted() is False
        logged = self.audit({'phase': 'post', 'decision': 'recorded' if accepted else 'withheld', 'gate_exit': code, 'gate_says': label,
                             'upstream_failure': failure, 'event': post})
        if not accepted or not logged:
            return self.refusal('result withheld')
        return result

    # ---------------- the MCP server side
    def tools(self):
        try:
            self.upstream.start()
            listed = self.upstream.request('tools/list', {}).get('tools')
        except UpstreamError:
            return []                               # no upstream, no tools
        return [t for t in listed if isinstance(t, dict) and t.get('name') in READ_ONLY] if isinstance(listed, list) else []

    def handle(self, message):
        method, ident = message.get('method'), message.get('id')
        if ident is None:
            return None                             # a notification: nothing to answer
        if method == 'initialize':
            version = (message.get('params') or {}).get('protocolVersion') or '2024-11-05'
            return {'protocolVersion': version, 'capabilities': {'tools': {}}, 'serverInfo': SERVER_INFO}
        if method == 'ping':
            return {}
        if method == 'tools/list':
            return {'tools': self.tools()}
        if method == 'tools/call':
            try:
                return self.call(message.get('params'))
            except Exception:                       # an error of the proxy itself is a refusal, never a pass
                return self.refusal('denied')
        raise LookupError(method)

    def serve(self):
        for raw in sys.stdin.buffer:
            try:
                message = json.loads(raw.decode('utf-8'))
            except ValueError:
                continue
            if not isinstance(message, dict):
                continue
            try:
                result = self.handle(message)
            except LookupError:
                reply = {'jsonrpc': '2.0', 'id': message.get('id'), 'error': {'code': -32601, 'message': 'method not found'}}
            else:
                if result is None:
                    continue
                reply = {'jsonrpc': '2.0', 'id': message.get('id'), 'result': result}
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + '\n')
            sys.stdout.flush()


def main():
    argv = sys.argv[1:]
    own, upstream = (argv[:argv.index('--')], argv[argv.index('--') + 1:]) if '--' in argv else (argv, [])
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', required=True)
    parser.add_argument('--gate-dir', required=True)
    parser.add_argument('--audit', required=True)
    parser.add_argument('--gate-timeout', type=float, default=20)
    parser.add_argument('--upstream-timeout', type=float, default=120)
    args = parser.parse_args(own)
    if not upstream:
        parser.error('the upstream command is required after "--"')
    sys.stdout.reconfigure(encoding='utf-8')
    proxy = Proxy(args, upstream)
    try:
        proxy.serve()
    finally:
        proxy.upstream.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
