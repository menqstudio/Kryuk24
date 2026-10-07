# Bro API reader v0.3.2 — package for GPT review

Prepared by Claude on 07.10.2026. **Nothing from this package is installed on the server.** The server was only read.

v0.3.1 answered GPT's review of v0.3.0 (time zone in the Metrica query, numbers never cut, installer recovery, isolation claim withdrawn); GPT accepted those collector corrections. v0.3.2 adds only the two steps GPT asked for before a server install: the collector's own service user with the install procedure for it, and the whole chain run with real readings. No new functions. See "Changes in v0.3.2" below.

**Install procedure, revision 2 (07.10.2026).** GPT accepted the v0.3.2 code for a supervised STAGING install and asked for three corrections of the install instruction. They are made here: the negative secrets check no longer uses `cat`; the credentials folder is reachable for the new user without touching `/etc/kryuk24-bro`; no test request is written into the real database. The Python code is byte for byte v0.3.2 except one path in a docstring of `reader_provision.py`; what else changed is this file, the path in `provision_from_windows.ps1` and in the unit example, and two read-only blocks in `deploy/preinstall_facts.sh`.

## What it is

Three daily jobs stop depending on a browser and a model. The server reads the numbers itself over the official APIs:

| Queue job | Source | What is read |
|---|---|---|
| `HOSTING_DEADLINES` | Beget `user/getAccountInfo` | balance, days to block (the API's estimate), daily and monthly rate, plan |
| `METRICA` | Yandex Metrica `stat/v1/data` | site counter 113277361 and Yandex Maps card counter 86067232, as **two evidence sections of the one job** |
| `WEBMASTER` | Yandex Webmaster v4 | summary of the verified host `https:kryuk24.ru:443` |

No new queue job for Maps. `YANDEX_DIRECT` is **not ready** (request sent 07.10, API error 58) and `AVITO` is **on hold** by the owner; neither is contacted. `YANDEX_BUSINESS` stays a browser job.

## Files

| File | Role |
|---|---|
| `bro_api_reader.py` | the readings. No queue, no database. `--out` writes a report file (dry-run) |
| `ops_api.py` | the queue side: claim → lease → observe for `API_READ` tasks; `--dry-run` or `--write` |
| `install_patch.py` | adds the `API_READ` kind to the installed code: `check` / `apply` / `rollback` |
| `reader_provision.py` | server side of credential provisioning (root, standard input only) |
| `provision_from_windows.ps1` | Gev's side of provisioning |
| `deploy/kryuk-api-read.service.example` | one supervised run by hand, as the collector's own user `kryuk-api-read`. No timer, no `[Install]` |
| `deploy/preinstall_facts.sh` | read-only facts about units, the database folder and the code folder; run first, keep the output |
| `deploy/db_share_check.py` | rehearsal in a throwaway `/tmp` folder: two users, one WAL database, shared through a group |
| `fixtures/server_base/` | the seven files exactly as installed on the server on 07.10 (sha256 checked); tests run against them |
| `test_bro_api_reader.py`, `test_ops_api.py` | 18 + 27 tests, no real service, no real secret |
| `evidence/` | real readings through the whole chain into a throwaway database: v0.3.2 (`real_chain_windows_v032_…`) and the earlier v0.3.0 one; `make_chain_evidence.py` is how they are made |
| `YANDEX_BUSINESS_MAIL_PROPOSAL.md` | proposal only; nothing installed. Updated: the whole-mailbox decision is recorded, the forward-only variant is withdrawn |

## What I found in the server code (read on 07.10, 11:14 UTC)

- `kind` is written once, at planning (`ops_work.JOBS`), and `plan()` never touches an existing row. So changing the kind of three jobs affects **only days planned after the patch**. Today's ten rows, their revisions, the report draft (revision 8) and the ten observations stay as they are.
- `kind` is checked in two places only: `ops_work.observe` (machine evidence only for `LOCAL_READ`) and `ops_local.run_local` (takes only `LOCAL_READ`).
- `bro_api.py` and `bro_worker.py` decide by **job name**, not by kind: both list `METRICA`, `WEBMASTER`, `HOSTING_DEADLINES` as browser work. Without a change the browser worker could claim an `API_READ` task before the collector and write `OPERATOR_REPORTED` evidence into it. The patch closes that.
- `ops_views.py` does not read `kind`, and shows trust through `TRUST.get(...)`. `MACHINE_OBSERVED` is already labelled "the server checked it itself", which is exactly true for this collector. So **`ops_views.py` is not in the patch and no new trust value was added.**
- The daily report takes the observations of the other jobs as they are; nothing changes there.

## The patch (exact replacements, each must be found exactly once)

- `ops_work.py`: three jobs get kind `API_READ`; machine evidence is accepted for `LOCAL_READ` and `API_READ`, still refused for everything else.
- `bro_api.py`: `API_READ` tasks are not listed as work and cannot be claimed, observed or drafted over HTTP (403, "outside scope"). Their status still shows in `daily_statuses`.
- `bro_worker.py`: the local adapter bridge skips `API_READ` tasks.
- `test_bro_http.py`: one existing test used `METRICA` as "some other browser task"; it now uses `YANDEX_DIRECT`. Without this one line that test fails with 403 instead of 409.

`apply` refuses unless all four files have the known sha256 and saves each as `<name>.before-api-read`. The files are written one after another, so a failure in the middle is handled:

- a write that fails makes `apply` undo its own work (patched files, saved copies, added files, temporary files) and answer `REFUSED`, exit 2. The folder is then byte for byte what it was;
- if the undo cannot finish, or the process is killed, the saved copies stay and the answer is `PARTIAL`, exit 3. `rollback` accepts such a half-applied folder and can be repeated until it succeeds;
- `rollback` restores every file first and deletes the saved copies last. It gives back every byte and removes the three added files.

This is recovery, not an atomic switch of seven files: for the moment between the first and the last write the folder is mixed. Restart the services only after `APPLIED` or `ROLLED BACK`, never after `PARTIAL`.

## How the rules are met

- **Only reads.** Yandex is asked with GET only. Beget's read method is one POST form to `user/getAccountInfo`; no other Beget method can be requested. The allowed list is checked before any request leaves (`allowed()`): one Beget path, one Metrica path, three Webmaster paths. `webmaster:verify` and the Beget "account administration" category allow more than reading; the collector cannot reach those methods.
- **HTTP.** HTTPS with certificate verification, no redirects followed, 30 s timeout, 1 MB answer limit, no proxy from the environment. Retry (twice) only after a timeout, 429 or 5xx. Auth and request errors are not retried.
- **Secrets.** The collector accepts only `yandex_read_token`, `beget_login`, `beget_api_password`. A file with any other key (actions token, mail, Avito) is refused, and so is a file every user can read. No secret, no Authorization header, no request body and no error body of a service goes into a result, a log or the database; only a short code such as `HTTP_403`, `API_ERROR`, `METRIC_MISSING`. A result that would contain a secret is dropped (`SECRET_IN_REPORT`).
- **Numbers.** A value is recorded only from a valid answer with the expected type. A real zero is recorded as zero. A missing or wrong-typed metric makes the reading `BLOCKED` (`METRIC_MISSING`), with no number at all. A number is never cut or rounded. `NaN` / `Infinity` are refused as not JSON; a number that overflows to infinity, a negative count, a count over 10^9, more users than visits, and goal clicks without a visit are refused as `METRIC_INVALID`. Beget's balance may be negative (a debt); days, rates, page counts and SQI may not.
- **Sampled Metrica numbers.** With `sampled=false` every count must be a whole number; a fraction is refused. With `sampled=true` the numbers are the API's estimates: they are kept exactly as returned, marked `exact: false` and `units: estimated counts`, and `sample_share` must be above 0 and not above 1, otherwise `BLOCKED`. The two consistency checks (users ≤ visits, no clicks without a visit) apply to exact numbers only.
- **Metrica.** Whole days of the Europe/Moscow calendar: yesterday, and the seven finished days ending yesterday. Every query carries `timezone=+03:00` (sent as `%2B03%3A00`), so the days do not depend on the counter's own setting; the evidence records `utc_offset`. `accuracy=full` is asked, and `sampled` / `sample_share` from the answer are kept. Goals are named `goal_clicks` and labelled as clicks on a button, not calls or orders. Site and Maps are never added. If one counter fails, the good section is kept in the observation and the `METRICA` task becomes `BLOCKED`, not `DONE`.
- **Beget.** `days_to_block` carries the note that it is the API's estimate, not a guaranteed deadline.
- **Queue.** Each attempt claims under its own name `API_READ:<random>`. The queue's own `owned()` check refuses a result from an expired or replaced attempt, and a `DONE` task is not claimable, so a repeated run writes nothing. Lease 600 s; the slowest possible reading is 384 s. Only the current Yerevan day can be read, because "yesterday" is counted from now.

## What is verified, and what is not

Verified:
- Windows (Python 3.12.10) and the server (Python 3.14.4, in a temp folder under `/tmp`, removed after; 07.10, 12:37 UTC): `test_bro_api_reader.py` 18 OK, `test_ops_api.py` 27 OK. The socket `ResourceWarning`s GPT saw are gone (the HTTP error object is now closed); the Windows run prints no warning.
- **The whole chain with real readings, v0.3.2, read token only, from Gev's Windows account** (`evidence/real_chain_windows_v032_20261007T123548Z.json`, made by `evidence/make_chain_evidence.py`): the fixtures are copied, `install_patch.apply` is run on the copy, today is planned in a new empty database. Dry-run: three readings `OK`, `would_write: true`, counts unchanged (0 observations, 10 events). Write run: three tasks `DONE`, one `MACHINE_OBSERVED` observation each (3 observations, 16 events). Second write run: three `NOT_CLAIMABLE`, counts unchanged. Second dry-run: `would_write: false`, counts unchanged. The other seven tasks stayed `PENDING`. The Metrica observation with the new fields (`utc_offset`, `exact`, `units`) is 1887 characters; the queue's limit is 4000.
- One real read-only run of the collector alone (`evidence/real_readings_windows_v031_20261007T122005Z.json`): Metrica accepts `timezone=+03:00`; all four Metrica totals sets equal the v0.3.0 evidence taken an hour earlier. That fits counters already set to Moscow time, but it does not prove it: the counters' own zone setting was not read. The first v0.3.1 run blocked `WEBMASTER`: the new upper limit was applied to `user_id`, which is an identifier far above 10^9. Fixed (no upper limit for the identifier) and covered by a test.
- **A real apply process killed in the middle**: `test_a_real_apply_process_killed_in_the_middle_is_recovered_by_rollback` starts `apply` in a real subprocess and kills it (`SIGKILL` on the server, `TerminateProcess` on Windows) while it stands inside its third file write. Only the pause is arranged: the child's `os.replace` reports where it is and waits. After the kill two files are patched, the third is not, a `.new` file is left; a new `apply` refuses; `rollback` gives back every byte.
- SQLite on the server (3.46.1), one user, throwaway `/tmp` folder: with umask 077 the `-wal` and `-shm` files get the mode of the database file (0660 stays 0660, 0600 stays 0600), and in a setgid folder they get the folder's group. Both files are removed when the last connection closes. This is why the plan below needs no change of any unit's `UMask`.
- `deploy/db_share_check.py` ran on the server in its `--same-user` mode (six steps PASS, folder removed). That shows the script works; it proves nothing about two users.
- (v0.3.0, not repeated: the four patched files are byte for byte the same, see the sha256 below) On the server, a temp copy of `/opt/kryuk24` with the patch applied: the server's own suites all pass (`test_ops` 19, `test_bro_worker` 9, `test_bro_http` 24, `test_runtime` 7, `test_secure_server` 12, and the seven small ones). Rollback on that copy returned the four original sha256.
- `reader_provision.py` through a pipe on the server with fake values: folder 750, files 640.

Not verified:
- **Two real users sharing the database.** The users and the group do not exist; creating them is a server change and waits for Gev's word. Step 4 of the install is exactly this test and must say PASS before the real folder is touched.
- **The facts of the real server** that the plan depends on: owner, group and mode of `/var/lib/kryuk24` and `runtime.sqlite`, the units' `User` / `UMask`, which units use `/opt/kryuk24`, whether the code folder is readable by another user. `deploy/preinstall_facts.sh` reads them; it was not run (in this session reading the production server was not permitted to Claude). The script itself is therefore untested.
- The other two "simulated" installer tests are simulations and are named so: write failures are `os.replace` raising, not a really full disk; `test_a_folder_arranged_as_if_apply_died_early…` arranges the files by hand, no process is killed there.
- A sampled answer was never seen from the real API; that rule is tested against the stand-in only.
- Nothing ran against the real server database. `provision_from_windows.ps1` as a whole was not run (it would send the real credentials). The `systemd-run` and unit commands below were not executed.

## Changes in v0.3.2

1. **The collector's own service user.** Unit: `User=kryuk-api-read`, `Group=kryuk-api-read`, `SupplementaryGroups=kryuk-db`. Credentials: their own top-level folder `/etc/kryuk24-api-read` `0750 root:kryuk-api-read`, files `0640` (revision 2: not under `/etc/kryuk24-bro`, which is `root:kryuk-run 0750` and holds the Bro server credential; the new user could not pass through it, and opening it for traversal would weaken that boundary, so it is left exactly as it is); `kryuk-run` is not in that group, so `kryuk-capture` and `kryuk-bro-api` have no file permission to them. Database: a new group `kryuk-db` with exactly two members, `kryuk-run` and `kryuk-api-read`; the database folder gets that group, group `rwx` and setgid; the database file gets that group and group `rw`. Owner stays `kryuk-run` everywhere, no unit's `UMask` changes, permissions are only added. `kryuk-run` must be a member too: the queue code opens and closes the database for every call, so whoever opens it first creates `-wal` and `-shm`, and the other user must be able to use them.
   **What this costs, and it stays written here:** `kryuk-run` gains one group, and the collector can read and write the database file and create and delete files directly in `/var/lib/kryuk24` (SQLite needs that for `-wal` / `-shm`). That is wider than the HTTP worker, which reaches the queue only through the bounded Bro API. The collector is deterministic code with a fixed list of requests, but at the level of file permissions it is trusted with the whole database. It still cannot read the subfolders that are `0700 kryuk-run`.
2. **Install procedure** rewritten for that, with the services stopped while the code is replaced (no process runs mixed code) and their earlier state put back after.
3. **Chain evidence** with real v0.3.2 readings, and the script that makes it.
4. **Report wording.** The earlier "killed apply" test was a simulation. It is renamed to say so, and a test with a really killed subprocess is added.
5. Collector code: one line, the HTTP error object is closed (the `ResourceWarning`s). `provision_from_windows.ps1` passes the group `kryuk-api-read`. Nothing else in the collector, the queue side or the installer changed.

Accepted by GPT and unchanged: the queue split (`API_READ`), `MACHINE_OBSERVED` with no new trust value, no browser fallback for `API_READ` tasks, `ops_views.py` outside the patch, time zone / number rules / installer recovery of v0.3.1, and the sampling rule: a sampled answer is kept as a marked estimate (`exact: false`, `sample_share`, `units: estimated counts`) and the task becomes `DONE`. `DONE` means the reading finished, not that the numbers are exact; whoever uses such a number for a budget decision must say it is an estimate.

## Install (accepted by GPT for supervised STAGING; starts only on Gev's word)

Every step is run by Claude over SSH except step 9. A step that does not give the expected answer stops the install. Not touched at any step: timers (none is added), `sending_enabled`, today's report draft and its digest.

1. Copy this folder to the server, e.g. `/home/kryuk/bro_api_reader`. `sha256sum -c SHA256SUMS.txt`.
2. Facts, read-only: `sudo sh deploy/preinstall_facts.sh > ~/facts-before.txt`. Read it. Expected: journal mode `wal`; owner of the folder and the database `kryuk-run`; the users and groups of step 3 absent; `/etc/kryuk24-api-read` absent; the code folder readable by others. It lists the units that use `/opt/kryuk24`: **that list, not the names written below, is what gets stopped in step 5.** It also holds the table row counts and the report draft digest: the snapshot for step 8. Anything unexpected: stop and report.
3. Users and groups (nothing uses them yet):
   `sudo groupadd --system kryuk-db`
   `sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin kryuk-api-read`
   `sudo usermod -aG kryuk-db kryuk-api-read && sudo usermod -aG kryuk-db kryuk-run`
4. **Two real users, throwaway database only:** `sudo python3 deploy/db_share_check.py --owner kryuk-run --reader kryuk-api-read --group kryuk-db --outsider nobody`. It works in a new folder under `/tmp` and removes it. Must end with `RESULT: PASS` (seven steps). **If it does not: the permissions of the real database are not changed.** Undo step 3 (Rollback, step 5) and stop. This is also the write test of the whole install: both users write, each into files the other created.
5. Back up the database as before each patch. Then write down the state and stop everything that uses the code, timers first:
   `systemctl is-active kryuk-operations.timer kryuk-capture kryuk-bro-api; systemctl is-enabled kryuk-operations.timer kryuk-capture kryuk-bro-api` (expected today: all three active; `kryuk-bro-api` disabled, the other two enabled)
   `sudo systemctl stop kryuk-operations.timer`, then `systemctl is-active kryuk-operations.service kryuk-backup.service` must not say `activating` (a planning or backup run in progress: wait for it to end), then `sudo systemctl stop kryuk-capture kryuk-bro-api`.
6. The patch: `sudo python3 install_patch.py --code /opt/kryuk24 check`, then `apply`. Compare the printed sha256 with the list at the end of this file and with `SHA256SUMS.txt`.
   `REFUSED`: nothing changed; go to step 8 and stop there. `PARTIAL`: **start nothing**; run `rollback` until it says `ROLLED BACK`, then step 8, and stop.
7. Database permissions, additive only, and only after step 4 said PASS (the values before are in `facts-before.txt`):
   `sudo chgrp kryuk-db /var/lib/kryuk24 /var/lib/kryuk24/runtime.sqlite && sudo chmod g+rwxs /var/lib/kryuk24 && sudo chmod g+rw /var/lib/kryuk24/runtime.sqlite`
   `ls /var/lib/kryuk24/runtime.sqlite-wal /var/lib/kryuk24/runtime.sqlite-shm` should find nothing with every service stopped. If one is there, give it the same group and `g+rw`.
8. Put the earlier state back: `sudo systemctl start kryuk-capture kryuk-bro-api kryuk-operations.timer` (only those that were active in step 5; nothing is enabled or disabled). Checks, all of them reads: `/health` answers STAGING with `sending_enabled: false`; the operator page opens; `bro_pull.py --queue-only` returns the queue; `sudo sh deploy/preinstall_facts.sh > ~/facts-after.txt` and `diff` with the first one: the table row counts and the report draft digest must be the same, the differences must be only the ones this install made (group, mode, users, time).
   **No test request is sent to `/capture`: the real database gets no test row.** What stands in for it: the owner of the folder and the file is still `kryuk-run` and only group rights were added, so nothing the services could do before is taken away; the one new situation, `-wal` / `-shm` created by the other user, is exactly what step 4 tested with the two real users. The first real write of the services after the install is the 06:00 UTC planning; it is checked in step 11 before anything else.
9. On Windows Gev runs `provision_from_windows.ps1`. Expected answer: `written: beget-read.json, yandex-read.json`. Then `sudo stat -c '%U:%G %a %n' /etc/kryuk24-api-read /etc/kryuk24-api-read/*.json` must show `root:kryuk-api-read 750` and `640`, and `sudo stat -c '%U:%G %a %n' /etc/kryuk24-bro` must show what `facts-before.txt` shows.
   Access checks. They open the file and read nothing, so nothing can be printed whatever the permissions are; the answer is one word:
   `for u in kryuk-api-read kryuk-run nobody; do for f in beget-read.json yandex-read.json; do printf '%s %s: ' $u $f; sudo -u $u head -c 0 /etc/kryuk24-api-read/$f >/dev/null 2>&1 && echo ALLOWED || echo DENIED; done; done`
   Expected: `kryuk-api-read` ALLOWED twice, `kryuk-run` and `nobody` DENIED twice each. And the other direction, the Bro server credential stays closed to the collector:
   `sudo -u kryuk-api-read head -c 0 /etc/kryuk24-bro/bro-server.json >/dev/null 2>&1 && echo ALLOWED || echo DENIED` must say DENIED.
   Every parent folder on the collector's path, as the collector sees it: `sudo -u kryuk-api-read test -x /etc && sudo -u kryuk-api-read test -x /etc/kryuk24-api-read && echo TRAVERSAL-OK`.
10. Dry-run as the new user; nothing is written. It opens the real database read-only, which in WAL mode already needs the group access, so this is the proof of step 7 on the real database:
    `sudo systemd-run --wait --pipe --collect -p User=kryuk-api-read -p Group=kryuk-api-read -p SupplementaryGroups=kryuk-db -p UMask=0077 -p WorkingDirectory=/opt/kryuk24 /usr/bin/python3 /opt/kryuk24/ops_api.py --db /var/lib/kryuk24/runtime.sqlite --secrets /etc/kryuk24-api-read/beget-read.json --secrets /etc/kryuk24-api-read/yandex-read.json --dry-run`
    On the install day the three tasks still have the old kind, so the answer says `would_write: false` with the real readings. That is the expected result. After it, the snapshot once more (`preinstall_facts.sh`, `diff`): row counts and digest unchanged. Then the factual report goes to GPT; until then the install is not confirmed.
11. The next day, after the 06:00 UTC planning. First: the planning ran and wrote (ten tasks for the new day, three of them `API_READ`) and `stat` of `runtime.sqlite*` shows the group `kryuk-db`. Then copy `deploy/kryuk-api-read.service.example` to `/etc/systemd/system/kryuk-api-read.service`, `sudo systemctl daemon-reload`, and one supervised run: `sudo systemctl start kryuk-api-read`, result in `journalctl -u kryuk-api-read`. After it: the three tasks `DONE` with `MACHINE_OBSERVED`, the other seven untouched, the operator page still opens. **No timer is created.**

## Rollback

1. `sudo systemctl stop kryuk-operations.timer`, wait for a run in progress as in step 5, `sudo systemctl stop kryuk-capture kryuk-bro-api`.
2. `sudo python3 install_patch.py --code /opt/kryuk24 rollback` until it says `ROLLED BACK`.
3. Database folder and file back to the owner, group and mode recorded in `facts-before.txt` (`chgrp`, `chmod`).
4. `sudo systemctl start` the units that were active before; the read checks of step 8.
5. `sudo rm -f /etc/systemd/system/kryuk-api-read.service && sudo systemctl daemon-reload`; `sudo rm -r /etc/kryuk24-api-read`; `sudo gpasswd -d kryuk-run kryuk-db`; `sudo userdel kryuk-api-read`; `sudo groupdel kryuk-db`. The services must be restarted once more after `gpasswd` for `kryuk-run` to lose the group.

Rows already planned as `API_READ` keep that kind. After rollback the browser worker can claim them again by job name; observations already written stay.

## sha256 after `apply`

```
d1e6a2dfa653f40ddbf886c170e8c0d143b1750ad59c1703c647313f7e8818d6  ops_work.py
ebc5cd54d4873b638179862d5cfadbeec1780cc753bd2453c0ba290ea0b7e320  bro_api.py
e5c123894874d9b17136c52cedc2be2498fb2c4113f27a9d03e6324af9ce4e91  bro_worker.py
60d08729512e459cc8d551f42e56f424ff38161fe5969767b8d322ac312125cb  test_bro_http.py
```
The three added files have the sha256 listed in `SHA256SUMS.txt`.

---

# Հայերեն

**Սերվերում ոչ մի բան դրված չի։** Սերվերը միայն կարդացվել ա։

## Ինչ ա սա

Օրվա երեք գործը էլ զննարկիչից ու մոդելից կախված չի. սերվերն ինքն ա թվերը կարդում պաշտոնական API-ներով։ `HOSTING_DEADLINES`՝ Beget, `METRICA`՝ կայքի ու Yandex Քարտեզի քարտի հաշվիչները՝ որպես մեկ գործի երկու առանձին բաժին, `WEBMASTER`՝ հաստատված host-ի ամփոփումը։ Քարտեզի համար նոր գործ չի ավելացվել։ Direct-ը պատրաստ չի (error 58), Avito-ն սպասում ա Գևի խոսքին. ոչ մեկին collector-ը չի դիպչում։

## Ինչ գտա սերվերի կոդում

- `kind`-ը գրվում ա մեկ անգամ՝ պլանավորելիս, ու եղած տողը `plan()`-ը չի փոխում։ Ուրեմն փոփոխությունը վերաբերում ա միայն patch-ից հետո պլանավորվող օրերին։ Այսօրվա տասը տողը, revision-ները, հաշվետվության սևագիրը ու հին դիտարկումները մնում են նույնը։
- `bro_api.py`-ն ու `bro_worker.py`-ն որոշում են գործի անունով, ոչ թե տեսակով. առանց ուղղման զննարկչի աշխատողը կարար `API_READ` գործը collector-ից շուտ վերցներ։ Patch-ը դա փակում ա։
- `ops_views.py`-ն `kind` չի կարդում, `MACHINE_OBSERVED`-ն արդեն ցույց ա տալիս «ստուգել է սերվերն ինքը»։ Դրա համար `ops_views.py`-ն patch-ում չկա։

## Կանոնները

**v0.3.2.** GPT-ն collector-ի ուղղումները (ժամային գոտի, թվեր, installer-ի վերականգնում) ընդունել ա։ Այս տարբերակում միայն երկու բան ա ավելացել, նոր ֆունկցիա չկա. collector-ը աշխատում ա իր առանձին օգտատիրոջ տակ (`kryuk-api-read`), ու ամբողջ շղթան անցել ա իրական ընթերցումներով ժամանակավոր բազայում։

- Միայն կարդալ. թույլատրված հասցեների ցուցակը ստուգվում ա հարցումից առաջ։ Beget-ից հնարավոր ա միայն `getAccountInfo`։
- HTTPS՝ վկայականի ստուգումով, առանց redirect-ի, 30 վրկ, 1 ՄԲ սահման. կրկնում ա միայն timeout / 429 / 5xx դեպքում։
- Collector-ը ընդունում ա միայն կարդալու երեք բանալին. actions token-ով կամ փոստի բանալիով ֆայլը մերժվում ա։ Գաղտնիքը, Authorization-ը ու ծառայության սխալի տեքստը ոչ log-ում են, ոչ բազայում։
- Թիվը գրվում ա միայն ճիշտ պատասխանից։ Իրական զրոն զրո ա. պակաս կամ սխալ տեսակի ցուցանիշը՝ `BLOCKED`, առանց թվի։ Թիվը չի կտրվում ու չի կլորացվում։ Sampled պատասխանի թվերը գնահատական են. մնում են ոնց որ եկել են, նշվում են `exact: false`։
- Metrica՝ Մոսկվայի օրացույցով ամբողջ օրեր (երեկ ու վերջին յոթ ավարտված օրը), հարցման մեջ `timezone=+03:00`. նպատակները սեղմումներ են, ոչ զանգ կամ պատվեր. կայքն ու Քարտեզը չեն գումարվում. մեկի ձախողման դեպքում լավ մասը մնում ա, բայց գործը `DONE` չի դառնում։
- Հերթ՝ ամեն փորձ իր անունով. հին կամ ժամկետանց փորձի արդյունքը հերթը մերժում ա, կրկնակի գործարկումը ոչինչ չի գրում։

## Ինչն ա ստուգված, ինչը՝ ոչ

Ստուգված. 18 + 27 թեստ Windows-ում ու սերվերում (ժամանակավոր թղթապանակում), առանց զգուշացումների։ Ամբողջ շղթան v0.3.2-ի իրական ընթերցումներով ժամանակավոր բազայում (`evidence/real_chain_windows_v032_20261007T123548Z.json`). dry-run-ը ոչինչ չի գրել, write-ը երեք գործը դարձրել ա `DONE` մեկական `MACHINE_OBSERVED` դիտարկումով, երկրորդ գործարկումը ոչինչ չի գրել։ Իրական subprocess-ը սպանվել ա `apply`-ի երրորդ ֆայլը գրելիս, `rollback`-ը վերադարձրել ա ամեն բայթ։ Սերվերի SQLite-ում (մեկ օգտատիրոջով, `/tmp`-ում) `-wal` / `-shm` ֆայլերը վերցնում են բազայի ֆայլի mode-ը ու թղթապանակի խումբը։

Չստուգված. երկու իրական օգտատիրոջով բազայի կիսումը (օգտատերերը չկան. դնելու 4-րդ քայլը հենց էդ փորձն ա). սերվերի իրական փաստերը՝ թղթապանակի ու բազայի տերը, խումբը, mode-ը, unit-ների `User` / `UMask`-ը (`preinstall_facts.sh`-ը չի գործարկվել). sampled պատասխան իրական API-ից չի եկել. սերվերի իրական բազայի վրա ոչինչ չի աշխատել. `provision_from_windows.ps1`-ը ամբողջությամբ չի գործարկվել։

## Դնելը (GPT-ի ընդունելուց հետո, երբ Գևն ասի)

Բոլոր քայլերը անում ա Claude-ը SSH-ով, բացի 9-րդից։ Սպասված պատասխանը չտվող քայլը կանգնեցնում ա դնելը։ Հրամանները՝ վերևի անգլերեն բաժնում։

1. Թղթապանակը տանել սերվեր, ստուգել hash-երը։
2. Կարդալ սերվերի փաստերը (`preinstall_facts.sh`), պահել արդյունքը։
3. Ստեղծել `kryuk-db` խումբն ու `kryuk-api-read` օգտատիրոջը. `kryuk-run`-ին ավելացնել `kryuk-db` խմբին։
4. Փորձ `/tmp`-ում երկու օգտատիրոջով (`db_share_check.py`). պիտի ասի `RESULT: PASS`։
5. Բազայի պահուստ. գրել ծառայությունների վիճակը, կանգնեցնել timer-ը, հետո երկու ծառայությունը։
6. `install_patch.py check`, հետո `apply`, համեմատել hash-երը։ `PARTIAL`-ի դեպքում ոչինչ չմիացնել, նախ `rollback`։
7. Բազայի թղթապանակին ու ֆայլին տալ `kryuk-db` խումբը (միայն ավելացվում ա իրավունք, տերը մնում ա `kryuk-run`)։
8. Միացնել էն, ինչ միացած էր. ստուգել `/health`-ը, վահանակը, հերթը ու բազայի snapshot-ը (տողերի քանակներն ու սևագրի digest-ը նույնը)։ Իրական բազայում թեստային հայտ չի ստեղծվում։
9. Գևը Windows-ում աշխատացնում ա `provision_from_windows.ps1`-ը (գաղտնիքը ոչ ոք չի տեսնում)։ Հետո ստուգում՝ ով կարա բացել ֆայլերը. պատասխանը միայն ALLOWED / DENIED ա, բովանդակություն չի տպվում։ Գաղտնիքների թղթապանակը առանձին ա՝ `/etc/kryuk24-api-read`, `/etc/kryuk24-bro`-ին չենք դիպչում։
10. Dry-run նոր օգտատիրոջով. ոչինչ չի գրում։ Դնելու օրը երեք գործը դեռ հին տեսակի են, պատասխանը կլինի `would_write: false`՝ իրական թվերով։
11. Հաջորդ օրը՝ պլանավորումից հետո, մեկ հսկվող գործարկում `systemctl start kryuk-api-read`։ **Timer չի ստեղծվում։**

## Հետ գնալը

Կանգնեցնել ծառայությունները, `install_patch.py rollback`, բազայի թղթապանակի ու ֆայլի խումբն ու mode-ը հետ բերել գրված արժեքներին, միացնել ծառայությունները, ջնջել unit-ը, `readers` թղթապանակը, օգտատիրոջն ու խումբը։
