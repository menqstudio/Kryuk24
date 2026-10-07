# Request Flow v0.1 / Դիմումների հոսք v0.1

## EN

Five internal backend deliverables for roadmap phase 3, not five completed roadmap items:

1. Actual inquiry ledger for PHONE, WHATSAPP, TELEGRAM, SITE_FORM, OTHER and UNKNOWN. A click is not automatically imported as an inquiry. An inquiry creates no order.
2. Exact source-reference replay protection. Channel + reference + explicit test boolean identify the event; changed facts are rejected. No fuzzy contact/time matching. References must come from the trusted adapter; do not pass visitor-controlled identifiers directly.
3. Dispatcher-owned terminal dispositions: DECLINED, NO_RESPONSE, OUT_OF_SCOPE, DUPLICATE with evidence. Duplicate requires an existing request of the same owner and test class. Outcomes are immutable; no automatic reopening is provided.
4. Recoverable request-to-order conversion using existing Runtime.intake and OrderFlow.adopt. Required contact, pickup, destination, vehicle and evidence. Frozen CONVERTING intent precedes intake. Exact original revision/payload retry resumes safely after a crash, with one order/notification task, and links the managed order. CONVERTING is visible and cannot be declined. This is a recoverable multi-transaction workflow, not an atomic cross-service transaction. Intermediate NEW unmanaged order can exist until retry; no background worker or live HTTP routes are enabled. Existing legacy adapters MUST NOT mutate those intermediate orders; quarantine them until CONVERTED. A legacy mutation preventing enrolment requires operator reconciliation, never blind retry/new intake.
5. Owner-scoped read/history and cumulative test/real summaries. Conversion means order created, not completed or paid. Missing profit remains UNKNOWN.

Dependency: GPT Order Flow v0.1.1 must be integrated first. This package adds only runtime/request_flow; it does not supersede the Order Flow package. Runtime.py current GitHub main blob checked: 14656bee5236132299cbfae590a354f8a500cfc7, matching the prior pinned base f7c50c722a44460e55e131288295d6c64de60fbe. Reconcile current main during integration. No server snapshot, fixture, dashboard or site edits.

Principal must come from trusted authenticated role resolution, never JSON body. Internal methods do not supply authentication. Receive evidence is dispatcher attestation, not automated proof. Reads include private contact/address information: do not expose without access controls. Constructor creates additive schema: do not instantiate on a production DB for inspection. No send, payment, live connector, timetable or deployment is implemented/authorized. Roadmap item 9's operational dependencies and Armen acceptance remain open.

Local Linux: 10 request tests + 18 Order Flow tests + 7 existing runtime tests passed. Cases include concurrent conversion, exact replay, crash after intake, crash after adopt, audit rollback, owner denial, changed payload, duplicate mismatch. Windows untested here.

Integration tests:

```bash
PYTHONPATH=runtime/server:runtime/order_flow python -m unittest discover -s runtime/request_flow -v
PYTHONPATH=runtime/server python -m unittest discover -s runtime/order_flow -v
```

PowerShell: set `$env:PYTHONPATH='runtime/server;runtime/order_flow'` for request tests. Run existing relevant suites too. Separate feature branch/PR; author AND committer MenQ. CI Linux and Windows. Do not alter Claude's concurrent design or Order Flow PR. Do not deploy. Before any future schema install: consistent DB backup; rollback by restoring the whole consistent snapshot, not deleting tables containing records.

## HY

Հաջորդ հինգ backend գործն են, ոչ roadmap-ի հինգ փակված փուլ կամ կետ։

1. Իրական դիմումը գրանցվում է առանձին՝ զանգ, WhatsApp, Telegram, կայքի ձև և այլ/անհայտ աղբյուր։ Սեղմումը ինքնաբերաբար դիմում չի դառնում, դիմումը՝ պատվեր։
2. Նույն աղբյուրի նույն հաղորդումը կրկնակի չի ստեղծվում։ Փոխված փաստերով նույն հղումը մերժվում է։ Test/real տվյալները չեն խառնվում. հեռախոսով կամ ժամով ենթադրյալ նույնացում չկա։
3. Dispatcher-ը գրանցում է չդարձած պատվերի ելքն ու ապացույցը՝ մերժված, չպատասխանած, շրջանակից դուրս կամ հաստատված կրկնօրինակ։ Այլ տիրոջ/այլ test դասի դիմումը կրկնօրինակ հայտարարել չի կարելի։
4. Դիմումը փոխարկվում է եղած Runtime/Order Flow-ով՝ ամբողջ պարտադիր տվյալներով։ Ընդհատման դեպքում նույն հրամանը շարունակում է, նոր պատվեր չի ստեղծում։ Մինչև ավարտը CONVERTING է. հին adapter-ները միջանկյալ պատվերին չպետք է դիպչեն։ Սա մի քանի վերականգնելի transaction է, ոչ մեկ ընդհանուր transaction։ Ֆոնային վերականգնող գործարկում չկա։
5. Տիրոջ համար առանձին ընթերցում, պատմություն և test/real ամփոփում։ Փոխարկված լինելը վճարված կամ ավարտված լինել չի նշանակում, շահույթը մնում է UNKNOWN։

Կախվածություն՝ նախ ինտեգրել Order Flow v0.1.1-ը։ Principal-ը տալիս է վստահելի authenticated adapter-ը. HTTP/auth, UI, կենդանի աղբյուրների կապ, LIVE կամ deploy դեռ չկա։ GitHub main-ի runtime.py-ն համեմատված է։ Տեղական Linux՝ բոլոր 35 թեստն անցել են, Windows-ը դեռ չստուգված է։

Քլոդը նոր թղթապանակը ինտեգրում է առանձին PR-ով, համադրում ընթացիկ main-ի հետ, անում Linux/Windows CI և MenQ author/committer-ով commit։ Սա սերվերում տեղադրելու թույլտվություն կամ 3-րդ փուլի ավարտ չէ։
