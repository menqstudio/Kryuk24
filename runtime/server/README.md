# KRYUK24 Operations Runtime v0.8.0 — STAGING candidate

Start with [operations/V080_HANDOFF.md](operations/V080_HANDOFF.md). This release adds durable daily work/evidence/review queue, protected media manifests/previews, local morning checks and full DB+media backups. Existing site and form/contact scripts remain unchanged. Python3.10+, standard library only; Node is needed only for frontend regression tests.

Private dashboard after installing/restarting: `/operator/work`. Full deployment and acceptance instructions are in the handoff. Dynamic-IP replacement is prepared separately in [operations/STAGING_WITH_DYNAMIC_IP.md](operations/STAGING_WITH_DYNAMIC_IP.md), not installed here. Preserve actual kryuk-run user and existing DB/env/Nginx. No LIVE change, external message, browser executor or automatic image editing is enabled.

Locally:67 Python tests OK; frontend4+10+6+10 scenarios and11 SHA256 oracle cases PASS. These are local/harness checks, not new Windows/VPS/browser acceptance. See VALIDATION_V080.md.

## Historical v0.5 README (retained for original demo/tool context)

Current release instructions above take precedence over historical status claims below.

# KRYUK24 v0.5 — local workflow candidate / տեղային փորձի տարբերակ

## Outcome / Արդյունք

EN: Implements local form capture, request ID correlation, operator-recorded messenger observations, separate phone job records, snapshot export for Google Sheets, and SQLite backup. No automatic WhatsApp reading or server-side sending, continuous Google synchronization, public hosting, or live-site deployment is enabled. Connected-session Google sync was tested with synthetic records.
HY: Տեղում պատրաստ են ձևի գրանցումը, ընդհանուր ID-ն, չատում տեսած համընկնման գրանցումը, զանգային պատվերների առանձին հաշվառումը, Sheets արտահանումն ու բեքափը։ WhatsApp-ի ավտոմատ ընթերցում/սերվերից ուղարկում, մշտական Google համաժամացում և կենդանի կայքի միացում դեռ չկան։ Սեսիայի Google փոխանցումը փորձարկված է TEST տվյալներով։

## Run / Գործարկում

Python 3.10+:

```sh
python -m unittest -v test_runtime test_adapter test_notifications test_handoff test_secure_server test_sheets_plan
python demo_server.py --db test-runtime.sqlite
```

Open http://127.0.0.1:8765/ on the same computer. The original site files remain unchanged. An injected adapter intercepts the calculator and prebooking WhatsApp/Telegram buttons **ONLY IN THIS LOCAL SERVER**, opening a local preview instead of real messengers. The original standalone test button remains available.

Նույն համակարգչում բացել հասցեն։ Լրացնել հաշվիչը և սեղմել WhatsApp-ը․ այս տեղային տարբերակում բացվում է հաղորդագրության նախադիտումը, ոչ իրական չատը։ ID-ն նույնն է հաղորդագրության ու մատյանի մեջ։ Նախադիտման բացումը կատարվում է մինչև պահպանումը։ Եթե պահպանումը ձախողվում է՝ ուղարկման ճանապարհը չի սպասում դրան, և սխալը երևում է ձևում։ Նույն տվյալներով կրկնափորձը նույն ID-ն ունի, հասցեի փոփոխությունը՝ նոր ID։ Սա էջի ընթացիկ սեսիայի պաշտպանություն է, ոչ բոլոր սարքերի/վերաբեռնումների համընդհանուր կրկնօրինակների հայտնաբերում։

Main calculator and prebooking are covered. Original pricing/message composition is reused. Unknown contact/route/vehicle values are explicitly NOT_PROVIDED; no phone is inferred. Booking date/vehicle validation is preserved. The preview obtains the full stored message after capture; if storage fails, only the ID can be shown. No real message is sent by the local test.

## Journal / Մատյան

http://127.0.0.1:8765/test-orders

- Exact request ID + a reference and source evidence records an operator observation. This is manually supplied evidence, not independent WhatsApp API verification. A message reference cannot be matched to two requests. A probable match does not pass.
- Test acceptance/decline does not confirm customer price/payment or advance NEW to completed.
- Phone entries remain separate from website captures. Unknown money stays empty. COMPLETED is operator-reported, not proof of payment or profitability.
- TEST records must be excluded from business results.

Այս մատյանը տեղային փորձի համար է, մուտքի պաշտպանություն չունի։ Չբացել ինտերնետում, չտանել կենդանի հաճախորդների տվյալներ այս demo server։

## Operator tools / Օպերատորի գործիքներ

```sh
python kryuk_operator.py --db test-runtime.sqlite summary
python kryuk_operator.py --db test-runtime.sqlite backup --output backup-2026-10-06.sqlite
python kryuk_operator.py --db test-runtime.sqlite sheets-export --output export-2026-10-06
```

Backup uses SQLite's backup API (includes WAL); refuses to overwrite an existing output. Verify restoration on a separate copy. CSV export writes Website, WhatsApp and Phone snapshots without headers, with formula-injection escaping. Snapshot exports are not incremental: never append the same snapshot repeatedly or overwrite manually maintained data. Google rows must be matched/upserted by ID before an automated sync is introduced.

CLI supports `match` and `call`; see `python kryuk_operator.py --help` and subcommand help. Operator API remains bearer-protected in runtime.py, binds localhost, and supports /orders/{id}/whatsapp-match and /call-jobs. A bearer token must never be put into website JavaScript.

## Google Sheets / Google մատյան

Created and connector-read back:
https://docs.google.com/spreadsheets/d/132hGJXPflD6piC6iQi37yjtsZxejehjpVlQ_dhJnzoM/edit

Guide / Website / WhatsApp / Phone. Native template now contains one synthetic TEST row per data tab; no customer data uploaded. Connected-session ID-based sync tested; continuous sync NOT CONNECTED. Sheet rendering checked only through metadata/cell formatting, not browser visual inspection. No public sharing added. Account-specific access for Armen/Claude is not independently established. The actual Google Sheet ID is in GOOGLE_SHEET.json.

## Verification / Ստուգումներ

Linux: 33 Python tests; 4 JavaScript logic scenarios with a mock DOM (not a browser); JS syntax checks; CLI smoke verified backup restoration, CSV formula escaping and TEST exclusion. Browser binary unavailable here, so v0.5 desktop/mobile/Windows checks NOT RUN. Prior v0.3: Windows 18/18 and browser checks passed per Claude report. Original website hashes unchanged.

## Installation / Թարմացում

Claude: unpack into a new folder, retain previous versions and database. Back up the previous test database before using it with v0.5; new tables are added without dropping existing records. Restart the local server from this new folder and pass the absolute test database path if preserving prior tests. Check browser at desktop/mobile widths, calculator, booking, offline save, matching and phone entry. Give Gev one final combined test, not a new manual test after each feature.

## v0.5 connected-session Google sync / Google կապը սեսիայում

`sheets_plan.py` builds structured Sheets batchUpdate requests from snapshot CSVs and a freshly read snapshot of the three target sheets (header row included). It upserts by ID, rejects duplicate IDs/malformed headers, preserves orphan manual rows and avoids unchanged writes. All synchronized columns are Runtime-owned. Caller must read live cells immediately before write; a plan is not safe to reuse after concurrent manual changes. No unattended executor is included.

Test performed here: one synthetic website row, synthetic observed-message row and synthetic phone row were written to the actual native Sheet via connector and read back. Rebuilding from the resulting snapshot produced zero changes. TEST flags are TRUE. No real chat was read and no real message was sent.

## Secured staging service / Փակ փորձի սերվեր

New secure_server.py: loopback /capture service, strict request whitelist and size limits, allowed browser origins, idempotency, protected /operator journal and write endpoints. Operator credentials stay server-side (HTTP Basic login); require HTTPS in public deployment. Backend STAGING forces test=true; client cannot spoof it. /test-report is not exposed. Standard demo_server remains LOCAL ONLY.

`whatsapp-handoff.js` now has explicit modes: LOCAL_PREVIEW (default), STAGING (opens original messenger URL with TEST prefix), LIVE (original URL with ID). The latter two require KRYUK_HANDOFF_CONFIG with the confirmed public capture URL. Test of real messenger URLs was performed with mock window.open, not by actually opening/sending messages. If browser lacks crypto.randomUUID, existing messenger behavior remains available without capture.

Deployment service/environment example and prerequisites: deploy/STAGING.md. No VPS, DNS, TLS or service was installed. Do not use plain Python HTTP as the public TLS endpoint.

## Remaining before live / Մինչև կենդանի միացումը

Missing confirmed VPS/SSH access and hostname, reverse proxy TLS/rate limits/timeouts, actual production restore and external monitoring check, customer-data retention decision, and optionally separately authorized Google credentials for continuous sync. The code is a staging candidate, not proof of production readiness. Browser/Windows v0.5 and real WhatsApp receipt still require the final combined test.

Armen WhatsApp is linked according to Claude's report. Existing orders mostly arrive by phone. Do not infer total business volume from 7 days of WhatsApp. For new site requests, Claude may compare exact IDs during an authorized session; linked browser access does not create 24/7 monitoring. No Telegram bot is required for the visitor-sends-WhatsApp flow. Original call and messenger links must remain available on the live site during rollout.

## v0.7.0 / շարունակություն
Read deploy/V070_PATCH.md for STAGING install. Contact intentions are separate from business orders and are not proof of calls/messages. Protected /operator/site/ preview injects tracking on all8sourcepages without editing source or navigating to real contacts. Test49Python+4handoffJS+10contactJS; browser/VPS acceptance pending. operations/MASTER_ROADMAP.md carries the full company/clientscope, DAILY_OPERATIONS.md and CLAUDE_DAILY_REHEARSAL.md prepare recurring cabinet/mediawork. Scheduling is not activated here.
