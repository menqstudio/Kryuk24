# Deployment candidate / Տեղադրման պատրաստուկ

Not deployed or verified on an actual VPS. secure_server.py binds 127.0.0.1:8788; put it behind an HTTPS reverse proxy on a confirmed hostname (proposed runtime.kryuk24.ru, DNS not configured). Proxy: limit body to 8 KB; set read/header timeouts; rate-limit /capture per actual visitor IP; proxy to loopback. Python's rate limit is aggregate when behind a proxy and does not trust forwarded client IP headers. The allowed-origin check is a browser control, NOT authentication or sufficient bot prevention.

Create dedicated kryuk user, read-only application at /opt/kryuk24, private data at /var/lib/kryuk24, root-owned secret environment file /etc/kryuk24/capture.env. The supplied service auto-restarts and starts in STAGING (all captured records TEST). Do not add --live-capture before the final controlled test and explicit live rollout. Basic auth is allowed ONLY over HTTPS publicly. It currently gives a single authenticated operator role; no multi-user audit identity or MFA.

Operator: https://YOUR_RUNTIME_HOST/operator (username gev). Website capture: /capture. No outbound server messaging. CORS allowed origins must include the website origin AND operator origin exactly. Public intake supports no journal GET. Keep /test-report and demo_server.py off the public proxy. There is no website publication in this package.

For a staged browser test, attach:

```html
<script>
window.KRYUK_HANDOFF_CONFIG={mode:'STAGING',endpoint:'https://YOUR_RUNTIME_HOST/capture'};
</script>
<script src="whatsapp-handoff.js" defer></script>
```

STAGING opens the real original WhatsApp/Telegram URL with a TEST message; the customer/tester must still press Send. LIVE removes only the TEST prefix; backend test flag is controlled separately on the server. Local preview stays the default without config. No operator password/API token goes into the website. Do not enable LIVE browser mode against a staging backend or vice versa.

Deployment prerequisites still absent: confirmed VPS/SSH, domain/DNS, valid TLS, protected secret entry, external availability monitor, retention policy, production restore verification. We have not rented a server, changed DNS, installed a service or published website code.

Google: connector-session ID-based updates are provided by sheets_plan.py. They are not a persistent background sync service. Scheduled sync needs separately authorized credentials/access; never scrape an authenticated browser to imitate an always-on API. Do not place customer data in a public sheet.

HY: Այս ֆայլը տեղադրման պատրաստուկ է, ոչ իրական տեղադրված համակարգ։ Նախ VPS-ը, DNS-ը, HTTPS-ը և փակ մուտքը պատրաստել, հետո միասնական թեստը։ Կայքի WhatsApp/զանգի գործող ճանապարհը պահպանել։

Backup scheduling candidate: deploy/kryuk-backup.service + .timer. It creates private SQLite snapshots without deleting older ones; retention and off-host copies are not configured. A daily timer uses the host's timezone. No timer has been installed/enabled here. Provider backups and these local snapshots do not replace an off-host restore-tested copy.
