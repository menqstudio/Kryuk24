# KRYUK24: architecture

Components and boundaries. Part 1 is what is installed and was seen working; part 2 is the target accepted on 07.10.2026 and mostly not built. Nothing in part 2 may be read as existing. Evidence for part 1 is in [`CURRENT_STATE.md`](CURRENT_STATE.md).

The VPS address is not written here; it is in the private notes. It appears below as `<VPS>`.

## Part 1. Installed today

### 1.1 Map

```
customers ──> kryuk24.ru (static site, Beget shared hosting)        no connection to the runtime
                 └─ buttons: call, WhatsApp, Telegram; Metrica counter 113277361

Gev's browser ──HTTPS + Basic auth (owner realm)──┐
                                                  ├─> Nginx on <VPS>, runtime.kryuk24.ru
Windows Bro client ──HTTPS + Basic auth (Bro realm, only /bro/v1/)──┘
                                                  │
              kryuk-capture   127.0.0.1:8788  (runtime v0.8.1 + queue bridge v0.1.1, dashboard, /capture, /health)
              kryuk-bro-api   127.0.0.1:8789  (Bro HTTP bridge v0.2.0; active, not enabled)
              kryuk-operations.timer  06:00 UTC   plans the day's ten tasks
              kryuk-backup.timer      ~00:00–00:05 UTC
              ops_api.py (API reader v0.3.2)      installed, run by hand only, user kryuk-api-read
                                                  │
              /var/lib/kryuk24/runtime.sqlite (WAL)        /etc/kryuk24-bro   /etc/kryuk24-api-read
                                                  │
              outbound, read-only: Beget API, Yandex Metrica API, Yandex Webmaster API
```

### 1.2 Components

| Component | Where | What it does today | Boundary |
| --- | --- | --- | --- |
| Live site | Beget shared hosting, `site/` in git | Eight static pages, a price calculator, contact buttons, Metrica goals `call`, `whatsapp`, `telegram`. External services without keys: Photon, OSRM, Yandex Maps widget | Not connected to the runtime. A click is counted; a call or an order is not |
| VPS runtime | `<VPS>`, Ubuntu 26.04.1, code `/opt/kryuk24` (163 files), data `/var/lib/kryuk24` | Mode STAGING, `sending_enabled: false`. Services run as `kryuk-run`, `UMask=0077` | Only ports 22, 80, 443 are open; 8788 and 8789 listen on localhost only |
| Queue | `runtime.sqlite`, tables include `ops_tasks`, `ops_observations`, `ops_events`, `orders`, `contact_interactions`, `bro_receipts`, `bro_runs` (14 tables in the snapshot) | Ten tasks a day, planned at 06:00 UTC. Kinds: `LOCAL_READ`, `BROWSER_READ`, `API_READ`. A task ends `DONE` or `BLOCKED` with an observation and a trust label | The kind is written once, at planning; an existing row is never rewritten |
| Dashboard | `/operator/work`, file `ops_views.py` (Gev's design, sha256 `f5f6e9d8…`, protected: never overwritten, never part of a patch) | Shows the day and one approve button for the daily report draft | Owner realm only |
| Bro HTTP bridge | `/bro/v1/`, service `kryuk-bro-api` | Lets a remote worker read the queue and claim, observe and draft the browser tasks | Own Basic-auth realm, own password file; after the API reader patch it refuses `API_READ` tasks (403) |
| API reader | `ops_api.py`, `bro_api_reader.py` in `/opt/kryuk24`; source `runtime/api_reader/` | Reads Beget (`HOSTING_DEADLINES`), Metrica site counter and Maps card counter as two sections of one task (`METRICA`), Webmaster (`WEBMASTER`); writes `MACHINE_OBSERVED` evidence | Own user `kryuk-api-read`; fixed list of request paths; no timer; first write run not done yet |
| Mailbox | — | Does not exist | — |
| Approval | `ops_work.approve()` | Accepts the daily report draft when its status is `READY_REVIEW` and the digest matches | See 1.6 |
| Executors | — | None. Nothing publishes, replies, pays or sends | — |

Server code reconciliation (07.10.2026 13:08 UTC, copy in `runtime/server/` with `MANIFEST.md`): of 163 files, 139 equal GPT's release manifest found on the server. The remainder is exactly: the v0.8.1 patch files (equal to GPT's v0.8.1 package), the Bro bridge files (equal to the received packages), `ops_views.py`, 4 files patched and 3 added by the API reader install, and 4 saved copies `*.before-api-read`. A copy of the site on the server (59 files) is byte-identical to `site/`.

### 1.3 Windows: development and trial tools

| Thing | Where | Role |
| --- | --- | --- |
| This repository | `C:\Users\Admin\Desktop\Armen` | Code, documents, site, generators |
| Bro client | `C:\Users\Admin\KRYUK24-Bro\` (outside the repository) | `bro_pull.py`, provisioning and edge-check scripts, the client credential file |
| Trial run folder | `C:\Users\Admin\KRYUK24-Bro-Trial` | Evidence of the five real trial runs, ledger, review notes |
| Trial components | `runtime/wip/adapter_preflight/`, `runtime/wip/trial/`, `runtime/wip/chrome_proxy/` | Gate (`bro_gate_hook.py`), job runner (`win_job.py`), harness (`run_trial.py`), proxy (`bro_chrome_proxy.py`) |
| API setup | `tools/api_setup/` | Scripts that obtain and check tokens without printing them |
| Browser | Chrome profile "KRYUK24 — Armen" | Claude's manual round of the cabinets, in Gev's open session |

Today the daily round of the cabinets (Yandex Business, Direct, mail, WhatsApp list, Avito) is done by Claude by hand in that profile. That is supervised manual work, not a component.

### 1.4 Credential flow and trust boundaries (as installed)

```
Windows user environment (read token, Beget API login and password)
   └─ provision_from_windows.ps1 ──SSH──> reader_provision.py (root, standard input only)
         └─ /etc/kryuk24-api-read/beget-read.json, yandex-read.json   root:kryuk-api-read, folder 750, files 640
```

| Boundary | How it is held | Evidence |
| --- | --- | --- |
| Collector credentials versus the web services | `kryuk-run` is not in the group `kryuk-api-read` | Open check 07.10.2026: `kryuk-api-read` ALLOWED, `kryuk-run` DENIED, `nobody` DENIED |
| Bro server credential versus the collector | `/etc/kryuk24-bro` stays `root:kryuk-run 750`, untouched | `kryuk-api-read` on the Bro server credential: DENIED |
| Database | Group `kryuk-db` with exactly two members, `kryuk-run` and `kryuk-api-read`; folder `2770`, database and `-wal` / `-shm` `660`, owner stays `kryuk-run` | Two-real-user rehearsal PASS 7/7; dry-run as `kryuk-api-read` on the real database OK |
| Owner versus Bro over HTTP | Two Basic-auth realms and two password files in Nginx | Bro to owner routes: 14 of 14 refused. Owner to the Bro route: refused (one GET; the three POST routes were not tested) |
| What the collector may request | Allowed list checked before any request leaves: one Beget path, one Metrica path, three Webmaster paths | Package tests; the collector refuses a credentials file with any other key (actions token, mail, Avito) |

Stated cost of the database boundary: at file-permission level the collector is trusted with the whole database and can create and delete files directly in `/var/lib/kryuk24`. Since the install its group can also traverse that folder and read the old backup files there that have mode 644. See [`SECURITY.md`](SECURITY.md), known gaps.

### 1.5 Claim, lease, retry, idempotency, recovery (as installed)

| Mechanism | Where | Behaviour |
| --- | --- | --- |
| Claim | queue, API reader | Each attempt claims under its own name `API_READ:<random>` |
| Lease | queue | 600 s; the slowest possible reading is 384 s |
| Stale result | queue `owned()` check | A result from an expired or replaced attempt is refused |
| Idempotency of a run | queue | A `DONE` task is not claimable, so a repeated run writes nothing (shown in a throwaway database: second write run, three `NOT_CLAIMABLE`, counts unchanged) |
| HTTP retry | collector | Twice, only after a timeout, 429 or 5xx. Auth and request errors are not retried. No redirects, 30 s timeout, 1 MB answer limit |
| Partial reading | collector | If one Metrica counter fails, the good section is kept and the task becomes `BLOCKED`, not `DONE` |
| No fallback | patch | An `API_READ` task is never offered to the browser worker; an API failure does not fall back to a browser |
| Installer recovery | `install_patch.py` | `apply` refuses unless four files have the known sha256, saves each as `*.before-api-read`; a failed write is undone (`REFUSED`); an undo that cannot finish leaves `PARTIAL`; `rollback` accepts a half-applied folder and can be repeated. Recovery, not an atomic switch |
| One-shot trial runs | harness (`runtime/wip/trial/`) | An exclusive OS-held lock refuses a second `--execute`; every run gets a new `attempt-NN`; an append-only ledger |

Not installed: any idempotency or recovery for *actions*. There is no executor, so there is nothing to make idempotent yet.

### 1.6 Report approval is not action approval

What exists: the server builds a daily report draft; the owner presses one button; `approve()` checks only that the draft is in `READY_REVIEW` and that the digest matches. The digest covers the draft itself (`action, account, destination, body, reason, assets`), not the day's inputs.

Consequences, both verified in the staging database on 07.10.2026 (`runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`):

- a task of the same day changed status 1 h 35 min after the draft was built, and the draft stayed approvable unchanged. The system cannot tell which observations a draft was built from;
- approving the report authorises nothing. The system does not send the report to the owner of the business either.

So today there is exactly one approval, and it is an approval of a text. Publishing, replying, changing a card, spending or sending is done by a person, or by Claude in a supervised session after Gev's separate yes for that exact item.

### 1.7 Real requests and orders: the flow today and the data gaps

```
customer ──call / WhatsApp──> the owner's phone ──> order done        nothing is recorded
customer ──site button──> Metrica goal click                          a click, not a call or an order
customer ──Yandex Maps card──> "call" click in the card counter       a click, not a call or an order
```

| Gap | State |
| --- | --- |
| Requests and orders | Not recorded anywhere. Every row in the runtime's `orders` and `contact_interactions` is a test row |
| Live site to runtime | Not connected; there is no LIVE mode |
| Owner's cabinet in the runtime | Does not exist (GPT writes the code; decided 07.10.2026) |
| Call data | The calls statistics of the cabinets are empty or clicks only; a manually dialled number is not counted |
| Source of an order, cost per order, payment, commission | UNKNOWN |

Until a real flow exists, every KPI that depends on orders is UNKNOWN, not zero (GPT, 07.10.2026).

## Part 2. Target

Accepted by GPT on 07.10.2026 on Gev's decisions. Status of every row below is PLANNED unless it says otherwise. The work cycle: check → analyse → prepare → Gev's approval → execute → check the result → report.

### 2.1 Where each thing lives

| Machine | Holds | Does not hold |
| --- | --- | --- |
| VPS | Queue, API readers, mailbox connector, approval records, the executor of API and mail actions | A browser |
| Debian desktop | The final browser and media worker | The queue's authority: dispatch belongs to the runtime |
| Windows | Development and supervised trials | Production work |

The same job is never executed on two machines at once; the runtime dispatches.

**Debian browser and media worker: planned boundary only.** Gev says the machine exists, is separate from the VPS, has a desktop and is reached over VNC. Claude has not seen it: its address, version, Chrome and Claude Code are unverified, and there is no access. The migration has not started and does not start now. Claude's assessment, unverified on Linux: the gate and the proxy are plain Python and portable; the trial harness is tied to Windows (job objects, PowerShell process lists, `msvcrt` locks) and needs its own variant; trials passed on Windows must be run again on Debian.

### 2.2 Target components

| Component | Target | Open point |
| --- | --- | --- |
| API readers | Installed reader run daily after planning; Direct reading once Yandex grants access | The schedule is a separate yes; today no timer |
| Mailbox connector | The whole owner's Yandex mailbox, no restriction by sender or subject. New mail tracked by folder + UIDVALIDITY + UID; Message-ID against duplicates; "unread" is not a cursor; reading does not change the Seen flag. The runtime keeps the minimum the work needs; personal letters do not go into a report automatically | BLOCKED: no app, no credential. The hosting provider's mailbox at another mail service is out of scope |
| Approval contract | A new approval is bound to the action, the account, the target, the payload digest, the amount and the deadline. When the underlying task changes, the draft is marked stale; the old draft, digest and audit are never rewritten | Design not written; options are in `REPORT_DRAFT_staleness.md` |
| Executor | Performs only approved API and mail actions, with idempotency and with reconciliation of an uncertain result | Comes after the approval contract, never before |
| Real requests and orders | A request on the live site → the owner's record → completion → payment and commission, built on the existing runtime code; test and real rows are told apart | First read what the code already has; do not build from zero |
| Reports | Daily, weekly, monthly; budget | After orders are recorded |
| Monitor without AI | Deterministic checks: health, backup, hosting balance, certificate | Not prepared. Schedule and notification channel only on Gev's separate yes |
| Browser worker | Claude reaches the Chrome tools only through the proxy; the gate runs before and after every call; a missing policy or a failed gate refuses the call before Chrome | Waits for GPT's decisions on package v5.3; no real model run through the proxy |

### 2.3 Target credential flow

Yandex and Avito secrets move to the store of a trusted executor, are verified there, then are removed from the Windows user environment and the open sessions are restarted. An AI subprocess gets only an explicit environment allowlist, checked by a canary test; access to the store is checked as well. Two Yandex keys by purpose: a read key for daily reading and an actions key for approved actions. Not done; the choice of store is pending (see [`SECURITY.md`](SECURITY.md)).

### 2.4 Order of work (GPT, 07.10.2026)

Credentials clean-up → API reader install → recording of real requests and orders → mailbox and approval contract → executor → reports. The proxy goes separately. The single queue with owners is in [`ROADMAP.md`](ROADMAP.md).

---

# Հայերեն

Բաղադրիչներն ու սահմանները։ 1-ին մասը էն ա, ինչ դրված ա ու տեսել ենք աշխատելիս. 2-րդը՝ 07.10.2026-ին ընդունված թիրախը, որի մեծ մասը սարքած չի։ 2-րդ մասից ոչինչ չպիտի կարդացվի որպես եղած բան։ 1-ին մասի ապացույցները՝ [`CURRENT_STATE.md`](CURRENT_STATE.md)-ում։ VPS-ի հասցեն էստեղ չի գրվում, անձնական նշումներում ա. ներքևում՝ `<VPS>`։

## Մաս 1. Այսօր դրվածը

### 1.1 Քարտեզ

Սխեման վերևի անգլերեն մասում ա։ Բառերով. հաճախորդը գալիս ա `kryuk24.ru` (ստատիկ կայք Beget-ի հոստինգում), որը runtime-ին կապված չի. կոճակները զանգի, WhatsApp-ի ու Telegram-ի համար են, հաշվիչը՝ Metrica 113277361։ Գևի զննարկիչն ու Windows-ի Bro client-ը HTTPS-ով ու Basic auth-ով (երկու առանձին realm) գալիս են `<VPS>`-ի Nginx, `runtime.kryuk24.ru`։ Հետևում. `kryuk-capture` (127.0.0.1:8788), `kryuk-bro-api` (127.0.0.1:8789, active, բայց enabled չի), `kryuk-operations.timer` (06:00 UTC), `kryuk-backup.timer` (մոտ 00:00–00:05 UTC), ու API reader-ը, որ դրված ա ու գործարկվում ա միայն ձեռքով։ Տվյալները՝ `/var/lib/kryuk24/runtime.sqlite` (WAL)։ Դուրս գնացող հարցումները միայն կարդում են. Beget, Metrica, Webmaster։

### 1.2 Բաղադրիչներ

| Բաղադրիչ | Որտեղ | Ինչ ա անում այսօր | Սահման |
| --- | --- | --- | --- |
| Կենդանի կայք | Beget-ի հոստինգ, git-ում՝ `site/` | Ութ ստատիկ էջ, գնի հաշվիչ, կապի կոճակներ, Metrica-ի նպատակներ `call`, `whatsapp`, `telegram`։ Առանց բանալու արտաքին ծառայություններ՝ Photon, OSRM, Yandex Քարտեզի վիջեթ | Runtime-ին կապված չի։ Սեղմումը հաշվվում ա, զանգն ու պատվերը՝ չէ |
| VPS runtime | `<VPS>`, Ubuntu 26.04.1, կոդ `/opt/kryuk24` (163 ֆայլ), տվյալ `/var/lib/kryuk24` | STAGING, `sending_enabled: false`։ Ծառայությունները `kryuk-run`-ի տակ են, `UMask=0077` | Բաց են միայն 22, 80, 443. 8788-ն ու 8789-ը միայն localhost-ում են |
| Հերթ | `runtime.sqlite` (`ops_tasks`, `ops_observations`, `ops_events`, `orders`, `contact_interactions`, `bro_receipts`, `bro_runs` ու մնացածը, snapshot-ում 14 աղյուսակ) | Օրը տասը գործ, պլանավորվում ա 06:00 UTC-ին։ Տեսակներ՝ `LOCAL_READ`, `BROWSER_READ`, `API_READ`։ Գործը փակվում ա `DONE` կամ `BLOCKED`՝ դիտարկումով ու վստահության նշանով | Տեսակը գրվում ա մեկ անգամ՝ պլանավորելիս. եղած տողը չի վերագրվում |
| Վահանակ | `/operator/work`, `ops_views.py` (Գևի դիզայնը, sha256 `f5f6e9d8…`, պաշտպանված. չի վերագրվում, patch-ի մեջ չի մտնում) | Ցույց ա տալիս օրը ու մեկ կոճակ՝ օրվա հաշվետվության սևագիրը հաստատելու | Միայն տիրոջ realm-ը |
| Bro-ի HTTP կամուրջ | `/bro/v1/`, `kryuk-bro-api` | Հեռվի աշխատողը կարդում ա հերթը, վերցնում, դիտարկում ու սևագրում զննարկչի գործերը | Իր realm-ը, իր գաղտնաբառի ֆայլը. patch-ից հետո `API_READ` գործերը մերժում ա (403) |
| API reader | `/opt/kryuk24`-ում `ops_api.py`, `bro_api_reader.py`. աղբյուրը՝ `runtime/api_reader/` | Կարդում ա Beget-ը (`HOSTING_DEADLINES`), Metrica-ի կայքի ու Քարտեզի քարտի հաշվիչները՝ մեկ գործի երկու բաժնով (`METRICA`), Webmaster-ը (`WEBMASTER`). գրում ա `MACHINE_OBSERVED` ապացույց | Իր օգտատերը՝ `kryuk-api-read`. հարցումների ֆիքսված ցուցակ. timer չկա. առաջին գրող գործարկումը դեռ չի եղել |
| Փոստ | — | Չկա | — |
| Հաստատում | `ops_work.approve()` | Ընդունում ա սևագիրը, երբ վիճակը `READY_REVIEW` ա ու digest-ը համընկնում ա | Տես 1.6 |
| Executor-ներ | — | Չկան։ Ոչինչ չի հրապարակում, չի պատասխանում, չի վճարում, չի ուղարկում | — |

Սերվերի կոդի համեմատումը (07.10.2026 13:08 UTC, պատճենը `runtime/server/`-ում՝ `MANIFEST.md`-ով). 163 ֆայլից 139-ը նույնն են, ինչ սերվերում գտած GPT-ի release manifest-ը։ Մնացածը ճիշտ էս ա. v0.8.1-ի patch-ի ֆայլերը (նույնը, ինչ GPT-ի v0.8.1 փաթեթը), Bro-ի կամրջի ֆայլերը (նույնը, ինչ ստացված փաթեթները), `ops_views.py`-ն, API reader-ի install-ի փոխած 4 ու ավելացրած 3 ֆայլը, ու 4 պահված պատճեն՝ `*.before-api-read`։ Սերվերում եղած կայքի պատճենը (59 ֆայլ) բայթ առ բայթ նույնն ա, ինչ `site/`-ը։

### 1.3 Windows. մշակում ու փորձեր

| Ինչ | Որտեղ | Դերը |
| --- | --- | --- |
| Էս repo-ն | `C:\Users\Admin\Desktop\Armen` | Կոդ, փաստաթղթեր, կայք, գեներատորներ |
| Bro client | `C:\Users\Admin\KRYUK24-Bro\` (repo-ից դուրս) | `bro_pull.py`, provisioning-ի ու edge-check-ի սկրիպտներ, client-ի credential ֆայլը |
| Փորձի run folder | `C:\Users\Admin\KRYUK24-Bro-Trial` | Հինգ իրական run-ի ապացույցները, ledger-ը, review-ի նշումները |
| Փորձի բաղադրիչներ | `runtime/wip/adapter_preflight/`, `runtime/wip/trial/`, `runtime/wip/chrome_proxy/` | Gate (`bro_gate_hook.py`), job runner (`win_job.py`), harness (`run_trial.py`), proxy (`bro_chrome_proxy.py`) |
| API setup | `tools/api_setup/` | Սկրիպտներ, որ token վերցնում ու ստուգում են առանց տպելու |
| Զննարկիչ | Chrome-ի «KRYUK24 — Armen» պրոֆիլը | Claude-ի ձեռքով շրջայցը կաբինետներով, Գևի բաց նիստով |

Այսօր կաբինետների ամենօրյա շրջայցը (Yandex Բիզնես, Direct, փոստ, WhatsApp-ի ցուցակ, Avito) Claude-ն ա անում ձեռքով էդ պրոֆիլում։ Դա հսկվող ձեռքի աշխատանք ա, ոչ բաղադրիչ։

### 1.4 Credential-ների ճանապարհն ու վստահության սահմանները (ոնց դրված ա)

Windows-ի user environment-ից (կարդալու token, Beget-ի API-ի լոգին ու գաղտնաբառ) `provision_from_windows.ps1`-ը SSH-ով տալիս ա սերվերի `reader_provision.py`-ին (root, միայն standard input), որը գրում ա `/etc/kryuk24-api-read/beget-read.json` ու `yandex-read.json` (`root:kryuk-api-read`, թղթապանակը 750, ֆայլերը 640)։

| Սահման | Ոնց ա պահվում | Ապացույց |
| --- | --- | --- |
| Collector-ի credential-ները ու վեբ ծառայությունները | `kryuk-run`-ը `kryuk-api-read` խմբում չի | Բացելու ստուգում 07.10.2026. `kryuk-api-read`՝ ALLOWED, `kryuk-run`՝ DENIED, `nobody`՝ DENIED |
| Bro-ի server credential-ն ու collector-ը | `/etc/kryuk24-bro`-ն մնում ա `root:kryuk-run 750`, ձեռք չենք տվել | `kryuk-api-read`-ը Bro-ի credential-ի վրա՝ DENIED |
| Բազա | `kryuk-db` խումբ՝ ճիշտ երկու անդամով (`kryuk-run`, `kryuk-api-read`). թղթապանակը `2770`, բազան ու `-wal` / `-shm`-ը `660`, տերը մնում ա `kryuk-run` | Երկու իրական օգտատիրոջով փորձ՝ PASS 7/7. dry-run `kryuk-api-read`-ով իրական բազայի վրա՝ OK |
| Տերն ու Bro-ն HTTP-ով | Nginx-ում երկու Basic-auth realm ու երկու գաղտնաբառի ֆայլ | Bro → տիրոջ ուղիներ՝ 14-ից 14 մերժված։ Տեր → Bro-ի ուղի՝ մերժված (մեկ GET. երեք POST ուղին չեն փորձվել) |
| Ինչ կարա հարցնի collector-ը | Թույլատրված ցուցակը ստուգվում ա հարցումից առաջ. Beget-ի մեկ ուղի, Metrica-ի մեկ, Webmaster-ի երեք | Փաթեթի թեստերը. ուրիշ բանալիով ֆայլը (actions token, փոստ, Avito) collector-ը մերժում ա |

Բազայի սահմանի գինը, գրված բաց. ֆայլի իրավունքների մակարդակում collector-ին վստահված ա ամբողջ բազան, ու նա կարա ֆայլ ստեղծել-ջնջել `/var/lib/kryuk24`-ում։ Install-ից հետո իրա խումբը կարա նաև մտնել էդ թղթապանակ ու կարդալ էնտեղի հին պահուստները, որոնք 644 են։ Տես [`SECURITY.md`](SECURITY.md), հայտնի բացեր։

### 1.5 Claim, lease, retry, idempotency, վերականգնում (ոնց դրված ա)

| Մեխանիզմ | Որտեղ | Վարքը |
| --- | --- | --- |
| Claim | հերթ, API reader | Ամեն փորձ վերցնում ա իր անունով՝ `API_READ:<random>` |
| Lease | հերթ | 600 վրկ. ամենադանդաղ հնարավոր ընթերցումը 384 վրկ ա |
| Հնացած արդյունք | հերթի `owned()` ստուգումը | Ժամկետանց կամ փոխարինված փորձի արդյունքը մերժվում ա |
| Run-ի idempotency | հերթ | `DONE` գործը չի վերցվում, կրկնակի գործարկումը ոչինչ չի գրում (ցույց ա տրված ժամանակավոր բազայում. երկրորդ write run-ը՝ երեք `NOT_CLAIMABLE`, քանակները նույնը) |
| HTTP retry | collector | Երկու անգամ, միայն timeout / 429 / 5xx-ից հետո։ Auth-ի ու հարցման սխալը չի կրկնվում։ Redirect չկա, 30 վրկ, 1 ՄԲ սահման |
| Կիսատ ընթերցում | collector | Metrica-ի մեկ հաշվիչի ձախողման դեպքում լավ բաժինը մնում ա, գործը դառնում ա `BLOCKED`, ոչ `DONE` |
| Fallback չկա | patch | `API_READ` գործը զննարկչի աշխատողին չի տրվում. API-ի ձախողումը զննարկչի չի անցնում |
| Installer-ի վերականգնում | `install_patch.py` | `apply`-ը մերժում ա, եթե չորս ֆայլի sha256-ը հայտնին չի, ամեն մեկը պահում ա `*.before-api-read`. ձախողված գրելը հետ ա բերվում (`REFUSED`). չավարտված հետբերումը թողնում ա `PARTIAL`. `rollback`-ը ընդունում ա կիսատ թղթապանակը ու կրկնվում ա։ Սա վերականգնում ա, ոչ ատոմար անցում |
| Մեկանգամյա trial run-եր | harness | OS-ի պահած բացառիկ lock-ը մերժում ա երկրորդ `--execute`-ը. ամեն run՝ նոր `attempt-NN`. միայն ավելացվող ledger |

Դրված չի. *գործողությունների* համար ոչ idempotency կա, ոչ վերականգնում։ Executor չկա, ուրեմն դեռ բան չկա idempotent սարքելու։

### 1.6 Հաշվետվության հաստատումը գործողության հաստատում չի

Ինչ կա. սերվերը սարքում ա օրվա հաշվետվության սևագիրը, տերը սեղմում ա մեկ կոճակ, `approve()`-ը ստուգում ա միայն, որ սևագիրը `READY_REVIEW` ա ու digest-ը համընկնում ա։ Digest-ը ծածկում ա սևագիրը (`action, account, destination, body, reason, assets`), ոչ օրվա մուտքերը։

Հետևանքները, երկուսն էլ ստուգված staging բազայում 07.10.2026-ին (`runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`).

- նույն օրվա գործը վիճակը փոխեց սևագիրը սարքելուց 1 ժ 35 ր հետո, ու սևագիրը մնաց հաստատելի՝ անփոփոխ։ Համակարգը չգիտի՝ սևագիրը որ դիտարկումներից ա սարքվել.
- հաշվետվության հաստատումը ոչինչ չի թույլատրում։ Համակարգը հաշվետվությունը բիզնեսի տիրոջն էլ ինքը չի ուղարկում։

Այսինքն այսօր մեկ հաստատում կա, ու դա տեքստի հաստատում ա։ Հրապարակել, պատասխանել, քարտ փոխել, ծախսել կամ ուղարկել անում ա մարդը, կամ Claude-ը հսկվող նիստում՝ Գևի առանձին «հա»-ից հետո հենց էդ բանի համար։

### 1.7 Իրական դիմումներն ու պատվերները. այսօրվա հոսքն ու տվյալների բացերը

Հաճախորդը զանգում կամ գրում ա տիրոջ հեռախոսին, պատվերը կատարվում ա, ոչինչ չի գրվում։ Կայքի կոճակի սեղմումը դառնում ա Metrica-ի նպատակ՝ սեղմում, ոչ զանգ, ոչ պատվեր։ Քարտեզի քարտի «զանգել»-ը նույնպես սեղմում ա։

| Բաց | Վիճակ |
| --- | --- |
| Դիմումներ ու պատվերներ | Ոչ մի տեղ չեն գրվում։ Runtime-ի `orders` ու `contact_interactions` աղյուսակների բոլոր տողերը թեստային են |
| Կենդանի կայք → runtime | Կապված չի. LIVE ռեժիմ չկա |
| Տիրոջ կաբինետը runtime-ում | Չկա (կոդը գրում ա GPT-ն. որոշված ա 07.10.2026) |
| Զանգերի տվյալ | Կաբինետների զանգերի վիճակագրությունը դատարկ ա կամ միայն սեղմումներ. ձեռքով հավաքած համարը չի հաշվվում |
| Պատվերի աղբյուր, մեկ պատվերի ծախս, վճարում, միջնորդավճար | UNKNOWN |

Մինչև իրական հոսք չլինի, պատվերներից կախված ամեն KPI UNKNOWN ա, ոչ զրո (GPT, 07.10.2026)։

## Մաս 2. Թիրախ

Ընդունել ա GPT-ն 07.10.2026-ին, Գևի որոշումներով։ Ներքևի ամեն տող PLANNED ա, եթե ուրիշ բան չի գրված։ Շրջանը. ստուգել → վերլուծել → պատրաստել → Գևի հաստատում → կատարել → ստուգել արդյունքը → հաշվետվություն։

### 2.1 Որտեղ ինչն ա ապրում

| Մեքենա | Պահում ա | Չի պահում |
| --- | --- | --- |
| VPS | Հերթ, API reader-ներ, փոստի connector, հաստատման գրառումներ, API-ի ու փոստի գործողությունների executor | Զննարկիչ |
| Debian desktop | Վերջնական browser / media worker | Հերթի իշխանությունը. dispatch-ը runtime-ինն ա |
| Windows | Մշակում ու հսկվող փորձեր | Production աշխատանք |

Նույն job-ը երկու մեքենայում միաժամանակ չի կատարվում. բաժանում ա runtime-ը։

**Debian-ի browser / media worker-ը միայն պլանավորված սահման ա։** Գևի խոսքով մեքենան կա, VPS-ից առանձին ա, desktop ունի, կպնում ա VNC-ով։ Claude-ը չի տեսել. հասցեն, տարբերակը, Chrome-ի ու Claude Code-ի առկայությունը չստուգված են, մուտք չկա։ Տեղափոխումը չի սկսվել ու հիմա չի սկսվում։ Claude-ի գնահատումը, Linux-ում չստուգված. gate-ն ու proxy-ն մաքուր Python են ու տեղափոխելի. trial harness-ը Windows-ին ա կապված (job object, PowerShell-ով պրոցեսների ցուցակ, `msvcrt` lock) ու առանձին տարբերակ ա ուզում. Windows-ում անցած փորձերը Debian-ում նորից են քշվելու։

### 2.2 Թիրախային բաղադրիչներ

| Բաղադրիչ | Թիրախ | Բաց կետ |
| --- | --- | --- |
| API reader-ներ | Դրված reader-ը ամեն օր, պլանավորումից հետո. Direct-ի կարդալը, երբ Yandex-ը մուտք տա | Ժամանակացույցը առանձին «հա» ա. այսօր timer չկա |
| Փոստի connector | Տիրոջ Yandex փոստարկղը ամբողջությամբ, առանց ուղարկողով կամ վերնագրով սահմանափակման։ Նորը հաշվվում ա folder + UIDVALIDITY + UID-ով. Message-ID-ն՝ կրկնության դեմ. «unread»-ը cursor չի. կարդալը Seen դրոշը չի փոխում։ Runtime-ում մնում ա գործին պետք նվազագույնը. անձնական նամակները հաշվետվության մեջ ավտոմատ չեն գնում | BLOCKED. հավելված չկա, credential չկա։ Հոստինգի նամակների արկղը (ուրիշ փոստային ծառայությունում) scope-ում չի |
| Approval contract | Նոր հաստատումը կապվում ա գործողության, հաշվի, թիրախի, payload digest-ի, գումարի ու ժամկետի հետ։ Հիմքի գործը փոխվելիս սևագիրը նշվում ա հնացած. հին սևագիրը, digest-ն ու audit-ը չեն վերագրվում | Նախագիծը գրված չի. տարբերակները՝ `REPORT_DRAFT_staleness.md`-ում |
| Executor | Կատարում ա միայն հաստատված API-ի ու փոստի գործողությունները՝ idempotency-ով ու անորոշ արդյունքի reconciliation-ով | Գալիս ա approval contract-ից հետո, ոչ առաջ |
| Իրական դիմումներ ու պատվերներ | Կենդանի կայքի դիմում → տիրոջ գրանցում → ավարտ → վճարում ու միջնորդավճար, եղած runtime-ի կոդի հիմքով. թեստայինն ու իրականը տարբերակվում են | Նախ կարդալ՝ կոդում ինչ կա. զրոյից չկառուցել |
| Հաշվետվություններ | Օրական, շաբաթական, ամսական. բյուջե | Պատվերների գրանցումից հետո |
| Մոնիտոր առանց AI-ի | Deterministic ստուգումներ. health, backup, հոստինգի մնացորդ, վկայական | Պատրաստված չի։ Ժամանակացույցն ու ծանուցման ալիքը՝ միայն Գևի առանձին «հա»-ով |
| Browser worker | Claude-ը Chrome-ի գործիքներին հասնում ա միայն proxy-ով. gate-ը քշվում ա ամեն կանչից առաջ ու հետո. policy-ի բացակայությունը կամ gate-ի խափանումը մերժում ա կանչը մինչև Chrome-ին հասնելը | Սպասում ա GPT-ի որոշումներին v5.3 փաթեթի վրա. իսկական մոդելը proxy-ով չի աշխատել |

### 2.3 Credential-ների թիրախային ճանապարհը

Yandex-ի ու Avito-ի գաղտնիքները տեղափոխվում են վստահելի executor-ի պահոց, ստուգվում են էնտեղ, հետո հանվում Windows-ի user environment-ից, ու բաց նիստերը վերամեկնարկվում են։ AI subprocess-ը ստանում ա միայն explicit environment allowlist՝ canary թեստով ստուգված. պահոցի հասանելիությունն էլ ա ստուգվում։ Yandex-ի երկու բանալի՝ ըստ նպատակի. կարդացողը ամենօրյա կարդալու համար, գործողը՝ հաստատված գործողությունների։ Արված չի. պահոցի ընտրությունը սպասում ա (տես [`SECURITY.md`](SECURITY.md))։

### 2.4 Աշխատանքի հերթը (GPT, 07.10.2026)

Credential-ների մաքրում → API reader-ի տեղադրում → իրական դիմումների ու պատվերների գրանցում → փոստ ու approval contract → executor → հաշվետվություններ։ Proxy-ն՝ առանձին։ Մեկ հերթը տերերով՝ [`ROADMAP.md`](ROADMAP.md)-ում։
