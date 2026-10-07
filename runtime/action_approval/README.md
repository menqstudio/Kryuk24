# Action Approval v0.1 / Գործողության հաստատում v0.1

## EN

Five implementation deliverables for roadmap phase 4:

1. Exact immutable action envelope: action, account, target, payload, asset IDs/content SHA256, explicit amount (RUB integer kopecks or null), nonempty input fingerprint map, timezone-aware expiry and explicit test marker.
2. Canonical bounded JSON and SHA256; draft replay key bound to envelope and preparer. Floats, NaN and unsupported objects are rejected. Editing creates a new draft; previous approval cannot transfer.
3. Explicit APPROVED/REJECTED decision by configured trusted approver actor with APPROVER role, expected digest and evidence. PREPARER/EXECUTOR roles cannot approve. Revocation is possible before reservation only.
4. Input fingerprints and expiry checked both at approval and first reservation. Changed inputs produce terminal STALE; deadline reached produces EXPIRED. The report staleness finding in runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md informs this contract. It does not patch ops_work.py or alter/revoke any existing report.
5. Atomic once-only reservation and audit. Concurrent claims yield one new reservation. Exact claimant/key replay only says RESERVED, new_reservation=false, external result UNKNOWN. Another claimant/key fails. A crash after reservation requires reconciliation, not another execution. Audit failure rolls back status/reservation.

This is an INTERNAL contract module, not a completed phase, authenticated interface or executor. No external action occurred. Default action allowlist is empty (deny all); test fixtures explicitly enable SAMPLE REPORT_SEND. Configuring an action type is a technical constraint, not Gev's approval of any particular action. No payment/financial transfer adapter exists. The amount field alone does not validate taxes, spend limits or financial feasibility.

Trust boundary: ApprovalPrincipal must be constructed by a trusted authenticated adapter; the actor/role must NEVER come from user JSON, an AI assertion or external content. approver_actor is trusted immutable deployment configuration, bound to Gev's actual account by that adapter. The module does not implement login, consent UI, CSRF, origin checks, secret stores or privilege isolation from direct SQLite access. Do not expose methods until those controls exist.

Freshness boundary: current_inputs is supplied by trusted runtime code using actual current dependency snapshots, not executor/AI input. Fingerprints must include every dependency (task revisions/status, observations and their versions, asset bytes/account configuration as applicable). Resolve stable asset IDs and verify bytes against approved hashes. A fingerprint of an incomplete snapshot does not prove freshness. The external executor must recheck current inputs, allowlist, target/account identity and asset hashes as close to action as possible; this standalone module cannot prevent a separate external system changing after reservation. RESERVED is not success or an externally issued capability.

An expired/revoked/stale/rejected/pending draft cannot get a NEW reservation. Existing reservation replay intentionally remains inspectable after expiry for reconciliation and gives no new grant. Revocation AFTER reservation is refused because external outcome may be uncertain; stopping/reconciling an in-flight action belongs to executor contract, not silent reset. No timeout resets RESERVED. No execution result table/verification/retry/schedule is implemented here.

Compatibility: adds only runtime/action_approval and namespaced tables/trigger; imports existing runtime encode/now/db. No server snapshot, ops_views.py, site, API-reader fixtures, Request Flow or Order Flow files changed. Current-source references read from GitHub main: report finding blob e008a211e09c846919736c7b15b13839fc924c03; runtime.py blob 14656bee5236132299cbfae590a354f8a500cfc7 previously verified unchanged on main. Reconcile current main before integration.

Local Linux: 11 approval tests pass, covering exact target/payload/assets/amount/test/expiry binding, owner roles, stale inputs, equality at expiry boundary, rejection/revocation, concurrent one-time reservation, restart reconciliation and audit rollback. Windows untested. Existing modules unchanged; their preceding 35 passing tests are earlier evidence, not rerun in this package.

Claude: separate branch/PR, copy runtime/action_approval only, add Linux/Windows CI:

```bash
PYTHONPATH=runtime/server python -m unittest discover -s runtime/action_approval -v
```

PowerShell: `$env:PYTHONPATH='runtime/server'`, then same unittest command. Run relevant existing suites on current main. Commit author=committer=MenQ. No deploy or HTTP/UI integration implied. Constructor creates schema; do not instantiate on a production DB just to inspect. Future migration requires backup; restoring the whole consistent snapshot is rollback, never blindly deleting populated approval tables.

## HY

Հաջորդ հինգ գործերը՝ կոնկրետ գործողության հաստատման ներքին contract-ի համար։

1. Անփոփոխ նկարագրություն՝ գործողություն, հաշիվ, հասցեատեր/թիրախ, ամբողջ բովանդակություն, նյութերի hash-եր, գումար կամ null, ելակետային փաստերի fingerprint, ժամկետ և test դրոշ։
2. Բովանդակության SHA256 և նույն սևագրի կրկնակի գրանցման պաշտպանություն։ Փոխված բովանդակությունը պահանջում է նոր սևագիր ու նոր հաստատում։
3. Միայն վստահելի adapter-ով նույնացված Գևի հաշիվը կարող է հաստատել/մերժել։ Նախապատրաստողն ու executor-ը չեն կարող հաստատել։ Մինչև վերցնելը հաստատումը հետ կանչել կարելի է։
4. Հաստատելու և առաջին անգամ վերցնելու պահին ստուգվում են փաստերի fingerprint-ն ու ժամկետը։ Փոխված փաստեր՝ STALE, հասած ժամկետ՝ EXPIRED։ Եղած report-ի բագի նկարագրությունը կարդացված է, բայց ops_work.py-ն այս փաթեթով չի ուղղվում և գործող report-ին չենք դիպչում։
5. Մեկանգամյա վերցնում և transaction-ով պատմություն։ Զուգահեռ հրամաններից միայն մեկն է նոր վերցնում ստանում։ Կրկնելիս նոր գործողության թույլտվություն չի տրվում. արտաքին արդյունքը UNKNOWN է, պետք է reconciliation։

Սա դեռ ներքին մոդուլ է, ոչ աշխատող approval էջ, HTTP/auth կամ executor։ Թույլատրելի գործողությունների ցանկը լռելյայն դատարկ է։ Թեստերը SAMPLE տվյալներով են։ Իրական ուղարկում, հրապարակում, վճարում կամ սերվերի փոփոխություն չի կատարվել։

Principal-ի actor/role-ը body-ից կամ AI-ի խոսքից վերցնել չի կարելի։ Գևի հաշվի կապը հաստատում է վստահելի authenticated adapter-ը։ Fingerprint-ները տալիս է runtime-ը՝ իրական ընթացիկ բոլոր կախվածություններից, ոչ AI-ն։ Առանց այդ ինտեգրման հնարավոր չէ պնդել, որ գործող report-ի հնանալու խնդիրը փակված է։ Արտաքին գործողության պահի վերահսկումը executor-ի գործն է։

Վերցված գործողությունը չի «ազատվում» ժամկետով ու երկրորդ անգամ չի գործարկվում կուրորեն։ Հետ կանչելն էլ վերցնելուց հետո այս contract-ը չի տալիս, քանի որ արտաքին արդյունքը կարող է անորոշ լինել։

Linux-ում 11 նոր թեստն անցել են։ Windows-ը դեռ չստուգված է։ Քլոդը նոր թղթապանակը ինտեգրում է առանձին PR-ով, անում Linux/Windows CI, MenQ author/committer-ով commit։ Դեպլոյը, dashboard-ի կապը և 4-րդ փուլի փակումը այս փաթեթի մաս չեն։
