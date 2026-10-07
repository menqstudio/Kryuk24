# v0.6 — deployment and final acceptance
Prepared locally, not installed. Existing live website is unchanged.

1. Receive VPS public IP and SSH username; verify SSH host fingerprint through provider console. Keep private keys and passwords out of chats and packages.
2. Install Python 3, Nginx, certificate tooling; create unprivileged kryuk user. Put code in /opt/kryuk24, private data in /var/lib/kryuk24. Generate a unique 24+ character operator password locally and put only in /etc/kryuk24/capture.env (root-owned 0600).
3. Start capture service in default STAGING mode. Allow SSH only from operator networks where practical; allow public 80/443; do not expose 8788. Keep an existing SSH session open while checking firewall changes.
4. Set agreed runtime hostname DNS to VPS IP. Obtain certificate using an HTTP ACME challenge BEFORE enabling nginx-https.conf.example. Replace every REPLACE_RUNTIME_HOST. Run nginx -t on VPS before reload. This template assumes direct Internet -> Nginx, not Cloudflare or another proxy. Syntax/TLS issuance not tested here.
5. Operator password stays in browser Basic authentication, never in website JS. Configure exact origins (site and runtime host). Access journal only over HTTPS. Requests and customer data are not written to Nginx access logs. Backend process health is not a guarantee of complete delivery.
6. Enable daily backup timer. Before relying on it, make snapshot and restore into a NEW database file:
   python3 kryuk_operator.py --db /var/lib/kryuk24/runtime.sqlite backup --output /var/lib/kryuk24/manual-backup.sqlite
   python3 recovery.py --snapshot /var/lib/kryuk24/manual-backup.sqlite --output /var/lib/kryuk24/restore-check.sqlite
   Existing files are never overwritten. Off-server backup destination and retention are still undecided; same-server copies do not protect against losing the VPS.
7. Generate aggregate offline report:
   python3 report_html.py --db /var/lib/kryuk24/runtime.sqlite --output /var/lib/kryuk24/report-NEW.html
   All recorded history, not a period report. No client names, phones, addresses. No sending.
8. Test through HTTPS: desktop/mobile form, exact shared ID in WhatsApp draft, repeat click, changed route, missing capture server while original call/messenger path stays usable, unauthenticated journal rejected, authenticated match, recorded phone job, backup restoration, Google upsert repeated without duplicate.
9. Only after Gev checks the real staging request: approve LIVE_CAPTURE and website attachment. STAGING drafts have TEST labels; do not treat as actual work. LIVE_CAPTURE does not send WhatsApp messages automatically; visitor presses Send.

Continuous Google sync: NOT connected. Current Google connector works during sessions. Do not copy ChatGPT session credentials to VPS. Choose a separate supported credential route later.
24/7 outage alerts: NOT connected. No bot/recipient exists. Agree external monitor and notification destination before claiming monitoring.
Personal data retention: not decided. No automated deletion enabled.
References for the prepared Nginx template:
https://nginx.org/en/docs/http/ngx_http_ssl_module.html
https://nginx.org/en/docs/http/ngx_http_proxy_module.html
https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http/
