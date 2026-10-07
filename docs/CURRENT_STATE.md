# KRYUK24: current state

Verified state only. Last update: 07.10.2026, after the server reconciliation at 13:08 UTC. For any fact about today this file is the only source; older notes that disagree are superseded.

Status: **IMPLEMENTED** (written or configured), **VERIFIED** (seen by Claude in the named source on the named date), **BLOCKED** (cannot proceed, reason given), **PLANNED** (nothing written). Inside an evidence cell, "unverified" and "UNKNOWN" mean exactly that. "Armen" and "Gev" as evidence mean: their words, not checked by Claude.

Times are UTC unless marked. MSK = UTC+3, Yerevan = UTC+4. The VPS address is in the private notes (`<VPS>` here). No secret value appears in this file.

## 1. Deadlines

| What | By | Who | Status and evidence |
| --- | --- | --- | --- |
| Step 11 of the API reader install: one supervised write run | 08.10.2026, after 06:00 UTC (10:00 Yerevan) | Claude | PLANNED. `runtime/api_reader/README.md`, install step 11 |
| Avito: 24 listings expire, balance 0 ₽. On hold, nothing paid or changed | 11.10.2026 | Gev (decision) | VERIFIED, Avito API, 07.10.2026 11:57 |
| Address confirmation for the Yandex Business card (video). The banner is still in the cabinet | 13.10.2026 | Armen | VERIFIED, cabinet, 06.10.2026; deadline unchanged in the round of 07.10.2026 |
| Avito: 1 listing expires 14.10, 20 more expire 15.10, 1 on 26.10 | 15.10.2026 | Gev (decision) | VERIFIED, Avito API, 07.10.2026 11:57 |
| Hosting balance (shared hosting + VPS + IPv4, about 49 ₽ a day) | about 15.11.2026, calculated | Gev / Armen (payment) | VERIFIED, see the three readings in 4.1 |
| SSL certificate of the site | 30.12.2026 | hosting (auto-renewal unverified) | VERIFIED 06.10.2026 |
| Certificate of `runtime.kryuk24.ru` (Let's Encrypt) | 04.01.2027 | `certbot.timer` | VERIFIED, server, 07.10.2026 06:29 |
| Domain kryuk24.ru | 01.10.2027 | — | unverified after 01.10.2026 |

## 2. Site kryuk24.ru

| Item | Status | Evidence |
| --- | --- | --- |
| Live site = git `main` = tag `v33.1-live` | VERIFIED | 06.10.2026: 57 of 58 file hashes equal; the 58th is `.htaccess`, not served from outside, cannot be compared |
| Live checks: issues 0, errors [], links_bad [], test route 11 km / 5 100 ₽ | VERIFIED | `tools/tests/run_checks.py live`, 06.10.2026 |
| Eight pages: main, five city pages, manipulator, special vehicles; sitemap holds 8 URLs; the Khimki page is open | VERIFIED | 06.10.2026 |
| Calculator (car that does not start): wheels turn from 4 000 ₽; 1 blocked wheel 5 500; 2: 7 000; 3: 8 500; 4: 10 000; "do not know" 4 000 with a note | VERIFIED | tried on the live site, 06.10.2026. The 1 500 ₽ per wheel is Armen's answer of 06.10.2026 |
| The phrase about a free trip to the customer is not on the site | VERIFIED | 06.10.2026 (Armen: "по договоренности") |
| Tariff lines on the site: manipulator for a shift, 5–6 hours on site, 25 000 ₽; pulling out a stuck car without transport, from 5 000 ₽ | VERIFIED | 06.10.2026. The second line is part of an open contradiction, see [`DECISIONS.md`](DECISIONS.md) |
| `assets/logo-dark.png` and `theme-color` of the SEO pages are still black, the rest of the site is blue | VERIFIED | 06.10.2026. Fix goes with the next deploy |
| A copy of the site on the VPS (59 files) is byte-identical to `site/` | VERIFIED | server, 07.10.2026 13:08. Its folder on the server is not named in the sources of this document: UNKNOWN here |
| Three zips and one old picture remain in the hosting account's home folder (not `public_html`), 404 from the site | VERIFIED | 06.10.2026 |
| `site/README.md` names tag `v32-live` as the last deploy | stale line | the live tag is `v33.1-live` (06.10.2026); the deploy steps in that file are still the ones used |

## 3. Server and runtime

### 3.1 Host and services

| Item | Status | Evidence |
| --- | --- | --- |
| VPS at the hosting provider's cloud, Ubuntu 26.04.1, 2 cores / 2 GB / 30 GB, 27 ₽ + 5 ₽ (IPv4) a day | VERIFIED | server, 07.10.2026 06:29 |
| Login by SSH key only, user `kryuk` with sudo; password login over SSH is closed; the `root` password is locked since 07.10.2026 | VERIFIED | server, `passwd -S` shows `L`, 07.10.2026 |
| Firewall: 22, 80, 443 | VERIFIED | server, 07.10.2026 06:29 |
| `kryuk-capture`: active / enabled, `127.0.0.1:8788`, mode STAGING, `sending_enabled: false`. Runtime v0.8.1 + Bro queue bridge v0.1.1, runs as `kryuk-run` | VERIFIED | server, `/health`, 07.10.2026 13:02 |
| `kryuk-bro-api` (Bro HTTP bridge v0.2.0): active / **disabled**, `127.0.0.1:8789`. After a reboot it does not start by itself and `/bro/v1/` answers 502 | VERIFIED | server, 07.10.2026 13:02 |
| Nginx: `https://runtime.kryuk24.ru`, the whole host behind Basic auth (owner realm), a separate `location ^~ /bro/v1/` with its own password file. No IP rule | VERIFIED | server, 07.10.2026 06:29 |
| `kryuk-operations.timer`: daily 06:00 UTC (10:00 Yerevan), plans the day's ten tasks | VERIFIED | server, 07.10.2026 13:00–13:02 (`facts-before.txt`) |
| `kryuk-backup.timer`: daily around 00:00–00:05 UTC. The backup time is not the planning time | VERIFIED | server, 07.10.2026 13:00–13:02. An earlier note that the 10:00 Yerevan planning also makes the backup is superseded |
| `certbot.timer` exists; no Bro timer; no API reader timer | VERIFIED | server, 07.10.2026 |
| The live site is not connected to the runtime; there is no LIVE mode | VERIFIED | server, 07.10.2026 |
| All requests in the database are test requests | VERIFIED | server, 07.10.2026 06:29 |

### 3.2 Code on the server (reconciliation, 07.10.2026 13:08 UTC)

| Item | Status | Evidence |
| --- | --- | --- |
| `/opt/kryuk24` holds 163 files; 139 equal GPT's release manifest found there | VERIFIED | server, 07.10.2026 13:08; copy and list in `runtime/server/MANIFEST.md` |
| The other files are exactly: v0.8.1 patch files (equal to GPT's v0.8.1 package); Bro bridge files (equal to the received packages); `ops_views.py`; 4 files patched and 3 added by the API reader install; 4 saved copies `*.before-api-read` | VERIFIED | same |
| `ops_views.py` is Gev's design, sha256 `f5f6e9d8…`, protected: never overwritten. Unchanged by the install | VERIFIED | server, 07.10.2026 13:02 and 13:08 |
| `runtime/server/` is a read-only fetch of that code. It holds no database and no credentials | VERIFIED | brief of 07.10.2026, `runtime/server/MANIFEST.md` |
| Dashboard `/operator/work` in the new design since 07.10.2026 (only the look changed) | IMPLEMENTED | Gev looked at it; no feedback yet. Phone width and dark mode unverified. After the install the page was not opened in a browser: unverified |

### 3.3 Data

| Item | Status | Evidence |
| --- | --- | --- |
| Queue of 07.10.2026: nine tasks DONE in the morning; the Avito task was closed by Gev from the dashboard | VERIFIED | server, 07.10.2026 06:29 |
| Daily report draft: `APPROVED`, revision 9, digest `3e0c111c…` (Gev approved before the install) | VERIFIED | server, 07.10.2026 13:02 |
| Old tables equal the reference snapshot (orders 20, contact_interactions 36, ops_tasks 10, ops_observations 10, ops_events 52) | VERIFIED | server, 07.10.2026 06:29 |
| `bro_receipts` 0, `bro_runs` 0 | VERIFIED | server, 07.10.2026 13:02 |
| Table content hashes identical before the install, after the patch and after the dry-run (14 tables, 0 differences) | VERIFIED | `bro_snapshot.py`, server, 07.10.2026 13:00–13:02 |
| Old database backups in `/var/lib/kryuk24` (several `.sqlite` and `.json`, mode 644): since the install the collector's group can traverse the folder and read them. Nothing in the code or units names them; no process holds them open | VERIFIED | server, 07.10.2026 13:08 |
| Moving those backups into a subfolder `0700 kryuk-run` | PLANNED | not executed. Nothing is deleted |

### 3.4 API reader v0.3.2 r2

| Item | Status | Evidence |
| --- | --- | --- |
| Code accepted by GPT for a supervised STAGING install; install procedure revision 2 | VERIFIED | GPT, 07.10.2026; `runtime/api_reader/README.md` |
| Step 1: package on the server, 23 of 23 hashes OK | VERIFIED | server, 07.10.2026 13:00–13:02 |
| Step 2: facts read (journal mode `wal`; folder `kryuk-run:kryuk-run 750`, database `600`; code `root:root`; four units use the code, all `User=kryuk-run`, `UMask=0077`); snapshot and database backup taken | VERIFIED | `/root/api-read-install/facts-before.txt`, same time |
| Step 3: group `kryuk-db` (members `kryuk-run`, `kryuk-api-read`), system user `kryuk-api-read` (nologin) | VERIFIED | server, same time |
| Step 4: two-real-user rehearsal in a throwaway database: `RESULT: PASS`, 7 of 7 | VERIFIED | server, same time |
| Step 5: both timers stopped, then both services; no planning or backup run was in progress | VERIFIED | server, same time |
| Step 6: `install_patch.py check`, then `apply`: `APPLIED`; hashes of the seven files on disk match the README list and the package | VERIFIED | server, same time |
| Step 7: permissions added only: folder `kryuk-run:kryuk-db 2770`; database and `-wal` / `-shm` `kryuk-run:kryuk-db 660` | VERIFIED | server, same time |
| Step 8: earlier state restored (`kryuk-capture` active / enabled, `kryuk-bro-api` active / disabled, both timers active / enabled); `/health` STAGING, sending off | VERIFIED | server, 07.10.2026 13:02 |
| Step 9: credentials provisioned to `/etc/kryuk24-api-read` (`root:kryuk-api-read 750`, files `640`); answer `written: beget-read.json, yandex-read.json`; open checks ALLOWED / DENIED as expected; `/etc/kryuk24-bro` unchanged | VERIFIED | server, 07.10.2026 13:02. The script was run by Claude; no value was printed anywhere |
| Step 10: dry-run as `kryuk-api-read` on the real database, read-only: exit 0, three readings OK, all three `would_write: false` (today's rows have the old kind and are already DONE) | VERIFIED | server, 07.10.2026 13:02 |
| Step 11: plan check, install `kryuk-api-read.service`, one supervised run, three `DONE` with `MACHINE_OBSERVED` | PLANNED | 08.10.2026 after 06:00 UTC. No timer is created |
| Collector unit file in `/etc/systemd/system` | not installed | server, 07.10.2026 13:02 |
| After the install: the dashboard page in a browser and `bro_pull.py --queue-only` | unverified | both need a password. The first real write of the services under the new group is the 06:00 UTC planning of 08.10.2026 |
| Tests 18 + 27 on Windows and on the server | VERIFIED | 07.10.2026 12:37 (server, temp folder, removed after) |
| Whole chain with real readings into a throwaway database | VERIFIED | `runtime/api_reader/evidence/real_chain_windows_v032_20261007T123548Z.json` |
| A sampled Metrica answer from the real API; a really full disk during install; the counters' own time-zone setting | unverified | `runtime/api_reader/README.md` |
| Factual report of the install to GPT | PLANNED | after step 11 |

### 3.5 Bro bridge and browser path

| Item | Status | Evidence |
| --- | --- | --- |
| Bro HTTP bridge accepted: without or with a wrong password every route answers 401; traversal refused; ports 8788 and 8789 closed from outside | VERIFIED | 07.10.2026 |
| Isolation Bro → owner routes: 14 of 14 refused. Owner → Bro route: refused, confirmed in the browser and in the Nginx log (one GET) | VERIFIED | 07.10.2026 |
| The three POST routes owner → Bro; a scripted full matrix with the owner's correct password | unverified | GPT dropped the scripted matrix |
| Real adapter (an unattended Claude reading cabinets through Chrome) | BLOCKED | never run. The proxy package v5.3 waits for GPT's decisions |
| Gate and job runner v3.2: gate 50 tests OK, job 31 OK | VERIFIED | Windows, 07.10.2026; `runtime/wip/adapter_preflight/` |
| Trial harness v5.3: 68 self-tests OK. Five real runs exist | VERIFIED | `runtime/wip/trial/TRIAL_PLAN.md`; evidence in `C:\Users\Admin\KRYUK24-Bro-Trial` |
| T1 / attempt-04: CLEAR 16/16 (08:01), accepted by GPT, then narrowed: `T1.9` does not prove that the hook's allow is what let the tool run | VERIFIED | ledger and review notes, 07.10.2026 |
| T1 attempts 01, 02, 03: BLOCKED and kept untouched. Attempts 02 and 03 ran in parallel on one approval (Claude's mistake; a lock was added in v5.2) | VERIFIED | `TRIAL_PLAN.md`, section 0f |
| T2 / attempt-01: BLOCKED (7 PASS, 2 INCONCLUSIVE). With no hook and no allow rule two tools ran (`list_connected_browsers`, `tabs_context_mcp`); `tabs_create_mcp` was denied; no page was opened. GPT: the fail-closed requirement is not met, no exemption | VERIFIED | 07.10.2026 08:10 |
| Chrome proxy: 12 tests OK; live without a model: no policy → denied, with the trial policy → the browser list | VERIFIED | 07.10.2026 08:23; `runtime/wip/chrome_proxy/README.md` |
| A real Claude run through the proxy; a harness adapted to the proxy; a separate `--user-data-dir` for the trial Chrome; a Linux variant | not done | same file |
| No T2 rerun, no T3; a model run only on Gev's new yes | in force | GPT and Gev, 07.10.2026 |

## 4. External services

### 4.1 Hosting (Beget)

| Reading | Value | Source |
| --- | --- | --- |
| 07.10.2026, morning | 1 997,33 ₽, "40 days" | panel |
| 07.10.2026 09:07 UTC | 1 965,56 ₽, 41 days | API (`user/getAccountInfo`) |
| 07.10.2026 13:02 UTC | 1 960,22 ₽, 40 days | API, dry-run on the server |

All three were true at their time. A balance is always written with its time and source. Plan "Blog", 49,1 ₽ a day (API, 09:07). `days_to_block` is the API's estimate, not a guaranteed deadline. Gev topped up 2 000 ₽ on 06.10.2026 (Gev).

API access: VERIFIED 07.10.2026 09:07. Allowed methods are limited to "Account administration" (changed in the panel by Claude; `site/getList`, `dns/getData`, `cron/getList` answer `AUTH_ERROR Method disabled`).

### 4.2 Yandex Metrica and Webmaster

| Item | Status | Evidence |
| --- | --- | --- |
| Read token works for Metrica and Webmaster | VERIFIED | `tools/api_setup/yandex_check.ps1`, exit 0, 07.10.2026 09:08 |
| Three counters: the site counter 113277361 (5 goals: phone, WhatsApp, Telegram and two automatic); the Yandex Maps card counter; a counter of the Business self-made landing | VERIFIED | API, 07.10.2026 09:08 |
| Site, last 7 days at that reading: 415 visits, 364 people; yesterday 15 visits, goals 0. Server dry-run at 13:02: site 06.10, 15 visits / 11 people, `+03:00`, `exact: true` | VERIFIED | API, 07.10.2026. Visits include Gev's and Claude's own |
| Maps card counter, 7 days: 141 visits, 4 clicks on "call". A click is not a call and not an order | VERIFIED | API, 07.10.2026 09:08 |
| Site goals, 7 days to 06.10: phone 9, WhatsApp 15, Telegram 3 | VERIFIED | API, 07.10.2026 |
| Numbers before 04.10.2026 are contaminated by our own checks; since then the site checks do not load the counter | VERIFIED | `tools/tests/common.py`; decision of 04.10.2026 |
| Counters' `code_status` in the API is `CS_ERR_UNKNOWN` | meaning unverified | visits are counted |
| Webmaster: one verified host, 1 page in search (the main page, since 04.10), 8 pages crawled with code 200, no errors, 2 recommendations | VERIFIED | cabinet 06.10.2026; API 07.10.2026 |
| The site counter is linked to Webmaster and crawling by counter is on | VERIFIED | 07.10.2026, on Gev's yes |
| A mail "request to link the counter to the site in Webmaster" is unopened | open | confirming it is a button and needs a separate yes |

### 4.3 Yandex Business card

| Item | Status | Evidence |
| --- | --- | --- |
| Address "Москва, улица Бехтерева, 41, корп. 1", change approved 06.10.2026 20:02. The confirmation banner (by 13.10) is still there; the video is not sent | VERIFIED | cabinet, 06.10.2026 |
| The public business number is shown; the second number is hidden | VERIFIED | cabinet, 06.10.2026 |
| 13 services | VERIFIED | cabinet, 06.10.2026 |
| Photos: Services 14, Equipment 8, Video 1, Uncategorised 2. The 8 in "Equipment" are generated, not real; they stay until real ones exist (Gev, 06.10.2026) | VERIFIED | cabinet, 06.10.2026 |
| Logo in the blue scheme passed moderation | VERIFIED | cabinet, 07.10.2026 00:22 MSK. Public look unverified |
| 7 reviews, average 4.2; no official rating ("У вас пока нет рейтинга") | VERIFIED | cabinet, 07.10.2026 11:29–11:35 |
| Reply to Sergey's review (5 stars, 06.10): **sent; closed by Gev's decision on 07.10.2026; read-back UNVERIFIED**. After sending the page showed "no new reviews"; the posted text was not read back from the page | IMPLEMENTED, not verified | cabinet, 07.10.2026. See [`DECISIONS.md`](DECISIONS.md), contradiction 1 |
| Statistics 06.09–06.10: 362 views (Maps 190, Search 113, Navigator 59), 4 "call" clicks, 0 routes, 0 transitions to the site | VERIFIED | cabinet, 06.10.2026 |
| A mail "we partly accepted the edits" is unopened; what was refused | UNKNOWN | mail list, 07.10.2026 |
| Reviews and moderation results have no API. They arrive as letters in the owner's Yandex mailbox (129 letters from the Business sender; a review letter carries the full text, without the author's name and stars) | VERIFIED | mail, read on Gev's yes, 07.10.2026 |

### 4.4 Yandex Direct

| Item | Status | Evidence |
| --- | --- | --- |
| One campaign `search_msk_test1`: draft, search only, spend 0, balance 0 ₽; five older campaigns archived | VERIFIED | cabinet, 06.10.2026 and 07.10.2026 |
| Five groups, all drafts, one ad each (two headlines, two texts), Moscow and region. Group 5 holds 4 phrases, 5 were entered; the likely cause (a duplicate merged) is a conclusion, not checked | VERIFIED | cabinet, 06.10.2026 |
| Budget: the field says 12 000 ₽ a week (cabinet, 06.10); Armen's upper limit "до 15.000р" a week (Armen, 06.10); Gev: "the number as Armen said" (06.10). Whether the field includes VAT | unverified | 12 000 × 1,22 = 14 640 ₽ |
| Launch gaps: maximum bid empty; start date to be changed; goal values are placeholders; no quick links or clarifications; one phrase too broad; stop thresholds were computed for 20 000 ₽ and not revised; call tracking to be rechecked; account not funded | VERIFIED | cabinet, 06.10.2026; `research/Direct_launch_package_2026-10-04.md` |
| API: agreement accepted by Gev; the full-access request was sent 07.10.2026, status "new" | VERIFIED | Direct page "My requests", 07.10.2026 |
| API reading | BLOCKED | error 58 ("registration not finished") at 09:21, 07.10.2026 |
| Do not launch, do not pay without Gev | in force | Gev |

### 4.5 Avito (on hold by Gev)

| Item | Status | Evidence |
| --- | --- | --- |
| API reads | VERIFIED | 07.10.2026 11:05 and 11:57, read-only |
| 46 active listings, all by autoload, all priced 100 ₽, 45 with the same title template | VERIFIED | API, 07.10.2026 11:57 |
| Expiry: 24 by 11.10, 1 on 14.10, 20 on 15.10, 1 on 26.10; balance 0 ₽; no paid promotion | VERIFIED | same |
| 30 days: 577 unique views, 78 contacts, 27 favourites; 15 listings with 0 contacts; rating 5.0, 10 reviews (12.09–02.10), none answered; unread chats 0; call statistics empty | VERIFIED | same |
| Listing texts and photos; where the autoload file comes from; whether prolongation is paid | unverified | the API does not give them; the browser extension does not open the site |
| Nothing is changed or paid until Gev says so | in force | Gev, 07.10.2026 |

### 4.6 Mail, WhatsApp, other accounts

| Item | Status | Evidence |
| --- | --- | --- |
| Five rules in the owner's Yandex mailbox move letters into folders (Business, Avito, site, ads); no forwarding, nothing deleted | VERIFIED | mail, 07.10.2026, on Gev's word |
| All letters were marked read on 07.10.2026 on Gev's word (nothing deleted); from then on "unread" means new | VERIFIED | mail, 07.10.2026 |
| Mailbox for Bro: the Yandex app "KRYUK24 Bro Mail" (`mail:imap_full`, `mail:smtp`) | BLOCKED | not created; no mail credential |
| In the afternoon round of 07.10.2026 the mail was not checked: the extension did not allow the mail site in that session | not done | 07.10.2026 11:29–11:35 |
| WhatsApp Business (public number): description, address and site corrected and read back after reopening; five quick replies entered; the cover picture set by Gev | VERIFIED | WhatsApp Web, 07.10.2026 |
| WhatsApp: name still "Kruk24"; the map pin shows a wrong place; greeting and "driving" messages exist only on the phone | open | Armen, on the phone |
| WhatsApp list had no unread mark in the round; no chat was opened | VERIFIED | 07.10.2026 11:29–11:35 |
| A project Google account exists (created by Gev 06.10.2026); recovery mail not verified; its purpose | UNKNOWN | Gev has not said |
| The Google form for the owner is a draft, not published; replaced by the owner's cabinet in the runtime | decided | Gev, 07.10.2026 |

## 5. Brand and media

| Item | Status | Evidence |
| --- | --- | --- |
| Brand colour is blue (`tools/brand.py`, `INK = #13233A`); logo, avatar, livery, 7 signs, QR, WhatsApp kit, address guides rebuilt in blue | VERIFIED | Gev's decision 06.10.2026; files |
| Signage sizes: the owner sent a screenshot with every size circled and voice messages on 06.10.2026 | UNKNOWN | what the voice messages say (Claude does not hear audio) |
| Processed photo set: 23 frames, plates and passers-by covered, checked by eye. Three new frames (07.10) are not uploaded anywhere | VERIFIED | `photo/01_real_polished/`, 07.10.2026 |
| The video of 07.10.2026 was copied, its content not watched | unverified | no ffmpeg |

## 6. Repository, backup, clean-up

| Item | Status | Evidence |
| --- | --- | --- |
| Git: no remote, nothing pushed | VERIFIED | 07.10.2026 |
| Git bundle with all refs in `D:\KRYUK24_backup\`, verified by `git bundle verify` and a test clone (commit count and HEAD equal) | VERIFIED | 07.10.2026; `docs/cleanup/CLEANUP_STAGE1_REPORT.md` |
| 15 files that git does not hold, copied to `D:\KRYUK24_backup\untracked_2026-10-07\`, each compared by sha256 | VERIFIED | same |
| `D:` is the same physical disk as `C:`. A copy off this disk | does not exist | same; precondition for GitHub, not met |
| Secrets scan: **no secret was detected by the stated checks** (pattern scan over tracked text and all 162 commits on all refs). Images, PDFs and `.docx` are not covered; a secret written as plain prose without a marker word would not be seen | VERIFIED within those limits | `docs/cleanup/CLEANUP_STAGE1_REPORT.md`, 07.10.2026 |
| `.mcp.json` is git-ignored; a secret-free `.mcp.json.example` is in git | VERIFIED | `.gitignore`, 07.10.2026 |
| Stage 1 of the clean-up (inventory `docs/inventory/FILES.csv`, 811 rows; backup; audit) | VERIFIED | same report |
| Stage 2 (structure applied, these seven documents, Drive split) | in progress | branch `cleanup/stage2-structure`, 07.10.2026 |
| CI file `.github/workflows/ci.yml` | IMPLEMENTED, **not run on GitHub** (no repository exists yet) | the file; every command in it was run by hand, see next row |
| Checks from a fresh clone of the branch, 07.10.2026 | VERIFIED locally | Linux (server, Python 3.14.4, temporary folder, 13:32 UTC): API reader 18 + 27, server code 102, package manifest, site references, all pass. Windows (Python 3.12.10): API reader 45, gate and job runner 81, Chrome proxy 12, trial harness 68: all pass. Site: 265 static references with none missing; the browser checks through the moved tools/tests ran to the end against the local copy with no error and no 404 reported |
| Dependency list for `tools/` | IMPLEMENTED | `tools/requirements.txt`, taken from the working environment; an install from it on a clean machine was not tried |
| GitHub: a separate private repository by clean initial import; account and Drive location confirmed by Gev before anything is published | PLANNED | brief of 07.10.2026 |
| Credentials clean-up on Windows | BLOCKED on a decision | see [`SECURITY.md`](SECURITY.md) |

## 7. Business numbers

| Item | Value | Status |
| --- | --- | --- |
| Completed orders a day, revenue, average bill, cost per order, margin | UNKNOWN | no order log; target is 5 a day |
| What the owner says: answers calls 24/7, two shifts, 4–6 orders a day, the manipulator is his own | Armen, 06.10.2026 | not measured |
| Fleet and drivers: 3 tow trucks, 2 drivers | Gev, 04.10.2026 | conflicts with "50 machines day and night" (Armen, 06.10.2026); not used anywhere; open |
| Ad spend | 0 ₽ | VERIFIED, cabinet 06.10.2026 |
| Competitors in Maps, week 21–27.09, radius 5 km: KRYUK24 fifth with under 1 % of the category traffic | Yandex report | VERIFIED 05.10.2026 |

---

# Հայերեն

Միայն ստուգված վիճակը։ Վերջին թարմացումը՝ 07.10.2026, սերվերի կոդի համեմատումից հետո (13:08 UTC)։ Այսօրվա ցանկացած փաստի համար միակ աղբյուրը էս ֆայլն ա. չհամընկնող հին նշումները փոխարինված են։

Վիճակներ. **IMPLEMENTED** (գրված կամ կարգավորված ա), **VERIFIED** (Claude-ը տեսել ա նշված աղբյուրում նշված օրը), **BLOCKED** (առաջ չի գնում, պատճառը գրված ա), **PLANNED** (ոչինչ գրված չի)։ «Չստուգված» ու «UNKNOWN» նշանակում են հենց դա։ «Արմեն» ու «Գև» որպես ապացույց՝ իրանց խոսքն ա, Claude-ը չի ստուգել։ Ժամերը UTC են, եթե ուրիշ բան չի գրված (MSK = UTC+3, Երևան = UTC+4)։ VPS-ի հասցեն անձնական նշումներում ա։ Գաղտնիքի արժեք էստեղ չկա։

## 1. Ժամկետներ

| Ինչ | Մինչև | Ով | Վիճակ ու ապացույց |
| --- | --- | --- | --- |
| API reader-ի 11-րդ քայլը. մեկ հսկվող գրող գործարկում | 08.10.2026, 06:00 UTC-ից հետո (10:00 Երևան) | Claude | PLANNED. `runtime/api_reader/README.md`, քայլ 11 |
| Avito. 24 հայտարարություն փակվում ա, մնացորդ 0 ₽։ HOLD, ոչինչ չի վճարվել ու չի փոխվել | 11.10.2026 | Գև (որոշում) | VERIFIED, Avito API, 07.10.2026 11:57 |
| Yandex Բիզնեսի քարտի հասցեի հաստատում (վիդեո)։ Բանները կաբինետում դեռ կա | 13.10.2026 | Արմեն | VERIFIED, կաբինետ, 06.10.2026. ժամկետը 07.10-ի շրջայցում նույնն էր |
| Avito. 1-ը փակվում ա 14.10-ին, ևս 20-ը՝ 15.10-ին, 1-ը՝ 26.10-ին | 15.10.2026 | Գև (որոշում) | VERIFIED, Avito API, 07.10.2026 11:57 |
| Հոստինգի մնացորդ (հոստինգ + VPS + IPv4, մոտ 49 ₽ օրը) | մոտ 15.11.2026, հաշվարկ | Գև / Արմեն (վճարում) | VERIFIED, երեք ընթերցումը՝ 4.1-ում |
| Կայքի SSL վկայական | 30.12.2026 | հոստինգ (ինքնաթարմացումը չստուգված) | VERIFIED 06.10.2026 |
| `runtime.kryuk24.ru`-ի վկայական (Let's Encrypt) | 04.01.2027 | `certbot.timer` | VERIFIED, սերվեր, 07.10.2026 06:29 |
| Դոմեն kryuk24.ru | 01.10.2027 | — | չստուգված 01.10.2026-ից հետո |

## 2. Կայք kryuk24.ru

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Կենդանի կայք = git `main` = `v33.1-live` պիտակ | VERIFIED | 06.10.2026. 58-ից 57 hash-ը համընկնում ա. 58-րդը `.htaccess`-ն ա, դրսից չի տրվում |
| Կենդանի ստուգումներ. issues 0, errors [], links_bad [], փորձնական երթուղի 11 կմ / 5 100 ₽ | VERIFIED | `tools/tests/run_checks.py live`, 06.10.2026 |
| Ութ էջ. գլխավոր, հինգ քաղաք, մանիպուլյատոր, սպեցտեխնիկա. sitemap-ում 8 URL. Химки-ի էջը բաց ա | VERIFIED | 06.10.2026 |
| Հաշվիչ (չգործարկվող մեքենա). անիվները պտտվում են՝ 4 000 ₽-ից. 1 փակ անիվ՝ 5 500. 2՝ 7 000. 3՝ 8 500. 4՝ 10 000. «չգիտեմ»՝ 4 000 ու նշում | VERIFIED | փորձված կենդանի կայքում, 06.10.2026։ 1 500 ₽ ամեն անիվին՝ Արմենի պատասխանն ա (06.10.2026) |
| «Ճանապարհը մինչև հաճախորդ անվճար ա» միտքը կայքում չկա | VERIFIED | 06.10.2026 (Արմեն՝ «по договоренности») |
| Սակագնի տողեր կայքում. մանիպուլյատոր հերթափոխով, 5–6 ժամ տեղում՝ 25 000 ₽. խրված մեքենան հանել առանց տեղափոխման՝ 5 000 ₽-ից | VERIFIED | 06.10.2026։ Երկրորդ տողը բաց հակասության մաս ա, տես [`DECISIONS.md`](DECISIONS.md) |
| `assets/logo-dark.png`-ն ու SEO էջերի `theme-color`-ը դեռ սև են, մնացած կայքը կապույտ ա | VERIFIED | 06.10.2026։ Կուղղվի հաջորդ հրապարակմամբ |
| VPS-ում եղած կայքի պատճենը (59 ֆայլ) բայթ առ բայթ նույնն ա, ինչ `site/`-ը | VERIFIED | սերվեր, 07.10.2026 13:08։ Սերվերում որ թղթապանակում ա՝ էս փաստաթղթի աղբյուրներում գրված չի. էստեղ UNKNOWN |
| Հոստինգի հաշվի տնային թղթապանակում (ոչ `public_html`) մնացել են երեք zip ու մեկ հին նկար, կայքից 404 են | VERIFIED | 06.10.2026 |
| `site/README.md`-ում վերջին հրապարակումը գրված ա `v32-live` | հնացած տող | կենդանի պիտակը `v33.1-live`-ն ա (06.10.2026). հրապարակման քայլերը նույնն են |

## 3. Սերվեր ու runtime

### 3.1 Մեքենան ու ծառայությունները

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| VPS հոստինգի ամպում, Ubuntu 26.04.1, 2 միջուկ / 2 ԳԲ / 30 ԳԲ, օրը 27 ₽ + 5 ₽ (IPv4) | VERIFIED | սերվեր, 07.10.2026 06:29 |
| Մուտք միայն SSH բանալիով, օգտատեր `kryuk` (sudo). SSH-ով գաղտնաբառով մուտքը փակ ա. `root`-ի գաղտնաբառը կողպված ա 07.10.2026-ից | VERIFIED | սերվեր, `passwd -S`՝ `L`, 07.10.2026 |
| Firewall. 22, 80, 443 | VERIFIED | սերվեր, 07.10.2026 06:29 |
| `kryuk-capture`. active / enabled, `127.0.0.1:8788`, STAGING, `sending_enabled: false`։ Runtime v0.8.1 + Bro queue bridge v0.1.1, աշխատում ա `kryuk-run`-ի տակ | VERIFIED | սերվեր, `/health`, 07.10.2026 13:02 |
| `kryuk-bro-api` (Bro HTTP bridge v0.2.0). active / **disabled**, `127.0.0.1:8789`։ Reboot-ից հետո ինքը չի բարձրանա, `/bro/v1/`-ը կտա 502 | VERIFIED | սերվեր, 07.10.2026 13:02 |
| Nginx. `https://runtime.kryuk24.ru`, ամբողջը Basic auth-ի հետևում (տիրոջ realm), առանձին `location ^~ /bro/v1/`՝ իր գաղտնաբառի ֆայլով։ IP-ի կանոն չկա | VERIFIED | սերվեր, 07.10.2026 06:29 |
| `kryuk-operations.timer`. ամեն օր 06:00 UTC (10:00 Երևան), պլանավորում ա օրվա տասը գործը | VERIFIED | սերվեր, 07.10.2026 13:00–13:02 (`facts-before.txt`) |
| `kryuk-backup.timer`. ամեն օր մոտ 00:00–00:05 UTC։ Պահուստի ժամը պլանավորման ժամը չի | VERIFIED | սերվեր, 07.10.2026 13:00–13:02։ Հին նշումը, թե 10:00-ի պլանավորումը պահուստն էլ ա անում, փոխարինված ա |
| `certbot.timer` կա. Bro-ի timer չկա. API reader-ի timer չկա | VERIFIED | սերվեր, 07.10.2026 |
| Կենդանի կայքը runtime-ին կապված չի. LIVE ռեժիմ չկա | VERIFIED | սերվեր, 07.10.2026 |
| Բազայի բոլոր հայտերը թեստային են | VERIFIED | սերվեր, 07.10.2026 06:29 |

### 3.2 Կոդը սերվերում (համեմատում, 07.10.2026 13:08 UTC)

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| `/opt/kryuk24`-ում 163 ֆայլ կա. 139-ը նույնն են, ինչ էնտեղ գտած GPT-ի release manifest-ը | VERIFIED | սերվեր, 07.10.2026 13:08. պատճենն ու ցուցակը՝ `runtime/server/MANIFEST.md` |
| Մնացածը ճիշտ էս ա. v0.8.1-ի patch-ի ֆայլեր (= GPT-ի v0.8.1 փաթեթ). Bro-ի կամրջի ֆայլեր (= ստացված փաթեթներ). `ops_views.py`. API reader-ի install-ի փոխած 4 ու ավելացրած 3 ֆայլը. 4 պահված պատճեն՝ `*.before-api-read` | VERIFIED | նույնը |
| `ops_views.py`-ն Գևի դիզայնն ա, sha256 `f5f6e9d8…`, պաշտպանված. չի վերագրվում։ Install-ը չի փոխել | VERIFIED | սերվեր, 07.10.2026 13:02 ու 13:08 |
| `runtime/server/`-ը էդ կոդի միայն-կարդալով պատճենն ա։ Ոչ բազա կա, ոչ credential | VERIFIED | 07.10.2026-ի brief, `runtime/server/MANIFEST.md` |
| Վահանակ `/operator/work`՝ նոր դիզայնով 07.10.2026-ից (միայն տեսքն ա փոխվել) | IMPLEMENTED | Գևը նայել ա, արձագանք դեռ չկա։ Հեռախոսի լայնությունն ու մուգ ռեժիմը չստուգված են։ Install-ից հետո էջը զննարկչով չի բացվել՝ չստուգված |

### 3.3 Տվյալներ

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| 07.10.2026-ի հերթը. առավոտյան ինը գործ DONE. Avito-ի գործը վահանակից փակել ա Գևը | VERIFIED | սերվեր, 07.10.2026 06:29 |
| Օրվա հաշվետվության սևագիրը. `APPROVED`, revision 9, digest `3e0c111c…` (Գևը հաստատել ա install-ից առաջ) | VERIFIED | սերվեր, 07.10.2026 13:02 |
| Հին աղյուսակները նույնն են, ինչ հենակետային snapshot-ը (orders 20, contact_interactions 36, ops_tasks 10, ops_observations 10, ops_events 52) | VERIFIED | սերվեր, 07.10.2026 06:29 |
| `bro_receipts` 0, `bro_runs` 0 | VERIFIED | սերվեր, 07.10.2026 13:02 |
| Աղյուսակների բովանդակության hash-երը նույնն են install-ից առաջ, patch-ից հետո ու dry-run-ից հետո (14 աղյուսակ, 0 տարբերություն) | VERIFIED | `bro_snapshot.py`, սերվեր, 07.10.2026 13:00–13:02 |
| Հին բազայի պահուստները `/var/lib/kryuk24`-ում (մի քանի `.sqlite` ու `.json`, mode 644). install-ից հետո collector-ի խումբը կարա մտնել թղթապանակ ու կարդալ դրանք։ Կոդում ու unit-ներում ոչինչ դրանք չի նշում. ոչ մի պրոցես բաց չի պահում | VERIFIED | սերվեր, 07.10.2026 13:08 |
| Էդ պահուստները տանել ենթաթղթապանակ՝ `0700 kryuk-run` | PLANNED | արված չի։ Ոչինչ չի ջնջվում |

### 3.4 API reader v0.3.2 r2

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Կոդը GPT-ն ընդունել ա հսկվող STAGING install-ի համար. install-ի կարգը՝ revision 2 | VERIFIED | GPT, 07.10.2026. `runtime/api_reader/README.md` |
| Քայլ 1. փաթեթը սերվերում, 23 hash-ից 23-ը OK | VERIFIED | սերվեր, 07.10.2026 13:00–13:02 |
| Քայլ 2. փաստերը կարդացվել են (journal mode `wal`. թղթապանակը `kryuk-run:kryuk-run 750`, բազան `600`. կոդը `root:root`. կոդն օգտագործում են չորս unit, բոլորը `User=kryuk-run`, `UMask=0077`). snapshot ու բազայի պահուստ | VERIFIED | `/root/api-read-install/facts-before.txt`, նույն ժամին |
| Քայլ 3. խումբ `kryuk-db` (անդամներ `kryuk-run`, `kryuk-api-read`), system օգտատեր `kryuk-api-read` (nologin) | VERIFIED | սերվեր, նույն ժամին |
| Քայլ 4. երկու իրական օգտատիրոջով փորձ ժամանակավոր բազայում. `RESULT: PASS`, 7-ից 7 | VERIFIED | սերվեր, նույն ժամին |
| Քայլ 5. կանգնեցվել են երկու timer-ը, հետո երկու ծառայությունը. պլանավորման կամ պահուստի ընթացիկ run չկար | VERIFIED | սերվեր, նույն ժամին |
| Քայլ 6. `install_patch.py check`, հետո `apply`՝ `APPLIED`. սկավառակի յոթ ֆայլի hash-երը համընկնում են README-ի ցուցակին ու փաթեթին | VERIFIED | սերվեր, նույն ժամին |
| Քայլ 7. միայն իրավունք ա ավելացվել. թղթապանակը `kryuk-run:kryuk-db 2770`. բազան ու `-wal` / `-shm`-ը `kryuk-run:kryuk-db 660` | VERIFIED | սերվեր, նույն ժամին |
| Քայլ 8. վերադարձվել ա նախկին վիճակը (`kryuk-capture` active / enabled, `kryuk-bro-api` active / disabled, երկու timer-ը active / enabled). `/health`՝ STAGING, ուղարկելը անջատված | VERIFIED | սերվեր, 07.10.2026 13:02 |
| Քայլ 9. credential-ները դրվել են `/etc/kryuk24-api-read`-ում (`root:kryuk-api-read 750`, ֆայլերը `640`). պատասխանը՝ `written: beget-read.json, yandex-read.json`. բացելու ստուգումները ALLOWED / DENIED՝ ոնց սպասվում էր. `/etc/kryuk24-bro`-ն անփոփոխ ա | VERIFIED | սերվեր, 07.10.2026 13:02։ Սկրիպտը գործարկել ա Claude-ը. արժեք ոչ մի տեղ չի տպվել |
| Քայլ 10. dry-run `kryuk-api-read`-ով իրական բազայի վրա, միայն կարդալով. exit 0, երեք ընթերցումն էլ OK, երեքն էլ `would_write: false` (այսօրվա տողերը հին տեսակի են ու արդեն DONE) | VERIFIED | սերվեր, 07.10.2026 13:02 |
| Քայլ 11. ստուգել պլանը, դնել `kryuk-api-read.service`-ը, մեկ հսկվող գործարկում, երեք `DONE`՝ `MACHINE_OBSERVED`-ով | PLANNED | 08.10.2026, 06:00 UTC-ից հետո։ Timer չի ստեղծվում |
| Collector-ի unit ֆայլը `/etc/systemd/system`-ում | դրված չի | սերվեր, 07.10.2026 13:02 |
| Install-ից հետո. վահանակի էջը զննարկչով ու `bro_pull.py --queue-only`-ն | չստուգված | երկուսն էլ գաղտնաբառով են։ Ծառայությունների առաջին իրական գրելը նոր խմբով 08.10.2026-ի 06:00 UTC-ի պլանավորումն ա |
| Թեստեր 18 + 27 Windows-ում ու սերվերում | VERIFIED | 07.10.2026 12:37 (սերվեր, ժամանակավոր թղթապանակ, հետո ջնջված) |
| Ամբողջ շղթան իրական ընթերցումներով ժամանակավոր բազայում | VERIFIED | `runtime/api_reader/evidence/real_chain_windows_v032_20261007T123548Z.json` |
| Sampled պատասխան իրական API-ից. իրոք լցված սկավառակ install-ի ժամանակ. հաշվիչների սեփական ժամային գոտին | չստուգված | `runtime/api_reader/README.md` |
| Install-ի փաստացի զեկույցը GPT-ին | PLANNED | 11-րդ քայլից հետո |

### 3.5 Bro-ի կամուրջն ու զննարկչի ճանապարհը

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Bro-ի HTTP կամուրջը ընդունված ա. առանց կամ սխալ գաղտնաբառով բոլոր ուղիները 401. traversal-ը չի անցնում. 8788 ու 8789-ը դրսից փակ են | VERIFIED | 07.10.2026 |
| Մեկուսացում Bro → տիրոջ ուղիներ. 14-ից 14 մերժված։ Տեր → Bro-ի ուղի. մերժված, հաստատված զննարկչով ու Nginx-ի log-ով (մեկ GET) | VERIFIED | 07.10.2026 |
| Տեր → Bro-ի երեք POST ուղին. սկրիպտային ամբողջ մատրիցան տիրոջ ճիշտ գաղտնաբառով | չստուգված | GPT-ն հրաժարվեց սկրիպտային մատրիցայից |
| Իրական adapter (առանց հսկողության Claude-ը Chrome-ով կաբինետ կարդա) | BLOCKED | երբեք չի գործարկվել։ Proxy-ի v5.3 փաթեթը սպասում ա GPT-ի որոշումներին |
| Gate ու job runner v3.2. gate 50 թեստ OK, job 31 OK | VERIFIED | Windows, 07.10.2026. `runtime/wip/adapter_preflight/` |
| Trial harness v5.3. 68 ինքնաթեստ OK։ Հինգ իրական run կա | VERIFIED | `runtime/wip/trial/TRIAL_PLAN.md`. ապացույցները՝ `C:\Users\Admin\KRYUK24-Bro-Trial` |
| T1 / attempt-04. CLEAR 16/16 (08:01), GPT-ն ընդունել ա, հետո նեղացրել. `T1.9`-ը չի ապացուցում, որ գործիքը թողել ա հենց hook-ի allow-ը | VERIFIED | ledger ու review-ի նշումներ, 07.10.2026 |
| T1 attempt 01, 02, 03. BLOCKED, անփոփոխ պահված։ 02-ն ու 03-ը քշվել են զուգահեռ մեկ հաստատումով (Claude-ի սխալը. v5.2-ում lock ա ավելացվել) | VERIFIED | `TRIAL_PLAN.md`, բաժին 0f |
| T2 / attempt-01. BLOCKED (7 PASS, 2 INCONCLUSIVE)։ Առանց hook-ի ու allow կանոնի երկու գործիք աշխատեց (`list_connected_browsers`, `tabs_context_mcp`). `tabs_create_mcp`-ն մերժվեց. էջ չբացվեց։ GPT. fail-closed պահանջը չի կատարվել, բացառություն չկա | VERIFIED | 07.10.2026 08:10 |
| Chrome proxy. 12 թեստ OK. կենդանի՝ առանց մոդելի. առանց policy-ի՝ մերժում, փորձի policy-ով՝ զննարկիչների ցուցակը | VERIFIED | 07.10.2026 08:23. `runtime/wip/chrome_proxy/README.md` |
| Իսկական Claude-ի run proxy-ով. proxy-ին հարմարեցված harness. առանձին `--user-data-dir` փորձի Chrome-ի համար. Linux-ի տարբերակ | արված չի | նույն ֆայլը |
| T2 չկրկնել, T3 չսկսել. model run՝ միայն Գևի նոր «հա»-ով | գործում ա | GPT ու Գև, 07.10.2026 |

## 4. Արտաքին ծառայություններ

### 4.1 Հոստինգ (Beget)

| Ընթերցում | Արժեք | Աղբյուր |
| --- | --- | --- |
| 07.10.2026, առավոտ | 1 997,33 ₽, «40 days» | վահանակ |
| 07.10.2026 09:07 UTC | 1 965,56 ₽, 41 օր | API (`user/getAccountInfo`) |
| 07.10.2026 13:02 UTC | 1 960,22 ₽, 40 օր | API, dry-run սերվերում |

Երեքն էլ ճիշտ էին իրանց պահին։ Մնացորդը միշտ գրվում ա ժամով ու աղբյուրով։ Տարիֆ «Blog», օրը 49,1 ₽ (API, 09:07)։ `days_to_block`-ը API-ի գնահատականն ա, ոչ երաշխավորված ժամկետ։ Գևը 06.10.2026-ին լիցքավորել ա 2 000 ₽ (Գև)։

API-ի մուտքը՝ VERIFIED 07.10.2026 09:07։ Թույլատրված մեթոդները սահմանափակված են «Account administration»-ով (Claude-ը փոխել ա վահանակում. `site/getList`, `dns/getData`, `cron/getList` տալիս են `AUTH_ERROR Method disabled`)։

### 4.2 Yandex Metrica ու Webmaster

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Կարդալու token-ը աշխատում ա Metrica-ի ու Webmaster-ի համար | VERIFIED | `tools/api_setup/yandex_check.ps1`, exit 0, 07.10.2026 09:08 |
| Երեք հաշվիչ. կայքինը՝ 113277361 (5 նպատակ. հեռախոս, WhatsApp, Telegram ու երկու ավտոմատ). Yandex Քարտեզի քարտի հաշվիչը. Բիզնեսի ինքնաշեն լենդինգի հաշվիչը | VERIFIED | API, 07.10.2026 09:08 |
| Կայք, վերջին 7 օրը էդ ընթերցմամբ. 415 այց, 364 մարդ. երեկ 15 այց, նպատակներ 0։ Սերվերի dry-run 13:02-ին. կայք 06.10՝ 15 այց / 11 մարդ, `+03:00`, `exact: true` | VERIFIED | API, 07.10.2026։ Այցերի մեջ Գևի ու Claude-ի մուտքերն էլ կան |
| Քարտեզի քարտի հաշվիչ, 7 օր. 141 այց, 4 «զանգել» սեղմում։ Սեղմումը ոչ զանգ ա, ոչ պատվեր | VERIFIED | API, 07.10.2026 09:08 |
| Կայքի նպատակներ, 7 օր մինչև 06.10. հեռախոս 9, WhatsApp 15, Telegram 3 | VERIFIED | API, 07.10.2026 |
| Մինչև 04.10.2026 թվերը աղտոտված են մեր ստուգումներով. դրանից հետո կայքի թեստերը հաշվիչը չեն բեռնում | VERIFIED | `tools/tests/common.py`. 04.10.2026-ի որոշում |
| Հաշվիչների `code_status`-ը API-ում `CS_ERR_UNKNOWN` ա | իմաստը չստուգված | այցեր հաշվվում են |
| Webmaster. մեկ հաստատված host, որոնման մեջ 1 էջ (գլխավորը, 04.10-ից), 8 էջ շրջանցված 200 կոդով, սխալ չկա, 2 խորհուրդ | VERIFIED | կաբինետ 06.10.2026. API 07.10.2026 |
| Կայքի հաշվիչը կապված ա Webmaster-ին, հաշվիչով շրջանցումը միացված ա | VERIFIED | 07.10.2026, Գևի «հա»-ով |
| «Հաշվիչը Webmaster-ում կայքին կապելու հարցում» նամակը չի բացվել | բաց | հաստատելը կոճակ ա, առանձին «հա» ա պետք |

### 4.3 Yandex Բիզնեսի քարտ

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Հասցե՝ «Москва, улица Бехтерева, 41, корп. 1», փոփոխությունը հաստատվել ա 06.10.2026 20:02-ին։ Հաստատման բանները (մինչև 13.10) դեռ կա. վիդեոն չի ուղարկվել | VERIFIED | կաբինետ, 06.10.2026 |
| Հանրային համարը երևում ա. երկրորդ համարը թաքցված ա | VERIFIED | կաբինետ, 06.10.2026 |
| 13 ծառայություն | VERIFIED | կաբինետ, 06.10.2026 |
| Նկարներ. Услуги 14, Оборудование 8, Видео 1, Без категории 2։ «Оборудование»-ի 8-ը գեներացված են, ոչ իսկական. մնում են, մինչև իսկականը լինի (Գև, 06.10.2026) | VERIFIED | կաբինետ, 06.10.2026 |
| Կապույտ լոգոն անցել ա մոդերացիան | VERIFIED | կաբինետ, 07.10.2026 00:22 MSK։ Հանրային տեսքը չստուգված |
| 7 կարծիք, միջինը 4.2. պաշտոնական վարկանիշ չկա | VERIFIED | կաբինետ, 07.10.2026 11:29–11:35 |
| Սերգեյի կարծիքի պատասխանը (5 աստղ, 06.10). **ուղարկված ա. փակված ա Գևի որոշմամբ 07.10.2026-ին. էջից հետ կարդալը ՉՍՏՈՒԳՎԱԾ ա**։ Ուղարկելուց հետո էջը ցույց տվեց «նոր կարծիք չկա». դրված տեքստը էջից չի կարդացվել | IMPLEMENTED, չստուգված | կաբինետ, 07.10.2026։ Տես [`DECISIONS.md`](DECISIONS.md), հակասություն 1 |
| Վիճակագրություն 06.09–06.10. 362 դիտում (Карты 190, Поиск 113, Навигатор 59), 4 «զանգել» սեղմում, 0 երթուղի, 0 անցում կայք | VERIFIED | կաբինետ, 06.10.2026 |
| «Մասամբ ընդունեցինք ուղղումները» նամակը չի բացվել. ինչն ա մերժվել | UNKNOWN | նամակների ցուցակ, 07.10.2026 |
| Կարծիքներն ու մոդերացիայի արդյունքները API չունեն։ Գալիս են նամակով տիրոջ Yandex փոստարկղ (129 նամակ Բիզնեսի ուղարկողից. կարծիքի նամակում ամբողջ տեքստը կա, հեղինակի անունն ու աստղերը՝ չէ) | VERIFIED | փոստ, կարդացված Գևի «հա»-ով, 07.10.2026 |

### 4.4 Yandex Direct

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Մեկ կամպանիա `search_msk_test1`. սևագիր, միայն որոնում, ծախս 0, մնացորդ 0 ₽. հին հինգ կամպանիան արխիվում են | VERIFIED | կաբինետ, 06.10.2026 ու 07.10.2026 |
| Հինգ խումբ, բոլորը սևագիր, ամեն մեկում մեկ հայտարարություն (երկու վերնագիր, երկու տեքստ), Մոսկվա ու մարզ։ 5-րդ խմբում 4 ֆրազ կա, մուտքագրվել էր 5. հավանական պատճառը (կրկնակը միացվել ա) եզրակացություն ա, չի ստուգվել | VERIFIED | կաբինետ, 06.10.2026 |
| Բյուջե. դաշտում՝ շաբաթական 12 000 ₽ (կաբինետ, 06.10). Արմենի վերին սահմանը՝ շաբաթական «до 15.000р» (Արմեն, 06.10). Գև՝ «թիվը ոնց Արմենն ա ասել» (06.10)։ Դաշտը НДС-ով ա, թե առանց | չստուգված | 12 000 × 1,22 = 14 640 ₽ |
| Գործարկման բացեր. առավելագույն ստավկան դատարկ ա. սկզբի օրը փոխելու ա. նպատակների արժեքները լցոն են. быстрые ссылки ու уточнения չկան. մեկ ֆրազը լայն ա. կանգառի շեմերը հաշված են 20 000 ₽-ի համար ու չեն վերանայվել. коллтрекинг-ը վերաստուգելու ա. հաշիվը լիցքավորված չի | VERIFIED | կաբինետ, 06.10.2026. `research/Direct_launch_package_2026-10-04.md` |
| API. պայմանագիրը ընդունել ա Գևը. լրիվ մուտքի հայտը ուղարկվել ա 07.10.2026-ին, վիճակը՝ «новая» | VERIFIED | Direct-ի «Мои заявки» էջ, 07.10.2026 |
| API-ով կարդալը | BLOCKED | error 58 («գրանցումը ավարտված չի»), 07.10.2026 09:21 |
| Չգործարկել, չվճարել առանց Գևի | գործում ա | Գև |

### 4.5 Avito (Գևի HOLD)

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| API-ն կարդում ա | VERIFIED | 07.10.2026 11:05 ու 11:57, միայն կարդալով |
| 46 ակտիվ հայտարարություն, բոլորը autoload-ով, բոլորի գինը 100 ₽, 45-ը նույն կաղապարով վերնագրով | VERIFIED | API, 07.10.2026 11:57 |
| Ժամկետներ. 24-ը մինչև 11.10, 1-ը 14.10, 20-ը 15.10, 1-ը 26.10. մնացորդ 0 ₽. վճարովի առաջխաղացում չկա | VERIFIED | նույնը |
| 30 օրում. 577 եզակի դիտում, 78 կոնտակտ, 27 ընտրյալ. 15 հայտարարություն 0 կոնտակտով. վարկանիշ 5.0, 10 կարծիք (12.09–02.10), ոչ մեկին պատասխան չկա. չկարդացած չատ 0. զանգերի վիճակագրությունը դատարկ ա | VERIFIED | նույնը |
| Հայտարարությունների տեքստն ու նկարները. autoload-ի ֆայլի աղբյուրը. երկարաձգումը վճարովի՞ ա | չստուգված | API-ն չի տալիս. զննարկչի extension-ը կայքը չի բացում |
| Ոչինչ չի փոխվում ու չի վճարվում, մինչև Գևը չասի | գործում ա | Գև, 07.10.2026 |

### 4.6 Փոստ, WhatsApp, մնացած հաշիվները

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Տիրոջ Yandex փոստարկղում հինգ կանոն նամակները տանում են թղթապանակներ (Բիզնես, Avito, կայք, գովազդ). վերահասցեավորում չկա, ոչինչ չի ջնջվում | VERIFIED | փոստ, 07.10.2026, Գևի ասելով |
| 07.10.2026-ին Գևի ասելով բոլոր նամակները նշվել են կարդացած (ոչինչ չի ջնջվել). դրանից հետո «չկարդացած» = նոր | VERIFIED | փոստ, 07.10.2026 |
| Փոստը Bro-ի համար. Yandex-ի հավելված «KRYUK24 Bro Mail» (`mail:imap_full`, `mail:smtp`) | BLOCKED | ստեղծված չի. փոստի credential չկա |
| 07.10.2026-ի կեսօրվա շրջայցում փոստը չի ստուգվել. extension-ը էդ նիստում փոստի կայքը չէր թողնում | արված չի | 07.10.2026 11:29–11:35 |
| WhatsApp Business (հանրային համարը). նկարագրությունը, հասցեն ու կայքը ուղղված են ու վերաբացելով հետ կարդացված. հինգ արագ պատասխան մտցված ա. շապիկի նկարը դրել ա Գևը | VERIFIED | WhatsApp Web, 07.10.2026 |
| WhatsApp. անունը դեռ «Kruk24» ա. քարտեզի նշանը սխալ տեղ ա ցույց տալիս. ողջույնի ու «ղեկին եմ» հաղորդագրությունները միայն հեռախոսում են | բաց | Արմեն, հեռախոսից |
| Շրջայցում WhatsApp-ի ցուցակում չկարդացածի նշան չկար. ոչ մի չատ չի բացվել | VERIFIED | 07.10.2026 11:29–11:35 |
| Նախագծի Google հաշիվ կա (ստեղծել ա Գևը 06.10.2026-ին). վերականգնման փոստը հաստատված չի. ինչի համար ա | UNKNOWN | Գևը չի ասել |
| Տիրոջ համար Google ձևը սևագիր ա, հրապարակված չի. փոխարինվում ա runtime-ում տիրոջ կաբինետով | որոշված | Գև, 07.10.2026 |

## 5. Բրենդ ու մեդիա

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Բրենդի գույնը կապույտ ա (`tools/brand.py`, `INK = #13233A`). լոգոն, ավատարը, մեքենայի գունավորումը, 7 ցուցանակը, QR-ը, WhatsApp-ի հավաքածուն, հասցեի ուղեցույցները վերահավաքված են կապույտով | VERIFIED | Գևի որոշումը 06.10.2026. ֆայլերը |
| Ցուցանակների չափերը. տերը 06.10.2026-ին ուղարկել ա սքրինշոթ՝ բոլոր չափերը շրջանակած, ու ձայնայիններ | UNKNOWN | ինչ ա ասված ձայնայիններում (Claude-ը ձայն չի լսում) |
| Մշակված նկարների սեթ. 23 կադր, համարանիշներն ու անցորդները փակած, աչքով ստուգված։ Երեք նոր կադրը (07.10) ոչ մի տեղ չեն վերբեռնվել | VERIFIED | `photo/01_real_polished/`, 07.10.2026 |
| 07.10.2026-ի վիդեոն պատճենված ա, բովանդակությունը չի դիտվել | չստուգված | ffmpeg չկա |

## 6. Repo, պահուստ, մաքրում

| Կետ | Վիճակ | Ապացույց |
| --- | --- | --- |
| Git. remote չկա, ոչինչ push արված չի | VERIFIED | 07.10.2026 |
| Git bundle բոլոր ref-երով՝ `D:\KRYUK24_backup\`-ում, ստուգված `git bundle verify`-ով ու փորձնական clone-ով (commit-ների քանակն ու HEAD-ը համընկնում են) | VERIFIED | 07.10.2026. `docs/cleanup/CLEANUP_STAGE1_REPORT.md` |
| Git-ից դուրս 15 ֆայլը պատճենված ա `D:\KRYUK24_backup\untracked_2026-10-07\`, ամեն մեկը համեմատված sha256-ով | VERIFIED | նույնը |
| `D:`-ն նույն ֆիզիկական սկավառակն ա, ինչ `C:`-ն։ Էս սկավառակից դուրս պատճեն | չկա | նույնը. GitHub-ի նախապայման ա, չի կատարվել |
| Գաղտնիքների սկան. **նշված ստուգումներով գաղտնիք չի հայտնաբերվել** (pattern-ով սկան tracked տեքստի ու բոլոր 162 commit-ի վրա)։ Նկարները, PDF-ներն ու `.docx`-ը չեն ծածկվում. առանց նշան-բառի, սովորական տեքստով գրված գաղտնիքը չէր երևա | VERIFIED էդ սահմաններում | `docs/cleanup/CLEANUP_STAGE1_REPORT.md`, 07.10.2026 |
| `.mcp.json`-ը git-ում չի. առանց գաղտնիքի `.mcp.json.example`-ը git-ում ա | VERIFIED | `.gitignore`, 07.10.2026 |
| Մաքրման 1-ին փուլը (inventory `docs/inventory/FILES.csv`, 811 տող. պահուստ. audit) | VERIFIED | նույն զեկույցը |
| 2-րդ փուլը (կառուցվածքի կիրառում, էս յոթ փաստաթուղթը, Drive-ի բաժանում) | ընթացքի մեջ | ճյուղ `cleanup/stage2-structure`, 07.10.2026 |
| CI-ի ֆայլ `.github/workflows/ci.yml` | IMPLEMENTED, **GitHub-ում չի աշխատել** (repo դեռ չկա) | ֆայլը. մեջի ամեն հրամանը ձեռքով աշխատացվել ա, տես հաջորդ տողը |
| Ստուգումներ ճյուղի թարմ clone-ից, 07.10.2026 | VERIFIED տեղում | Linux (սերվեր, Python 3.14.4, ժամանակավոր թղթապանակ, 13:32 UTC). API reader 18 + 27, սերվերի կոդ 102, փաթեթի manifest, կայքի հղումներ՝ բոլորն անցնում են։ Windows (Python 3.12.10). API reader 45, gate ու job runner 81, Chrome proxy 12, trial harness 68՝ բոլորն անցնում են։ Կայք. 265 ստատիկ հղում, պակաս չկա. browser ստուգումները տեղափոխված tools/tests-ով մինչև վերջ աշխատել են տեղական պատճենի վրա, սխալ ու 404 չեն գրել |
| `tools/`-ի կախվածությունների ցուցակ | IMPLEMENTED | `tools/requirements.txt`, վերցված աշխատող միջավայրից. մաքուր մեքենայում դրանից տեղադրել չի փորձվել |
| GitHub. առանձին private repo՝ մաքուր սկզբնական import-ով. հաշիվն ու Drive-ի տեղը Գևն ա հաստատում, մինչև որևէ բան հրապարակվի | PLANNED | 07.10.2026-ի brief |
| Credential-ների մաքրումը Windows-ում | BLOCKED՝ որոշման վրա | տես [`SECURITY.md`](SECURITY.md) |

## 7. Բիզնեսի թվեր

| Կետ | Արժեք | Վիճակ |
| --- | --- | --- |
| Օրվա ավարտված պատվերներ, հասույթ, միջին չեկ, մեկ պատվերի ծախս, մարժա | UNKNOWN | պատվերների մատյան չկա. թիրախը օրը 5-ն ա |
| Տիրոջ ասածը. զանգերին պատասխանում ա 24/7, երկու հերթափոխ, օրը 4–6 պատվեր, մանիպուլյատորը իրանն ա | Արմեն, 06.10.2026 | չափված չի |
| Պարկ ու վարորդներ. 3 էվակուատոր, 2 վարորդ | Գև, 04.10.2026 | չի համընկնում «50 մեքենա գիշեր-ցերեկ»-ի հետ (Արմեն, 06.10.2026). ոչ մի տեղ չի օգտագործվում. բաց ա |
| Գովազդի ծախս | 0 ₽ | VERIFIED, կաբինետ 06.10.2026 |
| Մրցակիցները Քարտեզում, շաբաթ 21–27.09, շառավիղ 5 կմ. KRYUK24-ը հինգերորդն ա, կատեգորիայի տրաֆիկի 1 %-ից պակաս | Yandex-ի հաշվետվություն | VERIFIED 05.10.2026 |
