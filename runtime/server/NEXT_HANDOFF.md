# Claude handoff / Փոխանցում — v0.5

Տեղային ամբողջ շղթան պատրաստ է, բայց կենդանի միացում չկա։ Կարդալ README և deploy/STAGING.md։ Գործարկել 33 Python ստուգումն ու node test_handoff_js.cjs (4 տրամաբանական սցենար)։ Վերջում միայն մեկ միասնական browser/Windows փորձ՝ հաշվիչ, նախնական գրանցում, պահպանում, ID, չատում ID-ի համեմատում, մատյան, զանգային գրառում և Sheets։

secure_server.py-ի փակ փորձը ունի առանձին մուտք․ գաղտնիքը տեղադրել private env-ում, չարտահանել չատ կամ website JS։ Դեմո սերվերը հանրային չդարձնել։ VPS և իրական endpoint դեռ չկան, տեղադրման օրինակները չեն գործարկվել։

Google Sheet: actual connector-session sync tested, one synthetic TEST row in Website/WhatsApp/Phone. ID-based plan repeat gives zero updates. Continuous sync unavailable without separately configured access. Before connector writes always re-read live target cells; do not reuse a stale snapshot. Do not overwrite manually maintained rows. No customer data or real chats used in our tests.

English: staged code and connected-session bridge implemented; no VPS/deployment, browser v0.5 or actual WhatsApp delivery tested here. Preserve existing site and prices. Real launch follows Gev's review of final combined test.

## v0.6 additions
Read deploy/FINISH_ON_VPS.md. Added recovery.py (new destination only), report_html.py (aggregate Russian offline HTML, no PII, excludes TEST), and direct-public Nginx HTTPS/rate-limit template. 36 Python tests + 4 mocked frontend scenarios pass locally on Linux. Keep all deployment in STAGING until real end-to-end test. Nginx template requires real certificates and VPS nginx -t. No promise of always-on Google sync or outage alerts.

## v0.6.1 / փակ փորձ
Adds authenticated /operator/staging + preview + JS in STAGING only. Apply instructions: deploy/V061_PATCH.md. Preserves kryuk-run deployment choice (reported by Claude), data and env. Local37 tests+4 JS PASS; VPS and browser pending. No messenger opens from the synthetic test page.

## v0.6.2 / query routing
GET paths parsed with urlsplit before comparison. Regression proved404 before fix and passes after (38 tests+4 mocked JS). Follow deploy/V062_PATCH.md. Browser/VPS pending locally; Claude reported previous server hotfix independently.

## v0.7.0 / contact intentions and full work scope
STAGING contacts table, beacon/keepalive tracker, per-button5sID reuse, linked-form single event, Moscowdaily real/TESTcounts, HTMLreport. See deploy/V070_PATCH.md. Original8page source untouched. New operations/MASTER_ROADMAP.md preserves full agency/client scope; DAILY_OPERATIONS.md and CLAUDE_DAILY_REHEARSAL.md prepare recurring cabinet/mediawork. No recurringClaude executor configured here; no publicationauthority widened.

## v0.7.1 / form ownership regression
Use deploy/V071_PATCH.md. Ownership WeakSet established before clicks prevents document capture from counting the same formtransition twice across native microtaskcheckpoints. New test_real_markup_contacts.cjs parses actual site/index.html, reproduces oldfailure and passes6cases afterfix. Local49Python+20JS scenarios; actualVPS/browserpending. ExistingTESThistory retained; use deltas foracceptance.


## v0.7.2 / Windows + reload identity
Read deploy/V072_PATCH.md. Windows originalfailure unknown; explicitUTF8bytes and completechilddiagnostics added (cp1252portabilityhazard independentlyreproduced). Same-tab24hpendingidentity usesSHA256fingerprint+initialmetadata, no rawformtext cached; New Requestexplicitreset. Local50Python+30JSscenarios+11hashoraclecases pass. VPS/Windows/browsercandidatepending; Claude-reportedv0.7.1 realChrome acceptance preserved.
