# v0.7.0 — contact intentions / կոնտակտի սեղմումներ

STAGING ONLY. No live-site attachment, no messages, no change to budgets/prices. Keep existing IP allowlist, Basic Auth and kryuk-run user.

## Apply / տեղադրել
Before code updates: use existing backup tool; record the successful separate recovery evidence. Preserve /var/lib/kryuk24 and /etc/kryuk24.
Replace runtime.py, secure_server.py, whatsapp-handoff.js, test-orders.html, staging-form.html, report_html.py, test_handoff_js.cjs, test_secure_server.py. Add staging_site.py, contact_metrics.py, contact-clicks.js, test_contact_metrics.py, test_contact_clicks_js.cjs. Additive SQLite table contact_interactions is created on startup; existing orders/events stay.
The protected /operator/staging page now loads tracking and offers three SYNTHETIC direct-link controls. These controls prevent actual calls/messages; the tracker itself never prevents navigation. This synthetic page tests the mechanism. A protected full-source preview is also available at /operator/site/ for all8pages.
Nginx: add a kryuk_preview limit_req_zone at http scope and /operator/site/ location from the example (allows asset loading while preserving backendBasicAuth and inherited IPallowlist). Then add exact location /contact-click to CURRENT TLS server, using same limit_req zone/status/proxy settings as /capture. Copy that location from deploy/nginx-https.conf.example. Do NOT replace the whole active config and lose IP allowlist/certificate paths. nginx -t before reload. No new firewall ports or env variables.
Run python3 -m unittest discover -v (49 OK), node test_handoff_js.cjs (4 PASS), node test_contact_clicks_js.cjs (10 PASS). Restart capture service and inspect active status.

## Acceptance / ընդունում
From allowed IP, authenticate at /operator/staging. Click each synthetic direct control: each records a TEST contact intention, zero orders created. Journal shows daily Moscow-time counts by call/wa/tg and separate TEST totals. Same button within5seconds, including page reload in same tab with working sessionStorage, reuses event ID and counts once. After5seconds it counts another intention. This is NOT visitor-level cross-browser deduplication.
Form WhatsApp/Telegram button: one order + one linked interaction in ONE SQLite transaction; repeated capture with same ID adds neither. No independent click event for handled form buttons. Invalid/prevented form submissions are not contacts.
Close backend / make endpoint unreachable in staging only: genuine links must still work unchanged when tracker runs; synthetic test controls intentionally stay within page. Browser acceptance must separately confirm genuine-link navigation without sending any message. All frontend tests here are mock DOM, not browser verification.
Preview ?id query fix from0.6.2 remains. Check protected preview200, unauthenticated401.
Optional TEST HTML report:
python3 report_html.py --db /var/lib/kryuk24/runtime.sqlite --output /var/lib/kryuk24/test-click-report-NEW.html --include-test-clicks
Default reports exclude TEST. Test report clearly labels included TEST clicks and still excludes synthetic business orders/calls.

## Meaning / իմաստ
Clicks are intentions only. Captured form + linked intention is ONE contact case, shown in distinct sections for different measurements; never add order count to click count as total leads. Form contact counted when capture succeeds; a failed capture is a measurement gap, not proof of no click. No confirmed call, received message or completed order is inferred.
Backend time is receipt time UTC; daily grouping Europe/Moscow fixedUTC+3. Beacon has no delivery receipt. Pending delivery, blocked cookies/storage, closed browser/network can lose measurement. Zero rows do not imply zero business activity.

## Metadata / տվյալներ
Exact whitelist: channel,page,position,button code,referrer domain, UTM campaign codes, yclid, device category, server TEST flag. No full referrer, destination href/phone, name, IP or raw UA in contact table. Page paths restricted to8 current site pages + synthetic stage. Device is viewport category, not fingerprint. Source fields are visitor-supplied, not verified attribution. Missing source remains unknown/direct.
UTM restricted to80character ASCII campaign codes; free text, emails and phone-like strings rejected/dropped. Do not put customer names in campaign codes. yclid is an attribution identifier and should NOT be described as fully anonymous. Network infrastructure still processes IP for rate limits; this promise concerns persisted contact rows, not a legal finding.
Retention/off-server backups unresolved; do not enable live collection before decisions. No Google click sync or Metrica comparison yet.

## Full-site attachment later / հետո
contact-clicks.js detects tel:, HTTPS wa.me/api.whatsapp.com and t.me links by document capture listener, including dynamically-created and SEO-page links. It excludes handled form transitions via the event flag set by whatsapp-handoff.js. Position selectors cover header.hdr/header, .hero, .callbar, form attributes and footer.foot; other contact buttons labelled content.
The protected FULL-SITE preview at /operator/site/ injects these scripts on all8pages. External navigation is blocked only by the separate staging wrapper, not by the tracker. CSP blocks external analytics/maps, so their behavior must be verified in a separate approved test later. It uses this configuration (plus pagePrefix mapping):
window.KRYUK_CONTACT_CONFIG={mode:'STAGING',endpoint:'https://runtime.kryuk24.ru/contact-click'};
then contact-clicks.js, then whatsapp-handoff.js on pages with forms. Injection occurs in protected response HTML; source site files are unchanged. Preserve existing Metrica listeners/goals. Check form validation, maps/calculator, mobile sticky links, all8pages before requesting live approval.
Form request-ID persistence across reload remains separate backlog; existing form dedup is only same open-page state. Direct-click dedup introduced here does not fix that separate issue.
