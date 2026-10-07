# Business Service v0.1 / Միասնական backend v0.1

## EN

Five connected backend deliverables, not five additional completed roadmap phases:

1. A single application facade over Request Flow and Order Flow: intake, disposition, conversion, order commands and audit. It uses the existing modules and adds no schema.
2. Role/association checks for every exposed method. Dispatcher sees/writes only owned requests/orders; assigned partner only sees a limited projection and reports; configured Gev OWNER reads business state but OWNER alone grants no dispatcher accounting writes. Trusted PREPARER/EXECUTOR roles are separate from Gev's approval role. Full order history is not exposed to partner.
3. Read-only owner board with compact request/order cards, closure checklist, incomplete conversions and test/real separation. Board omits contact/address/evidence/payload fields. Detail reads are private and must be authenticated. No revenue/profit invention: profit UNKNOWN.
4. Connected proposal -> owner decision -> SimulationExecutor -> owner approval/execution audit. Current fingerprints come from a configured trusted provider, not a caller's supplied current_inputs. Stale proposal or stale approval cannot start simulation.
5. End-to-end integration tests across all four modules, including request -> order -> delivery -> payment -> 20% commission -> feedback -> Close and draft -> approval -> simulation -> readback. Delivered is not Closed; partner report does not change dispatcher price.

Dependencies (exact package revisions): Order Flow v0.1.1, Request Flow v0.1, Action Approval v0.1, Action Executor v0.1 (simulation-only). Nothing here supersedes or changes those packages. This new folder is runtime/business_service. Current GitHub PR #7 checked open at head 245a312018b760e0f60d676061cbd7a0f69a834c, base f7c50c722a44460e55e131288295d6c64de60fbe; do not assume a merge occurred. Reconcile any subsequent Claude fixes before integrating and rerun the combined tests.

IMPORTANT: Identity is a trusted internal object, not login/authentication or a verified account by itself. Never build its actor/roles directly from HTTP body or AI input. An authenticated adapter must resolve identities/roles from trusted account/session storage. No HTTP/UI/CSRF/origin/session management is provided. This is NOT a completed owner cabinet, site connection, real operational trial or deploy. ops_views.py and site are untouched.

inputs_provider is trusted configuration supplied by the integrator. It must read a complete consistent dependency snapshot from authoritative state. The SAMPLE test callback does not constitute installed ops_work.py integration or fix the existing report staleness issue. Asset-byte checking, real external adapter and real effect verification remain absent. `execute_simulation` rejects real actions through the underlying executor. Reading/recording internal test=False ledger entries is supported but no real entry or production DB was touched.

One runtime/database per business realm. Configuration requires owner identity equals approval approver, and the executor uses the same ApprovalStore. Owner board uses one SQLite snapshot for counts/cards. No multi-tenant isolation claim. Lower-level modules remain internal and must not be separately exposed to bypass facade checks. Callback providers are code, not external-content policies.

Local Linux: 8 new integration tests + all preceding 57 tests = 65 PASS in a combined run. Windows UNVERIFIED. Prior local suites: runtime 7, Order Flow 18, Request Flow 10, Approval 11, Executor 11. This is not a claim about GitHub CI or VPS.

```bash
PYTHONPATH=runtime/server:runtime/order_flow:runtime/request_flow:runtime/action_approval:runtime/action_executor python -m unittest discover -s runtime/business_service -v
```

Windows PowerShell: set the same PYTHONPATH entries separated by semicolons. Run every dependency suite as well. This folder needs no new runtime DB migrations, but its underlying modules create schema if instantiated; never point constructors at production for inspection.

## Claude handoff / merge sequence

1. Verify ZIP and file manifest. Copy this folder only into a separate feature PR based on all four dependency branches or their merged versions. Preserve design work. Author AND committer MenQ.
2. Add business_service tests to Linux/Windows jobs with all dependency paths. Keep existing required suites. Report actual head SHA, CI result, dependency graph and limitations. Do not mark phases complete from a green unit suite.
3. Wait for green CI/review on the exact head of every PR. Order Flow first; Request Flow after Order Flow. Approval before Executor. Business Service after all four. Repo presentation is independent of this graph and follows its own visual acceptance.
4. As earlier PRs merge, update/rebase dependent branches onto current main, resolve changes and rerun CI on NEW head SHAs before merging them. A green older head is insufficient. Preserve MenQ author/committer when rebasing/merging, and existing two-parent merge policy where applicable. Confirm resulting main CI after merges.
5. No VPS deployment, LIVE enablement, external action or scheduled run. Operational integration needs a separate explicit scope and acceptance. Keep a record of merged SHAs/tests and remaining boundaries.

Dependency graph:

- Order Flow -> Request Flow
- Action Approval -> Simulation Executor
- Order Flow + Request Flow + Action Approval + Simulation Executor -> Business Service

## HY

Հաջորդ հինգ գործը եղած մասերի կապն է, ոչ նոր հինգ փակված փուլ․

1. Միասնական մուտք դիմումների և պատվերների համար՝ եղած մոդուլներով։
2. Դերերի և պատկանելության սահմաններ։ Dispatcher-ը իր պատվերի տերն է, partner-ը միայն սահմանափակ տեսք ունի և հաղորդում է, Գևի OWNER դերը պատվերի հաշվառման փաստերը չի փոխում։
3. Տիրոջ միայն կարդալու ամփոփում՝ դիմումներ, պատվերներ, փակման պակասող պայմաններ, չավարտված փոխարկումներ, test/real առանձին։ Կոնտակտները, հասցեները և ապացույցները ընդհանուր board-ում չեն երևում։ Շահույթը UNKNOWN է։
4. Սևագիր -> Գևի որոշում -> simulation executor -> audit կապ։ Ընթացիկ fingerprint-ը տալիս է վստահելի provider-ը, ոչ հրամանի body-ն։
5. Ամբողջ շղթայի թեստեր՝ մինչև Close և approval-ից մինչև simulation-ի ստուգված արդյունք։

Սա ներքին backend է. HTTP, login/authentication, UI, իրական կայքի/նամակի կապ կամ կենդանի գործարկում չկա։ Identity-ը վստահելի adapter-ից պետք է գա. body-ից/AI-ի խոսքից դեր վերցնել չի կարելի։ Գործող report-ի staleness-ը դեռ փակված չէ, քանի դեռ provider-ը իրական runtime-ի ամբողջական կախվածություններից չի կարդում։

Կախվածությունները՝ Order Flow v0.1.1, Request Flow v0.1, Approval v0.1, simulation Executor v0.1։ Նախորդ ֆայլերը չեն փոխվել։ Linux-ում բոլոր փաթեթների 65 թեստերը միասին անցել են, դրանցից 8-ը նոր ինտեգրման թեստերն են։ Windows-ը դեռ չստուգված է։

Քլոդը դնում է առանձին PR-ով, Linux/Windows CI է ավելացնում։ Merge հերթը՝ Order Flow -> Request Flow, Approval -> Executor, հետո Business Service։ Repo-ի դիզայնը անկախ է։ Ամեն նախորդ merge-ից հետո կախված ճյուղերը համադրվում են նոր main-ի հետ, նոր head-ի CI-ն նորից կանաչ է պահանջվում։ Վերջում main-ի CI-ն ստուգվում է։ Բոլոր commit/merge-երի author=committer=MenQ։

Սերվերի deploy, LIVE, արտաքին գործողություն կամ timer այս փաթեթով չի արվում։
