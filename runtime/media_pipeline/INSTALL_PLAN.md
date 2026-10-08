# Media pipeline: install plan for the server / Մեդիայի հոսք. սերվերում դնելու պլան

**Status: a plan. Nothing in it has been done.** It is written so that Gev can approve one exact change. Server facts were read on 08.10.2026 11:13 UTC with a read-only script; where a line is not a read fact it says so.

## EN

### What the server is today (read)

| Thing | Fact |
| --- | --- |
| Runtime database | `/var/lib/kryuk24/runtime.sqlite`, `kryuk-run:kryuk-db`, mode 660, WAL; folder `kryuk-run:kryuk-db` 2770 |
| Runtime's media folder | `/var/lib/kryuk24/media` **does not exist**. The dashboard (`kryuk-capture`, user `kryuk-run`) reads prepared pictures from there (`/operator/media/<asset>`) |
| Portal data | `/var/lib/kryuk24-armen`, `kryuk-armen:kryuk-armen`, mode 700; database 600; every photo file 600. Nobody else can read it |
| Users | `kryuk-run` (groups `kryuk-run`, `kryuk-db`), `kryuk-armen` (its own group only) |
| Backups | `kryuk-backup.timer` copies the runtime database every night into `/var/lib/kryuk24/backups` (last: 08.10.2026 00:00 UTC). The portal's data is in no backup |
| Timers | backup and daily operations only. This plan adds none |

### The change, exactly

1. **Who runs it.** The pipeline runs as the runtime's own user `kryuk-run`, because the pictures it stores must be readable by the dashboard, which runs as `kryuk-run` and stores media files with mode 400. No new user. It gets one extra right: reading the portal's data.
2. **Reading the portal (file permissions).** `kryuk-run` is added to the group `kryuk-armen`. The portal's folder becomes 750, its photo folder 750, its database 640, its photo files 640 (group may read, nobody may write but the portal). This needs a small change of the portal, reviewed like any other: new files 640 instead of 600, the unit's `UMask=0027`, and one restart of the portal. **`kryuk-run` gets no write right in the portal's folder.** Consequence: the clean-up cannot remove the portal's second copy of an original; that removal stays a supervised hand step until decided otherwise.
3. **Code.** `/opt/kryuk24-media/` (root-owned, 755/644): `media_pipeline.py`, `media_cli.py`, its own Python environment with Pillow 12.3.0. It imports the installed runtime code from `/opt/kryuk24` and changes none of it.
4. **Database migration.** Four new tables in `runtime.sqlite`, made by `CREATE TABLE IF NOT EXISTS`: `media_work`, `media_work_sources`, `media_work_assets`, `media_work_events`. **No existing table is altered.** In use the pipeline adds rows to two existing tables through the existing code paths: `ops_originals` and `ops_assets` (the shared inbox), and it writes the draft of the day's `MEDIA_INBOX` task through `Operations.draft`.
5. **Media folder.** `/var/lib/kryuk24/media` is created, `kryuk-run:kryuk-run` 700 (the mode the runtime's code uses), with `originals/`, `prepared/`, `tmp/` made on first use. Storage limit 5 GiB (the disk has 25 GiB free).
6. **How it is started.** By hand, one command at a time (`sudo -u kryuk-run … media_cli.py intake | queue | claim | …`). **No service, no timer, nothing at boot.** A unit file or a timer is a later, separate yes.
7. **What it does not include.** No HTTP route for agents (the Bro sidecar is not touched). No Nginx change. No publication: a draft waits in Gev's dashboard; publishing is a person's step after his approval, recorded by the existing path.

### Backup before the change

| What | How | Where |
| --- | --- | --- |
| Runtime database | SQLite online backup, then `PRAGMA integrity_check` and a row count of every table on the copy | `/root/kryuk24-config-backups/runtime.sqlite.before-media-<time>`, mode 600 |
| Portal database | the same | `/root/kryuk24-config-backups/portal.sqlite.before-media-<time>`, mode 600 |
| Portal photo files | not copied (they are not changed; only their mode changes). Their names, sizes and sha256 are listed before and after | the evidence file |
| Permissions | owner, group and mode of every touched path, before and after (`preinstall_facts.sh` of both packages) | the evidence file |

### Steps, each a small script that prints facts and stops at the first unexpected answer

1. Read-only facts and the two backups.
2. Portal: update its code (files 640), set `UMask=0027`, `chmod` the existing folder and files, add `kryuk-run` to the group, restart the portal once. Check: the portal answers as before; `kryuk-run` can read a photo and cannot create a file there.
3. Install `/opt/kryuk24-media` and its Python; run the module's 17 tests on the server.
4. Create the media folder; run `storage` once (this creates the four tables). Check: the row counts of all existing tables are unchanged.
5. `intake`: Gev's marked test photo is skipped (`excluded: 1`), nothing else is there today. From here a real photo of Armen's goes: intake → an agent claims, looks, declares the regions → variants → `submit` → the draft in Gev's dashboard.
6. Read-only facts again; evidence file; `docs/CURRENT_STATE.md`.

### Rollback

- **Before any photo was taken in:** drop the four tables, remove `/var/lib/kryuk24/media` (empty) and `/opt/kryuk24-media`, take `kryuk-run` out of the group, put the portal's modes and `UMask` back, restart the portal. The existing tables were never altered, so nothing of the runtime needs restoring.
- **After photos were taken in:** the same, plus removing this pipeline's rows from `ops_originals` and `ops_assets` (they are recognisable: provenance starts with `ARMEN_PORTAL`, trust `AGENT_DECLARED_MASKS`) and resetting a `MEDIA_INBOX` draft with `Operations.revise`. **An original is removed from the inbox only after checking that the portal still holds the same bytes (sha256); otherwise it stays.** The database backup of step 1 is the last resort; restoring it would undo everything else written to the runtime since, so it is not the normal way back.

### Risks, said outright

- `kryuk-run` gains read access to Armen's photos and answers. Today no other service can read them.
- The portal's files become group-readable. The group has two members: the portal and the runtime.
- Step 2 restarts the portal: whoever is signed in signs in again.
- Covering plates and faces rests on the agent's declaration and on Gev's look at approval. The code detects nothing.
- Not verified until done: the dashboard showing a media draft with pictures made by this pipeline.

### The yes that is asked for

"Yes: install the media pipeline as written in `runtime/media_pipeline/INSTALL_PLAN.md`: `kryuk-run` reads the portal through the group, the portal's files become 640 with one restart, four new tables, the media folder, code in `/opt/kryuk24-media`, started by hand, no timer, no publication."

## HY

**Վիճակը. պլան ա։ Սրանից ոչինչ արված չի։** Գրված ա, որ Գևը հաստատի մեկ հստակ փոփոխություն։ Սերվերի փաստերը կարդացվել են 08.10.2026 11:13 UTC-ին միայն-կարդացող սկրիպտով։

### Սերվերն այսօր (կարդացած)

- Runtime-ի բազան՝ `/var/lib/kryuk24/runtime.sqlite`, `kryuk-run:kryuk-db`, 660, WAL։
- Runtime-ի media պանակը՝ `/var/lib/kryuk24/media`, **չկա**։ Վահանակը (`kryuk-capture`, user `kryuk-run`) պատրաստ նկարները էնտեղից ա կարդում։
- Կաբինետի տվյալը՝ `/var/lib/kryuk24-armen`, 700. բազան 600, ամեն նկար 600։ Ուրիշ ոչ ոք չի կարող կարդալ։
- Պահուստ. runtime-ի բազան ամեն գիշեր պատճենվում ա։ Կաբինետի տվյալը ոչ մի պահուստում չկա։
- Timer. միայն պահուստն ու օրվա գործերը։ Էս պլանը նոր timer չի դնում։

### Փոփոխությունը, ճշգրիտ

1. **Ով ա աշխատացնում։** Հոսքը աշխատում ա runtime-ի սեփական `kryuk-run` user-ով, որովհետև իր պահած նկարները պիտի կարդա վահանակը, որը `kryuk-run`-ով ա աշխատում։ Նոր user չկա։ Ստանում ա մեկ նոր իրավունք՝ կարդալ կաբինետի տվյալը։
2. **Կաբինետը կարդալը (ֆայլերի իրավունքներ)։** `kryuk-run`-ը ավելանում ա `kryuk-armen` խմբին։ Կաբինետի պանակը դառնում ա 750, նկարների պանակը 750, բազան 640, նկարները 640 (խումբը կարդում ա, գրում ա միայն կաբինետը)։ Դրա համար կաբինետի փոքր փոփոխություն ա պետք՝ նոր ֆայլերը 640, unit-ի `UMask=0027`, ու կաբինետի մեկ restart։ **`kryuk-run`-ը կաբինետի պանակում գրելու իրավունք չի ստանում։** Հետևանքը. մաքրումը չի կարող հանել կաբինետի երկրորդ պատճենը. դա մնում ա հսկվող ձեռքի քայլ։
3. **Կոդ։** `/opt/kryuk24-media/` (root-ինը). երկու ֆայլ ու սեփական Python՝ Pillow 12.3.0-ով։ Դրված runtime-ի կոդից ոչինչ չի փոխում։
4. **Բազայի migration։** Չորս նոր աղյուսակ `runtime.sqlite`-ում (`CREATE TABLE IF NOT EXISTS`)՝ `media_work`, `media_work_sources`, `media_work_assets`, `media_work_events`։ **Եղած ոչ մի աղյուսակ չի փոխվում։** Աշխատելիս տողեր ա ավելացնում եղած `ops_originals`-ում ու `ops_assets`-ում եղած կոդով, ու գրում ա օրվա `MEDIA_INBOX` գործի սևագիրը։
5. **Media պանակ։** Ստեղծվում ա `/var/lib/kryuk24/media`-ն, `kryuk-run:kryuk-run` 700։ Պահեստի սահմանը 5 GiB (սկավառակում 25 GiB ազատ կա)։
6. **Ոնց ա գործարկվում։** Ձեռքով, մեկ հրամանով։ **Ծառայություն, timer, boot-ի ժամանակ գործարկում չկա։**
7. **Ինչ չի մտնում։** Ագենտների HTTP ճանապարհ, Nginx-ի փոփոխություն, հրապարակում։ Սևագիրը սպասում ա Գևի վահանակում։

### Պահուստ փոփոխությունից առաջ

- Runtime-ի բազան ու կաբինետի բազան՝ SQLite online backup-ով, հետո `integrity_check` ու ամեն աղյուսակի տողերի թիվը պատճենի վրա. `/root/kryuk24-config-backups/`, 600։
- Կաբինետի նկարները չեն պատճենվում (չեն փոխվում, փոխվում ա միայն ռեժիմը). անունները, չափերն ու sha256-ը գրվում են առաջ ու հետո։
- Ամեն դիպչած ճանապարհի տերը, խումբն ու ռեժիմը՝ առաջ ու հետո։

### Քայլերը

1. Միայն-կարդացող փաստեր ու երկու պահուստ։
2. Կաբինետ. կոդի թարմացում (ֆայլերը 640), `UMask=0027`, եղած ֆայլերի `chmod`, `kryuk-run`-ը խմբում, մեկ restart։ Ստուգում. կաբինետը պատասխանում ա ինչպես առաջ. `kryuk-run`-ը նկարը կարդում ա ու էնտեղ ֆայլ ստեղծել չի կարողանում։
3. `/opt/kryuk24-media`-ն ու իր Python-ը. մոդուլի 17 թեստը սերվերում։
4. Media պանակը. `storage` մեկ անգամ (ստեղծում ա չորս աղյուսակը)։ Ստուգում. եղած բոլոր աղյուսակների տողերի թվերը նույնն են։
5. `intake`. Գևի նշված թեստային նկարը բաց ա թողնվում (`excluded: 1`)։ Էստեղից Արմենի իրական նկարը գնում ա. ընդունում → ագենտը վերցնում ա, նայում, նշում տեղերը → տարբերակներ → `submit` → սևագիր Գևի վահանակում։
6. Նորից փաստեր. evidence. `docs/CURRENT_STATE.md`։

### Rollback

- **Մինչև որևէ նկար ընդունվելը.** ջնջել չորս աղյուսակը, հանել դատարկ media պանակն ու `/opt/kryuk24-media`-ն, `kryuk-run`-ը հանել խմբից, կաբինետի ռեժիմներն ու `UMask`-ը հետ դնել, կաբինետը restart անել։ Եղած աղյուսակները չեն փոխվել, runtime-ից վերականգնելու բան չկա։
- **Նկարներ ընդունվելուց հետո.** նույնը, գումարած էս հոսքի տողերը `ops_originals`-ից ու `ops_assets`-ից հանելը (ճանաչվում են. provenance-ը սկսվում ա `ARMEN_PORTAL`-ով, վստահությունը `AGENT_DECLARED_MASKS` ա) ու `MEDIA_INBOX`-ի սևագրի հետ բերելը։ **Բնօրինակը inbox-ից հանվում ա միայն ստուգելուց հետո, որ կաբինետը նույն բայթերը դեռ ունի (sha256). հակառակ դեպքում մնում ա։** 1-ին քայլի բազայի պահուստը վերջին միջոցն ա. այն հետ դնելը կջնջեր runtime-ում դրանից հետո գրված ամեն ինչ։

### Ռիսկերը, ուղիղ

- `kryuk-run`-ը ստանում ա Արմենի նկարներն ու պատասխանները կարդալու իրավունք։ Այսօր ուրիշ ոչ մի ծառայություն դրանք չի կարդում։
- Կաբինետի ֆայլերը դառնում են խմբի համար կարդացվող։ Խմբում երկու անդամ կա՝ կաբինետն ու runtime-ը։
- 2-րդ քայլը կաբինետը restart ա անում. մտածը նորից ա մտնում։
- Համարանիշների ու դեմքերի փակումը հենվում ա ագենտի հայտարարածի ու Գևի նայելու վրա։ Կոդը ոչինչ չի հայտնաբերում։
- Մինչև անելը ստուգված չի. վահանակը էս հոսքի սարքած նկարներով սևագիրը ցույց տալիս ա։

### Ինչ «հա» ա խնդրվում

«Հա. մեդիայի հոսքը դիր ինչպես գրված ա `runtime/media_pipeline/INSTALL_PLAN.md`-ում. `kryuk-run`-ը կաբինետը կարդում ա խմբով, կաբինետի ֆայլերը դառնում են 640 մեկ restart-ով, չորս նոր աղյուսակ, media պանակ, կոդը `/opt/kryuk24-media`-ում, գործարկումը ձեռքով, առանց timer-ի, առանց հրապարակման։»
