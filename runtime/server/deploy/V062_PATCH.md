# v0.6.2 / query routing ուղղում
Apply only secure_server.py and test_secure_server.py from this version. Preserve data, env, kryuk-run identity, systemd and Nginx configuration.
GET routing now compares urlsplit(self.path).path, keeping query strings in the browser for preview ID lookup. Operator authentication still applies before returning the preview. POST/OPTIONS behavior is unchanged.
New regression: GET /operator/staging-preview?id=K24-... rejects unauthenticated access with401 and returns authenticated HTML200; checks the captured request remains present. Test reproduced404 before fix, passes after.
Local Linux Python3.12: 38 tests OK; 4 mocked frontend scenarios PASS. No VPS deployment or real-browser verification performed by Codex.
Claude: run python3 -m unittest discover -v and node test_handoff_js.cjs; restart kryuk-capture.service; confirm protected preview with ?id=... renders in browser. No live mode, messages, data replacement, or live-site attachment.
