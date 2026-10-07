# STAGING closure when Gev's public IP changes

Candidate, not applied here. Keep current IP restriction until the replacement passes on the actual VPS. No new provider/domain/cost required.

Use Nginx Basic auth on the ENTIRE443 server, with the SAME `gev` username and SAME current operator password. This makes health/capture/contact-click/previews private regardless of source IP. Backend operator authentication remains. Two different passwords would break the request handoff. This gate is for STAGING ONLY; it cannot be attached to the public live-site form. Never embed credentials in JS, URLs, chat or screenshots.

1. Back up the real Nginx config privately. Read the actual TLS server/certbot challenge locations; don't replace the working file with a generic template.
2. Root on VPS: `python3 /opt/kryuk24/deploy/make_staging_password.py`. Reads the existing env file locally, uses `openssl passwd -6 -stdin`, creates a NEW `/etc/nginx/kryuk-staging.htpasswd`, root:www-data0640. No secret/hash output or password argv. Helper supports plain env values with optional outer quotes; confirm the current password value uses that format. Existing output is never overwritten. Hash compatibility must be tested against VPS Nginx, not inferred from local code tests.
3. Inside the actual443 server add:

```nginx
auth_basic "KRYUK24 STAGING";
auth_basic_user_file /etc/nginx/kryuk-staging.htpasswd;
satisfy all;
```

Keep `allow CURRENT_IP; deny all;` during this first phase. Retain TLS, rate limits, logs privacy, body limits and existing route locations. Check no nested location uses auth_basic off / satisfy any. Nginx forwards the browser Authorization header to the backend by default; verify this on the installed proxy configuration. Health and capture must also be gated. HTTP80 ACME challenge must remain publicly reachable; don't apply Basic auth there.
4. `nginx -t`, reload, then from the allowed IP: each route /health, /capture, /contact-click, /operator/work and /operator/site/ gives401 without credentials (GET vs POST route specifics still apply after auth). Correct credentials give /health200STAGING/sendingfalse, operator/site/work200. Wrong password401. Browser form capture works and no messenger opens.
5. Only after phase4 passes, remove the TLS IP allow/deny rules, validate/reload. Test from a DIFFERENT network: no/wrong credentials401; correct credentials200. This proves dynamicIP no longer blocks Gev and staging remains private. Use browser password prompt or password input on curl; never command-line plaintext password. Verify OPTIONS is also gated, nobody can POST without authentication.
6. Run `certbot renew --dry-run` again because Nginx changed. Recheck logs don't include raw bodies/Authorization. Rollback is restoring the old private Nginx config and IP rule, nginx-t/reload. Do not switch LIVE and do not connect kryuk24.ru.

This does not restrict SSH; existing key-only SSH/firewall policy remains. Monitor auth attempts and keep operator credentials private. Report successful checks and exact status codes; don't label this installed until Claude actually executes it.
