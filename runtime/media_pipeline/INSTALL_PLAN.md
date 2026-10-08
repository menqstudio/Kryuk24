# Media pipeline: install plan for the server, r2 / Մեդիայի հոսք. սերվերում դնելու պլան, r2

**Status: a plan for review. Nothing in it has been done on the live runtime, and by Gev's word of 08.10.2026 nothing will be until GPT has reviewed the current head, the diff and the evidence.** Server facts were read on 08.10.2026 11:13 UTC with a read-only script. What was tried was tried in a temporary place on the server (11:37 UTC); each such line says so.

r2 replaces r1 of the same day. What changed: the runtime no longer gets read access to the portal's database or photo folder; test data is kept apart by an account, not by marks; backup and rollback are code with tests and were tried.

## EN

### 1. What the photo flow actually needs from the portal

| Needed | Why |
| --- | --- |
| The photo file, byte for byte | it becomes the original of the shared inbox |
| Its id in the portal | so that a repeat makes no second original and no second work |
| Its sha256 | to check the file before taking it in |
| Its format (JPEG, PNG, WebP) | the file name and the queue's fixed fields |
| Who uploaded (always `armen`) and when | "who put it and when" in the inbox record |
| The purpose Armen chose (work, equipment, other) | the queue's fixed fields |

**Not needed and not given:** the answers to the daily questions, the request keys, the previews, the rows of the test account, the rows marked as a test, the credential file, the portal's database as such.

### 2. How it gets exactly that: the outbox

- The portal itself puts each of Armen's own photos into one folder, the outbox: a hard link to the original (one file on the disk under two names) and a small metadata file with the seven facts above. The metadata file appears last and whole; without it the intake ignores the photo.
- Only photos of the account `armen` that are not marked as a test are handed over. A photo marked later is taken back out, and the intake then withdraws its work from the queue if Gev has not got it before him yet.
- The pipeline reads the outbox and nothing else of the portal. Its code holds no SQL for the portal's tables at all (a test checks that), and the intake was run with the portal's database and photo folder deleted (a test).
- Without the outbox setting no photo leaves the portal. **That is the state of the live portal today:** its unit has no `--outbox`.

### 3. File permissions, exactly

| Path | Today (read) | After | Who gains what |
| --- | --- | --- | --- |
| new group `kryuk-media-in` | absent | members `kryuk-armen`, `kryuk-run` | nothing by itself |
| `/var/lib/kryuk24-armen` | `kryuk-armen:kryuk-armen` 700 | `kryuk-armen:kryuk-media-in` 710 | the group may pass through to a name it knows; it cannot list the folder |
| `…/portal.sqlite` | 600 | 600, unchanged | nobody: the runtime cannot read answers or anything else in it |
| `…/photos` | 700 | 700, unchanged | nobody: previews and the test account's photos stay closed |
| `…/outbox` | absent | `kryuk-armen:kryuk-media-in` 2750 | the group may list and read; only the portal writes |
| a handed-over photo file | 600 | 640, group `kryuk-media-in` (the same file as in `photos`, reachable only through the outbox) | the group may read that photo |
| `/var/lib/kryuk24/media` | absent | `kryuk-run:kryuk-run` 700 | the runtime's own folder |

The outbox sits inside the portal's data folder because a hard link needs one file system and the portal's service sees each writable path as its own: with the outbox beside the data folder the rehearsal got copies, with it inside it got one file under two names (both runs are in the evidence).

**Tried on the server in a temporary place with the real users `kryuk-armen` and `kryuk-run`:** the runtime user read an outbox photo; it was refused the portal's database, the listing of the photo folder, a preview by its path, the listing of the data folder, writing into the outbox and removing an outbox file.

The pipeline runs as `kryuk-run` because the pictures it stores must be readable by the dashboard, which runs as `kryuk-run` and stores media with mode 400. So the pipeline can do in the runtime's database whatever the runtime can. Narrowing that would need a change of the installed dashboard code; it is not proposed here.

### 4. Test data is kept apart by the system

- A third account, `test`: it uploads and answers like Armen, sees only its own rows, and the page says «Тестовый вход». Its rows are never Armen's: not in Armen's state, not in the reviewer's, not in the outbox, so never in the inbox, the queue, a draft or a publication.
- Installed in the live portal's code since 08.10.2026 11:38 UTC. **The account does not exist until Gev sets its password** (`provision_from_windows.ps1 -Account test`) and the portal is restarted once.
- The four rows of Gev's earlier test under `armen` stay marked in `armen_excluded`. Marking by hand remains only for a mistake of that kind.

### 5. Database migration

Four new tables in `runtime.sqlite`, `CREATE TABLE IF NOT EXISTS`: `media_work`, `media_work_sources`, `media_work_assets`, `media_work_events`. No existing table is altered. In use the pipeline adds rows to `ops_originals` and `ops_assets` through the existing `MediaStore`, and writes the draft of the day's `MEDIA_INBOX` task through `Operations.draft`.

### 6. Backup, tried

`media_rollback.py backup`: SQLite's online backup into a new file (never over an existing one, mode 600), `PRAGMA integrity_check` on the copy, row count and content fingerprint of every table.

- **Tried:** in the rehearsal the copy passed the check; after intake and processing a copy of that backup had the same 14 tables with the same fingerprints as the snapshot taken before.
- Before the real install: the runtime database and the portal database, into `/root/kryuk24-config-backups/`. The portal's photo files are not copied: the install changes the mode and group of handed-over files only; their names, sizes and sha256 go into the evidence before and after.

### 7. Rollback, tried

`media_rollback.py rollback`:

| Rule | Tried in the rehearsal |
| --- | --- |
| The history of accepted work is written to an archive file first (the four tables and the pipeline's inbox rows); without the archive nothing is removed; an existing archive is never written over | archive of 5726 bytes, mode 600, with the events `TAKEN_IN`, `TAKEN_IN`, `CLAIMED`, `PREPARED` |
| An original leaves the inbox only when the outbox still holds the same bytes | two originals removed, both photos whole in the outbox afterwards |
| **An original that is the only copy the pipeline can see is never removed** | one photo taken out of the outbox before the rollback: its original stayed in the inbox, whole, with its row |
| Work whose publication is recorded keeps its original, final variant and approval records | by test |
| It refuses while a draft of this pipeline is before Gev | by test |
| The four tables are dropped; every other table is as it was before the pipeline | 14 tables before, 14 after, none differs |
| A second run does nothing | "nothing to roll back" |
| Files are removed after the database step: a run cut off there leaves unnamed files, never a missing one | by the order in the code |

Beyond the database: take `--outbox` out of the portal's unit and restart it, remove the outbox folder (its photos are the same files as in `photos`, which stay), put `/var/lib/kryuk24-armen` back to 700 and `kryuk-armen`, remove the group, remove `/opt/kryuk24-media` and an empty `/var/lib/kryuk24/media`.

### 8. Repeated and interrupted runs, tried

| Case | Result | Where |
| --- | --- | --- |
| Intake run twice | second run: 2 known, 0 imported | rehearsal, test |
| The same bytes under another id | no second original, no second work | test |
| Intake cut off after the copy, before the work row | next run makes the one work; one original | test |
| Intake cut off in the middle of the copy (1000 of 5999287 bytes under the photo's name) | next run replaces the half file and reports `repaired: 1`; a file an inbox row names is never written over | rehearsal, test |
| Hand-over cut off between the link and the metadata file | next hand-over completes it | test |
| Upload repeated by Armen | the portal stores the bytes once | rehearsal, test |

### 9. Steps on the server, after the review and Gev's yes

1. Read-only facts; the two backups.
2. Group `kryuk-media-in` with its two members; the outbox folder; the data folder to 710. Check as in the rehearsal: what `kryuk-run` can and cannot reach, on the real paths.
3. Portal unit: add `--outbox`; one restart; `hand_over` runs at the next upload. Today it would hand over nothing: the only photo is Gev's marked test.
4. `/opt/kryuk24-media` with its Python; the 23 tests on the server.
5. Media folder; `storage` once (creates the four tables); snapshot compared with step 1: no existing table changed.
6. From here a real photo of Armen's: upload → outbox → `intake` → an agent claims, looks, declares the regions → variants → `submit` → the draft in Gev's dashboard. Started by hand; no service, no timer.
7. Facts again; evidence; `docs/CURRENT_STATE.md`.

### 10. Not in this plan, said outright

- Removing the portal's own file after a publication. Today the photo exists as one file in the portal (two names) and one in the inbox. The pipeline has no right to write in the portal, on purpose.
- An HTTP route for agents, a timer, more than one draft a day.
- A backup routine for the portal's data.
- Detection: covering plates and faces rests on the agent's declaration and on Gev's look at approval.
- Not verified until installed: the live dashboard showing a media draft with pictures made by this pipeline.

## HY

**Վիճակը. պլան՝ review-ի համար։ Կենդանի runtime-ում սրանից ոչինչ արված չի, ու Գևի 08.10.2026-ի խոսքով չի արվի, մինչև GPT-ն չնայի ընթացիկ head-ը, diff-ն ու evidence-ը։** Փորձվածը փորձվել ա սերվերում ժամանակավոր տեղում (11:37 UTC)։

r2-ը փոխարինում ա նույն օրվա r1-ին։ Ինչ փոխվեց. runtime-ը այլևս չի ստանում կաբինետի բազան կամ նկարների պանակը կարդալու իրավունք. թեստային տվյալը առանձնացված ա հաշվով, ոչ թե նշումով. պահուստն ու rollback-ը կոդ են՝ թեստերով, ու փորձվել են։

### 1. Ինչ ա իրականում պետք նկարների հոսքին

Նկարի ֆայլը՝ բայթ առ բայթ, կաբինետի ID-ն, sha256-ը, ֆորմատը, ով ա դրել (միշտ `armen`) ու երբ, Արմենի ընտրած նպատակը։ **Պետք չի ու չի տրվում.** օրվա հարցերի պատասխանները, հարցումների բանալիները, preview-ները, test հաշվի տողերը, թեստ նշված տողերը, գաղտնաբառի ֆայլը, կաբինետի բազան որպես այդպիսին։

### 2. Ոնց ա ստանում հենց դա. ելքի արկղ (outbox)

- Կաբինետն ինքն ա Արմենի ամեն նկարը դնում մեկ պանակում. hard link բնօրինակին (մեկ ֆայլ սկավառակում՝ երկու անունով) ու փոքր metadata ֆայլ՝ էդ յոթ փաստով։ Metadata-ն հայտնվում ա վերջում ու ամբողջական. առանց դրա ընդունումը նկարը չի տեսնում։
- Փոխանցվում են միայն `armen` հաշվի, թեստ չնշված նկարները։ Հետո նշված նկարը հետ ա վերցվում, ու ընդունումը դրա գործը հանում ա հերթից, եթե դեռ Գևի առաջ չի։
- Հոսքը կարդում ա միայն outbox-ը։ Իր կոդում կաբինետի աղյուսակների համար SQL ընդհանրապես չկա (թեստը ստուգում ա), ու ընդունումը աշխատեցվել ա կաբինետի բազան ու նկարների պանակը ջնջած վիճակում (թեստ)։
- Առանց outbox-ի կարգավորման ոչ մի նկար կաբինետից դուրս չի գալիս։ **Կենդանի կաբինետի վիճակը այսօր հենց դա ա.** unit-ում `--outbox` չկա։

### 3. Ֆայլերի իրավունքները, ճշգրիտ

| Ճանապարհ | Այսօր | Հետո | Ով ինչ ա ստանում |
| --- | --- | --- | --- |
| նոր խումբ `kryuk-media-in` | չկա | անդամներ՝ `kryuk-armen`, `kryuk-run` | ինքնին՝ ոչինչ |
| `/var/lib/kryuk24-armen` | 700 | `kryuk-armen:kryuk-media-in` 710 | խումբը անցնում ա միջով դեպի իմացած անուն. պանակը ցուցակել չի կարող |
| `…/portal.sqlite` | 600 | 600, անփոփոխ | ոչ ոք. runtime-ը պատասխանները չի կարդում |
| `…/photos` | 700 | 700, անփոփոխ | ոչ ոք. preview-ներն ու test հաշվի նկարները փակ են |
| `…/outbox` | չկա | `kryuk-armen:kryuk-media-in` 2750 | խումբը ցուցակում ու կարդում ա. գրում ա միայն կաբինետը |
| փոխանցված նկարի ֆայլը | 600 | 640, խումբը `kryuk-media-in` | խումբը կարդում ա էդ նկարը |
| `/var/lib/kryuk24/media` | չկա | `kryuk-run:kryuk-run` 700 | runtime-ի սեփական պանակը |

**Փորձվել ա սերվերում ժամանակավոր տեղում՝ իրական `kryuk-armen` ու `kryuk-run` user-ներով.** runtime-ի user-ը կարդաց outbox-ի նկարը. մերժվեց՝ կաբինետի բազան, նկարների պանակի ցուցակը, preview-ն իր ճանապարհով, տվյալների պանակի ցուցակը, outbox-ում գրելը ու outbox-ի ֆայլ ջնջելը։

Հոսքը աշխատում ա `kryuk-run`-ով, որովհետև իր պահած նկարները պիտի կարդա վահանակը։ Ուրեմն runtime-ի բազայում հոսքը կարող ա անել էն ամենը, ինչ runtime-ը։ Դա նեղացնելը դրված վահանակի կոդի փոփոխություն կուզեր. էստեղ չի առաջարկվում։

### 4. Թեստային տվյալը առանձնացված ա համակարգով

- Երրորդ հաշիվ՝ `test`. նկար ա դնում ու պատասխանում Արմենի պես, տեսնում ա միայն իր տողերը, էջը գրում ա «Тестовый вход»։ Իր տողերը երբեք Արմենինը չեն. չկան Արմենի վիճակում, review-ի վիճակում, outbox-ում, ուրեմն երբեք չեն հասնում inbox-ին, հերթին, սևագրին կամ հրապարակմանը։
- Կենդանի կաբինետի կոդում ա 08.10.2026 11:38 UTC-ից։ **Հաշիվը գոյություն չունի, մինչև Գևը գաղտնաբառը չդնի** (`provision_from_windows.ps1 -Account test`) ու կաբինետը մեկ անգամ restart չլինի։
- Գևի նախորդ տեստի չորս տողը մնում են նշված։ Ձեռքով նշելը մնում ա միայն էդպիսի սխալի համար։

### 5. Բազայի migration

Չորս նոր աղյուսակ `runtime.sqlite`-ում (`CREATE TABLE IF NOT EXISTS`)։ Եղած ոչ մի աղյուսակ չի փոխվում։ Աշխատելիս տողեր են ավելանում `ops_originals`-ում ու `ops_assets`-ում եղած կոդով, ու գրվում ա օրվա `MEDIA_INBOX` գործի սևագիրը։

### 6. Պահուստ, փորձված

`media_rollback.py backup`. SQLite-ի online backup նոր ֆայլի մեջ (երբեք եղածի վրա, 600), `integrity_check` պատճենի վրա, ամեն աղյուսակի տողերի թիվն ու բովանդակության մատնահետքը։ **Փորձվել ա.** պատճենը անցավ ստուգումը. ընդունումից ու մշակումից հետո էդ պահուստի պատճենը ուներ նույն 14 աղյուսակը նույն մատնահետքերով, ինչ մինչև հոսքը վերցրած snapshot-ը։

### 7. Rollback, փորձված

- Ընդունված աշխատանքի պատմությունը նախ գրվում ա արխիվի ֆայլում. առանց արխիվի ոչինչ չի հանվում. եղած արխիվի վրա չի գրվում։ Փորձում՝ 5726 բայթ, 600, իրադարձությունները՝ `TAKEN_IN`, `TAKEN_IN`, `CLAIMED`, `PREPARED`։
- Բնօրինակը inbox-ից հանվում ա միայն երբ outbox-ը նույն բայթերը դեռ ունի։ Փորձում՝ երկու բնօրինակ հանվեց, երկու նկարն էլ outbox-ում ամբողջ մնացին։
- **Բնօրինակը, որը հոսքի տեսած միակ պատճենն ա, երբեք չի հանվում։** Փորձում՝ մեկ նկար հանվեց outbox-ից rollback-ից առաջ. իր բնօրինակը մնաց inbox-ում, ամբողջ, իր տողով։
- Հրապարակումը գրանցած գործը պահում ա բնօրինակը, վերջնական տարբերակն ու հաստատման գրառումները (թեստ)։ Մերժում ա, քանի դեռ էս հոսքի սևագիրը Գևի առաջ ա (թեստ)։
- Չորս աղյուսակը ջնջվում ա. մնացած ամեն աղյուսակ նույնն ա, ինչ մինչև հոսքը։ Փորձում՝ 14 առաջ, 14 հետո, ոչ մեկը չի տարբերվում։ Երկրորդ գործարկումը ոչինչ չի անում։
- Ֆայլերը հանվում են բազայի քայլից հետո. էնտեղ ընդհատված գործարկումը թողնում ա անանուն ֆայլեր, երբեք՝ պակաս։

### 8. Կրկնակի ու ընդհատված գործարկում, փորձված

- Ընդունումը երկու անգամ. երկրորդը՝ 2 known, 0 imported։
- Նույն բայթերը ուրիշ ID-ով. երկրորդ բնօրինակ ու երկրորդ գործ չկա (թեստ)։
- Ընդունումը ընդհատվել ա պատճենից հետո, գործի տողից առաջ. հաջորդը սարքում ա մեկ գործը, մեկ բնօրինակ (թեստ)։
- Ընդունումը ընդհատվել ա պատճենի կեսին (5999287 բայթից 1000-ը նկարի անվան տակ). հաջորդը փոխարինում ա կիսատ ֆայլը, `repaired: 1`. inbox-ի տողի նշած ֆայլի վրա երբեք չի գրվում։
- Փոխանցումը ընդհատվել ա link-ի ու metadata-ի մեջտեղում. հաջորդը ավարտում ա (թեստ)։

### 9. Քայլերը սերվերում, review-ից ու Գևի «հա»-ից հետո

1. Միայն-կարդացող փաստեր. երկու պահուստ։
2. `kryuk-media-in` խումբը երկու անդամով. outbox-ի պանակը. տվյալների պանակը՝ 710։ Ստուգում իրական ճանապարհների վրա. ինչին ա `kryuk-run`-ը հասնում, ինչին՝ չէ։
3. Կաբինետի unit-ում `--outbox`. մեկ restart։ Այսօր ոչինչ չէր փոխանցվի. միակ նկարը Գևի նշված տեստն ա։
4. `/opt/kryuk24-media`-ն իր Python-ով. 23 թեստը սերվերում։
5. Media պանակը. `storage` մեկ անգամ (ստեղծում ա չորս աղյուսակը). snapshot-ը համեմատվում ա 1-ին քայլի հետ։
6. Էստեղից Արմենի իրական նկարը. upload → outbox → `intake` → ագենտը վերցնում ա, նայում, նշում տեղերը → տարբերակներ → `submit` → սևագիր Գևի վահանակում։ Ձեռքով. ծառայություն ու timer չկա։
7. Նորից փաստեր. evidence. `docs/CURRENT_STATE.md`։

### 10. Ինչը էս պլանում չկա, ուղիղ

- Հրապարակումից հետո կաբինետի սեփական ֆայլը հանելը։ Այսօր նկարը կա որպես մեկ ֆայլ կաբինետում (երկու անունով) ու մեկը inbox-ում։ Հոսքը կաբինետում գրելու իրավունք չունի, դիտմամբ։
- Ագենտների HTTP ճանապարհ, timer, օրը մեկից ավել սևագիր, կաբինետի տվյալների պահուստի ռեժիմ։
- Հայտնաբերում. համարանիշների ու դեմքերի փակումը հենվում ա ագենտի հայտարարածի ու Գևի նայելու վրա։
- Մինչև դնելը ստուգված չի. կենդանի վահանակը էս հոսքի սարքած նկարներով սևագիրը ցույց տալիս ա։
