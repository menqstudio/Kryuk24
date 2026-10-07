# Simulation Executor v0.1 / Փորձնական executor v0.1

## EN

Five internal deliverables for the executor dependency track:

1. Action allowlist at approval and adapter boundaries; exact approved account/target/payload/assets/amount binding; real `test=false` envelopes rejected before reservation.
2. ApprovalStore v0.1 integration: only a new valid reservation can attempt an action. Stale/expired/rejected/revoked/pending approval does not execute. Same actor/key replay reconciles only.
3. Durable execution journal and audit written before adapter invocation. Status starts UNKNOWN so a crash cannot turn uncertainty into a repeat permission. Another actor/key cannot take over. Adapter exceptions are recorded without potentially secret raw error text.
4. Reconciliation by execution key. A found result is verified; a missing or mismatched result remains UNKNOWN with no automatic retry. Reservation-without-journal gap is fail-closed: no new attempt. Restart can reconcile an effect whose response or verification commit was lost.
5. Durable simulated-service readback rather than trusting perform's response. Success is explicitly SIMULATION_VERIFIED with SIMULATED_ONLY trust; it is never real external evidence.

This increment contains ONLY SimulationExecutor/SimulationAdapter, not a real external executor. Adapter uses a separate local SQLite effect table to imitate an external service; no network or external SDK exists. `external_execution_enabled=false` always. This demonstrates recovery/control paths, not hosted API correctness or phase 5 acceptance. No public/financial action occurred or is authorised by delivery.

Dependency: Action Approval v0.1 exact package. Does not need Order Flow or Request Flow. Place this new folder at runtime/action_executor. Existing files remain unchanged. Test command:

```bash
PYTHONPATH=runtime/server:runtime/action_approval python -m unittest discover -s runtime/action_executor -v
PYTHONPATH=runtime/server python -m unittest discover -s runtime/action_approval -v
```

PowerShell: `$env:PYTHONPATH='runtime/server;runtime/action_approval'`; then run the executor unittest command. Verified Linux: 11 executor + 11 approval tests pass. Windows UNVERIFIED here.

Trust/configuration requirements inherited from ApprovalStore: principal comes from authenticated trusted role resolution; current_inputs must come from actual trusted current snapshots; action configuration is not approval. No auth/HTTP/UI, live asset-byte checking, execution credentials, spend/tax checks, scheduled workers or external receipt verification is implemented. Do not expose it as a production route. Do not replace SimulationAdapter with a network adapter by removing the test flag check; a real adapter requires its own explicitly reviewed protocol, identity checks, external readback, idempotency/reconciliation capability and authorised trial.

Reserve and execution journal use separate transactions. If journal creation fails AFTER reservation, approval stays consumed/RESERVED. Recovery reports UNKNOWN and intentionally does not execute even if local fake effect lookup is empty. This favors safety over automatic availability. Operator reconciliation/new exact approval, if warranted, must be separately designed; this module never resets the reservation.

Caller execution keys must uniquely identify the action globally. Existing collision is rejected; a race on the same key across different drafts can leave the losing approval RESERVED without a journal and requires reconciliation. Use stable draft-specific keys in the trusted adapter. Never use an unscoped visitor-controlled key. Do not reconcile a still-running action to infer that an absent response proves no effect. A successful replay returns existing evidence and grants no new action; report/inspect remains accessible to the configured approver.

Constructor creates additive simulation/journal schema. No production DB was accessed. Future installation needs consistent backup and migration review; rollback is full consistent snapshot restore, not deletion of approval/execution tables. Runtime/server remains the recorded read-only snapshot; ops_views.py and API fixtures remain unchanged.

Claude handoff: separate branch/PR after Action Approval dependency, add new suite to Linux and Windows CI, run relevant existing suites on current main; author=committer MenQ. State actual results and limitations in PR. No VPS install, sending, publishing, payments, timer or live adapter trial. This does not close roadmap phase 5.

## HY

Հաջորդ հինգը executor-ի կառավարման փորձնական հիմքն են․

1. Թույլատրելի գործողությունների ցանկ և հաստատված ամբողջ նկարագրության ստուգում։ Իրական (`test=false`) գործողությունները մերժվում են։
2. Կապ Approval v0.1-ին՝ միայն նոր, վավեր մեկանգամյա վերցնումը կարող է փորձ կատարել։ Հնացած/ժամկետանց/մերժված/հետկանչված հաստատումով փորձ չկա։
3. Գործարկման մատյան և audit՝ գործողությունից առաջ։ Ընդհատումը թողնում է UNKNOWN, ոչ նոր թույլտվություն։
4. Անորոշ արդյունքի reconciliation՝ առանց կույր կրկնելու։ Կորած պատասխանից կամ restart-ից հետո գտնված արդյունքը ստուգվում է։ Չգտնվածը չի նշանակում «չի կատարվել» և կրկնելու իրավունք չի տալիս։
5. Արդյունքի անկախ ընթերցում տեղական simulation ծառայության աղյուսակից։ Վիճակը հստակ SIMULATION_VERIFIED է, վստահությունը՝ SIMULATED_ONLY։

Սա իրական արտաքին executor չէ։ Միայն տեղական simulation է. ցանց, հրապարակում, նամակի ուղարկում, վճարում կամ իրական ապացույց չկա։ Դրանով roadmap-ի 5-րդ փուլը չի փակվում։

Կախվածություն՝ նախ Action Approval v0.1։ Նոր թղթապանակն է runtime/action_executor։ Linux-ում 11 նոր և Approval-ի 11 թեստերը նորից անցել են։ Windows-ը դեռ չստուգված է։

Հաստատման վերցնումն ու մատյանի գրանցումը տարբեր transaction-ներ են։ Եթե դրանց արանքում խափանում է լինում, հաստատումը մնում է վերցված, արդյունքը UNKNOWN. ավտոմատ կրկնում չկա։ Բանալին պետք է լինի կայուն և կոնկրետ սևագրին հատուկ։ Principal-ը և ընթացիկ փաստերը տալիս է վստահելի adapter-ը, ոչ request body-ն կամ AI-ն։

Իրական adapter-ը առանձին contract, փորձ և թույլտվություն է պահանջում. simulation-ի test սահմանը հանելով LIVE դարձնել չի կարելի։ HTTP/auth/UI, իրական նյութերի բայթերի ստուգում, credential-ներ և արտաքին ապացույցների ստուգում դեռ չկա։

Քլոդը առանձին PR է բացում, Linux/Windows CI է ավելացնում և MenQ author/committer-ով commit անում։ Սերվերում չի տեղադրում և արտաքին գործողություն չի կատարում։
