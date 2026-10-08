# Lock-aware media store: the patch and its install script / Կողպեքով պահեստ. patch-ն ու install սկրիպտը

**Status, 08.10.2026: written for review. `install.sh` was not run on the server. It is run only after GPT's review and Gev's separate word.**

## EN

### What is here

| File | What it is |
| --- | --- |
| `make_patch.py` | Makes `ops_media.py` and `ops_work.py` from the installed files recorded in `runtime/server/`, by exact replacements. `--check` proves the two files here are what it makes |
| `ops_media.py`, `ops_work.py` | The lock-aware store. sha256 `0f877f77…97df4` and `69aa0809…a251` |
| `install.sh` | Puts the two files into `/opt/kryuk24` on the server, and takes them out again |
| `selftest.py` | A functional check of the two files with the Python that runs it, in a temporary folder |
| `test_install.py` | 38 tests of `install.sh` and `selftest.py` |
| `trial_on_server.sh` | A trial on the server, in a temporary place, of the two things the tests only stand in for: the hold with the real systemd, and the service starting with the new files. Run 08.10.2026 |
| `trial_overlay_on_server.sh` | A second trial: the hold and the guard where `install.sh` puts them, on throwaway units whose unit files and drop-ins are under `/etc/systemd/system`. No real unit is touched and no backup is made. **Written, not run: it waits for GPT's review and Gev's word** |

### What `install.sh` does

```
sudo bash install.sh            # install
sudo bash install.sh rollback   # both originals back
sudo bash install.sh status     # what is installed and what is held; changes nothing
sudo bash install.sh release    # take a left hold away; refused unless the files and the service are confirmed
```

In order, stopping at the first unexpected answer:

1. The two new files beside it have the reviewed sha256. Otherwise STOP.
2. Both installed files are the originals this change was made from (`5ca3e4de…` and `d1e6a2df…`). Both new: `ALREADY INSTALLED`, exit 0. Anything else: STOP, nothing changed.
3. No kept copy is in the way; both files are `root:root 644`; the tools it needs exist; no unit file is waiting for a reload; no timer of a held unit fires within ten minutes.
4. **The hold.** For `kryuk-operations`, `kryuk-api-read` and `kryuk-backup` it writes a drop-in under `/etc/systemd/system/<unit>.d/` with a condition that is false while the drop-in exists. For `kryuk-capture` it writes a drop-in with `Restart=no` and a condition on a marker under `/run`; the script makes that marker only for the seconds of its own restart and removes it again. It reloads systemd and reads back that all four are loaded. From here to the end no timer and no hand can start the three units, systemd does not restart the service by itself, and nothing but this script can start it. **Before it writes anything it looks at the four paths**: a file of that name that it did not write (compared byte for byte with what it writes) stops it with nothing changed, and is never overwritten or removed, by `install`, `rollback` or `release`; a hold of its own left by an earlier run stops a fresh `install` (the way out is `rollback`) and is taken over by `rollback`.
5. None of the three is running (the state is read: a running one-shot unit is `activating`, which `is-active` reports as not active). No other process runs code of the folder except `kryuk-capture` and `kryuk-bro-api`. `kryuk-capture` is running and `/health` answers. The script does not start what was stopped.
6. Both originals are copied beside themselves (`.before-store-lock`) and the copies are checked by sha256.
7. `ops_media.py`, then `ops_work.py`, each put in place by a rename and read back.
8. `selftest.py` runs as the user of `kryuk-capture` (read from the unit, `kryuk-run` today) with `/usr/bin/python3`.
9. Step 5's two checks again, then one restart of `kryuk-capture`. No other service is restarted, started, stopped or enabled.
10. The health check again. The four drop-ins and the marker are taken away.

**A failure in 7 to 10** puts both originals back, `ops_work.py` first. Before anything is put back both kept copies are checked and both installed files must be the original or the new one. Each step is checked by name, not left to `set -e`; the script stops at the first step that fails and does not touch the next file. Only when both checksums are the originals' is the service restarted and asked for health; then the kept copies are removed, the hold is taken away, exit 1.

**When that cannot be done** (a file could not be put back, or the service does not come up with the originals) the script says `STOP`, prints the state of both files, keeps both kept copies, does **not** restart the service on a pair it could not confirm, leaves the one-shot units **held** and the service **guarded**, and exits 2. In that state nothing that loads the two files can start: not a one-shot unit, not the service after a crash (`Restart=no`), and not either of them after a restart of the server, because the drop-ins are on the disk and there is no marker. The guard does not stop a process that is already running: it goes on with what it had loaded, and stays down once it ends. A person looks, then `rollback` (it can be run again): it puts the originals back, starts a service that an earlier run had left guarded, checks `/health` and lets everything go.

**`release`** takes a left hold away only when the state is confirmed: the two installed files are a pair (both original or both new), no half-put file is left, no one-shot unit and no other process of the folder is running, and the service **is running**, was started in a later second than both files were last changed (the same second does not tell the order, so it confirms nothing) and answers `/health`. A stopped service confirms nothing: nothing shows that it works with the files on the disk, so `release` refuses and the way out is `rollback`. Otherwise it says why, changes nothing and exits 2. In the same way `install` does not say `ALREADY INSTALLED` for two new files while a hold is left. There is no option to force it; the drop-ins are four small files that a person can read and delete by hand, knowingly.

`rollback` goes the same way on request: the same hold, the same checks, the same exit 2.

**What it never touches:** any database, any media file, any credential, Nginx, the portal, a timer, a unit file. Its own four drop-ins (`/etc/systemd/system/<unit>.d/90-kryuk-store-lock-install.conf`) exist only while it runs, or after a STOP until a person has put the state right.

**The operating condition (not enforced by the script):** during the maintenance window nobody starts `ops_cli.py` or `bro_worker.py` by hand. The hold is for systemd; the script looks for such a process twice and cannot stop one started after its last look.

### Why the hold (GPT's review of `195c896`)

A process that has loaded the original files writes into the store without the lock. A check that the one-shot units are idle says nothing about the next second: a timer could start one with the original code, and it could still be running beside the restarted service. So nothing that loads these files can start between the first check and the end. `test_install` forces a start at every moment of an install, of a failed install and of a rollback: the stand-in systemd refuses each one, and starts the unit again afterwards.

### Why the hold is on the disk and the service is guarded (GPT's review of `4795423`)

Two ways were left open in which a state that was not confirmed could be run. `release` took the hold away without looking at the files or the service; it now refuses unless the state is confirmed. And the hold lived under `/run`, which a restart of the server empties: after a STOP and a restart the timers were free again, and the enabled `kryuk-capture` would start by itself on files nobody had confirmed. The drop-ins are now on the disk, and the service has one of its own. `test_install` restarts the stand-in server after a STOP and after a killed run: neither the service nor a one-shot unit starts; `release` is refused; `rollback` puts the originals back and lets everything go.

### Why a stopped service confirms nothing, and why systemd may not restart it (GPT's review of `ef2c9e4`)

`release` used to take a stopped service as safe: "nothing runs other files". But after a killed run and a restart of the server both new files are in place, the service is down because of its guard, and nobody has seen it work with them; a release there would let it start on code whose self-test, restart and health check may never have passed. `release` now refuses whenever the service is down.

And the marker used to exist for the whole window, so after `kill -9` it stayed under `/run`, and `kryuk-capture` has `Restart=on-failure`: a crash would have been restarted by systemd on files nobody confirmed. The guard now sets `Restart=no`, and the marker exists only while the script itself restarts the service. `test_install` kills the run at two moments (after the files, and inside the restart) and then lets the stand-in service crash: it stays down; on an ordinary day and after the hold is gone it comes back by itself.

### Why the script looks before it writes (GPT's review of `96b6a9b`)

`hold()` wrote to four fixed paths with `>` and `release()` removed them, without looking whether a file of that name was already there. A drop-in of somebody else under the same name would have been overwritten and then deleted. The script now knows its own files by their exact content and touches nothing else of that name. `test_install` puts a foreign file under the name before an install, before a rollback and before a release, and lets one appear in the middle of a run: it is never changed, and nothing of the script is written beside it. The two trial scripts refuse a name that is already taken in the same way.

**That comparison had a hole (GPT's review of `971c7c2`).** It compared `$(cat file)` with `$(hold_text)`, and command substitution drops every newline at the end: a foreign file that was the script's text plus one empty line passed as the script's own and could be removed. The comparison is now `cmp` on the bytes. `test_install` gives a file four such near-copies (one more newline, three more, the last newline missing, a newline in front) and runs `rollback`, `release` and `install` against each: all stop with nothing changed and the file as it was.

**Who else may write there.** Two runs of this script cannot overlap: each takes a lock (`flock` on `/run/kryuk-store-lock-install.lock`) before it looks at anything, and a second run stops with nothing changed. Another root process that edits the same four drop-in files between this script's look and its write is **not** locked out; nothing on this server does that today (read 08.10.2026: no kryuk unit has a drop-in), and during the maintenance window this script is the only thing that touches them. That is an operating condition, not a guarantee of the script.

### Why this order

The new `ops_media.py` works with the original `ops_work.py`. The new `ops_work.py` does not work with the original `ops_media.py` (`draft()` asks the store for its lock). So the store goes in first and comes out last: a restore that stops after its first step leaves a pair that works. `test_install.Order` holds this.

### Who loads the two files (read from the imports, 08.10.2026)

`secure_server.py` (the service `kryuk-capture`), `ops_daily.py` (`kryuk-operations`), `ops_api.py` (`kryuk-api-read`), `ops_backup.py`, and two command-line scripts started by hand: `ops_cli.py` and `bro_worker.py`. `bro_api.py` (`kryuk-bro-api`) does not. `kryuk-backup` runs `deploy/backup_daily.py`, which loads neither; it is held all the same.

### Facts read from the server (08.10.2026, read-only; `../evidence/store_lock_install_facts_20261008T161433Z.txt` and `…facts2_20261008T164246Z.txt`)

- Both installed files are the originals, `root:root 644`; no `.before-store-lock` copy exists.
- Unit files are in `/etc/systemd/system`; none has a drop-in. `kryuk-capture`, `kryuk-operations`, `kryuk-backup` and `kryuk-bro-api` run as `kryuk-run`; `kryuk-api-read` as `kryuk-api-read`. The unit files in `runtime/server/deploy/` say `User=kryuk`: the repository differs from the server here. Not changed in this round.
- Running from the code folder: `bro_api.py` and `secure_server.py`, nothing else. No cron entry names the folder.
- Timers: `kryuk-backup` 00:04 UTC, `kryuk-operations` 06:00 UTC, both persistent. `kryuk-api-read` has no timer.
- `/var/lib/kryuk24/media` does not exist: the store has never stored a file on the server.

### What was tried, and what was not

| | |
| --- | --- |
| `test_install.py`, 38 tests, Windows with Git Bash (Python 3.12.10) | passed 08.10.2026 |
| The same 38 tests on the server's Linux (bash 5.3.9, Python 3.14.4), as an unprivileged user in a temporary folder, stand-ins only | passed 23:04 UTC, two runs in a row (`../evidence/store_lock_install_tests_server_20261008T230405Z.txt`). A run at 23:00 UTC failed one test: the test that counts the marker also counted the new lock file of the run; the count now leaves the lock out, the script was not changed for it. The 36 tests of the head before: passed 22:37 UTC, four runs in a row (`../evidence/store_lock_install_tests_server_20261008T223756Z.txt`). The first run of this round on Linux, 22:36 UTC, failed one test: the stand-in service was given a start time one second in the future, so on a fast machine a release was confirmed that the test expected to be refused; the starting state of the tests is now as on the server (old files, a service started after them), and the script was not changed for it (the 34 tests of the head before: `../evidence/store_lock_install_tests_server_20261008T181542Z.txt`; earlier heads: `…174635Z.txt`, `…165427Z.txt`) |
| Twenty-one deliberate breaks of the script over the rounds. After `971c7c2`, two, each noticed, checked by a command that fails on a miss: own files recognised through `$(...)` again; the run lock not taken. The round before (after `96b6a9b`), four, each noticed, checked by a command that fails on a miss: no look for a foreign drop-in; `release` removing a file it did not write; a start in the same second counted as after; an install starting over a hold an earlier run left. The round before: `release` taking a stopped service as confirmed; a guard without `Restart=no`; the marker kept for the whole window; two new files with a hold left counted as installed; a rollback that leaves a guarded service down; the marker not removed after the restart. Earlier: `release` without its check; a guard that always lets the service start; the marker left after a STOP; `release` not comparing the start of the service with the files; no hold; a failed restore step that does not stop the restore; a restart although the originals are not back; the hold given up in a state that needs a person; a running one-shot unit accepted | each made its test fail. One of this round, "the marker not removed after the restart", was **not** noticed at first: the test only looked before the restart, and head `858d8b3` was pushed with this row already saying "each". The test now counts the marker at every health check, at the self-test and at the restart, and notices it; corrected in the next commit |
| Rehearsal of the first head on the server in a temporary folder, as `kryuk-run`: status, install, second run, rollback | passed 16:19 UTC (`../evidence/store_lock_install_rehearsal_20261008T161921Z.txt`) |
| The real branches of `install.sh` (units, user, hold, restart, health) | only against stand-ins. They show what the script asks for and what it does with each answer, not that the server answers that way |
| `trial_on_server.sh`: the hold with the real systemd on a throwaway unit; the service started and restarted with the new files in a temporary copy, as `kryuk-run`, on port 18788 | **passed 08.10.2026 17:17 UTC**, 35 checks, after the CI of `25ead0a` was green (`../evidence/store_lock_trial_server_20261008T171738Z.txt`). Real systemd 259: a running one-shot unit is `activating` and `is-active --quiet` answers 3; with the drop-in loaded `ConditionResult` is `no` and the command does not run; with the drop-in deleted it runs again, even before a reload. The service started as `kryuk-run` with Python 3.14.4 on the copy with the two new files, answered `/health`, was restarted (a new process) and answered again; nothing in its journal. Afterwards: no unit, no file, no port left; the real files and the real service (same process since 11:12 UTC) unchanged. **The first run, 17:16 UTC, said TRIAL FAILED**: two of my expectations were wrong (a one-shot unit stopped while its command runs ends as `failed`, not `inactive`); the hold and the service part passed in it too. It is kept beside the second (`…run1_wrong_expectation_20261008T171659Z.txt`); the script was changed only in those expectations. Not shown by that trial: a drop-in applied to a real unit file under `/etc` (the throwaway unit was under `/run`, and the hold was under `/run` then) |
| `trial_overlay_on_server.sh`: the hold on a throwaway one-shot unit and the guard (`Restart=no`, marker) on a throwaway service, unit files and drop-ins under `/etc/systemd/system` | **not run**: it waits for GPT's review and Gev's word. Until then that these drop-ins behave on this server's systemd as in the stand-in is how systemd is documented to work, not seen here. Its first form ran the real `kryuk-backup` once; GPT advised against it and it was never run |
| The real restart of the real `kryuk-capture` with the new files | **not tried**: that is the install |
| A killed script (`kill -9` after both new files were in place) and a restart of the server after it | tried against the stand-in systemd only: everything stays held, `rollback` brings the originals back. Not tried with a real restart of the server |

### Known limits

- The hold stops systemd from starting the three units. It does not stop a person with a shell from running `ops_cli.py` or `bro_worker.py` by hand during the install: the script looks for such a process twice (before the files change and before the restart) and not in between. This is an operating condition of the maintenance window, not a guarantee of the script.
- A script killed with `kill -9` exactly while it restarts the service leaves its marker under `/run` until the server restarts or `rollback` runs: in that state a person could start the service by hand. systemd does not (`Restart=no`), and `status` says that a marker is left.
- The guard does not stop a running process. After a STOP the service that is running goes on with the code it had loaded.
- After a STOP the service is deliberately unable to start. If it crashes in that state it stays down until a person has run `rollback`.
- A timer that fires while its unit is held loses that run. The script refuses to start within ten minutes of one; an install that hangs longer could still lose one.
- The lock file is created with the umask of whoever first takes the lock (`0077` in the units, so mode `600`). Today every unit that can take it runs as `kryuk-run`, and the plan runs the pipeline as `kryuk-run` too (`../INSTALL_PLAN.md`, section 3). A unit under another user would be refused the file; nothing gives it access, and this script does not either.

## HY

**Վիճակը, 08.10.2026. գրված ա review-ի համար։ `install.sh`-ը սերվերում չի աշխատացվել։ Կաշխատացվի միայն GPT-ի review-ից ու Գևի առանձին խոսքից հետո։**

### Ինչ կա էստեղ

`make_patch.py`-ն սարքում ա `ops_media.py`-ն ու `ops_work.py`-ն սերվերում դրված ֆայլերից՝ ճշգրիտ փոխարինումներով։ `install.sh`-ը էդ երկու ֆայլը դնում ա սերվերի `/opt/kryuk24`-ում ու կարողանում ա հետ հանել։ `selftest.py`-ն ստուգում ա, որ երկու ֆայլը գործնականում աշխատում են։ `test_install.py`-ն 31 թեստ ա։ `trial_on_server.sh`-ը սերվերում, ժամանակավոր տեղում փորձում ա էն երկու բանը, որ թեստերում փոխարինողներով են. պահելը իրական systemd-ով ու ծառայության մեկնարկը նոր ֆայլերով։

### Ինչ ա անում `install.sh`-ը

Հերթով, առաջին անսպասելի պատասխանի վրա կանգնում ա.

1. Կողքի երկու նոր ֆայլի sha256-ը review-ածն ա։
2. Դրված երկու ֆայլն էլ բնօրինակն են։ Երկուսն էլ նոր են՝ `ALREADY INSTALLED`։ Ուրիշ վիճակ՝ STOP, ոչինչ չի փոխվում։
3. Պատճեն ճանապարհին չկա, ֆայլերը `root:root 644` են, գործիքները կան, ոչ մի unit ֆայլ reload-ի չի սպասում, պահվող unit-ի timer-ը տասը րոպեից շուտ չի կրակում։
4. **Պահելը։** `kryuk-operations`, `kryuk-api-read`, `kryuk-backup` unit-ների համար `/etc/systemd/system/<unit>.d/`-ում drop-in ա գրում՝ պայմանով, որ կեղծ ա, քանի դեռ drop-in-ը կա։ `kryuk-capture`-ի համար էլ drop-in ա գրում՝ `Restart=no`-ով ու `/run`-ի նշանի պայմանով. նշանը սկրիպտը սարքում ա միայն իր restart-ի վայրկյանների համար ու նորից հանում։ Reload ա անում systemd-ն ու հետ կարդում, որ չորսն էլ բեռնված են։ Էստեղից մինչև վերջ երեք unit-ը ոչ timer-ը, ոչ ձեռքը չի կարող սկսել, իսկ ծառայությունը կարող ա սկսել միայն էս run-ը։
5. Երեքից ոչ մեկը չի աշխատում (վիճակն ա կարդացվում. աշխատող one-shot unit-ը `activating` ա)։ Պանակի կոդով ուրիշ պրոցես չկա, բացի `kryuk-capture`-ից ու `kryuk-bro-api`-ից։ `kryuk-capture`-ը աշխատում ա, `/health`-ը պատասխանում ա։
6. Երկու բնօրինակն էլ պատճենվում են կողքին (`.before-store-lock`) ու ստուգվում sha256-ով։
7. `ops_media.py`, հետո `ops_work.py`, ամեն մեկը՝ rename-ով ու հետ կարդալով։
8. `selftest.py`՝ `kryuk-capture`-ի user-ով։
9. 5-րդ քայլի երկու ստուգումը նորից, հետո մեկ restart՝ միայն `kryuk-capture`։
10. Նորից health։ Չորս drop-in-ն ու նշանը հանվում են։

**7-ից 10-ի ձախողումը** երկու բնօրինակն էլ հետ ա դնում, `ops_work.py`-ն առաջինը։ Հետ դնելուց առաջ ստուգվում են երկու պատճենն ու դրված ֆայլերի վիճակը։ Ամեն քայլը ստուգվում ա առանձին, ոչ թե թողնվում `set -e`-ին. առաջին ձախողված քայլի վրա կանգնում ա ու հաջորդ ֆայլին ձեռք չի տալիս։ Միայն երբ երկու checksum-ն էլ բնօրինակինն են, ծառայությունը restart ա արվում ու health ա հարցվում. հետո պատճենները հանվում են, պահելը հանվում ա, exit 1։

**Երբ դա չի ստացվում** (ֆայլը հետ չի դրվում, կամ ծառայությունը բնօրինակներով չի բարձրանում) սկրիպտը ասում ա `STOP`, տպում ա երկու ֆայլի վիճակը, պահում ա երկու պատճենն էլ, ծառայությունը restart **չի** անում չհաստատված զույգով, one-shot unit-ները թողնում ա **պահված**, ծառայությունը՝ **փակված** (նշանը հանած), ու դուրս ա գալիս 2-ով։ Էդ վիճակում էս ֆայլերը բեռնող ոչինչ չի կարող սկսվել. ոչ one-shot unit, ոչ ծառայությունը crash-ից հետո, ոչ էլ դրանք սերվերի restart-ից հետո, որովհետև drop-in-ները դիսկի վրա են, իսկ նշանը՝ հիշողության մեջ։ Մարդը նայում ա, հետո `rollback`։

**`release`-ը** մնացած պահելը հանում ա միայն երբ վիճակը հաստատված ա. երկու ֆայլը զույգ են (երկուսն էլ բնօրինակ կամ երկուսն էլ նոր), կիսատ դրված ֆայլ չկա, one-shot unit կամ պանակի ուրիշ պրոցես չի աշխատում, ծառայությունը **աշխատում ա**, սկսվել ա երկու ֆայլի վերջին փոփոխությունից հետո ու պատասխանում ա `/health`-ին։ Կանգնած ծառայությունը ոչինչ չի հաստատում (GPT-ի review-ը `ef2c9e4`-ի). էդ դեպքում ելքը `rollback`-ն ա, որ բնօրինակները հետ ա դնում, ծառայությունը բարձրացնում դրանցով ու բաց թողնում։ Թե չէ ասում ա ինչու, ոչինչ չի փոխում ու դուրս ա գալիս 2-ով։ Ստիպելու տարբերակ չկա։

**Ինչին երբեք ձեռք չի տալիս.** ոչ մի բազա, ոչ մի նկար, ոչ մի գաղտնաբառ, Nginx, կաբինետ, timer, unit ֆայլ։ Իր չորս drop-in-ը կան միայն աշխատելու ընթացքում, կամ STOP-ից հետո՝ մինչև մարդը վիճակը կարգի բերի։

**Աշխատանքի պայման (սկրիպտը չի պարտադրում).** maintenance պատուհանի ընթացքում ոչ ոք ձեռքով չի սկսում `ops_cli.py` կամ `bro_worker.py`։ Պահելը systemd-ի համար ա. սկրիպտը էդպիսի պրոցես փնտրում ա երկու անգամ ու չի կարող կանգնեցնել վերջին նայելուց հետո սկսածը։

### Ինչու պահելը դիսկի վրա ա, ու ծառայությունը փակվում ա (GPT-ի review-ը `4795423`-ի)

Երկու ճանապարհ էր բաց մնացել, որով չհաստատված վիճակը կարող էր աշխատել։ `release`-ը պահելը հանում էր առանց ֆայլերին կամ ծառայությանը նայելու. հիմա մերժում ա, եթե վիճակը հաստատված չի։ Ու պահելը `/run`-ում էր, որ սերվերի restart-ը դատարկում ա. STOP-ից ու restart-ից հետո timer-ները նորից ազատ էին, ու enabled `kryuk-capture`-ը ինքը կբարձրանար չհաստատված ֆայլերով։ Հիմա drop-in-ները դիսկի վրա են, ու ծառայությունն էլ իրենն ունի։ Թեստը STOP-ից ու սպանված run-ից հետո restart ա անում փոխարինող սերվերը. ոչ ծառայությունը, ոչ one-shot unit-ը չեն սկսվում, `release`-ը մերժվում ա, `rollback`-ը բնօրինակները հետ ա դնում ու ամեն ինչ բաց թողնում։

### Ինչու պահել (GPT-ի review-ը `195c896`-ի)

Հին ֆայլերը բեռնած պրոցեսը պահեստում գրում ա առանց կողպեքի։ «One-shot-ները հիմա չեն աշխատում» ստուգումը ոչինչ չի ասում հաջորդ վայրկյանի մասին. timer-ը կարող էր մեկը սկսել հին կոդով, ու դա կշարունակեր աշխատել restart արած ծառայության կողքին։ Դրա համար առաջին ստուգումից մինչև վերջ էս ֆայլերը բեռնող ոչինչ չի կարող սկսվել։ Թեստը մեկնարկ ա պարտադրում տեղադրման, ձախողված տեղադրման ու rollback-ի ամեն պահի. ամեն մեկը մերժվում ա, իսկ վերջից հետո unit-ը նորից սկսվում ա։

### Ինչու էս հերթով

Նոր `ops_media.py`-ն աշխատում ա հին `ops_work.py`-ի հետ, հակառակը՝ չէ։ Դրա համար պահեստը դրվում ա առաջինը ու հանվում վերջինը. առաջին քայլից հետո կանգնած restore-ը թողնում ա աշխատող զույգ։

### Ով ա բեռնում էս երկու ֆայլը (կարդացած import-ներից)

`secure_server.py` (`kryuk-capture`), `ops_daily.py` (`kryuk-operations`), `ops_api.py` (`kryuk-api-read`), `ops_backup.py`, ու ձեռքով սկսվող երկու սկրիպտ՝ `ops_cli.py`, `bro_worker.py`։ `bro_api.py`-ն (`kryuk-bro-api`)՝ չէ։

### Ինչ ա փորձվել, ինչ՝ չէ

- 38 թեստ՝ անցել են Windows-ում ու սերվերի Linux-ում (Python 3.14.4, ժամանակավոր պանակ, միայն փոխարինողներով)։
- Սկրիպտը քսանմեկ ձևով դիտմամբ փչացրել եմ (վերջին փուլում՝ երկու)՝ ամեն անգամ իր թեստը ընկել ա։
- **Համեմատությունը հիմա `cmp`-ով ա, բայթ առ բայթ** (GPT-ի review-ը `971c7c2`-ի). առաջ `$(...)`-ով էր, որ վերջի դատարկ տողերը գցում ա, ու մեկ ավել դատարկ տողով օտար ֆայլը կանցներ որպես սկրիպտինը։
- **Երկու run իրար վրա չեն ընկնում** (lock `/run`-ում)։ Ուրիշ root պրոցես, որ նույն չորս ֆայլը նույն պահին փոխի, փակված չի. maintenance պատուհանում էդ ֆայլերին կպնում ա միայն էս սկրիպտը. դա աշխատանքի պայման ա, ոչ երաշխիք։
- **Գրելուց առաջ նայում ա** (GPT-ի review-ը `96b6a9b`-ի). եթե չորս ճանապարհից մեկում նույն անունով ֆայլ կա, որ ինքը չի գրել (համեմատվում ա բայթ առ բայթ), կանգնում ա ու ոչինչ չի փոխում. էդպիսի ֆայլը երբեք չի վերագրվում ու չի ջնջվում՝ ոչ `install`-ով, ոչ `rollback`-ով, ոչ `release`-ով։ Նույն վայրկյանին եղած մեկնարկն ու ֆայլի փոփոխությունը ոչինչ չեն հաստատում։
- `trial_overlay_on_server.sh` (պահելն ու պահակը `/etc`-ում դրված throwaway unit-ների վրա, իրական unit-ի չի կպնում, backup չի սարքում). **գրված ա, չի աշխատացվել**. սպասում ա GPT-ի review-ին ու Գևի խոսքին։
- `install.sh`-ի իրական ճյուղերը (unit-ներ, user, պահել, restart, health)՝ միայն փոխարինողներով։
- `trial_on_server.sh`. **անցել ա 08.10.2026 17:17 UTC-ին**, 35 ստուգում, `25ead0a`-ի CI-ի կանաչից հետո։ Իրական systemd-ով. աշխատող one-shot unit-ը `activating` ա. drop-in-ը բեռնած՝ հրամանը չի աշխատում. drop-in-ը ջնջած՝ նորից աշխատում ա։ Ծառայությունը բարձրացավ `kryuk-run`-ով, Python 3.14.4-ով, երկու նոր ֆայլով պատճենի վրա, պատասխանեց `/health`-ին, restart արվեց ու նորից պատասխանեց։ Հետո ոչ unit, ոչ ֆայլ, ոչ պորտ չմնաց. իրական ֆայլերն ու իրական ծառայությունը չեն փոխվել։ **Առաջին run-ը (17:16 UTC) ասեց TRIAL FAILED**. իմ երկու սպասումն էր սխալ (աշխատելիս կանգնեցրած one-shot unit-ը դառնում ա `failed`, ոչ թե `inactive`). պահելն ու ծառայության մասը էնտեղ էլ անցել էին։ Երկու run-ն էլ evidence-ում են։ Փորձը չի ցույց տալիս, որ `/run`-ի drop-in-ը գործում ա `/etc`-ի unit ֆայլի վրա. դա `install.sh`-ն ինքն ա հետ կարդում իրական unit-ների վրա։
- **Չի փորձվել.** իրական `kryuk-capture`-ի իրական restart-ը նոր ֆայլերով (դա հենց տեղադրումն ա). հոսանքի անջատում կամ սպանված սկրիպտ երկու քայլի արանքում։

### Հայտնի սահմաններ

- Պահելը systemd-ին չի թողնում սկսել երեք unit-ը։ Shell ունեցող մարդուն չի խանգարում ձեռքով աշխատացնել `ops_cli.py`-ն կամ `bro_worker.py`-ն. սկրիպտը էդպիսի պրոցես փնտրում ա երկու անգամ, ոչ թե ամբողջ ընթացքում։
- Timer-ը, որ կրակում ա, երբ իր unit-ը պահված ա, էդ run-ը կորցնում ա։ Սկրիպտը չի սկսում, եթե մինչև timer-ը տասը րոպեից քիչ ա մնացել։
