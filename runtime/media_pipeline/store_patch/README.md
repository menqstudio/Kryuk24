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
| `test_install.py` | 26 tests of `install.sh` and `selftest.py` |
| `trial_on_server.sh` | A trial on the server, in a temporary place, of the two things the tests only stand in for: the hold with the real systemd, and the service starting with the new files |

### What `install.sh` does

```
sudo bash install.sh            # install
sudo bash install.sh rollback   # both originals back
sudo bash install.sh status     # what is installed and what is held; changes nothing
sudo bash install.sh release    # let the one-shot units start again, after a STOP that left them held
```

In order, stopping at the first unexpected answer:

1. The two new files beside it have the reviewed sha256. Otherwise STOP.
2. Both installed files are the originals this change was made from (`5ca3e4de…` and `d1e6a2df…`). Both new: `ALREADY INSTALLED`, exit 0. Anything else: STOP, nothing changed.
3. No kept copy is in the way; both files are `root:root 644`; the tools it needs exist; no unit file is waiting for a reload; no timer of a held unit fires within ten minutes.
4. **The hold.** For `kryuk-operations`, `kryuk-api-read` and `kryuk-backup` it writes a drop-in under `/run/systemd/system/<unit>.d/` with a condition that is false while the drop-in exists, reloads systemd and reads back that the drop-in is loaded. From here to the end no timer and no hand can start them.
5. None of the three is running (the state is read: a running one-shot unit is `activating`, which `is-active` reports as not active). No other process runs code of the folder except `kryuk-capture` and `kryuk-bro-api`. `kryuk-capture` is running and `/health` answers. The script does not start what was stopped.
6. Both originals are copied beside themselves (`.before-store-lock`) and the copies are checked by sha256.
7. `ops_media.py`, then `ops_work.py`, each put in place by a rename and read back.
8. `selftest.py` runs as the user of `kryuk-capture` (read from the unit, `kryuk-run` today) with `/usr/bin/python3`.
9. Step 5's two checks again, then one restart of `kryuk-capture`. No other service is restarted, started, stopped or enabled.
10. The health check again. The hold is taken away.

**A failure in 7 to 10** puts both originals back, `ops_work.py` first. Before anything is put back both kept copies are checked and both installed files must be the original or the new one. Each step is checked by name, not left to `set -e`; the script stops at the first step that fails and does not touch the next file. Only when both checksums are the originals' is the service restarted and asked for health; then the kept copies are removed, the hold is taken away, exit 1.

**When that cannot be done** (a file could not be put back, or the service does not come up with the originals) the script says `STOP`, prints the state of both files, keeps both kept copies, does **not** restart the service on a pair it could not confirm, leaves the one-shot units **held**, and exits 2. A person looks, then `rollback` (it can be run again) and, if needed, `release`.

`rollback` goes the same way on request: the same hold, the same checks, the same exit 2.

**What it never touches:** any database, any media file, any credential, Nginx, the portal, a timer, a unit file under `/etc`. The hold is under `/run`: a restart of the server removes it by itself.

### Why the hold (GPT's review of `195c896`)

A process that has loaded the original files writes into the store without the lock. A check that the one-shot units are idle says nothing about the next second: a timer could start one with the original code, and it could still be running beside the restarted service. So nothing that loads these files can start between the first check and the end. `test_install` forces a start at every moment of an install, of a failed install and of a rollback: the stand-in systemd refuses each one, and starts the unit again afterwards.

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
| `test_install.py`, 26 tests, Windows with Git Bash (Python 3.12.10) | passed 08.10.2026 |
| The same 26 tests on the server's Linux (bash 5.3.9, Python 3.14.4), as an unprivileged user in a temporary folder, stand-ins only | passed 16:54 UTC (`../evidence/store_lock_install_tests_server_20261008T165427Z.txt`) |
| Seven deliberate breaks of the script: no hold; the hold taken away in the middle; a failed restore step that does not stop the restore; a restart although the originals are not back; the hold given up in a state that needs a person; a running one-shot unit accepted; no look for other processes | each made its test fail |
| Rehearsal of the first head on the server in a temporary folder, as `kryuk-run`: status, install, second run, rollback | passed 16:19 UTC (`../evidence/store_lock_install_rehearsal_20261008T161921Z.txt`) |
| The real branches of `install.sh` (units, user, hold, restart, health) | only against stand-ins. They show what the script asks for and what it does with each answer, not that the server answers that way |
| `trial_on_server.sh`: the hold with the real systemd on a throwaway unit; the service started and restarted with the new files in a temporary copy, as `kryuk-run`, on port 18788 | **passed 08.10.2026 17:17 UTC**, 35 checks, after the CI of `25ead0a` was green (`../evidence/store_lock_trial_server_20261008T171738Z.txt`). Real systemd 259: a running one-shot unit is `activating` and `is-active --quiet` answers 3; with the drop-in loaded `ConditionResult` is `no` and the command does not run; with the drop-in deleted it runs again, even before a reload. The service started as `kryuk-run` with Python 3.14.4 on the copy with the two new files, answered `/health`, was restarted (a new process) and answered again; nothing in its journal. Afterwards: no unit, no file, no port left; the real files and the real service (same process since 11:12 UTC) unchanged. **The first run, 17:16 UTC, said TRIAL FAILED**: two of my expectations were wrong (a one-shot unit stopped while its command runs ends as `failed`, not `inactive`); the hold and the service part passed in it too. It is kept beside the second (`…run1_wrong_expectation_20261008T171659Z.txt`); the script was changed only in those expectations. Not shown by the trial: a drop-in under `/run` applied to a unit file under `/etc` (the throwaway unit is under `/run`); `install.sh` reads that back on the real units before it goes on |
| The real restart of the real `kryuk-capture` with the new files | **not tried**: that is the install |
| A power cut or a killed script between two steps | **not tried**. After one, `status` says what is installed and what is held; `rollback` puts back what has a kept copy; `release` takes a left hold away |

### Known limits

- The hold stops systemd from starting the three units. It does not stop a person with a shell from running `ops_cli.py` or `bro_worker.py` by hand during the install: the script looks for such a process twice (before the files change and before the restart) and not in between.
- A timer that fires while its unit is held loses that run. The script refuses to start within ten minutes of one; an install that hangs longer could still lose one.
- The lock file is created with the umask of whoever first takes the lock (`0077` in the units, so mode `600`). Today every unit that can take it runs as `kryuk-run`, and the plan runs the pipeline as `kryuk-run` too (`../INSTALL_PLAN.md`, section 3). A unit under another user would be refused the file; nothing gives it access, and this script does not either.

## HY

**Վիճակը, 08.10.2026. գրված ա review-ի համար։ `install.sh`-ը սերվերում չի աշխատացվել։ Կաշխատացվի միայն GPT-ի review-ից ու Գևի առանձին խոսքից հետո։**

### Ինչ կա էստեղ

`make_patch.py`-ն սարքում ա `ops_media.py`-ն ու `ops_work.py`-ն սերվերում դրված ֆայլերից՝ ճշգրիտ փոխարինումներով։ `install.sh`-ը էդ երկու ֆայլը դնում ա սերվերի `/opt/kryuk24`-ում ու կարողանում ա հետ հանել։ `selftest.py`-ն ստուգում ա, որ երկու ֆայլը գործնականում աշխատում են։ `test_install.py`-ն 26 թեստ ա։ `trial_on_server.sh`-ը սերվերում, ժամանակավոր տեղում փորձում ա էն երկու բանը, որ թեստերում փոխարինողներով են. պահելը իրական systemd-ով ու ծառայության մեկնարկը նոր ֆայլերով։

### Ինչ ա անում `install.sh`-ը

Հերթով, առաջին անսպասելի պատասխանի վրա կանգնում ա.

1. Կողքի երկու նոր ֆայլի sha256-ը review-ածն ա։
2. Դրված երկու ֆայլն էլ բնօրինակն են։ Երկուսն էլ նոր են՝ `ALREADY INSTALLED`։ Ուրիշ վիճակ՝ STOP, ոչինչ չի փոխվում։
3. Պատճեն ճանապարհին չկա, ֆայլերը `root:root 644` են, գործիքները կան, ոչ մի unit ֆայլ reload-ի չի սպասում, պահվող unit-ի timer-ը տասը րոպեից շուտ չի կրակում։
4. **Պահելը։** `kryuk-operations`, `kryuk-api-read`, `kryuk-backup` unit-ների համար `/run/systemd/system/<unit>.d/`-ում drop-in ա գրում՝ պայմանով, որ կեղծ ա, քանի դեռ drop-in-ը կա, reload ա անում systemd-ն ու հետ կարդում, որ drop-in-ը բեռնված ա։ Էստեղից մինչև վերջ ոչ timer-ը, ոչ ձեռքը դրանք չի կարող սկսել։
5. Երեքից ոչ մեկը չի աշխատում (վիճակն ա կարդացվում. աշխատող one-shot unit-ը `activating` ա)։ Պանակի կոդով ուրիշ պրոցես չկա, բացի `kryuk-capture`-ից ու `kryuk-bro-api`-ից։ `kryuk-capture`-ը աշխատում ա, `/health`-ը պատասխանում ա։
6. Երկու բնօրինակն էլ պատճենվում են կողքին (`.before-store-lock`) ու ստուգվում sha256-ով։
7. `ops_media.py`, հետո `ops_work.py`, ամեն մեկը՝ rename-ով ու հետ կարդալով։
8. `selftest.py`՝ `kryuk-capture`-ի user-ով։
9. 5-րդ քայլի երկու ստուգումը նորից, հետո մեկ restart՝ միայն `kryuk-capture`։
10. Նորից health։ Պահելը հանվում ա։

**7-ից 10-ի ձախողումը** երկու բնօրինակն էլ հետ ա դնում, `ops_work.py`-ն առաջինը։ Հետ դնելուց առաջ ստուգվում են երկու պատճենն ու դրված ֆայլերի վիճակը։ Ամեն քայլը ստուգվում ա առանձին, ոչ թե թողնվում `set -e`-ին. առաջին ձախողված քայլի վրա կանգնում ա ու հաջորդ ֆայլին ձեռք չի տալիս։ Միայն երբ երկու checksum-ն էլ բնօրինակինն են, ծառայությունը restart ա արվում ու health ա հարցվում. հետո պատճենները հանվում են, պահելը հանվում ա, exit 1։

**Երբ դա չի ստացվում** (ֆայլը հետ չի դրվում, կամ ծառայությունը բնօրինակներով չի բարձրանում) սկրիպտը ասում ա `STOP`, տպում ա երկու ֆայլի վիճակը, պահում ա երկու պատճենն էլ, ծառայությունը restart **չի** անում չհաստատված զույգով, one-shot unit-ները թողնում ա **պահված**, ու դուրս ա գալիս 2-ով։ Մարդը նայում ա, հետո `rollback` (կարելի ա նորից աշխատացնել) ու, եթե պետք ա, `release`։

**Ինչին երբեք ձեռք չի տալիս.** ոչ մի բազա, ոչ մի նկար, ոչ մի գաղտնաբառ, Nginx, կաբինետ, timer, `/etc`-ի unit ֆայլ։ Պահելը `/run`-ում ա. սերվերի restart-ը ինքն ա հանում։

### Ինչու պահել (GPT-ի review-ը `195c896`-ի)

Հին ֆայլերը բեռնած պրոցեսը պահեստում գրում ա առանց կողպեքի։ «One-shot-ները հիմա չեն աշխատում» ստուգումը ոչինչ չի ասում հաջորդ վայրկյանի մասին. timer-ը կարող էր մեկը սկսել հին կոդով, ու դա կշարունակեր աշխատել restart արած ծառայության կողքին։ Դրա համար առաջին ստուգումից մինչև վերջ էս ֆայլերը բեռնող ոչինչ չի կարող սկսվել։ Թեստը մեկնարկ ա պարտադրում տեղադրման, ձախողված տեղադրման ու rollback-ի ամեն պահի. ամեն մեկը մերժվում ա, իսկ վերջից հետո unit-ը նորից սկսվում ա։

### Ինչու էս հերթով

Նոր `ops_media.py`-ն աշխատում ա հին `ops_work.py`-ի հետ, հակառակը՝ չէ։ Դրա համար պահեստը դրվում ա առաջինը ու հանվում վերջինը. առաջին քայլից հետո կանգնած restore-ը թողնում ա աշխատող զույգ։

### Ով ա բեռնում էս երկու ֆայլը (կարդացած import-ներից)

`secure_server.py` (`kryuk-capture`), `ops_daily.py` (`kryuk-operations`), `ops_api.py` (`kryuk-api-read`), `ops_backup.py`, ու ձեռքով սկսվող երկու սկրիպտ՝ `ops_cli.py`, `bro_worker.py`։ `bro_api.py`-ն (`kryuk-bro-api`)՝ չէ։

### Ինչ ա փորձվել, ինչ՝ չէ

- 26 թեստ՝ անցել են Windows-ում ու սերվերի Linux-ում (Python 3.14.4, ժամանակավոր պանակ, միայն փոխարինողներով)։
- Սկրիպտը յոթ ձևով դիտմամբ փչացրել եմ՝ ամեն անգամ իր թեստը ընկել ա։
- `install.sh`-ի իրական ճյուղերը (unit-ներ, user, պահել, restart, health)՝ միայն փոխարինողներով։
- `trial_on_server.sh`. **անցել ա 08.10.2026 17:17 UTC-ին**, 35 ստուգում, `25ead0a`-ի CI-ի կանաչից հետո։ Իրական systemd-ով. աշխատող one-shot unit-ը `activating` ա. drop-in-ը բեռնած՝ հրամանը չի աշխատում. drop-in-ը ջնջած՝ նորից աշխատում ա։ Ծառայությունը բարձրացավ `kryuk-run`-ով, Python 3.14.4-ով, երկու նոր ֆայլով պատճենի վրա, պատասխանեց `/health`-ին, restart արվեց ու նորից պատասխանեց։ Հետո ոչ unit, ոչ ֆայլ, ոչ պորտ չմնաց. իրական ֆայլերն ու իրական ծառայությունը չեն փոխվել։ **Առաջին run-ը (17:16 UTC) ասեց TRIAL FAILED**. իմ երկու սպասումն էր սխալ (աշխատելիս կանգնեցրած one-shot unit-ը դառնում ա `failed`, ոչ թե `inactive`). պահելն ու ծառայության մասը էնտեղ էլ անցել էին։ Երկու run-ն էլ evidence-ում են։ Փորձը չի ցույց տալիս, որ `/run`-ի drop-in-ը գործում ա `/etc`-ի unit ֆայլի վրա. դա `install.sh`-ն ինքն ա հետ կարդում իրական unit-ների վրա։
- **Չի փորձվել.** իրական `kryuk-capture`-ի իրական restart-ը նոր ֆայլերով (դա հենց տեղադրումն ա). հոսանքի անջատում կամ սպանված սկրիպտ երկու քայլի արանքում։

### Հայտնի սահմաններ

- Պահելը systemd-ին չի թողնում սկսել երեք unit-ը։ Shell ունեցող մարդուն չի խանգարում ձեռքով աշխատացնել `ops_cli.py`-ն կամ `bro_worker.py`-ն. սկրիպտը էդպիսի պրոցես փնտրում ա երկու անգամ, ոչ թե ամբողջ ընթացքում։
- Timer-ը, որ կրակում ա, երբ իր unit-ը պահված ա, էդ run-ը կորցնում ա։ Սկրիպտը չի սկսում, եթե մինչև timer-ը տասը րոպեից քիչ ա մնացել։
