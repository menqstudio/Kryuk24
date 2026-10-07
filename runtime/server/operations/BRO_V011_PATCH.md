# Bro Queue Bridge v0.1.1 — ordering fix / հերթի ուղղում

Replace only ops_work.py and test_bro_worker.py after preserving installed files and backing up DB. ops_views.py is NOT included. No schema migration, task reopening or data reset is required. report(day) now orders by rowid, and report() by day DESC,rowid. This preserves the insertion sequence independently of timestamp precision. New regression test gives all tasks the same created value and checks both reports and the first Bro claim.

Փոխարինել միայն երկու նշված ֆայլերը։ Վահանակը, Nginx-ը և ընթացիկ տվյալները պահել։ Անցկացնել Python թեստերը Windows/VPS-ում։ ops_work.py-ն բեռնող capture գործընթացին անհրաժեշտ է վերագործարկում՝ փոփոխությունն ուժի մեջ մտնելու համար․ նախ ավարտել ընթացիկ փորձերը, ապա վերագործարկել միայն capture-ը և ստուգել առողջությունն ու մատյանի թվերը։ Bro-ի adapter/timer չի ավելացվել։

## Architecture decision / Ճարտարապետական ուղղություն

Confirmed by code inspection: HTTP work/report, claim and observe already exist, but use Gev's owner credential and the shared AUTHENTICATED_OPERATOR lease identity. A draft HTTP endpoint does not exist. Those routes are insufficient as an isolated Bro API. Do NOT give the AI adapter Gev's owner credential: it could access approve and other operator actions.

Next implementation: dedicated authenticated worker routes and a Windows pull client over HTTPS. Worker capability must expose only sanitized current-day queue reads, unique-run claim, owned-lease observe, and REPORT_DRAFT submission. No approve, plan, customer ledger, messaging or account-change capability. Separate worker credential plus an explicit Nginx gate arrangement is required because existing nginx Basic auth intercepts the whole host; don't simply exempt worker routes from auth. Keep operator gate and DB on VPS, credentials in the trusted bridge process only, never in the AI subprocess. Include HTTP race, expired lease, wrong owner, unauthorized route and cross-day checks.

Real adapter, unattended Chrome permissions and Windows descendant-process cancellation remain untested/uninstalled. Do not create a timer yet. Existing DAILY_REPORT digest and READY_REVIEW state must remain untouched. No-PENDING on a new day means the plan for that day does not exist; bridge IDLE does not prove an adapter connection. Use the normal daily planner, or a separately labeled acceptance task through an implemented task mechanism; do not reopen completed business checks silently. Plain Armenian adapter output remains compatible; no JSON-language migration is introduced here.
