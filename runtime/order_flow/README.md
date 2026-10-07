# Dispatch Order Flow v0.1.1 / Պատվերի հոսք v0.1.1

## English

Implemented internal backend increment for roadmap phase 3; NOT a completed phase or deployed release. Built against `menqstudio/Kryuk24` commit `f7c50c722a44460e55e131288295d6c64de60fbe`, runtime.py Git blob `14656bee5236132299cbfae590a354f8a500cfc7`. No production database was accessed. No external system changed. No change to ops_views.py or the archived server snapshot.

Place this folder at `runtime/order_flow/`. Resolve imports against `runtime/server/` when running tests:

```bash
PYTHONPATH=runtime/server python3 -m unittest discover -s runtime/order_flow -p 'test_*.py' -v
```

PowerShell: `$env:PYTHONPATH='runtime/server'`; then run the same unittest command. Windows has NOT been tested here. Verified locally on Linux: 18 new tests and 7 existing runtime tests pass.

### Behaviour

- Reuses existing orders/events and Runtime.intake. Adds only namespaced dispatch tables and a status/revision guard for explicitly enrolled orders.
- Explicit adopt requires NEW, current revision, dispatcher and a boolean test marker. No historical order is migrated or inferred. Existing unmanaged orders retain legacy behaviour.
- Dispatcher remains the owner and price authority. Assigned partner may append reports only. Reports do not verify payment, completion or repricing.
- Confirmed price has a version. Customer confirmation is required before assignment and repricing. Repricing is refused after financial settlement starts.
- Money is integer kopecks. Commission due = 20% of dispatcher-recorded customer-confirmed price, rounded to nearest kopeck (half-up). Commission payment is evidence recording, not money transfer.
- Progress, ETA, call status, verified delivery/payment, commission settlement, feedback and an open issue have explicit commands. DELIVERED is not CLOSED.
- Close requires dispatcher-attested completion/payment, exact paid confirmed amount, exact settled commission, recorded feedback state and no open issue.
- Optimistic revisions, BEGIN IMMEDIATE, atomic event/state/idempotency write; replay returns the original result; changed payload with same key is refused. Closed orders are immutable.
- Evidence is attestation, NOT automated verification of real receipts or customer identity. Test records are always TEST_ONLY. PARTNER_REPORTED / DISPATCHER_ATTESTED actor roles are recorded for real commands. The caller cannot submit a trust label.

### Integration requirements / remaining work

`Principal` MUST come from a trusted authenticated adapter, not a request body. This module is internal and provides no HTTP authentication. A shared operator credential is not proof of an individual dispatcher or partner identity. Do not expose commands before role/account resolution and origin/CSRF validation are implemented.

No HTTP/UI, live site connection, partner portal, cost/profit KPI, cancellation/no-show, post-payment corrections/refunds, owner transfer, multiple simultaneous complaints, evidence-file verification, retention policy or automatic historical migration is implemented. These require subsequent explicit contracts. Keep this increment in development/STAGING testing; no LIVE enablement is provided.

The SQLite guard is a trusted-code compatibility control, not isolation from processes with unrestricted DB write access. Do not create OrderFlow on the production DB merely to inspect it: constructor creates schema. Legacy public transition cannot update enrolled orders; later HTTP integration must map commands deliberately.

### Claude handoff

1. Reconcile against current main; preserve concurrent design work.
2. Copy only this new folder into a feature branch. Do not edit runtime/server's recorded snapshot or API-reader hash-locked fixtures.
3. Run the new tests against current runtime plus existing relevant suites on Linux and Windows.
4. Review authority, financial contract, additive schema and rollback: do not blindly remove triggers/tables if enrolled orders exist. Back up before any future staging migration; restoring a consistent snapshot is the rollback path until a migration tool exists.
5. Commit author AND committer MenQ; no AI trailers. Open PR with actual checks and limitations. No production deploy implied.

## Հայերեն

Սա իրական պատվերների հոսքի backend-ի առաջին հավելումն է, ոչ ամբողջ 3-րդ փուլի ավարտ կամ deploy։ Հիմքը՝ վերը նշված GitHub commit-ը։ Սերվերի, արտաքին ծառայությունների և ops_views.py-ի փոփոխություն չկա։

Օգտագործում է եղած orders/events-ը և intake-ը։ Հավելումը առանձին թղթապանակում է, սերվերի գրանցված պատճենը չի վերագրվում։ Միայն NEW և հստակ test boolean ունեցող պատվերն է ընդունվում նոր հոսք։ Պատմական վիճակ չի հորինվում։

Պատվերի տերը dispatcher-ն է։ Partner-ը միայն հաղորդում է. իր ասած գինը կամ վճարումը հաստատված փաստ չի դառնում։ Dispatcher-ը գրանցում է հաճախորդի հաստատած գինը և դրա փոփոխությունը։ Commission-ը դրա 20%-ն է, գումարները՝ ամբողջ կոպեկներով։

Առկա են առաջընթացի, ETA-ի, զանգի, աշխատանքի ավարտի ու վճարման հավաստման, commission-ի հաշվարկի/մարման, feedback-ի և խնդրի հրամանները։ Գործն ավարտված է ≠ պատվերը փակված է։ Փակումը պահանջում է բոլոր ստուգումները։ Կան կրկնակի հրամանի պաշտպանություն, revision, transaction և audit։

Տեղական Linux ստուգում՝ 18 նոր և 7 եղած runtime թեստն անցել են։ Windows, HTTP/UI, կայքի կապը, LIVE, cancellations/refunds և profit հաշվարկը դեռ պատրաստ չեն։ Principal-ը պետք է տա վստահելի authenticated adapter-ը. body-ից վերցնել չի կարելի։ Ապացույցները մարդու հավաստումներ են, ոչ իրական կտրոնի ավտոմատ ստուգում։

Քլոդը համադրում է ընթացիկ main-ի հետ, նոր թղթապանակը դնում առանձին ճյուղում, կատարում Linux/Windows ստուգումները և MenQ author/committer-ով բացում PR։ Սերվերում տեղադրելու թույլտվություն այս փաթեթը չի տալիս։

## v0.1.1 additions / Հավելումներ

- `get()` includes a closure checklist with machine-readable missing conditions. It is informational, not a new approval.
- `history()` returns ordered audit events, retaining original/repriced amounts and partner attestations. Internal private read only; an HTTP adapter must enforce access.
- `summary(test=False)` excludes enrolled test records by default. It reports cumulative paid/closed counts and commission evidence totals in kopecks. These are dispatcher-attested customer payments, NOT KRYUK revenue or profit. Costs/profit/source attribution stay UNKNOWN. No time-window KPI is claimed. Unmanaged records are excluded and counted.
- Audit-failure rollback, concurrent same-command replay, test/real separation and tiny rounded commission tested. Zero due can be recorded with explicit evidence.

Հայերեն. Փակման checklist-ը ցույց է տալիս պակասող պայմանները։ History-ն պահում է պատվերի հին ու նոր փաստերը։ Հաշվետվությունը լռելյայն բացառում է test պատվերները, ցույց է տալիս վճարված/փակված քանակներն ու commission-ի գրանցված թվերը. դրանք շահույթ կամ KRYUK հասույթ չեն։ Ծախսը, շահույթը և աղբյուրային վերագրումը UNKNOWN են։ Սրանք ներքին API-ներ են, ոչ հրապարակային endpoint։

This package supersedes v0.1; integrate v0.1.1 once, not both. Base files are unchanged. This is still a backend increment, not a deployed system or completed roadmap phase.
