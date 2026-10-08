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
| `test_install.py` | 31 tests of `install.sh` and `selftest.py` |
| `trial_on_server.sh` | A trial on the server, in a temporary place, of the two things the tests only stand in for: the hold with the real systemd, and the service starting with the new files. Run 08.10.2026 |
| `trial_overlay_on_server.sh` | A second trial: the hold's drop-in on the real `kryuk-backup` unit (it must not run while held, and must run after), and the service's guard on a throwaway unit. **Written, not run: it touches a real unit and makes one extra database snapshot, so it waits for Gev's word** |

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
4. **The hold.** For `kryuk-operations`, `kryuk-api-read` and `kryuk-backup` it writes a drop-in under `/etc/systemd/system/<unit>.d/` with a condition that is false while the drop-in exists. For `kryuk-capture` it writes a drop-in that lets the service start only while a marker of this run exists under `/run`. It reloads systemd and reads back that all four are loaded. From here to the end no timer and no hand can start the three units, and the service can be started only by this run.
5. None of the three is running (the state is read: a running one-shot unit is `activating`, which `is-active` reports as not active). No other process runs code of the folder except `kryuk-capture` and `kryuk-bro-api`. `kryuk-capture` is running and `/health` answers. The script does not start what was stopped.
6. Both originals are copied beside themselves (`.before-store-lock`) and the copies are checked by sha256.
7. `ops_media.py`, then `ops_work.py`, each put in place by a rename and read back.
8. `selftest.py` runs as the user of `kryuk-capture` (read from the unit, `kryuk-run` today) with `/usr/bin/python3`.
9. Step 5's two checks again, then one restart of `kryuk-capture`. No other service is restarted, started, stopped or enabled.
10. The health check again. The four drop-ins and the marker are taken away.

**A failure in 7 to 10** puts both originals back, `ops_work.py` first. Before anything is put back both kept copies are checked and both installed files must be the original or the new one. Each step is checked by name, not left to `set -e`; the script stops at the first step that fails and does not touch the next file. Only when both checksums are the originals' is the service restarted and asked for health; then the kept copies are removed, the hold is taken away, exit 1.

**When that cannot be done** (a file could not be put back, or the service does not come up with the originals) the script says `STOP`, prints the state of both files, keeps both kept copies, does **not** restart the service on a pair it could not confirm, leaves the one-shot units **held** and the service **guarded** with its marker removed, and exits 2. In that state nothing that loads the two files can start: not a one-shot unit, not the service after a crash, and not either of them after a restart of the server, because the drop-ins are on the disk and the marker is in memory. A person looks, then `rollback` (it can be run again).

**`release`** takes a left hold away only when the state is confirmed: the two installed files are a pair (both original or both new), no half-put file is left, no one-shot unit and no other process of the folder is running, and the service either is not running or was started after both files were last changed and answers `/health`. Otherwise it says why, changes nothing and exits 2. There is no option to force it; the drop-ins are four small files that a person can read and delete by hand, knowingly.

`rollback` goes the same way on request: the same hold, the same checks, the same exit 2.

**What it never touches:** any database, any media file, any credential, Nginx, the portal, a timer, a unit file. Its own four drop-ins (`/etc/systemd/system/<unit>.d/90-kryuk-store-lock-install.conf`) exist only while it runs, or after a STOP until a person has put the state right.

**The operating condition (not enforced by the script):** during the maintenance window nobody starts `ops_cli.py` or `bro_worker.py` by hand. The hold is for systemd; the script looks for such a process twice and cannot stop one started after its last look.

### Why the hold (GPT's review of `195c896`)

A process that has loaded the original files writes into the store without the lock. A check that the one-shot units are idle says nothing about the next second: a timer could start one with the original code, and it could still be running beside the restarted service. So nothing that loads these files can start between the first check and the end. `test_install` forces a start at every moment of an install, of a failed install and of a rollback: the stand-in systemd refuses each one, and starts the unit again afterwards.

### Why the hold is on the disk and the service is guarded (GPT's review of `4795423`)

Two ways were left open in which a state that was not confirmed could be run. `release` took the hold away without looking at the files or the service; it now refuses unless the state is confirmed. And the hold lived under `/run`, which a restart of the server empties: after a STOP and a restart the timers were free again, and the enabled `kryuk-capture` would start by itself on files nobody had confirmed. The drop-ins are now on the disk, and the service has one of its own. `test_install` restarts the stand-in server after a STOP and after a killed run: neither the service nor a one-shot unit starts; `release` is refused; `rollback` puts the originals back and lets everything go.

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
| `test_install.py`, 31 tests, Windows with Git Bash (Python 3.12.10) | passed 08.10.2026 |
| The same 31 tests on the server's Linux (bash 5.3.9, Python 3.14.4), as an unprivileged user in a temporary folder, stand-ins only | passed 17:46 UTC (`../evidence/store_lock_install_tests_server_20261008T174635Z.txt`; the 26 tests of the second head: `…165427Z.txt`) |
| Nine deliberate breaks of the script: `release` without its check; a service guard that always lets it start; the marker left after a STOP; `release` not comparing the start of the service with the files; no hold; a failed restore step that does not stop the restore; a restart although the originals are not back; the hold given up in a state that needs a person; a running one-shot unit accepted | each made its test fail |
| Rehearsal of the first head on the server in a temporary folder, as `kryuk-run`: status, install, second run, rollback | passed 16:19 UTC (`../evidence/store_lock_install_rehearsal_20261008T161921Z.txt`) |
| The real branches of `install.sh` (units, user, hold, restart, health) | only against stand-ins. They show what the script asks for and what it does with each answer, not that the server answers that way |
| `trial_on_server.sh`: the hold with the real systemd on a throwaway unit; the service started and restarted with the new files in a temporary copy, as `kryuk-run`, on port 18788 | **passed 08.10.2026 17:17 UTC**, 35 checks, after the CI of `25ead0a` was green (`../evidence/store_lock_trial_server_20261008T171738Z.txt`). Real systemd 259: a running one-shot unit is `activating` and `is-active --quiet` answers 3; with the drop-in loaded `ConditionResult` is `no` and the command does not run; with the drop-in deleted it runs again, even before a reload. The service started as `kryuk-run` with Python 3.14.4 on the copy with the two new files, answered `/health`, was restarted (a new process) and answered again; nothing in its journal. Afterwards: no unit, no file, no port left; the real files and the real service (same process since 11:12 UTC) unchanged. **The first run, 17:16 UTC, said TRIAL FAILED**: two of my expectations were wrong (a one-shot unit stopped while its command runs ends as `failed`, not `inactive`); the hold and the service part passed in it too. It is kept beside the second (`…run1_wrong_expectation_20261008T171659Z.txt`); the script was changed only in those expectations. Not shown by that trial: a drop-in applied to a real unit file under `/etc` (the throwaway unit was under `/run`, and the hold was under `/run` then) |
| `trial_overlay_on_server.sh`: the hold's drop-in under `/etc` on the real `kryuk-backup`, and the guard on a throwaway unit | **not run**: it waits for Gev's word (a real unit, one extra snapshot). Until then that a drop-in under `/etc/systemd/system/<unit>.d/` stops a real unit of this server is how systemd is documented to work, read back by `install.sh` (`DropInPaths`) but not seen here |
| The real restart of the real `kryuk-capture` with the new files | **not tried**: that is the install |
| A killed script (`kill -9` after both new files were in place) and a restart of the server after it | tried against the stand-in systemd only: everything stays held, `rollback` brings the originals back. Not tried with a real restart of the server |

### Known limits

- The hold stops systemd from starting the three units. It does not stop a person with a shell from running `ops_cli.py` or `bro_worker.py` by hand during the install: the script looks for such a process twice (before the files change and before the restart) and not in between. This is an operating condition of the maintenance window, not a guarantee of the script.
- A script killed with `kill -9` leaves its marker under `/run` until the server restarts: until then the service could still be restarted by systemd after a crash. The three one-shot units stay held in that case too.
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
4. **Պահելը։** `kryuk-operations`, `kryuk-api-read`, `kryuk-backup` unit-ների համար `/etc/systemd/system/<unit>.d/`-ում drop-in ա գրում՝ պայմանով, որ կեղծ ա, քանի դեռ drop-in-ը կա։ `kryuk-capture`-ի համար էլ drop-in ա գրում, որով ծառայությունը կարող ա սկսվել միայն քանի դեռ էս run-ի նշանը կա `/run`-ում։ Reload ա անում systemd-ն ու հետ կարդում, որ չորսն էլ բեռնված են։ Էստեղից մինչև վերջ երեք unit-ը ոչ timer-ը, ոչ ձեռքը չի կարող սկսել, իսկ ծառայությունը կարող ա սկսել միայն էս run-ը։
5. Երեքից ոչ մեկը չի աշխատում (վիճակն ա կարդացվում. աշխատող one-shot unit-ը `activating` ա)։ Պանակի կոդով ուրիշ պրոցես չկա, բացի `kryuk-capture`-ից ու `kryuk-bro-api`-ից։ `kryuk-capture`-ը աշխատում ա, `/health`-ը պատասխանում ա։
6. Երկու բնօրինակն էլ պատճենվում են կողքին (`.before-store-lock`) ու ստուգվում sha256-ով։
7. `ops_media.py`, հետո `ops_work.py`, ամեն մեկը՝ rename-ով ու հետ կարդալով։
8. `selftest.py`՝ `kryuk-capture`-ի user-ով։
9. 5-րդ քայլի երկու ստուգումը նորից, հետո մեկ restart՝ միայն `kryuk-capture`։
10. Նորից health։ Չորս drop-in-ն ու նշանը հանվում են։

**7-ից 10-ի ձախողումը** երկու բնօրինակն էլ հետ ա դնում, `ops_work.py`-ն առաջինը։ Հետ դնելուց առաջ ստուգվում են երկու պատճենն ու դրված ֆայլերի վիճակը։ Ամեն քայլը ստուգվում ա առանձին, ոչ թե թողնվում `set -e`-ին. առաջին ձախողված քայլի վրա կանգնում ա ու հաջորդ ֆայլին ձեռք չի տալիս։ Միայն երբ երկու checksum-ն էլ բնօրինակինն են, ծառայությունը restart ա արվում ու health ա հարցվում. հետո պատճենները հանվում են, պահելը հանվում ա, exit 1։

**Երբ դա չի ստացվում** (ֆայլը հետ չի դրվում, կամ ծառայությունը բնօրինակներով չի բարձրանում) սկրիպտը ասում ա `STOP`, տպում ա երկու ֆայլի վիճակը, պահում ա երկու պատճենն էլ, ծառայությունը restart **չի** անում չհաստատված զույգով, one-shot unit-ները թողնում ա **պահված**, ծառայությունը՝ **փակված** (նշանը հանած), ու դուրս ա գալիս 2-ով։ Էդ վիճակում էս ֆայլերը բեռնող ոչինչ չի կարող սկսվել. ոչ one-shot unit, ոչ ծառայությունը crash-ից հետո, ոչ էլ դրանք սերվերի restart-ից հետո, որովհետև drop-in-ները դիսկի վրա են, իսկ նշանը՝ հիշողության մեջ։ Մարդը նայում ա, հետո `rollback`։

**`release`-ը** մնացած պահելը հանում ա միայն երբ վիճակը հաստատված ա. երկու ֆայլը զույգ են (երկուսն էլ բնօրինակ կամ երկուսն էլ նոր), կիսատ դրված ֆայլ չկա, one-shot unit կամ պանակի ուրիշ պրոցես չի աշխատում, ծառայությունը կամ չի աշխատում, կամ սկսվել ա երկու ֆայլի վերջին փոփոխությունից հետո ու պատասխանում ա `/health`-ին։ Թե չէ ասում ա ինչու, ոչինչ չի փոխում ու դուրս ա գալիս 2-ով։ Ստիպելու տարբերակ չկա։

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

- 31 թեստ՝ անցել են Windows-ում ու սերվերի Linux-ում (Python 3.14.4, ժամանակավոր պանակ, միայն փոխարինողներով)։
- Սկրիպտը ինը ձևով դիտմամբ փչացրել եմ՝ ամեն անգամ իր թեստը ընկել ա։
- `trial_overlay_on_server.sh` (պահելու drop-in-ը իրական `kryuk-backup` unit-ի վրա). **գրված ա, չի աշխատացվել**. իրական unit ա ու մեկ ավել snapshot ա սարքում, դրա համար սպասում ա Գևի խոսքին։
- `install.sh`-ի իրական ճյուղերը (unit-ներ, user, պահել, restart, health)՝ միայն փոխարինողներով։
- `trial_on_server.sh`. **անցել ա 08.10.2026 17:17 UTC-ին**, 35 ստուգում, `25ead0a`-ի CI-ի կանաչից հետո։ Իրական systemd-ով. աշխատող one-shot unit-ը `activating` ա. drop-in-ը բեռնած՝ հրամանը չի աշխատում. drop-in-ը ջնջած՝ նորից աշխատում ա։ Ծառայությունը բարձրացավ `kryuk-run`-ով, Python 3.14.4-ով, երկու նոր ֆայլով պատճենի վրա, պատասխանեց `/health`-ին, restart արվեց ու նորից պատասխանեց։ Հետո ոչ unit, ոչ ֆայլ, ոչ պորտ չմնաց. իրական ֆայլերն ու իրական ծառայությունը չեն փոխվել։ **Առաջին run-ը (17:16 UTC) ասեց TRIAL FAILED**. իմ երկու սպասումն էր սխալ (աշխատելիս կանգնեցրած one-shot unit-ը դառնում ա `failed`, ոչ թե `inactive`). պահելն ու ծառայության մասը էնտեղ էլ անցել էին։ Երկու run-ն էլ evidence-ում են։ Փորձը չի ցույց տալիս, որ `/run`-ի drop-in-ը գործում ա `/etc`-ի unit ֆայլի վրա. դա `install.sh`-ն ինքն ա հետ կարդում իրական unit-ների վրա։
- **Չի փորձվել.** իրական `kryuk-capture`-ի իրական restart-ը նոր ֆայլերով (դա հենց տեղադրումն ա). հոսանքի անջատում կամ սպանված սկրիպտ երկու քայլի արանքում։

### Հայտնի սահմաններ

- Պահելը systemd-ին չի թողնում սկսել երեք unit-ը։ Shell ունեցող մարդուն չի խանգարում ձեռքով աշխատացնել `ops_cli.py`-ն կամ `bro_worker.py`-ն. սկրիպտը էդպիսի պրոցես փնտրում ա երկու անգամ, ոչ թե ամբողջ ընթացքում։
- Timer-ը, որ կրակում ա, երբ իր unit-ը պահված ա, էդ run-ը կորցնում ա։ Սկրիպտը չի սկսում, եթե մինչև timer-ը տասը րոպեից քիչ ա մնացել։
