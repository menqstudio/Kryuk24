# Lock-aware media store: the patch and its install script / Կողպեքով պահեստ. patch-ն ու install սկրիպտը

**Status, 08.10.2026: written for review. Not run on the server. It is run only after GPT's review and Gev's separate word.**

## EN

### What is here

| File | What it is |
| --- | --- |
| `make_patch.py` | Makes `ops_media.py` and `ops_work.py` from the installed files recorded in `runtime/server/`, by exact replacements. `--check` proves the two files here are what it makes |
| `ops_media.py`, `ops_work.py` | The lock-aware store. sha256 `0f877f77…97df4` and `69aa0809…a251` |
| `install.sh` | Puts the two files into `/opt/kryuk24` on the server, and takes them out again |
| `selftest.py` | A functional check of the two files with the Python that runs it, in a temporary folder |
| `test_install.py` | 19 tests of `install.sh` and `selftest.py` |

### What `install.sh` does

```
sudo bash install.sh            # install
sudo bash install.sh rollback   # both originals back
sudo bash install.sh status     # what is installed; changes nothing
```

In order, stopping at the first unexpected answer:

1. The two new files beside it have the reviewed sha256. Otherwise STOP.
2. Both installed files are the originals this change was made from (`5ca3e4de…` and `d1e6a2df…`). Both new: `ALREADY INSTALLED`, exit 0. Anything else, one changed by somebody or one new and one original: STOP, nothing changed.
3. No kept copy is in the way; both files are `root:root 644`; `curl`, `runuser`, `systemctl` exist.
4. No one-shot unit that loads the files is running (`kryuk-operations`, `kryuk-api-read`, `kryuk-backup`); `kryuk-capture` is running; `http://127.0.0.1:8788/health` answers. The script does not start what was stopped.
5. Both originals are copied beside themselves (`.before-store-lock`) and the copies are checked by sha256.
6. `ops_media.py`, then `ops_work.py`, each put in place by a rename.
7. `selftest.py` runs as the user of `kryuk-capture` (read from the unit, `kryuk-run` today) with `/usr/bin/python3`.
8. One restart of `kryuk-capture`. No other service is restarted, started, stopped or enabled.
9. The health check again.

A failure in 6 to 9 puts both originals back (`ops_work.py` first), restarts `kryuk-capture` with them, checks health, removes the kept copies and exits 1. `rollback` does the same on request, and also waits for a running one-shot unit.

**What it never touches:** any database, any media file, any credential, Nginx, the portal, a timer, a unit file. It does not create the media folder or the lock file: the store creates `<media root>/.pipeline.lock` the first time something takes the lock.

### Why this order

The new `ops_media.py` works with the original `ops_work.py`. The new `ops_work.py` does not work with the original `ops_media.py` (`draft()` asks the store for its lock). So the store goes in first and comes out last, and a unit that starts in the middle reads a pair that works. `test_install.Order` holds this.

### Facts read from the server (08.10.2026 16:14 UTC, read-only; `../evidence/store_lock_install_facts_20261008T161433Z.txt`)

- Both installed files are the originals, `root:root 644`; no `.before-store-lock` copy exists.
- `kryuk-capture`, `kryuk-operations`, `kryuk-backup` and `kryuk-bro-api` run as `kryuk-run`; `kryuk-api-read` runs as `kryuk-api-read`. The unit files in `runtime/server/deploy/` say `User=kryuk`: the repository differs from the server here. Not changed in this round.
- `/var/lib/kryuk24` is `kryuk-run:kryuk-db 2770`. `/var/lib/kryuk24/media` does not exist: the store has never stored a file on the server.
- Timers: `kryuk-backup` 00:04 UTC, `kryuk-operations` 06:00 UTC.
- `/health` answered `{"mode":"STAGING","ok":true,"sending_enabled":false}`.

### What was tried, and what was not

| | |
| --- | --- |
| `test_install.py`, 19 tests, Windows with Git Bash (Python 3.12.10) | passed 08.10.2026 |
| Four deliberate breaks of the script (no rollback after a failed health check; a second service restarted; the one-shot check removed; the checksum gate removed) | each made its test fail |
| Rehearsal on the server in a temporary folder, as `kryuk-run`, Python 3.14.4: status, install, second run, rollback | passed 16:19 UTC; the real files and the service unchanged (`../evidence/store_lock_install_rehearsal_20261008T161921Z.txt`) |
| The real branches (units, user, restart, health) | only against stand-ins for `systemctl`, `curl`, `runuser`, `id`, `stat`, `install`, `sleep`. They show what the script asks for and what it does with each answer, not that the server answers that way |
| The real restart of `kryuk-capture` with the new files and its real health check | **not tried anywhere** |
| A power cut or a killed script between two steps | **not tried**. After one, `status` says what is installed; `rollback` puts back what has a kept copy |

### Known limits

- Between step 4 and step 6 a timer could start a one-shot unit. It would read a working pair (see the order). The script does not stop timers.
- The lock file is created with the umask of whoever first takes the lock (`0077` in the units, so mode `600`). Today every unit that can take it runs as `kryuk-run`, and the plan runs the pipeline as `kryuk-run` too (`../INSTALL_PLAN.md`, section 3). A unit under another user would be refused the file; nothing gives it access, and this script does not either.

## HY

### Ինչ կա էստեղ

`make_patch.py`-ն սարքում ա `ops_media.py`-ն ու `ops_work.py`-ն սերվերում դրված ֆայլերից՝ ճշգրիտ փոխարինումներով։ `install.sh`-ը էդ երկու ֆայլը դնում ա սերվերի `/opt/kryuk24`-ում ու կարողանում ա հետ հանել։ `selftest.py`-ն ստուգում ա, որ երկու ֆայլը գործնականում աշխատում են էն Python-ով, որով աշխատացվում ա։ `test_install.py`-ն 19 թեստ ա։

**Վիճակը, 08.10.2026. գրված ա review-ի համար։ Սերվերում չի աշխատացվել։ Կաշխատացվի միայն GPT-ի review-ից ու Գևի առանձին խոսքից հետո։**

### Ինչ ա անում `install.sh`-ը

Հերթով, առաջին անսպասելի պատասխանի վրա կանգնում ա.

1. Կողքի երկու նոր ֆայլի sha256-ը review-ածն ա։ Չէ՝ STOP։
2. Դրված երկու ֆայլն էլ էն բնօրինակներն են, որոնցից էս փոփոխությունը սարքվել ա։ Երկուսն էլ նոր են՝ `ALREADY INSTALLED`։ Ուրիշ ցանկացած վիճակ՝ STOP, ոչինչ չի փոխվում։
3. Պահված կրկնօրինակ ճանապարհին չկա, ֆայլերը `root:root 644` են, `curl`, `runuser`, `systemctl` կան։
4. Էս ֆայլերը բեռնող one-shot unit չի աշխատում, `kryuk-capture`-ը աշխատում ա, `/health`-ը պատասխանում ա։ Կանգնածը սկրիպտը չի բարձրացնում։
5. Երկու բնօրինակն էլ պատճենվում են կողքին (`.before-store-lock`) ու ստուգվում sha256-ով։
6. `ops_media.py`, հետո `ops_work.py`, ամեն մեկը՝ rename-ով։
7. `selftest.py`՝ `kryuk-capture`-ի user-ով (կարդացվում ա unit-ից, էսօր `kryuk-run`)։
8. Մեկ restart՝ միայն `kryuk-capture`։ Ուրիշ ոչ մի ծառայության ձեռք չի տրվում։
9. Նորից health։

6-ից 9-ի ցանկացած ձախողում երկու բնօրինակն էլ հետ ա դնում (`ops_work.py`-ն առաջինը), restart ա անում, health ա ստուգում, կրկնօրինակները հանում ա ու դուրս գալիս 1-ով։ `rollback`-ը նույնն ա անում խնդրանքով։

**Ինչին երբեք ձեռք չի տալիս.** ոչ մի բազա, ոչ մի նկար, ոչ մի գաղտնաբառ, Nginx, կաբինետ, timer, unit ֆայլ։

### Ինչու էս հերթով

Նոր `ops_media.py`-ն աշխատում ա հին `ops_work.py`-ի հետ, հակառակը՝ չէ։ Դրա համար պահեստը դրվում ա առաջինը ու հանվում վերջինը. մեջտեղում սկսած unit-ը կարդում ա աշխատող զույգ։

### Սերվերից կարդացած փաստեր (08.10.2026 16:14 UTC, միայն կարդալով)

- Դրված երկու ֆայլն էլ բնօրինակն են, `root:root 644`։
- `kryuk-capture`, `kryuk-operations`, `kryuk-backup`, `kryuk-bro-api`՝ `kryuk-run` user-ով. `kryuk-api-read`՝ իր user-ով։ Repo-ի unit ֆայլերում գրված ա `User=kryuk`. repo-ն էստեղ սերվերից տարբեր ա։ Էս փուլում չի փոխվել։
- `/var/lib/kryuk24/media` պանակը չկա. պահեստը սերվերում դեռ ոչ մի ֆայլ չի պահել։

### Ինչ ա փորձվել, ինչ՝ չէ

- 19 թեստ՝ անցել են Windows-ում Git Bash-ով։ Սկրիպտը չորս ձևով դիտմամբ փչացրել եմ՝ ամեն անգամ իր թեստը ընկել ա։
- Փորձ սերվերում՝ միայն ժամանակավոր պանակում, `kryuk-run`-ով, Python 3.14.4-ով. անցել ա 16:19 UTC-ին, իրական ֆայլերն ու ծառայությունը չեն փոխվել։
- Իրական ճյուղերը (unit-ներ, user, restart, health)՝ միայն փոխարինողներով։ Ցույց են տալիս՝ սկրիպտը ինչ ա հարցնում ու ինչ ա անում ամեն պատասխանի հետ, ոչ թե որ սերվերը հենց էդպես ա պատասխանում։
- **Ոչ մի տեղ չի փորձվել.** `kryuk-capture`-ի իրական restart-ը նոր ֆայլերով ու իրական health-ը. հոսանքի անջատում կամ սպանված սկրիպտ երկու քայլի արանքում։
