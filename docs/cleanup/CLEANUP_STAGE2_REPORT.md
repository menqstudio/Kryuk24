# KRYUK24 — cleanup stage 2: structure, server code, documents, CI, fresh-checkout checks

Prepared by Claude on 07.10.2026, branch `cleanup/stage2-structure` (from `main` at `7b1c92f`). For GPT's review.

> **Written before publication.** What follows is the state of the branch on 07.10.2026 before the first push. The push, the off-disk copy, the Drive upload and the CI results came after it and are in `GITHUB_SETUP_RESULT.md` and `docs/CURRENT_STATE.md`.

**At the time of writing:** no remote, no push, no Drive upload, no history rewrite. Nothing on the server was changed by this stage (one read-only fetch of the code). `main` is untouched and stays the working branch until this one is reviewed.

## 1. The new tree (as it would be published: 500 files, 30.7 MB)

```
README.md                      the one entry point (EN + HY)
.gitignore  .mcp.json.example  .github/workflows/ci.yml  .claude/skills/learn-by-doing/
docs/
  ARCHITECTURE.md  CURRENT_STATE.md  DECISIONS.md  ROADMAP.md  OPERATIONS.md  SECURITY.md     canonical, EN + HY
  LESSONS.md                    working lessons (was in the root)
  media-index.md                what goes to Drive: groups, sizes, access, sha256 by reference
  inventory/FILES.csv           852 files on disk: bytes, git state, full sha256, class, destination
  cleanup/                      stage 1 and stage 2 reports, MAPPING.csv, LEGACY_BACKUPS_STEP.md
site/                 59 files   the live site kryuk24.ru, byte-identical to before and to the server copy
runtime/
  api_reader/         24         API reader v0.3.2 r2: code, tests, fixtures, evidence, deploy files. INSTALLED on the server
  server/             141        the code exactly as installed in /opt/kryuk24 (fetched read-only), with MANIFEST.md
  server_patches/     2          Claude's copy of the installed ops_views.py, an older edge-check patch
  received/           41         GPT's packages as received, with MAPPING.md (which is installed, which is superseded)
  wip/                24         WORK IN PROGRESS, with README.md: adapter_preflight/, chrome_proxy/, trial/
tools/                43         site checks (tests/), generators, api_setup/, requirements.txt, check_site_assets.py, make_inventory.py
research/             11         prices as given by the owner, launch package, audits
brand/                75         brand sources and the renders the tools read
photo/                26         processed photos for publication (plates covered) and the photo rules
offers/               32         texts and kits for the owner
```

Outside git, on disk, git-ignored:

- `_drive_staging/` — 336 files, 84.1 MB, under their old paths: photo originals (restricted), stories, video, generated images, unused web copies, mockups, the old archive, guide videos, the report to the owner.
- `_private/legacy_docs/` — 14 files: the old state documents and the files with personal data.

## 2. What moved (682 files tracked before; none lost)

| Action | Files |
|---|---|
| moved to a new path, content identical | 265 |
| moved, and folder names inside rewritten | 28 |
| kept in place | 45 |
| out of git, to Drive staging | 330 |
| out of git, to private materials: old state documents merged into the canonical ones | 8 |
| out of git, to private materials: personal data or working history | 6 |

`docs/cleanup/MAPPING.csv` has one row per old path: action, new path, sha256 before, and whether the content is identical. The script that made the moves hashed every file before and after: **no file changed content except the 28 listed**, and those changed only in folder names (`06_Landing` → `site` and the like; one absolute Windows path in `tools/make_signage_docx.py` became relative; two WIP files find the gate at `../adapter_preflight`).

Never rewritten: `site/` (must equal the live site), `runtime/api_reader/` (accepted package, hash-locked), `runtime/received/`, `runtime/server/`, `research/`.

Added: `runtime/server/` (139 files from the server + a manifest + one fixture), the seven documents, `docs/media-index.md`, `runtime/wip/README.md`, `runtime/received/MAPPING.md`, `.github/workflows/ci.yml`, `tools/requirements.txt`, `tools/check_site_assets.py`, `tools/make_inventory.py`, the reports in `docs/cleanup/`.

## 3. Review points 1–6

1. **The real source of the runtime.** `/opt/kryuk24` was fetched read-only on 07.10.2026 at 13:08 UTC: 163 files. Each one has a known origin: 139 equal GPT's release manifest found on the server; `ops_backup.py` and `test_ops.py` equal GPT's v0.8.1 package; the Bro bridge files equal the received packages; `ops_views.py` is Gev's design (`f5f6e9d8…`), kept as it is, not overwritten anywhere; 4 files are the API reader patch (expected hashes), 3 are its added files, 4 are its saved copies. In the repository: 139 files in `runtime/server/`. Left out: the database, `/etc` credentials, the 4 saved copies, `reference/` (19 copies of project documents), and the server's `GOOGLE_SHEET.json` (account-specific sheet id). In its place is a **marked test fixture** of the same name with made-up values, so that `sheets_plan.py` and its test run from a checkout; it must never be copied to the server.
2. **The site works from a checkout.** `site/` keeps its images, fonts and icons (59 files, 2.8 MB). Static check: 265 local references, none missing. Browser checks: see section 5.
3. **Moves checked by dependencies.** Every code file that named a moved folder was found by search (25 files) and rewritten by rule; then every test suite was run from a fresh clone (section 5), all tools were byte-compiled, and the site checks were run through the moved `tools/tests`. **Not checked:** the 21 generator scripts were not executed (they need fonts, ffmpeg, a browser, and three of them need inputs that now live on Drive: `docs/media-index.md` says which).
4. **Inventory.** `docs/inventory/FILES.csv` now has the full sha256 and is regenerated by `tools/make_inventory.py`: 852 rows, 494 tracked. The 813 / 811 difference of stage 1: the zip was built before the report and the CSV themselves existed in the tree; the next run counted those two files. The "132 MB of media" in the stage 1 report was wrong: the tracked tree was 107 MB in total, of which media and brand were about 79 MB. Today: 30.7 MB tracked, 84.1 MB staged for Drive.
5. **Actual state.** The API reader is installed (steps 1–10, 07.10.2026 13:00–13:02 UTC); the supervised write run is pending for 08.10.2026 after the 06:00 UTC planning. This is what `docs/CURRENT_STATE.md` says. The six contradictions and their resolutions are in `docs/DECISIONS.md`, section 7; see section 6 below.
6. **One entry point.** `README.md` in the root; the other six canonical documents in `docs/`. The unfinished proxy, gate and trial harness are under `runtime/wip/` with a README that says they run nowhere.

## 4. Secrets and personal data

Wording: **no secret was detected by the stated checks.** That is not a statement that none exists.

| Check | Scope | Result |
|---|---|---|
| Pattern scan (token forms, key blocks, password hashes, credentials in a URL, literal Authorization values, quoted assignments, a word for "password" followed by a value) | 320 text files of the new tree | 7 hits, all test stand-ins or `owner:group` notation |
| The same over text pulled from documents | 12 PDF, 3 DOCX / XLSX | no hit |
| The same over history | every added line of every commit (stage 1) | no real secret detected |

Limits, stated plainly: 159 files are images, fonts or icons and were not read (76 jpg, 64 png, 16 woff2, 3 ico); no OCR was done. PDF text was read from the literal strings of the files; text drawn as outlines or with re-encoded fonts is not readable that way, and the signage PDFs are mostly outlines. A secret written as plain prose with no marker word would not be found.

Personal data after the moves: the owner's personal number, personal remarks and the working history are out of the published tree. **Left, in the accepted API reader package only** (its files are hash-locked): the server address in `runtime/api_reader/provision_from_windows.ps1` (a default parameter) and the mailbox address in `runtime/api_reader/YANDEX_BUSINESS_MAIL_PROPOSAL.md`. They can be turned into configuration at the next package version; changing them now would change the accepted hashes. The public business number stays in the site code, where it belongs.

## 5. Checks from a fresh clone of this branch

**Local results (07.10.2026):**

| Where | What | Result |
|---|---|---|
| Linux: the server, Python 3.14.4, temporary folder, 13:32 UTC | API reader | 18 + 27 pass |
| | server code, `python3 -m unittest discover -p "test_*.py"` in `runtime/server/` | 102 pass |
| | `sha256sum -c` of the API reader manifest | all OK |
| | `tools/check_site_assets.py` | 265 references, 0 missing |
| Windows, Python 3.12.10, 13:48 UTC | API reader | 18 + 27 pass |
| | WIP: gate hook and job runner | 50 + 31 pass |
| | WIP: Chrome proxy | 12 pass |
| | WIP: trial harness self-test | 68 pass |
| | `tools/check_site_assets.py` | 265 references, 0 missing |
| | site browser checks, `tools/tests/run_checks.py` against the local copy | ran to the end; no error and no 404 reported on any page |
| | all scripts in `tools/` byte-compile | yes |

The temporary folder on the server was removed after the run; `/opt/kryuk24` was not touched.

**GitHub CI: written, not run.** `.github/workflows/ci.yml` holds the same commands (Linux: API reader, server code, manifest, site references; Windows: API reader and the three WIP suites). It has never executed, because no repository exists. Its first run is part of the publishing step.

**Does the project reproduce from a fresh checkout?** The code and its tests: yes, as above. The site: yes (static and browser checks). The tools: they compile; they were not run. A server cannot be rebuilt from the repository alone: the database, the credentials and the Nginx configuration are not in it by design, and a restore procedure for them has not been written or tried (`docs/OPERATIONS.md` marks this UNKNOWN).

## 6. The six contradictions

| # | Contradiction | Resolution | Evidence |
|---|---|---|---|
| 1 | Reply to Sergey's review: open in the task list, sent in the state file, with different texts | **Closed by Gev's decision (07.10.2026): a reply exists, enough for this stage.** | The read-back of the posted text is UNVERIFIED: no browser was connected when it was tried |
| 2 | Old handoff: "no API", Beget 0 ₽ | Superseded; `docs/CURRENT_STATE.md` is the only source | API readings of 07.10.2026 |
| 3 | "No service has an API connection" | Superseded: Beget, Metrica, Webmaster are read by API | `runtime/api_reader/evidence/`, server dry-run 13:02 UTC |
| 4 | Beget balance, three numbers | Each is true at its time; a balance is always written with time and source | panel 07.10 morning 1 997,33 ₽; API 09:07 UTC 1 965,56 ₽; API 13:02 UTC 1 960,22 ₽ |
| 5 | `RULES.md` cited as rules | It is an unapproved draft; no canonical document cites it as a rule; the file is in the private materials | — |
| 6 | Tariff "from 4 000" vs "from 5 000" | **Open: the owner's decision.** Site and card keep the current wording; no document states either as settled | waits for Armen's answer |

## 7. Additional access on the server, recorded

Old hand-made copies of the database in `/var/lib/kryuk24` (mode 644) became readable by the collector's group with the install. Nothing in the code or the units names them and no process held them open (13:08 UTC). The step that moves them into a `0700` subfolder is prepared in `docs/cleanup/LEGACY_BACKUPS_STEP.md`. **Not executed; nothing deleted.**

## 8. What is still open

| Item | State |
|---|---|
| Copy of the bundle and of the untracked files **off this physical disk** | NOT DONE. `D:` is the same disk. Needs a medium or a destination from Gev. The clean initial import should not happen before it |
| GitHub: separate private KRYUK24 repository, clean initial import, full history kept in the bundle | prepared (this branch is the tree to import); account and settings are Gev's; nothing created |
| Drive upload and file ids in `docs/media-index.md` | not started; location is Gev's |
| Windows environment and MCP credentials clean-up | NOT CLOSED: the secrets are still in the user environment and `.mcp.json` still hands them to four third-party programs. To finish after the move to the server store, without printing values |
| Supervised collector run | 08.10.2026, after the 06:00 UTC planning; first check that the planning wrote and that three tasks are `API_READ`; no timer |
| Generators in `tools/` | compile; not run; not read one by one |
| Node tests of GPT's release (`*.cjs`) | not run |
| `main` and this branch | diverge by design until review; the state file on `main` keeps being updated, and `docs/CURRENT_STATE.md` here must be refreshed from it before the merge |
| Old state documents | merged into the seven documents by a subagent and spot-checked, not compared line by line; the originals are in the bundle and in the private materials |
