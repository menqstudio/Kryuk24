# KRYUK24 — cleanup and GitHub preparation, stage 1: inventory, backup, secrets audit

Prepared by Claude on 07.10.2026, branch `cleanup/inventory-2026-10-07`. For GPT's review.

**Stage 1 changes nothing that existed.** No file in the repository was moved, renamed, archived or deleted. No history was rewritten, nothing was pushed, no remote exists. The server, its data, `ops_views.py` and the approvals were not touched. What was added: this report, `docs/inventory/FILES.csv`, and (earlier the same day, on `main`) `.mcp.json.example`.

Stage 2 (apply the structure, write the seven canonical documents, CI) is **not done**. It is described in section 7 and waits for two things named there.

## 1. Backup (done, verified)

| What | Where | Proof |
|---|---|---|
| Git bundle, all refs (3 branches + this one, 8 tags) | `D:\KRYUK24_backup\` | fresh clone from the bundle: same commit count, same HEAD, same number of files, all branches and tags present |
| Everything git does not hold (ignored and untracked, without caches): 15 files, 9.4 MB | `D:\KRYUK24_backup\untracked_2026-10-07\` | every copy compared with its source by sha256; `MANIFEST.sha256.txt` inside |

The backup folder is restricted to the owner account and SYSTEM (inheritance removed). It holds `_private/` (2 files, not opened by Claude) and the local `.mcp.json`, so it is treated as secret-bearing.

**Limit:** `D:` is on the same physical disk as `C:` (one 477 GB drive). This protects against deleting or damaging the folder, not against losing the disk. A copy off this disk is Gev's choice (stick, private repository).

## 2. Secrets audit (no value is shown here or was printed)

Scanned: every tracked text file and every untracked non-ignored text file (357 files; 323 binary or large files were not scanned), and **every added line of all 162 commits on all refs**.

Patterns: Yandex OAuth token form, private key blocks, password hashes (htpasswd / crypt), credentials inside a URL, literal `Authorization` values, quoted assignments to password / secret / token / api key / client secret, AWS and GitHub token forms, long hex after a secret word. Plus a loose pass over prose (a word for "password" in Russian, English or Armenian followed by a value-like word).

| Result | Tree | History |
|---|---|---|
| Real secret found by pattern | **0** | **0** |
| Test stand-ins (values that contain "test", "fake", "example" and the like) | 3 | 3, all still in the tree |
| Loose prose pass | 6 lines, all read with the value masked: file names, `owner:group` notation, one test stand-in | same files |
| File names that suggest a secret or a database, ever committed | 4, all scripts that handle a secret, none a secret file | — |

So no rewrite of history is proposed. **What this audit cannot see:** text inside images, PDFs and `.docx` (132 MB of the repository is media); a secret written as plain prose without any marker word. `_private/` was never committed (confirmed: no path under it in any commit).

**Not secrets, but a decision is needed before any upload, even to a private repository:**

- Personal data in tracked text: phone numbers on 568 lines in 86 files (mostly the public business number in site code; Armen's personal number is among them), mail addresses on 17 lines in 9 files, the VPS address on 7 lines in 6 files, account logins (Yandex, Beget, Avito account id), OAuth client ids (public by design).
- `04_Photo/00_real_source/` (25 files, 13.7 MB): Armen's originals with number plates and people visible.
- `02_Research/Armen_answers_…` and `HISTORY.md`: the owner's words and the working history, including private remarks.

## 3. The tree, with roles

Counts are files on disk; "git" is how many of them are tracked. Roles marked *(by name)* were classified from names and commit history, not by reading every file.

```
Armen/                                  811 files on disk, 680 in git, 107 MB tracked, .git 96 MB
├─ 00_STATE.md  01_TASKS.md  HISTORY.md  LESSONS.md  MISSION.md  RULES.md (draft, not approved)
│  BUSINESS_STATE.md  GPT_HANDOFF_CURRENT.md  README.md      state and decision documents; to be merged (section 6)
├─ .gitignore  .mcp.json.example                              config; the example holds no secret and no id
├─ .claude/skills/learn-by-doing/                             working instruction for Claude (1 file in git)
├─ 02_Research/            13 files   prices as given by the owner, his answers, Direct launch package: accepted source
├─ 03_Brand/               76 files   10 MB  logo, lockups, avatar, livery, favicon, signage: brand assets (svg sources + rendered)
├─ 04_Photo/               92 files   59 MB
│  ├─ 00_real_source/      25         originals from the owner (plates and people visible)
│  ├─ 01_real_polished/    23         processed, plates covered: what may be published
│  ├─ 02_stories/ 03_video/           7, 18 MB  rendered stories and one promo video
│  ├─ 04_generated_mood/ 05_hero_bg/  7, 16 MB  generated images, used only as mood on the site
│  └─ 06_web_unused/       27         web-size copies not used on the site
├─ 05_Offers_and_forms/    35 files   10 MB  texts for the owner, WhatsApp kit, QR, address video guide
├─ 06_Landing/             59 files   3 MB   THE LIVE SITE kryuk24.ru (tag v33.1-live): canonical code
├─ 07_Mockups/navy-light/  64 files   9 MB   design exploration before v32 (by name); 44 of its files are byte copies of 03_Brand
├─ 08_Reports/             12 files   2 MB   one report to the owner (05.10) and its images: generated
├─ 09_Operations/          101 files  1 MB   the runtime and Bro work
│  ├─ bro_api_reader/      24         API reader v0.3.2 r2: canonical, accepted by GPT, INSTALL PENDING
│  ├─ bro_adapter_preflight/ 10 git   gate hook, Windows job object, tool schemas: unfinished, waits for GPT on the proxy
│  ├─ bro_chrome_proxy/     5 git     proxy in front of the Chrome tools: unfinished, never run with a real model
│  ├─ bro_runtime_trial/    8 git     trial harness v5.3 (T1 accepted, T2 blocked): unfinished
│  ├─ patches_by_claude/    2         copy of the installed ops_views.py (protected) and an edge-check patch
│  ├─ from_GPT_v0.7.0/ v0.8.0/ v0.8.1/        GPT's runtime handoffs (documents only; the code is on the server)
│  ├─ from_GPT_bro_v0.1.0/ v0.1.1/ v0.2.0/    GPT's queue bridge and HTTP bridge (installed: v0.1.1 + v0.2.0)
│  ├─ from_GPT_bro_edge_v0.2.0/ v0.2.1/       GPT's edge acceptance checks (v0.2.1 is the used one)
│  ├─ runs/                 1         first manual daily check, 07.10
│  └─ to_GPT_*.md           3         reports already delivered to GPT
├─ tools/                  40 git     site checks (tools/tests, 12), brand and media generators (21), api_setup scripts (7)
├─ _ARCHIVE/               190 files  18 MB  earlier brand, 25 landing backups, rejected logos, unused scripts: already archived
├─ _private/               2 files    NOT IN GIT. credentials-related; not opened
└─ docs/                   new        this report and the inventory
```

Per-file list with size, git state, last commit date, content hash, class and decision: `docs/inventory/FILES.csv` (811 rows; `_private` rows carry no name).

By class: canonical code 102 files; accepted specification or reference 35; tests, fixtures, evidence 23; useful but unfinished 23; old or superseded 271; generated output 140; media and brand 201 (79 MB); state documents 9; secret or machine-specific 4.

## 4. What was moved, archived, deleted

| Where | What | How |
|---|---|---|
| The repository | nothing | — |
| Desktop and Downloads (outside the repository, on Gev's request, 07.10) | 53 items, about 66 MB: exact duplicates of files that are in the repository, and package zips replaced by a later version | **Recycle Bin**, restorable; nothing deleted for good |
| Desktop\ZIP | the current package `KRYUK24_Bro_API_Reader_Package_v0_3_2_r2_from_Claude.zip` | moved there from Downloads (Gev's rule from 07.10: every zip goes to that folder) |

Candidates for removal from git later, **none executed**, each needs a yes:

1. `07_Mockups/navy-light/`: 44 byte-for-byte copies of `03_Brand` files (7.7 MB) plus mockups superseded by the live site.
2. `_ARCHIVE/` (18 MB): move to Drive with an index; keep the mapping.
3. `04_Photo/06_web_unused/` (27 files): unused web copies.
4. Rendered media in general (section 5).

Nothing is proposed for irreversible deletion.

## 5. GitHub and Drive split (proposal)

| GitHub (private) | Drive | Neither |
|---|---|---|
| `06_Landing/` (the site as deployed) | `04_Photo/` originals, polished set, stories, video, generated | `_private/` |
| `09_Operations/` code, tests, fixtures, deploy files, evidence JSON | `03_Brand/` rendered PNG / PDF, signage print files | local `.mcp.json`, `.claude/settings.local.json` |
| `tools/` | `05_Offers_and_forms/` rendered kits, guides, video | databases, live logs, credentials |
| `02_Research/` texts | `08_Reports/` | mail content |
| brand **sources** (svg, generator scripts, `brand.py`) | `07_Mockups/`, `_ARCHIVE/` | |
| the canonical documents (section 6) | package zips and evidence zips | |
| `docs/media-index.md`: for every Drive item a stable file id or link, role, date, sha256 | | |

Rule: Drive never holds a second canonical copy of code or decisions. After a move, each file is checked by sha256 against `FILES.csv`, not by the copy tool's success message.

Open, Gev's decisions: which GitHub account and repository (nothing is created until he names it); which Drive (the project's `kryuk24msk` Google account exists); whether the owner's originals with plates and people go to Drive at all or stay local; whether Armen's personal number and private remarks may be in a private repository as they are.

Effect on size: about 107 MB tracked today, about 8 MB after the split (code, texts, sources). The history would still carry the media (`.git` 96 MB). Two honest options, to be chosen after review: (a) push the history as it is to a private repository; (b) start the GitHub repository from a clean import of the reorganised tree and keep the full history in the bundle. No rewrite is proposed for secrets, because none was found.

## 6. Proposed structure and documents (stage 2, not applied)

```
site/            <- 06_Landing
runtime/         <- 09_Operations code: api_reader/, chrome_proxy/, adapter_preflight/, trial/, server_patches/
runtime/received/<- from_GPT_* as received, with a MAPPING.md (which version is installed, which is superseded)
tools/           <- tools (tests stay next to what they test)
brand/           <- brand sources only
research/        <- 02_Research
docs/            <- README, ARCHITECTURE, CURRENT_STATE, DECISIONS, ROADMAP, OPERATIONS, SECURITY (EN + HY), media-index, inventory
archive/         <- only the mapping file once the content is on Drive
```

Document merge, nothing lost: `00_STATE.md` → `CURRENT_STATE.md`; `01_TASKS.md` → `ROADMAP.md` (one prioritised queue); decisions scattered in `00_STATE.md`, `BUSINESS_STATE.md`, `MISSION.md`, GPT's operating model → `DECISIONS.md`; install, backup, rollback from the package READMEs → `OPERATIONS.md`; secrets and authority → `SECURITY.md`; `HISTORY.md` and `LESSONS.md` stay as they are; `GPT_HANDOFF_CURRENT.md` and `BUSINESS_STATE.md` become pointers. `RULES.md` stays marked as an unapproved draft and is not presented as accepted.

Root entry point: one `CLAUDE.md` / `README.md` pair that says what applies where (today the instructions are spread over the global file, the skill, memory notes and the top of `00_STATE.md`).

CI (to be written, nothing exists): Linux and Windows jobs for `runtime/api_reader` (18 + 27 tests, verified on both today), `adapter_preflight` and `chrome_proxy` and `trial` (Windows only: job objects, `msvcrt`), site checks from `tools/tests` in the mode that does not touch the live site or Metrica. Dependency specification: the runtime code uses the standard library only; `tools/` has a virtual environment whose package list is not yet written down.

## 7. What is unfinished or contradictory

**Stage 2 itself is not done:** structure not applied, the seven documents not written, CI not written, reproduction from a fresh checkout not tested, Drive not prepared. It waits for (1) the API reader install, because GPT's rule is not to move the same files during the install and `09_Operations/bro_api_reader` is the centre of the move; (2) Gev's answers in section 5.

Unfinished work in the tree (not deleted, not treated as ready):

| Item | What is missing | Next step |
|---|---|---|
| API reader v0.3.2 r2 | not installed; two real users sharing the database not proven; server facts not read | Gev's word, then the 11 install steps |
| Chrome proxy, gate, trial harness | never run with a real model through the proxy; T2 blocked; Linux variant absent | GPT's decisions on package v5.3 |
| Credentials | Yandex and Avito secrets still in the Windows user environment; four third-party MCP programs receive them; store location not decided | decision VPS or separate Windows user, then move, verify, remove, restart sessions |
| Real requests and orders | nothing real is recorded; the live site is not connected to the runtime | read the existing runtime code first, then a proposal |
| Approval contract, stale draft | only the report digest is approved today; `REPORT_DRAFT_staleness.md` open | design for GPT |
| Mailbox | no app, no credential | Gev creates the app |
| Monitor without AI | not written | prepare; schedule only with Gev's separate yes |
| `tools/` generators | 21 scripts, several one-off; not read one by one in this stage | classify in stage 2 |
| `tools/.venv` | dependency list not recorded | write `requirements.txt` from what the scripts import |

Contradictions found in the documents (recorded, not resolved here):

1. `01_TASKS.md` lists the reply to Sergey's review as open with one approved text; `00_STATE.md` says a reply was sent, with a different text signed by Armen, and that the posted text was not read back.
2. `GPT_HANDOFF_CURRENT.md` (06.10) says there is no API and Beget is at 0 ₽; corrected by a dated note on top, body not rewritten. Same for `BUSINESS_STATE.md` (05.10).
3. `00_STATE.md` still says in its "Access" section that no service has an API connection; three are read by API since 07.10.
4. Beget balance: 1 997,33 ₽ in the deadlines table (panel, 07.10 morning) and 1 965,56 ₽ by API the same day; both were true at their time, the table was not updated.
5. `RULES.md` is a draft that Gev has not approved, yet other documents refer to its sections.
6. Tariff: "from 4 000" and "from 5 000" for pulling a car out, waiting for the owner's answer.

## 8. Tests run in this stage

`09_Operations/bro_api_reader`: 18 + 27 OK on Windows (Python 3.12.10), 07.10; the same suites OK on the server (Python 3.14.4) earlier the same day for v0.3.2. Other suites (gate 50, job 31, proxy 12, harness 68, site checks) were **not** rerun in this stage; their last recorded results are in `00_STATE.md`.

Reproduction from a fresh checkout: only the bundle clone was tested (it checks out and matches). Running the project from that clone was not tested.

---

# Հայերեն ամփոփում

**Առաջին փուլը ոչ մի եղած բան չի փոխել.** repo-ում ոչ մի ֆայլ չի տեղափոխվել, չի արխիվացվել, չի ջնջվել. պատմությունը չի վերագրվել, push չկա, remote չկա։ Սերվերին, `ops_views.py`-ին ու հաստատումներին չեմ դիպել։

- **Պահուստ.** Git bundle բոլոր ճյուղերով ու tag-երով՝ ստուգված թարմ clone-ով. git-ից դուրս 15 ֆայլը առանձին՝ sha256-ով համեմատված։ Երկուսն էլ `D:\KRYUK24_backup\`-ում են, փակ միայն Գևի հաշվի համար։ D:-ն նույն ֆիզիկական սկավառակն ա, դրսի պատճեն դեռ չկա։
- **Գաղտնիքներ.** Ծառում ու բոլոր 162 commit-ի պատմության մեջ pattern-ով իրական գաղտնիք չի գտնվել. կան միայն թեստային կեղծ արժեքներ։ Սկանը չի տեսնում նկարների, PDF-ների ու docx-ի ներսը։ Պատմության մաքրում չեմ առաջարկում։
- **Անձնական տվյալ.** Հեռախոսներ, փոստեր, VPS-ի հասցե, Արմենի բնօրինակ նկարներ (համարանիշներով ու մարդկանցով). նախքան որևէ upload՝ Գևի որոշումը։
- **Ծառը դերերով**՝ 3-րդ բաժնում, ամեն ֆայլը՝ `docs/inventory/FILES.csv`-ում։
- **GitHub / Drive.** GitHub՝ կոդ, թեստեր, տեքստեր, բրենդի աղբյուրներ, փաստաթղթեր (մոտ 8 ՄԲ). Drive՝ նկար, վիդեո, հաշվետվություն, արխիվ, zip-եր, GitHub-ում դրանց ցուցակը hash-երով։
- **Կիսատ.** Երկրորդ փուլն ամբողջությամբ (կառուցվածքի կիրառում, յոթ փաստաթուղթ, CI, Drive)։ Սպասում ա API reader-ի տեղադրմանը (նույն ֆայլերը միաժամանակ չենք շարժում) ու Գևի չորս պատասխանին. որ GitHub հաշիվը, որ Drive-ը, բնօրինակ նկարները գնո՞ւմ են Drive, անձնական տվյալները մնո՞ւմ են ոնց կան։
