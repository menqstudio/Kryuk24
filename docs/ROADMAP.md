# KRYUK24: roadmap

The approved roadmap (scope, phases, definition of done) comes first; then the dated deadlines and one prioritised queue. Order: dated items first, then GPT's order of work of 07.10.2026 (credentials → API reader → real requests and orders → mailbox and approval contract → executor → reports; the proxy separately), then everything that waits for a person. An item moves only when its dependency is met. Status of each item is in [`CURRENT_STATE.md`](CURRENT_STATE.md).

Owners: **Gev**, **Armen** (owner of the business), **Claude**, **GPT**, **Yandex** (external).

## Approved roadmap: scope, phases, definition of done

Approved by Gev on 07.10.2026 and published as [issue #3](https://github.com/menqstudio/Kryuk24/issues/3). This is the baseline of the product: what is being built, in which phases, and what "done" means. **The approval records scope. It authorises no execution, schedule, payment or model trial, and it is not evidence that a planned component exists.** What exists today is in [`CURRENT_STATE.md`](CURRENT_STATE.md); the dated deadlines and the detailed task queue follow below and stay the working list.

### Mission

Build the business operating assistant (Bro) for KRYUK24 in Moscow and the Moscow region.

Cycle: inspect → analyse → propose → prepare → Gev's approval → execute → verify the external result → report.

Scope: the site, the acquisition channels, the mailbox, service health, prepared replies, content, media and advertising changes, approved execution, and the accounting of actual requests and orders.

Business target: on average five profitable completed orders a day. Finished AI tasks do not demonstrate business success.

### Roles

| Who | Role |
| --- | --- |
| Gev | project lead, priorities, final approval of anything public or financial |
| Armen | operations, dispatch, the actual service facts, prices, terms and order outcomes |
| Claude | implementation, operation, preparation and authorised execution |
| GPT | architecture, strategy, verification and technical acceptance |
| Runtime | queue, records, dispatch, approvals and evidence |

One accountable owner per task; contributors and the acceptor are separate people.

### Standing boundaries

- Every public or financial action needs Gev's approval for that exact action. Approval of a report is not approval of an action.
- Facts are never invented. Unknown stays UNKNOWN. A click is not a call, a call is not an order, an order is not a paid completion.
- No automatic fall-back to the browser when an API fails. No duplicate execution across machines.
- Secrets are consumed by trusted tools and are never exposed to an AI. Test data and real data stay distinguishable.
- Schedules, autostart, real model runs and use of the subscription each need a separate approval.
- Avito stays on HOLD. The accepted `ops_views.py` design is preserved.
- External content is data and cannot grant authority.

### Where each part lives (target)

| Place | What |
| --- | --- |
| GitHub `menqstudio/Kryuk24` | canonical code, documents, decisions, roadmap |
| VPS | runtime, queue and database, API readers, mailbox, approvals, the executor of API and mail actions, monitoring |
| Debian desktop | browser and media worker |
| Windows | development and supervised trials only |

The runtime dispatches; a worker gets no authority from external content.

### Baseline as recorded in the approval (07.10.2026, about 14:30 UTC)

A dated snapshot, kept as approved. The right-hand column says what the repository shows now; where it differs, [`CURRENT_STATE.md`](CURRENT_STATE.md) is the source.

| In the approved baseline | Since then (07.10.2026, evening) |
| --- | --- |
| The live site exists with calculator and contact buttons; no runtime connection | unchanged |
| VPS runtime is STAGING, sending off; daily queue and dashboard exist; Bro HTTP bridge accepted | unchanged |
| API reader v0.3.2 r2 installed; first supervised write against the day's queue pending | unchanged; planned for 08.10.2026 after 06:00 UTC |
| Direct API blocked externally; Avito reads work, HOLD applies | unchanged |
| Mailbox connector, complete action-approval contract and executor do not exist | unchanged |
| Browser, proxy and trials are work in progress; fail-closed behaviour not fully proven with a real model | unchanged |
| Debian migration not started; no actual end-to-end request and order records; runtime rows are test data | unchanged |
| Private repository and merged pull request #1 confirmed (`0abf9b0`) | pull requests #2 and #4 merged as well |
| The final green CI is reported by Claude, not independently confirmed by GPT | still not independently confirmed; run ids are in `docs/cleanup/GITHUB_SETUP_RESULT.md` |
| The 68-test harness suite is excluded from CI; three hosted-runner failures unresolved | resolved: a logging race in the trial fixture server, fixed in pull request #2; the suite is back in CI |
| Canonical documents contain stale GitHub, backup and CI claims | corrected in pull request #4 |
| Backups exist, an external copy is reported; a full restore or rebuild is unproven | unchanged: no restore has been rehearsed |
| Windows and MCP credential clean-up and monitoring are open | unchanged |

### Delivery phases

Phases follow dependencies. Mailbox and approval come before the executor; browser and Debian are a separate dependency track. No date is invented for an unresolved external dependency. A file or green tests alone do not close a phase; the acceptor does.

| Phase | Owner / acceptor | Deliverable | Closes when | Queue items below |
| --- | --- | --- | --- | --- |
| 0 Canonical state | Claude / GPT | Synchronise the current documents; tell snapshots from current facts; reconcile the scope of the final pull request; keep commit and CI evidence and the limits of coverage; refresh the inventory; publish this roadmap in EN and HY | the canonical documents agree with each other and every current claim has evidence or says UNKNOWN | 7, 8 |
| 1 Security and recovery | Claude / GPT | Trusted credential stores; verify, then remove the redundant Windows and MCP exposure; explicit AI environment and a canary; restrict the old backups without deleting; document and rehearse an isolated restore of database, configuration, code and credentials, and a server rebuild | access denials and permissions are verified and there is evidence of an actual recovery | 4, 5, 6 |
| 2 Reliable collection | Claude / GPT | First supervised API write after the planning and permission checks; three API tasks handled, the seven others untouched; repeat, partial and stale tests; the whole Yandex mailbox with stable cursors and no change of the Seen flag; Direct after the external grant, Avito after the HOLD is released | every needed source works, or is explicitly BLOCKED with a time and a source | 1, 11, 17, 2, 21 |
| 3 Real business flow | GPT (software) / Armen (operational acceptance) | Reuse the existing capture and order code; define request → order → completion → settlement; connect the site; record phone and messenger requests; keep test and real apart; the owner's cabinet: read-only view, a one-tap daily question that is not about money, upload of real photos. Who enters and who confirms accounting facts is defined separately | a real request can be followed to its final outcome and the missing facts are visible | 9, 19 |
| 4 Action approval | GPT (design) / Claude (implementation) | An approval is bound to the action, account, target, payload digest, assets, amount where relevant, expiry and the version of its inputs. Changed inputs mark the draft stale; the history is immutable | a stale, changed, rejected or wrong-target approval cannot execute | 10 |
| 5 Executor | Claude / GPT | Explicitly allowed action types; a valid approval; idempotency; reconciliation of an uncertain result before any retry; external verification; restart handling | one complete flow: draft → approval → execution → external verification → report | 12 |
| 6 Browser and Debian | Claude / GPT | Diagnose the three hosted-runner harness failures; adapt the harness to the proxy; an isolated trial browser; deny when policy, gate or proxy is missing or broken; hold results until the post-check; real trials only with a separate approval; a Linux harness and the required tests repeated on Debian | a bounded Debian worker takes assigned runtime jobs and returns verifiable evidence | 15, 16 |
| 7 Analysis, reporting, control | Claude / Gev | Prioritised findings and executable proposals; daily, weekly and monthly reports; actual requests, orders, conversion, revenue, cost and profit with UNKNOWN respected; deterministic monitoring of health, backup, hosting and certificates, and an approved alert channel | Gev sees outcomes, problems, proposals and pending approvals in one place | 13, 14 |
| 8 Controlled operation and v1.0 | Gev / GPT (technical acceptance) | Approve the LIVE conditions, frequencies, spend limits and stop rules; complete the acceptance tests; limited operation; close critical issues; record the accepted release and the operational owner | Gev's final acceptance | 18, 27 |

Where the phases stand, by evidence, on 07.10.2026: phase 0 is done on Claude's side with this document and waits for GPT's acceptance; in phase 6 the first deliverable (the three harness failures) is done; in phase 1 the off-disk copy exists and the step for the old backups is prepared, the rest is open; in phase 2 the API reader is installed and its first supervised write is pending. Phases 3, 4, 5, 7 and 8 have nothing built. Queue items 3 and 20 to 26 are day-to-day operation of the business and belong to no phase.

### v1.0: definition of done

All of these, together:

1. Approved scheduled collection without constant reliance on Gev's open desktop.
2. Actual requests and orders have a usable recording flow.
3. Concrete, evidence-based proposals and prepared materials.
4. A clear per-action approval interface for Gev.
5. No execution with a missing, stale, changed or expired approval.
6. One-time execution and a verified external outcome.
7. An uncertain outcome is recorded explicitly; no blind repeat.
8. The Debian browser and media worker operates within accepted boundaries.
9. Monitoring alerts, and a tested restore and recovery.
10. The GitHub documents are enough to understand, operate and continue the work without chat memory.
11. No critical open defect in the accepted scope.
12. Gev's final acceptance, which includes his visual acceptance of the repository presentation (see below).

**Acceptance window:** 14 consecutive days of the complete daily cycle, with failures logged and controlled, and Gev needed only for approvals and business decisions. Rare cases that the natural flow does not produce are exercised in controlled acceptance scenarios.

### Business success

Product acceptance and business success are separate. The first business target is an average of five profitable completed orders a day, measured over 30 consecutive days on recorded data. How a profitable order is calculated, and which costs it needs, is approved before the measurement starts. Technical readiness does not guarantee demand, and reaching the orders does not close security or recovery gaps.

### Out of scope for v1.0

Autonomous payments or financial commitments; unapproved public changes or advertising launches; unlimited integrations; production on Windows; unverified browser automation; a full fleet-dispatch ERP; a general BRO platform or other businesses.

### Repository presentation (design requirement, clarified by Gev on 07.10.2026)

**Scope: the visual presentation of this GitHub repository only.** An earlier reading that extended the request to a redesign of the runtime, the dashboard or the owner's cabinet is withdrawn; this section adds no runtime or dashboard work and authorises no change of code or deployment. The existing functional requirements of the product are untouched.

Rules: MenQ's applicable visual and documentation conventions (reference: the `menq-design-system-v1` branch of `menqstudio/MenQ-Standard`; read its canonical design and adoption sources first; the shared platform itself is locked and is not altered), with KRYUK24's own identity: the hook and the «КРЮК24 / ЭВАКУАТОР+» lockup from `brand/` and `tools/brand.py`; colours of the current generators: navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, white `#FFFFFF`; type: Roboto Condensed and Golos Text. `brand/README.md` still names the old `#111111`; it is reconciled with the dated navy decision and the current generators by source, not by silently mixing the two.

Deliverables:

1. An attractive, coherent root README with a branded SVG cover and a clear hierarchy.
2. Purposeful SVG visuals of the architecture, of the roadmap phases and of status, with no progress claim that evidence does not support.
3. Clear navigation to the canonical documents and to the detailed task queue.
4. The important text stays searchable, editable Markdown in EN and HY; images supplement it.
5. Verified rendering on GitHub: readable in light and dark, alt text, legible on a small screen, Armenian glyphs covered where needed. SVG files use no script, no `foreignObject` and no remotely loaded font.
6. Gev's visual acceptance of the repository presentation is part of the v1.0 acceptance.

It is queue item 27; nothing of it is built yet.

### How this is kept

| Document | Holds |
| --- | --- |
| `ROADMAP.md` | the approved scope, phases and definition of done, in EN and HY, and the working queue |
| `CURRENT_STATE.md` | current facts with evidence |
| `DECISIONS.md` | approvals and changes |
| Issues | executable tasks, each with one owner, dependencies, an acceptance criterion and evidence |

## Deadlines

| Date | What | Owner |
| --- | --- | --- |
| 08.10.2026, after 06:00 UTC (10:00 Yerevan) | Step 11 of the API reader install | Claude |
| before 10.10.2026 | One answer from Armen about Avito prolongation (Claude's proposal for the timing) | Gev asks Armen |
| 11.10.2026 | Avito: 24 listings expire, balance 0 ₽ | Gev (decision) |
| 13.10.2026 | Address confirmation video for the Yandex Business card | Armen |
| 13.10.2026 | Webmaster: check how many pages are in search | Claude |
| 14.10 and 15.10.2026 | Avito: 1 and then 20 more listings expire | Gev (decision) |
| 26.10.2026 | Avito: 1 listing expires | Gev (decision) |
| about 15.11.2026 (calculated) | Top up the hosting account | Gev / Armen |
| 30.12.2026 | Site SSL certificate (auto-renewal unverified) | hosting; check by Claude |
| 04.01.2027 | Certificate of `runtime.kryuk24.ru` | `certbot.timer`; check by Claude |
| 01.10.2027 | Domain kryuk24.ru (unverified after 01.10.2026) | Gev / Armen |

## The queue

| # | Item | Owner | Depends on | Next step |
| --- | --- | --- | --- | --- |
| 1 | **API reader, step 11:** one supervised write run | Claude | The 06:00 UTC planning of 08.10.2026 wrote the new day (ten tasks, three `API_READ`); `runtime.sqlite*` still shows group `kryuk-db` | Check the plan; install `kryuk-api-read.service`; one `systemctl start`; check three `DONE` with `MACHINE_OBSERVED`, seven others untouched, the dashboard opens. No timer. Then the factual report to GPT |
| 2 | **Avito before 11.10** (on hold) | Gev | Armen's answer: is prolongation in his cabinet free or paid, and who holds the autoload file | Claude's proposal: if free, permission for prolongation only, texts unchanged; if paid, decide after the figure. Until Gev's word nothing is changed or paid |
| 3 | **Address confirmation by 13.10** | Armen | Signage sizes question (his screenshot and voice messages of 06.10.2026, content unknown) → print → video | Gev finds out what is wrong with the sizes; Claude corrects the files; Armen films and sends the video |
| 4 | **Credentials clean-up on Windows** | Gev (decision on the store), Claude (preparation without values) | GPT fixed the placement; open is the store for the action and Avito secrets: the VPS or a separate Windows user | Claude prepares the move-and-verify plan, the list of everything that reads the user variables (`tools/api_setup/*.ps1`, `provision_from_windows.ps1`, `bro_api_reader.py --windows-user-store`, `.mcp.json`) and a canary check for each AI start. Gev starts the script; Claude and editor sessions are restarted |
| 5 | **Off-disk copy: done 07.10.2026** | Gev, Claude | none | External disk `E:\Kryuk24\backup_2026-10-07\`, every file compared by sha256. Left: decide how often it is refreshed |
| 6 | **Old database backups on the server into `0700 kryuk-run`** | Claude | A word for the server change (who gives it is not stated in the sources) | Move the `.sqlite` and `.json` backups into a subfolder; check the collector's group can no longer read them; nothing is deleted |
| 7 | **GitHub and Drive** | Gev (names the account and the Drive), Claude (import) | Item 5; Gev's answers on photo originals and personal data | Clean initial import into a separate private KRYUK24 repository; the old history stays in the bundle; each file moved to Drive is checked by sha256 against `docs/media-index.md` |
| 8 | **Clean-up: what is left after the push** | Claude | none | Published 07.10.2026 (`menqstudio/Kryuk24`, CI green on `main`). The harness self-test is back in CI (pull request #2: a logging race in the trial fixture server). Left: look at the recorded T1 and T2 attempts for the same race; read the 21 generator scripts one by one; verify the Drive copy file by file (needs Drive API access); decide on GitHub Pro for the protection of `main` (Gev) |
| 9 | **Real requests and orders** | Claude (reads the code, proposes), GPT (writes the owner's cabinet), Armen (uses it) | Item 1 closed | First read what the runtime already has (`orders`, `contact_interactions`, capture, the test flag); then a proposal; nothing built from zero. The owner's cabinet: read-only role, Russian page, one-tap question of the day without money, upload of real photos; STAGING only |
| 10 | **Approval contract and stale drafts** | Claude (draft for GPT), GPT (decision) | — | A design based on `runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`. The current draft is not changed or approved without Gev |
| 11 | **Mailbox for Bro** | Gev (creates the app), Claude (connector) | The Yandex app "KRYUK24 Bro Mail" with `mail:imap_full` and `mail:smtp`; IMAP switched on in the mailbox | After the app exists: the token by script, then a read check of the Business folder. Sending stays closed |
| 12 | **Executor of approved actions** | GPT (acceptance), Claude (build) | Items 4 and 10 | Nothing is written. Idempotency and reconciliation of an uncertain result are part of the first version |
| 13 | **Monitor without AI** (health, backup, hosting balance, certificate) | Claude | — for the preparation; Gev's separate yes for the schedule and the channel | Prepare the deterministic checks |
| 14 | **Reports**: daily in the runtime, weekly, monthly, budget | Claude | Item 9 (without recorded orders the numbers are UNKNOWN) | — |
| 15 | **Chrome proxy and trials** | GPT (decisions), Claude | GPT's answers on package v5.3: accept the proxy as the restriction layer; the form of trials with the proxy; stay on Windows until the first run with the proxy | Then: a harness adapted to the proxy, a separate `--user-data-dir` for the trial Chrome. T2 is rerun only on GPT's decision and Gev's new yes; T3 is not started |
| 16 | **Debian worker** | Gev (says when), Claude | Access to the machine; item 15 | Not started. A Linux variant of the harness; the Windows trials are run again there |
| 17 | **Yandex Direct API** | Yandex, then Claude | The answer to the full-access request (sent 07.10.2026, status "new"); it comes to the owner's mailbox | After the answer: `tools/api_setup/yandex_check.ps1 -Kind actions`. If Yandex asks for a real screenshot instead of the mock-up, make it once the Direct section of the dashboard exists |
| 18 | **Direct launch** (only after Gev's yes) | Gev (decisions), Claude (cabinet) | Item 9 (a working record of requests), VAT in the budget field, stop thresholds for the new budget, call tracking, competitor brand queries, account funded | Into the draft: maximum bid from the forecast, start date, goal values; narrow one broad phrase; quick links and clarifications. Checklist: `research/Direct_launch_package_2026-10-04.md` |
| 19 | **Answers from Armen** | Armen (Gev passes the questions) | — | Is "просто дернуть от 4 000" still valid (open contradiction 6); which districts he wants instead of the present city pages; is "50 machines" his own fleet or a partner network; where orders come from now and what one order costs (fuel, driver); the 20 questions of 02.10.2026; real photos of his equipment and jobs |
| 20 | **Reply to Sergey's review: closed by Gev's decision (07.10.2026)** | Claude | none | The read-back of the posted text stays UNVERIFIED; read it the next time a browser session in the working profile is open. It blocks nothing |
| 21 | **Two unopened letters** | Claude, on Gev's word | Mail access in the session | "We partly accepted the edits" (what was refused is UNKNOWN); the request to link the counter in Webmaster (confirming is a button and needs a separate yes) |
| 22 | **New photos and the card** | Gev (decision), Claude | — | Three processed frames of 07.10.2026: put them on the card and the site or not; the video of 07.10.2026 has not been watched. When real equipment photos exist, replace the eight generated ones in "Equipment" (deletion by Gev's hand) |
| 23 | **Site, next deploy** | Claude, Gev (yes) | — | `logo-dark.png` and `theme-color` in blue; correct the stale tag line in `site/README.md` |
| 24 | **WhatsApp Business on the phone** | Armen | — | Name "Kruk24" → "КРЮК24"; the map pin; greeting and "driving" messages. Texts: `offers/whatsapp_business_setup_2026-10-07.md`. Statuses from `offers/whatsapp_kit/`, one a day, chosen by a person |
| 25 | **Small items for Gev** | Gev | — | Approve or comment the new dashboard design (phone width and dark mode unverified); "previously open tabs" at start in the working profile; allow the mail site to the extension; switch the extension back on in the main profile after the trials; decide a separate Chrome profile for Bro; decide whether unattended runs may spend the subscription allowance; decide on the merged branches `navy-v32` and `v33`; a separate WhatsApp number for Claude and transcription of voice messages |
| 26 | **Small items for Claude** | Claude | — | Recheck the call-tracking numbers in Direct; check the status of the Business ad subscription and of the old Business landing; fix the encoding of the Direct error text in `yandex_check.ps1`; the daily check stays manual (first record in `docs/history/`) until one run without Gev's open session has passed with the right profile |
| 27 | **Repository presentation** (branded README, SVG cover, architecture / phases / status visuals, MenQ conventions with KRYUK24 identity) | Claude; acceptor Gev | Read the MenQ design sources first; reconcile `#111111` in `brand/README.md` with the navy decision | Nothing built. Repository presentation only: no dashboard, runtime or cabinet redesign. Verify rendering on GitHub in light and dark, on a small screen, with Armenian glyphs; SVG without script, `foreignObject` or remote fonts. Separate branch and pull request |

## Not in the queue

| Item | Why |
| --- | --- |
| A timer or autostart for Bro or for the API reader | Not created without Gev's separate yes |
| Avito changes, payments, prolongation | On hold by Gev |
| The Google form for the owner | Replaced by the owner's cabinet in the runtime; stays an unpublished draft |
| Call-log export from the owner's phone | Only with Armen's consent: the log holds his personal calls |
| New district pages | Wait for Armen's list (item 19) |

---

# Հայերեն

Նախ հաստատված ճանապարհային քարտեզը (շրջանակ, փուլեր, ավարտի սահմանում), հետո ժամկետներն ու մեկ առաջնահերթ հերթը։ Կարգը. նախ օր ունեցողները, հետո GPT-ի 07.10.2026-ի աշխատանքի հերթը (credential-ներ → API reader → իրական դիմումներ ու պատվերներ → փոստ ու approval contract → executor → հաշվետվություններ. proxy-ն առանձին), հետո էն ամենը, ինչ մարդու ա սպասում։ Կետը շարժվում ա միայն, երբ իրա կախվածությունը փակված ա։ Ամեն կետի վիճակը՝ [`CURRENT_STATE.md`](CURRENT_STATE.md)-ում։

Տերեր. **Գև**, **Արմեն** (բիզնեսի տերը), **Claude**, **GPT**, **Yandex** (դրսի)։

## Հաստատված ճանապարհային քարտեզ. շրջանակ, փուլեր, ավարտի սահմանում

Հաստատել ա Գևը 07.10.2026-ին, հրապարակված ա որպես [issue #3](https://github.com/menqstudio/Kryuk24/issues/3)։ Սա պրոդուկտի հիմքն ա. ինչ ենք կառուցում, ինչ փուլերով, ու ինչ ա նշանակում «ավարտված»։ **Հաստատումը գրանցում ա շրջանակը։ Ոչ մի կատարում, ժամանակացույց, վճարում կամ model-ի փորձ չի թույլատրում, ու ապացույց չի, որ պլանավորված բաղադրիչը կա։** Ինչ կա այսօր՝ [`CURRENT_STATE.md`](CURRENT_STATE.md)-ում. ժամկետներն ու մանրամասն հերթը ներքևում են ու մնում են աշխատանքային ցուցակը։

### Նպատակ

Կառուցել KRYUK24-ի բիզնեսի օպերացիոն օգնականը (Bro)՝ Մոսկվայի ու մարզի համար։

Շրջան. ստուգել → վերլուծել → առաջարկել → պատրաստել → Գևի հաստատում → կատարել → ստուգել արտաքին արդյունքը → հաշվետվություն։

Շրջանակ. կայքը, ներգրավման ալիքները, փոստարկղը, ծառայությունների վիճակը, պատրաստված պատասխանները, բովանդակությունը, նկարներն ու գովազդի փոփոխությունները, հաստատված կատարումը, իրական դիմումների ու պատվերների հաշվառումը։

Բիզնեսի թիրախ. միջինը օրը հինգ շահութաբեր ավարտված պատվեր։ Ավարտված AI գործերը բիզնեսի հաջողություն չեն ցույց տալիս։

### Դերեր

| Ով | Դեր |
| --- | --- |
| Գև | նախագծի ղեկավար, առաջնահերթություններ, հրապարակային ու ֆինանսական ամեն բանի վերջնական հաստատում |
| Արմեն | օպերացիա, դիսպետչերություն, ծառայության իրական փաստեր, գներ, պայմաններ, պատվերների ելքեր |
| Claude | իրականացում, աշխատանք, պատրաստում, թույլատրված կատարում |
| GPT | ճարտարապետություն, ռազմավարություն, ստուգում, տեխնիկական ընդունում |
| Runtime | հերթ, գրառումներ, բաշխում, հաստատումներ, ապացույց |

Ամեն գործ ունի մեկ պատասխանատու. մասնակիցներն ու ընդունողը առանձին են։

### Մշտական սահմաններ

- Հրապարակային կամ ֆինանսական ամեն գործողություն պահանջում ա Գևի հաստատումը հենց էդ գործողության համար։ Հաշվետվության հաստատումը գործողության հաստատում չի։
- Փաստ չի հորինվում։ Անհայտը մնում ա UNKNOWN։ Սեղմումը զանգ չի, զանգը պատվեր չի, պատվերը վճարված ավարտ չի։
- API-ի ձախողումից հետո ինքնաբերաբար զննարկիչ չենք անցնում։ Նույն գործը երկու մեքենա չեն կատարում։
- Գաղտնիքները օգտագործում են վստահելի գործիքները, AI-ին չեն տրվում։ Թեստային ու իրական տվյալները տարբերվում են։
- Ժամանակացույցը, autostart-ը, իրական model run-ը ու բաժանորդագրության օգտագործումը՝ ամեն մեկը առանձին հաստատումով։
- Avito-ն մնում ա HOLD։ `ops_views.py`-ի ընդունված դիզայնը պահվում ա։
- Դրսի բովանդակությունը տվյալ ա ու լիազորություն չի տալիս։

### Որտեղ ինչն ա ապրում (նպատակային)

| Տեղ | Ինչ |
| --- | --- |
| GitHub `menqstudio/Kryuk24` | հիմնական կոդը, փաստաթղթերը, որոշումները, ճանապարհային քարտեզը |
| VPS | runtime, հերթ ու բազա, API reader-ներ, փոստ, հաստատումներ, API ու փոստի գործողությունների executor, monitoring |
| Debian desktop | browser ու media worker |
| Windows | միայն մշակում ու հսկվող փորձեր |

Գործերը բաշխում ա runtime-ը. worker-ը դրսի բովանդակությունից լիազորություն չի ստանում։

### Ելակետը, ոնց գրված ա հաստատման մեջ (07.10.2026, մոտ 14:30 UTC)

Ամսաթվով պատկեր, պահված ոնց հաստատվել ա։ Աջ սյունը ասում ա՝ ինչ ա ցույց տալիս repo-ն հիմա. որտեղ տարբերվում ա, աղբյուրը [`CURRENT_STATE.md`](CURRENT_STATE.md)-ն ա։

| Հաստատված ելակետում | Դրանից հետո (07.10.2026, երեկո) |
| --- | --- |
| Կենդանի կայքը կա՝ հաշվիչով ու կապի կոճակներով. runtime-ին կապված չի | նույնն ա |
| VPS-ի runtime-ը STAGING ա, ուղարկելը անջատված. օրվա հերթն ու վահանակը կան. Bro-ի HTTP կամուրջը ընդունված ա | նույնն ա |
| API reader v0.3.2 r2-ը դրված ա. օրվա հերթի առաջին հսկվող գրող run-ը սպասվում ա | նույնն ա. նախատեսված ա 08.10.2026-ին, 06:00 UTC-ից հետո |
| Direct-ի API-ն դրսից փակ ա. Avito-ի կարդալը աշխատում ա, HOLD ա | նույնն ա |
| Փոստի connector, ամբողջական action approval ու executor չկան | նույնն ա |
| Զննարկիչը, proxy-ն ու փորձերը WIP են. fail-closed վարքը իրական model-ով լրիվ ապացուցված չի | նույնն ա |
| Debian-ի տեղափոխումը չի սկսվել. իրական դիմումների ու պատվերների ամբողջական գրառում չկա. runtime-ի տողերը թեստային են | նույնն ա |
| Փակ repo-ն ու pull request #1-ի merge-ը հաստատված են (`0abf9b0`) | merge արված են նաև pull request #2-ն ու #4-ը |
| Վերջնական կանաչ CI-ն Claude-ի հաղորդածն ա, GPT-ն անկախ չի հաստատել | դեռ անկախ հաստատված չի. գործարկումների համարները՝ `docs/cleanup/GITHUB_SETUP_RESULT.md`-ում |
| Harness-ի 68 թեստը CI-ից հանված ա. hosted runner-ի երեք ձախողումը չլուծված ա | լուծված ա. մատյանի մրցավազք trial-ի թեստային սերվերում, ուղղված pull request #2-ում. suite-ը նորից CI-ում ա |
| Հիմնական փաստաթղթերում GitHub-ի, պահուստի ու CI-ի հնացած պնդումներ կան | ուղղված են pull request #4-ում |
| Պահուստներ կան, արտաքին պատճենի մասին հաղորդված ա. ամբողջական restore կամ rebuild ապացուցված չի | նույնն ա. restore չի փորձվել |
| Windows-ի ու MCP-ի credential-ների մաքրումն ու monitoring-ը բաց են | նույնն ա |

### Փուլեր

Փուլերը գնում են կախվածություններով։ Փոստն ու հաստատումը executor-ից առաջ են. զննարկիչն ու Debian-ը առանձին կախվածության գիծ են։ Չլուծված դրսի կախվածության համար ամսաթիվ չի հորինվում։ Ֆայլը կամ կանաչ թեստը մենակ փուլ չի փակում. փակում ա ընդունողը։

| Փուլ | Պատասխանատու / ընդունող | Ինչ ա տրվում | Երբ ա փակվում | Հերթի կետեր |
| --- | --- | --- | --- | --- |
| 0 Հիմնական վիճակ | Claude / GPT | Համաժամեցնել գործող փաստաթղթերը. տարբերել պատկերները գործող փաստերից. հաշտեցնել վերջին pull request-ի շրջանակը. պահել commit-ների ու CI-ի ապացույցն ու ծածկույթի սահմանները. թարմացնել inventory-ն. հրապարակել այս քարտեզը EN ու HY | հիմնական փաստաթղթերը իրար չեն հակասում, ու ամեն գործող պնդում ունի ապացույց կամ գրված ա UNKNOWN | 7, 8 |
| 1 Անվտանգություն ու վերականգնում | Claude / GPT | Վստահելի credential պահոցներ. ստուգել, հետո հանել Windows-ի ու MCP-ի ավելորդ բացվածքը. AI-ի հստակ environment ու canary. սահմանափակել հին պահուստները առանց ջնջելու. գրել ու փորձել բազայի, կարգավորման, կոդի ու credential-ների մեկուսացված restore ու սերվերի rebuild | մերժումներն ու իրավունքները ստուգված են, ու կա իրական վերականգնման ապացույց | 4, 5, 6 |
| 2 Հուսալի հավաքում | Claude / GPT | API-ի առաջին հսկվող գրելը՝ պլանավորման ու իրավունքների ստուգումից հետո. երեք API գործը արված, մյուս յոթը անձեռնմխելի. կրկնության, մասնակիի ու հնացածի թեստեր. ամբողջ Yandex փոստարկղը՝ կայուն cursor-ներով ու առանց Seen դրոշը փոխելու. Direct՝ դրսի թույլտվությունից հետո, Avito՝ HOLD-ը հանելուց հետո | ամեն պետքական աղբյուր աշխատում ա, կամ հստակ BLOCKED ա՝ ժամով ու աղբյուրով | 1, 11, 17, 2, 21 |
| 3 Իրական բիզնես հոսք | GPT (ծրագիր) / Արմեն (օպերացիոն ընդունում) | Օգտագործել եղած capture ու order կոդը. սահմանել դիմում → պատվեր → ավարտ → հաշվարկ. կապել կայքը. գրանցել հեռախոսի ու մեսենջերի դիմումները. թեստայինն ու իրականը առանձին. տիրոջ կաբինետ՝ միայն դիտում, օրվա մեկ հպումով հարց, որ փողի մասին չի, իրական նկարների վերբեռնում։ Ով ա մուտքագրում ու ով ա հաստատում հաշվարկային փաստերը՝ սահմանվում ա առանձին | իրական դիմումը կարելի ա հետևել մինչև վերջնական ելքը, ու պակասող փաստերը երևում են | 9, 19 |
| 4 Գործողության հաստատում | GPT (նախագիծ) / Claude (իրականացում) | Հաստատումը կապված ա գործողությանը, հաշվին, թիրախին, payload-ի digest-ին, նյութերին, գումարին (որտեղ կա), ժամկետին ու մուտքերի տարբերակին։ Փոխված մուտքը սևագիրը դարձնում ա հնացած. պատմությունը չի փոխվում | հնացած, փոխված, մերժված կամ սխալ թիրախով հաստատումը չի կարա կատարվի | 10 |
| 5 Executor | Claude / GPT | Հստակ թույլատրված գործողությունների տեսակներ. վավեր հաստատում. idempotency. անորոշ արդյունքի ստուգում, մինչև կրկնելը. արտաքին ստուգում. վերագործարկման կառավարում | մեկ ամբողջ հոսք. սևագիր → հաստատում → կատարում → արտաքին ստուգում → հաշվետվություն | 12 |
| 6 Զննարկիչ ու Debian | Claude / GPT | Պարզել hosted runner-ի երեք harness ձախողումը. հարմարեցնել harness-ը proxy-ին. մեկուսացված փորձնական զննարկիչ. մերժել, երբ policy-ն, gate-ը կամ proxy-ն չկա կամ փչացած ա. արդյունքը պահել մինչև հետստուգումը. իրական փորձեր միայն առանձին հաստատումով. Linux-ի harness ու պետքական թեստերը նորից Debian-ում | սահմանափակված Debian worker-ը վերցնում ա runtime-ի տված գործերը ու վերադարձնում ա ստուգելի ապացույց | 15, 16 |
| 7 Վերլուծություն, հաշվետվություն, հսկողություն | Claude / Գև | Առաջնահերթավորված գտածոներ ու կատարելի առաջարկներ. օրական, շաբաթական, ամսական հաշվետվություններ. իրական դիմումներ, պատվերներ, կոնվերսիա, եկամուտ, ծախս, շահույթ՝ UNKNOWN-ը պահելով. health-ի, պահուստի, հոստինգի ու վկայականների deterministic monitoring ու հաստատված alert-ի ալիք | Գևը մեկ տեղում տեսնում ա արդյունքները, խնդիրները, առաջարկները ու սպասող հաստատումները | 13, 14 |
| 8 Հսկվող շահագործում ու v1.0 | Գև / GPT (տեխնիկական ընդունում) | Հաստատել LIVE-ի պայմանները, հաճախությունները, ծախսի սահմաններն ու կանգառի կանոնները. ավարտել ընդունման թեստերը. սահմանափակ շահագործում. փակել կրիտիկական խնդիրները. գրանցել ընդունված release-ն ու օպերացիոն պատասխանատուին | Գևի վերջնական ընդունումը | 18, 27 |

Որտեղ են փուլերը՝ ապացույցով, 07.10.2026-ին. 0-րդ փուլը Claude-ի կողմից արված ա այս փաստաթղթով ու սպասում ա GPT-ի ընդունմանը. 6-րդ փուլում առաջին կետը (harness-ի երեք ձախողումը) արված ա. 1-ին փուլում արտաքին պատճենը կա ու հին պահուստների քայլը պատրաստ ա, մնացածը բաց ա. 2-րդ փուլում API reader-ը դրված ա, առաջին հսկվող գրելը սպասվում ա։ 3, 4, 5, 7 ու 8 փուլերում ոչինչ կառուցված չի։ Հերթի 3 ու 20–26 կետերը բիզնեսի ամենօրյա աշխատանքն են ու ոչ մի փուլի չեն պատկանում։

### v1.0. ավարտի սահմանում

Բոլորը միասին.

1. Հաստատված պարբերական հավաքում՝ առանց Գևի բաց համակարգչից մշտական կախման։
2. Իրական դիմումներն ու պատվերները ունեն օգտագործելի գրանցման հոսք։
3. Կոնկրետ, ապացույցի վրա հիմնված առաջարկներ ու պատրաստ նյութեր։
4. Գևի համար հստակ, գործողություն առ գործողություն հաստատման միջերես։
5. Ոչ մի կատարում բացակայող, հնացած, փոխված կամ ժամկետանց հաստատումով։
6. Մեկ անգամ կատարում ու ստուգված արտաքին արդյունք։
7. Անորոշ արդյունքը գրվում ա հստակ. կույր կրկնություն չկա։
8. Debian-ի browser ու media worker-ը աշխատում ա ընդունված սահմաններում։
9. Monitoring-ի alert-ներ ու փորձված restore ու վերականգնում։
10. GitHub-ի փաստաթղթերը բավարար են հասկանալու, աշխատացնելու ու շարունակելու համար՝ առանց չատի հիշողության։
11. Ընդունված շրջանակում բաց կրիտիկական խնդիր չկա։
12. Գևի վերջնական ընդունումը, որի մեջ ա նաև repo-ի ներկայացման իրա վիզուալ ընդունումը (տես ներքևում)։

**Ընդունման պատուհան.** 14 օր անընդմեջ՝ օրվա ամբողջ շրջանով, ձախողումները գրանցված ու հսկվող, Գևը պետք ա միայն հաստատումների ու բիզնես որոշումների համար։ Հազվադեպ դեպքերը, որ բնական հոսքում չեն լինում, փորձվում են հսկվող սցենարներով։

### Բիզնեսի հաջողություն

Պրոդուկտի ընդունումն ու բիզնեսի հաջողությունը առանձին են։ Առաջին բիզնես թիրախը՝ միջինը օրը հինգ շահութաբեր ավարտված պատվեր, չափված 30 օր անընդմեջ՝ գրանցված տվյալներով։ Ոնց ա հաշվվում շահութաբեր պատվերը ու ինչ ծախսեր են պետք՝ հաստատվում ա չափումը սկսելուց առաջ։ Տեխնիկական պատրաստ լինելը պահանջարկ չի երաշխավորում, ու պատվերներին հասնելը չի փակում անվտանգության ու վերականգնման բացերը։

### v1.0-ի շրջանակից դուրս

Ինքնուրույն վճարումներ կամ ֆինանսական պարտավորություններ. չհաստատված հրապարակային փոփոխություններ կամ գովազդի գործարկում. անսահման ինտեգրումներ. production Windows-ում. չստուգված browser automation. ամբողջական fleet-dispatch ERP. ընդհանուր BRO հարթակ կամ ուրիշ բիզնեսներ։

### Repo-ի ներկայացումը (դիզայնի պահանջ, Գևի ճշտումը 07.10.2026-ին)

**Շրջանակ. միայն այս GitHub repo-ի տեսքը։** Ավելի վաղ ընթերցումը, որ պահանջը տարածում էր runtime-ի, վահանակի կամ տիրոջ կաբինետի վերադիզայնի վրա, հետ ա վերցված. այս բաժինը runtime-ի կամ վահանակի գործ չի ավելացնում ու կոդի կամ տեղադրման փոփոխություն չի թույլատրում։ Պրոդուկտի եղած ֆունկցիոնալ պահանջները մնում են։

Կանոններ. MenQ-ի համապատասխան վիզուալ ու փաստաթղթային կանոնները (հղում՝ `menqstudio/MenQ-Standard`-ի `menq-design-system-v1` ճյուղը. նախ կարդալ դրա հիմնական design ու adoption աղբյուրները. ընդհանուր հարթակը կողպված ա ու չի փոխվում), բայց КРЮК24-ի սեփական ինքնությամբ. կեռիկն ու «КРЮК24 / ЭВАКУАТОР+» lockup-ը `brand/`-ից ու `tools/brand.py`-ից. գործող generator-ների գույները՝ navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, սպիտակ `#FFFFFF`. տառատեսակները՝ Roboto Condensed ու Golos Text։ `brand/README.md`-ում դեռ գրված ա հին `#111111`-ը. հաշտեցվում ա ամսաթվով navy որոշման ու գործող generator-ների հետ՝ աղբյուրի հիմքով, ոչ թե երկուսը լուռ խառնելով։

Ինչ ա տրվում.

1. Գեղեցիկ, ամբողջական root README՝ բրենդային SVG շապիկով ու հստակ հիերարխիայով։
2. Նպատակային SVG պատկերներ՝ ճարտարապետության, քարտեզի փուլերի ու կարգավիճակի, առանց ապացույց չունեցող առաջընթացի պնդման։
3. Հստակ նավիգացիա դեպի հիմնական փաստաթղթերն ու մանրամասն հերթը։
4. Կարևոր տեքստը մնում ա որոնելի, խմբագրելի Markdown՝ EN ու HY. նկարները լրացնում են։
5. Ստուգված տեսք GitHub-ում. ընթեռնելի light ու dark, alt տեքստեր, փոքր էկրանին կարդացվող, հայերեն տառերը ծածկված, որտեղ պետք ա։ SVG ֆայլերում script, `foreignObject` ու դրսից բեռնվող font չկա։
6. Repo-ի ներկայացման Գևի վիզուալ ընդունումը v1.0-ի ընդունման մաս ա։

Հերթի 27-րդ կետն ա. դեռ ոչինչ արված չի։

### Ոնց ա սա պահվում

| Փաստաթուղթ | Ինչ ա պահում |
| --- | --- |
| `ROADMAP.md` | հաստատված շրջանակը, փուլերը ու ավարտի սահմանումը՝ EN ու HY, ու աշխատանքային հերթը |
| `CURRENT_STATE.md` | գործող փաստերը՝ ապացույցով |
| `DECISIONS.md` | հաստատումներն ու փոփոխությունները |
| Issues | կատարելի գործեր, ամեն մեկը մեկ պատասխանատուով, կախվածություններով, ընդունման չափանիշով ու ապացույցով |

## Ժամկետներ

| Օր | Ինչ | Ով |
| --- | --- | --- |
| 08.10.2026, 06:00 UTC-ից հետո (10:00 Երևան) | API reader-ի install-ի 11-րդ քայլը | Claude |
| մինչև 10.10.2026 | Արմենի մեկ պատասխանը Avito-ի երկարաձգման մասին (ժամկետը Claude-ի առաջարկն ա) | Գևը հարցնում ա Արմենին |
| 11.10.2026 | Avito. 24 հայտարարություն փակվում ա, մնացորդ 0 ₽ | Գև (որոշում) |
| 13.10.2026 | Հասցեի հաստատման վիդեոն Yandex Բիզնեսի քարտի համար | Արմեն |
| 13.10.2026 | Webmaster. նայել՝ քանի էջ կա որոնման մեջ | Claude |
| 14.10 ու 15.10.2026 | Avito. փակվում ա 1-ը, հետո ևս 20-ը | Գև (որոշում) |
| 26.10.2026 | Avito. փակվում ա 1-ը | Գև (որոշում) |
| մոտ 15.11.2026 (հաշվարկ) | Լիցքավորել հոստինգի հաշիվը | Գև / Արմեն |
| 30.12.2026 | Կայքի SSL վկայականը (ինքնաթարմացումը չստուգված) | հոստինգ. ստուգում ա Claude-ը |
| 04.01.2027 | `runtime.kryuk24.ru`-ի վկայականը | `certbot.timer`. ստուգում ա Claude-ը |
| 01.10.2027 | Դոմեն kryuk24.ru (չստուգված 01.10.2026-ից հետո) | Գև / Արմեն |

## Հերթը

| # | Կետ | Ով | Կախված ա | Հաջորդ քայլ |
| --- | --- | --- | --- | --- |
| 1 | **API reader, քայլ 11.** մեկ հսկվող գրող գործարկում | Claude | 08.10.2026-ի 06:00 UTC-ի պլանավորումը գրել ա նոր օրը (տասը գործ, երեքը `API_READ`). `runtime.sqlite*`-ը դեռ `kryuk-db` խմբով ա | Ստուգել պլանը. դնել `kryuk-api-read.service`-ը. մեկ `systemctl start`. ստուգել երեք `DONE`՝ `MACHINE_OBSERVED`-ով, մնացած յոթը անփոփոխ, վահանակը բացվում ա։ Timer չկա։ Հետո՝ փաստացի զեկույց GPT-ին |
| 2 | **Avito մինչև 11.10** (HOLD) | Գև | Արմենի պատասխանը. երկարաձգումը իրա կաբինետում անվճա՞ր ա, թե վճարովի, ու ում մոտ ա autoload-ի ֆայլը | Claude-ի առաջարկը. եթե անվճար ա՝ թույլտվություն միայն երկարաձգման համար, տեքստերը չեն փոխվում. եթե վճարովի ա՝ որոշել թիվը իմանալուց հետո։ Մինչև Գևի խոսքը ոչինչ չի փոխվում ու չի վճարվում |
| 3 | **Հասցեի հաստատում մինչև 13.10** | Արմեն | Ցուցանակների չափերի հարցը (06.10.2026-ի սքրինշոթն ու ձայնայինները, բովանդակությունը հայտնի չի) → տպել → վիդեո | Գևը պարզում ա՝ չափերի հետ ինչն ա սխալ. Claude-ը ուղղում ա ֆայլերը. Արմենը նկարում ու ուղարկում ա վիդեոն |
| 4 | **Credential-ների մաքրում Windows-ում** | Գև (պահոցի որոշումը), Claude (պատրաստում առանց արժեքների) | GPT-ն տեղերը ֆիքսել ա. բաց ա գործող ու Avito-ի գաղտնիքների պահոցը՝ VPS, թե առանձին Windows օգտատեր | Claude-ը պատրաստում ա տեղափոխման ու ստուգման պլանը, user փոփոխականները կարդացողների ցուցակը (`tools/api_setup/*.ps1`, `provision_from_windows.ps1`, `bro_api_reader.py --windows-user-store`, `.mcp.json`) ու canary ստուգում ամեն AI մեկնարկի համար։ Սկրիպտը գործարկում ա Գևը. Claude-ի ու editor-ի նիստերը վերամեկնարկվում են |
| 5 | **Պատճեն սկավառակից դուրս. արված ա 07.10.2026** | Գև, Claude | չկա | Արտաքին սկավառակ `E:\Kryuk24\backup_2026-10-07\`, ամեն ֆայլ sha256-ով համեմատված։ Մնում ա որոշել՝ ինչ հաճախությամբ թարմացվի |
| 6 | **Սերվերի հին բազայի պահուստները տանել `0700 kryuk-run`** | Claude | Սերվերի փոփոխության խոսք (ով ա տալիս՝ աղբյուրներում գրված չի) | `.sqlite` ու `.json` պահուստները տանել ենթաթղթապանակ. ստուգել, որ collector-ի խումբը էլ չի կարդում. ոչինչ չի ջնջվում |
| 7 | **GitHub ու Drive** | Գև (ասում ա հաշիվն ու Drive-ը), Claude (import) | 5-րդ կետը. Գևի պատասխանները բնօրինակ նկարների ու անձնական տվյալի մասին | Մաքուր սկզբնական import առանձին private KRYUK24 repo. հին պատմությունը մնում ա bundle-ում. Drive տարված ամեն ֆայլ ստուգվում ա sha256-ով `docs/media-index.md`-ի հետ |
| 8 | **Մաքրում. ինչ ա մնում push-ից հետո** | Claude | չկա | Հրապարակված ա 07.10.2026 (`menqstudio/Kryuk24`, `main`-ի CI-ն կանաչ)։ Harness-ի self-test-ը նորից CI-ում ա (pull request #2. մատյանի մրցավազք trial-ի թեստային սերվերում)։ Մնում ա. նայել գրանցված T1 ու T2 փորձերը նույն մրցավազքի համար. 21 գեներատոր սկրիպտը մեկ-մեկ կարդալ. Drive-ի պատճենը ստուգել ֆայլ առ ֆայլ (Drive API ա պետք). որոշել GitHub Pro-ն `main`-ի պաշտպանության համար (Գև) |
| 9 | **Իրական դիմումներ ու պատվերներ** | Claude (կարդում ա կոդը, առաջարկում), GPT (գրում ա տիրոջ կաբինետը), Արմեն (օգտագործում ա) | 1-ին կետը փակված | Նախ կարդալ՝ runtime-ում ինչ կա (`orders`, `contact_interactions`, capture, թեստային դրոշ). հետո առաջարկ. զրոյից ոչինչ չի կառուցվում։ Տիրոջ կաբինետը. միայն-կարդալու դեր, ռուսերեն էջ, օրվա հարց մեկ սեղմումով՝ առանց փողի, իսկական նկարների վերբեռնում. միայն STAGING |
| 10 | **Approval contract ու հնացած սևագրեր** | Claude (նախագիծ GPT-ի համար), GPT (որոշում) | — | Նախագիծ `runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`-ի հիմքով։ Գործող սևագիրը առանց Գևի չի փոխվում ու չի հաստատվում |
| 11 | **Փոստը Bro-ի համար** | Գև (ստեղծում ա հավելվածը), Claude (connector) | Yandex-ի հավելված «KRYUK24 Bro Mail»՝ `mail:imap_full` ու `mail:smtp` իրավունքներով. փոստարկղում IMAP-ը միացված | Հավելվածից հետո. token սկրիպտով, հետո Բիզնեսի թղթապանակի կարդալու ստուգում։ Ուղարկելը մնում ա փակ |
| 12 | **Հաստատված գործողությունների executor** | GPT (ընդունում), Claude (սարքում) | 4-րդ ու 10-րդ կետերը | Ոչինչ գրված չի։ Idempotency-ն ու անորոշ արդյունքի reconciliation-ը առաջին տարբերակի մաս են |
| 13 | **Մոնիտոր առանց AI-ի** (health, backup, հոստինգի մնացորդ, վկայական) | Claude | պատրաստելու համար՝ ոչինչ. ժամանակացույցի ու ալիքի համար՝ Գևի առանձին «հա» | Պատրաստել deterministic ստուգումները |
| 14 | **Հաշվետվություններ.** օրական runtime-ում, շաբաթական, ամսական, բյուջե | Claude | 9-րդ կետը (առանց գրանցված պատվերների թվերը UNKNOWN են) | — |
| 15 | **Chrome proxy ու փորձեր** | GPT (որոշումներ), Claude | GPT-ի պատասխանները v5.3 փաթեթի վրա. ընդունե՞լ proxy-ն որպես սահմանափակող շերտ. proxy-ով փորձերի ձևը. մնա՞լ Windows-ում մինչև proxy-ով առաջին run-ը | Հետո. proxy-ին հարմարեցված harness, առանձին `--user-data-dir` փորձի Chrome-ի համար։ T2-ը կրկնվում ա միայն GPT-ի որոշմամբ ու Գևի նոր «հա»-ով. T3-ը չի սկսվում |
| 16 | **Debian worker** | Գև (կասի՝ երբ), Claude | Մուտք մեքենա. 15-րդ կետը | Չի սկսվել։ Harness-ի Linux տարբերակ. Windows-ի փորձերը էնտեղ նորից են քշվում |
| 17 | **Yandex Direct-ի API** | Yandex, հետո Claude | Լրիվ մուտքի հայտի պատասխանը (ուղարկված 07.10.2026, վիճակը «новая»). կգա տիրոջ փոստարկղ | Պատասխանից հետո՝ `tools/api_setup/yandex_check.ps1 -Kind actions`։ Եթե Yandex-ը մակետի փոխարեն իսկական սքրինշոթ ուզի՝ անել, երբ վահանակում Direct-ի բաժինը լինի |
| 18 | **Direct-ի գործարկում** (միայն Գևի «հա»-ից հետո) | Գև (որոշումներ), Claude (կաբինետ) | 9-րդ կետը (դիմումների աշխատող գրանցում), НДС-ը բյուջեի դաշտում, կանգառի շեմերը նոր բյուջեի համար, коллтрекинг, մրցակիցների բրենդներով հարցումներ, լիցքավորված հաշիվ | Սևագրում. առավելագույն ստավկան կանխատեսումից, սկզբի օրը, նպատակների արժեքները. նեղացնել մեկ լայն ֆրազը. быстрые ссылки ու уточнения։ Չեկ-լիստը՝ `research/Direct_launch_package_2026-10-04.md` |
| 19 | **Արմենի պատասխանները** | Արմեն (հարցերը փոխանցում ա Գևը) | — | «Просто дернуть от 4 000»-ը դեռ գործո՞ւմ ա (բաց հակասություն 6). որ շրջաններն ա ուզում ներկա քաղաքների էջերի փոխարեն. «50 մեքենա»-ն իրա պա՞րկն ա, թե գործընկերների ցանց. որտեղից են գալիս պատվերները ու ինչ արժի մեկ պատվերը (վառելիք, վարորդ). 02.10.2026-ի 20 հարցը. իրա տեխնիկայի ու գործերի իսկական նկարներ |
| 20 | **Սերգեյի կարծիքի պատասխանը. փակված ա Գևի որոշմամբ (07.10.2026)** | Claude | չկա | Դրված տեքստի հետ կարդալը մնում ա ՉՍՏՈՒԳՎԱԾ. կարդալ, երբ աշխատանքային պրոֆիլում զննարկչի նիստ բաց լինի։ Ոչինչ չի կանգնեցնում |
| 21 | **Երկու չբացված նամակ** | Claude, Գևի խոսքով | Փոստի մուտք նիստում | «Մասամբ ընդունեցինք ուղղումները» (ինչն ա մերժվել՝ UNKNOWN). հաշվիչը Webmaster-ում կապելու հարցումը (հաստատելը կոճակ ա, առանձին «հա» ա պետք) |
| 22 | **Նոր նկարներն ու քարտը** | Գև (որոշում), Claude | — | 07.10.2026-ի երեք մշակված կադրը. դնե՞լ քարտում ու կայքում. 07.10.2026-ի վիդեոն չի դիտվել։ Երբ տեխնիկայի իսկական նկարներ լինեն՝ փոխել «Оборудование»-ի ութ գեներացվածը (ջնջում ա Գևը իրա ձեռքով) |
| 23 | **Կայք, հաջորդ հրապարակում** | Claude, Գև («հա») | — | `logo-dark.png`-ն ու `theme-color`-ը կապույտ. ուղղել `site/README.md`-ի հնացած պիտակի տողը |
| 24 | **WhatsApp Business հեռախոսում** | Արմեն | — | Անունը «Kruk24» → «КРЮК24». քարտեզի նշանը. ողջույնի ու «ղեկին եմ» հաղորդագրությունները։ Տեքստերը՝ `offers/whatsapp_business_setup_2026-10-07.md`։ Ստատուսները `offers/whatsapp_kit/`-ից, օրը մեկ, ընտրում ա մարդը |
| 25 | **Մանր կետեր Գևի համար** | Գև | — | Հաստատել կամ ասել՝ ինչ ուղղել վահանակի նոր դիզայնում (հեռախոսի լայնությունն ու մուգ ռեժիմը չստուգված են). աշխատանքային պրոֆիլում մեկնարկին «նախկինում բաց թաբերը». extension-ին թողնել փոստի կայքը. փորձերից հետո հիմնական պրոֆիլում extension-ը նորից միացնել. որոշել Bro-ի առանձին Chrome պրոֆիլը. որոշել՝ կարա՞ն առանց հսկողության run-երը ծախսեն բաժանորդագրության սահմանաչափը. որոշել merge արված `navy-v32` ու `v33` ճյուղերի հարցը. առանձին WhatsApp համար Claude-ի համար ու ձայնայինների տառադարձում |
| 26 | **Մանր կետեր Claude-ի համար** | Claude | — | Direct-ում վերաստուգել коллтрекинг-ի համարները. ստուգել Բիզնեսի գովազդային բաժանորդագրության ու Բիզնեսի հին լենդինգի վիճակը. ուղղել Direct-ի սխալի տեքստի կոդավորումը `yandex_check.ps1`-ում. ամենօրյա ստուգումը մնում ա ձեռքով (առաջին գրառումը `docs/history/`-ում), մինչև մեկ run առանց Գևի բաց նիստի անցնի ճիշտ պրոֆիլով |
| 27 | **Repo-ի ներկայացումը** (բրենդային README, SVG շապիկ, ճարտարապետության / փուլերի / կարգավիճակի պատկերներ, MenQ-ի կանոններ՝ КРЮК24-ի ինքնությամբ) | Claude. ընդունող՝ Գև | Նախ կարդալ MenQ-ի design աղբյուրները. հաշտեցնել `brand/README.md`-ի `#111111`-ը navy որոշման հետ | Ոչինչ արված չի։ Միայն repo-ի տեսքը. վահանակի, runtime-ի կամ կաբինետի վերադիզայն չկա։ Ստուգել GitHub-ում light ու dark, փոքր էկրան, հայերեն տառեր. SVG առանց script-ի, `foreignObject`-ի ու դրսի font-երի։ Առանձին ճյուղ ու pull request |

## Հերթում չկա

| Կետ | Ինչու |
| --- | --- |
| Timer կամ autostart Bro-ի կամ API reader-ի համար | Առանց Գևի առանձին «հա»-ի չի ստեղծվում |
| Avito-ում փոփոխություն, վճարում, երկարաձգում | Գևի HOLD-ի տակ ա |
| Google ձևը տիրոջ համար | Փոխարինված ա runtime-ում տիրոջ կաբինետով. մնում ա չհրապարակված սևագիր |
| Զանգերի մատյանի արտահանում տիրոջ հեռախոսից | Միայն Արմենի համաձայնությամբ. մատյանում իրա անձնական զանգերն էլ կան |
| Նոր շրջանների էջեր | Սպասում են Արմենի ցուցակին (կետ 19) |
