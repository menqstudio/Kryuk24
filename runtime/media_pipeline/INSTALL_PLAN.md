# Media pipeline: install plan for the server, r4 / Մեդիայի հոսք. սերվերում դնելու պլան, r4

**Status: a plan for review. Nothing in it has been done on the live runtime, and by Gev's word of 08.10.2026 nothing will be until GPT has reviewed the current head, the diff and the evidence.** Server facts were read on 08.10.2026 11:13 UTC with a read-only script. What was tried was tried in a temporary place on the server (11:37 UTC); each such line says so.

r4 adds the fixes of GPT's second review, of head `a52d133` (section 0b), to r3. r3 added the fixes of GPT's review of head `02c21fb` (section 0) to r2; the rest of the plan is r2's, with the numbers of the new rehearsal. r2 replaced r1 of the same day. What changed in r2: the runtime no longer gets read access to the portal's database or photo folder; test data is kept apart by an account, not by marks; backup and rollback are code with tests and were tried.

## EN

### 0. Review of head `02c21fb` (GPT, 08.10.2026): seven findings, each fixed with a test that fails on the reviewed code

| # | Found | Fix | Test |
| --- | --- | --- | --- |
| 1 | The rollback deleted an original the inbox had before the pipeline (the same picture taken in from another source first), and that row was not in the archive | A work records whether the pipeline made its original (`owns_original`: the inbox row carries exactly the provenance this intake writes). The rollback never removes an original it did not make, nor its row; every original a work used is in the archive. The clean-up no longer sweeps unnamed files beside such an original | `test_rollback_never_removes_an_original_the_inbox_had_before_the_pipeline` |
| 2 | The archive was read before the transaction: a second intake between the two lost its history while its tables were dropped | The rollback runs alone: under the pipeline's lock and inside one write transaction, from reading the history to dropping the tables. A failed run removes the archive it started | `test_one_operation_at_a_time_across_processes` |
| 3 | The repair of a half-written file could remove an original another importer had just registered | One lock across processes for intake, processing, submit, sync, clean-up and rollback (`media_lock.py`: a lock of the operating system, released when a process dies). Inside it the check and the removal are one write transaction of the runtime database, and a file that is whole by now is never removed | `test_a_file_that_is_whole_or_registered_by_now_is_never_removed_by_the_repair`, the lock test |
| 4 | A folder that does not exist was read as "the photos were taken back": NEW work became WITHDRAWN | A missing, unreadable or non-folder outbox is refused before anything is looked at. Withdrawal needs proof (first the portal's `INDEX.json`; replaced in 0b by a record per photo). A missing photo file or an empty folder changes no work | `test_a_missing_wrong_or_empty_outbox_is_refused_or_ignored_and_withdraws_nothing` |
| 5 | A hand-over copy cut off at 1000 bytes got its facts published by the next run | No copy at all: a hard link or an error that is said (the portal logs it; at start it refuses an outbox it cannot link into). The facts are written only after the outbox file was read back and its sha256 is the recorded one; a file under the photo's name that is not the photo is replaced first; a damaged portal original gets no facts | `test_hand_over_is_a_hard_link_checked_before_its_facts_appear_and_never_a_silent_copy` |
| 6 | A submit cut off after the draft left the work PREPARED, and the rollback went ahead | The works are marked `SUBMITTING` with their task before the draft is written; `sync` finishes or undoes that from what the task really holds. The rollback reads the tasks themselves: a draft in review or approved that names a variant of this pipeline blocks it, whatever the works' status says | `test_a_submit_cut_off_is_finished_or_undone_from_what_the_task_holds` |
| 7 | Saving an answer as the test account answered `ARMEN_REPORTED` | The stored result of a test answer is `TEST_NOT_COUNTED`, so the repeat of the same request says so too | `test_the_test_accounts_answer_is_never_reported_as_armens_also_when_repeated` |

Run against the reviewed code (`02c21fb`) the new tests fail: 10 of the pipeline's 28 and 4 of the portal's 28. On this head both suites pass, on Windows and on the server. The rehearsal was run again with this code (12:06 UTC): a wrong outbox path refused twice with the queue unchanged, a second operation refused while the lock was held, and the original the inbox had before the pipeline still there and whole after the rollback.


### 0b. Review of head `a52d133` (GPT, 08.10.2026): five more findings, each fixed with a test that fails on the reviewed code

| # | Found | Fix | Test |
| --- | --- | --- | --- |
| 1 | An importer outside the pipeline was halfway through writing a file under its final name; the pipeline's repair deleted that file; the importer finished into a file that was gone and registered a row without a file | The pipeline no longer deletes anything under the name of an original. `place()` copies the photo to a temporary file beside it, checks its sha256 and moves it over the name in one step (`os.replace`): the name always points to a whole file, and a writer still holding the old file writes into one nobody names. A registered original with wrong bytes is still left alone and reported. A move the system refuses is counted as `blocked` and tried again by the next run | `test_an_outside_importer_in_the_middle_of_its_write_does_not_lose_its_original` (two real processes), `test_the_inbox_name_is_filled_whole_and_nothing_under_it_is_ever_deleted` |
| 2 | The portal cut off after the facts of a new photo and before its `INDEX.json`: the intake took the photo in and withdrew it, because the old index did not name it | No index any more. A take-back is a record of its own for that photo, `<id>.withdrawn`, written by the portal before it takes the files out. The intake withdraws a work only when every one of its photos has a valid record; an absence proves nothing. Facts lying beside such a record are not taken in | `test_only_the_portals_own_record_for_that_photo_withdraws_it` |
| 3 | The clean-up deleted a file before the database step was committed; an error after the first file left a registered variant without its file | Rows first, files after, through a list kept in the database (`media_work_deletions`): cut off at any point there is a file nobody names or a line on the list, never a row whose file is gone; the next run finishes the list. The rollback takes the list over | `test_a_clean_up_cut_off_never_leaves_a_row_without_its_file` |
| 4 | A photo handed over earlier was not read again: with its bytes changed, `damaged` stayed empty and its facts stayed | Every hand-over reads every handed-over file back against its sha256; a photo that no longer matches loses its facts and is reported (and logged). The cost is one read of the outbox per run | in `test_hand_over_is_a_hard_link_checked_before_its_facts_appear_and_never_a_silent_copy` |
| 5 | A facts file holding `null` raised `TypeError` and stopped the whole intake | The entry is checked to be an object first; any damaged entry is counted and skipped, the photos beside it are taken in | `test_one_damaged_entry_does_not_stop_the_photos_beside_it` |

One more of the same kind, found while fixing these and not in the review: the clean-up swept "files without a row" beside an original, which could have been somebody else's write in progress. It now removes only what a row or the deletion list says is the pipeline's: a processing puts the names of its variant files on the list before it writes them and takes them off when it registers them (`test_interrupted_processing_is_taken_over_and_its_leftovers_go`).

Run against the reviewed code (`a52d133`) the new tests fail: 8 of the pipeline's 32 and 3 of the portal's 28. On this head both suites pass on Windows and on the server (Linux, including the two-process test). The rehearsal was run again with this code at 12:32 UTC.

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

- The portal itself puts each of Armen's own photos into one folder, the outbox: a hard link to the original (one file on the disk under two names, never a copy) and a small metadata file with the seven facts above, written only after the outbox file was read back against its sha256. The metadata file appears last and whole; without it the intake ignores the photo. Every run reads every handed-over file back against its sha256.
- Only photos of the account `armen` that are not marked as a test are handed over. A photo marked later gets a record of its own, `<id>.withdrawn`, and is then taken out; the intake withdraws its work from the queue if Gev has not got it before him yet. Only that record proves a take-back.
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

Five new tables in `runtime.sqlite`, `CREATE TABLE IF NOT EXISTS`: `media_work`, `media_work_sources`, `media_work_assets`, `media_work_events`, `media_work_deletions` (the list of files still to remove). No existing table is altered. In use the pipeline adds rows to `ops_originals` and `ops_assets` through the existing `MediaStore`, and writes the draft of the day's `MEDIA_INBOX` task through `Operations.draft`.

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
| Two operations at once | the second is refused while the first holds the lock; nothing changed | rehearsal, test |
| A wrong outbox path | refused, the queue unchanged | rehearsal, test |
| The same bytes under another id | no second original, no second work | test |
| Intake cut off after the copy, before the work row | next run makes the one work; one original | test |
| Intake cut off in the middle of the copy (1000 bytes under the photo's name) | next run moves a whole, checked file over the name and reports `repaired: 1`; nothing is deleted; a file an inbox row names is never written over | rehearsal, test |
| An outside importer halfway through its own write of the same photo | its row keeps its file, whole | test with two real processes |
| Clean-up cut off after the first file | no row without its file; the next run finishes the list | test |
| Hand-over cut off between the link and the metadata file | next hand-over completes it | test |
| A half file under the photo's name in the outbox | replaced by the link before any facts are written | test |
| Submit cut off after the draft | `sync` finishes it; the rollback refuses meanwhile | test |
| Upload repeated by Armen | the portal stores the bytes once | rehearsal, test |

### 9. Steps on the server, after the review and Gev's yes

1. Read-only facts; the two backups.
2. Group `kryuk-media-in` with its two members; the outbox folder; the data folder to 710. Check as in the rehearsal: what `kryuk-run` can and cannot reach, on the real paths.
3. Portal unit: add `--outbox`; one restart; `hand_over` runs at the next upload. Today it would hand over nothing: the only photo is Gev's marked test.
4. `/opt/kryuk24-media` with its Python; the 32 tests on the server.
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

### 0. `02c21fb` head-ի review-ը (GPT, 08.10.2026). յոթ գտած, ամեն մեկը ուղղված՝ թեստով, որը review-ած կոդի վրա ընկնում ա

1. **Rollback-ը ջնջում էր inbox-ի նախկին բնօրինակը։** Գործը հիմա գրանցում ա՝ բնօրինակը հոսքն ա սարքել, թե միայն օգտագործել (`owns_original`)։ Չսարքած բնօրինակն ու իր տողը երբեք չեն հանվում. գործի օգտագործած ամեն բնօրինակ արխիվում ա։
2. **Արխիվը transaction-ից առաջ էր։** Rollback-ը հիմա աշխատում ա մենակ. հոսքի կողպեքի տակ ու մեկ գրելու transaction-ի մեջ՝ պատմությունը կարդալուց մինչև աղյուսակները ջնջելը։
3. **Կիսատ ֆայլի repair-ը կարող էր ջնջել նոր գրանցված բնօրինակը։** Մեկ միջպրոցեսային կողպեք (`media_lock.py`) ընդունման, մշակման, submit-ի, sync-ի, մաքրման ու rollback-ի համար. ներսում ստուգումն ու հանելը մեկ transaction են, ու արդեն ամբողջ ֆայլը երբեք չի հանվում։
4. **Չեղած outbox-ը համարվում էր հետկանչ։** Չեղած, չկարդացվող կամ ոչ-պանակ outbox-ը մերժվում ա։ Հետկանչին ապացույց ա պետք (սկզբում կաբինետի `INDEX.json`-ը. 0բ-ում փոխարինվեց ամեն նկարի սեփական գրառումով). դատարկ պանակը ոչինչ չի ապացուցում։
5. **Կիսատ hand-over copy-ն հրապարակվում էր։** Copy այլևս չկա. hard link կամ ասված սխալ։ Փաստերը գրվում են միայն ֆայլը հետ կարդալուց ու sha256-ը ստուգելուց հետո։
6. **Ընդհատված submit-ը շրջանցում էր rollback-ի արգելքը։** Գործերը սևագրից առաջ նշվում են `SUBMITTING`. `sync`-ը ավարտում կամ հետ ա բերում՝ ըստ task-ի իրական վիճակի։ Rollback-ը կարդում ա հենց task-երը։
7. **Test-ի պատասխանը վերադարձնում էր `ARMEN_REPORTED`։** Հիմա `TEST_NOT_COUNTED` ա, կրկնության դեպքում էլ։

Review-ած կոդի վրա նոր թեստերն ընկնում են (հոսքի 28-ից 10-ը, կաբինետի 28-ից 4-ը). էս head-ի վրա երկու հավաքածուն էլ անցնում են Windows-ում ու սերվերում։ Փորձը նորից քշվել ա էս կոդով (12:06 UTC)։


**Վիճակը. պլան՝ review-ի համար։ Կենդանի runtime-ում սրանից ոչինչ արված չի, ու Գևի 08.10.2026-ի խոսքով չի արվի, մինչև GPT-ն չնայի ընթացիկ head-ը, diff-ն ու evidence-ը։** Փորձվածը փորձվել ա սերվերում ժամանակավոր տեղում (11:37 UTC)։

r2-ը փոխարինում ա նույն օրվա r1-ին։ Ինչ փոխվեց. runtime-ը այլևս չի ստանում կաբինետի բազան կամ նկարների պանակը կարդալու իրավունք. թեստային տվյալը առանձնացված ա հաշվով, ոչ թե նշումով. պահուստն ու rollback-ը կոդ են՝ թեստերով, ու փորձվել են։

### 0բ. `a52d133` head-ի review-ը (GPT, 08.10.2026). ևս հինգ գտած, ամեն մեկը ուղղված՝ թեստով, որը review-ած կոդի վրա ընկնում ա

1. **Արտաքին importer-ի մրցավազքը։** Հոսքն այլևս բնօրինակի անվան տակ ոչինչ չի ջնջում։ Նկարը պատճենվում ա կողքի ժամանակավոր ֆայլի մեջ, ստուգվում ա sha256-ով ու մեկ քայլով դրվում ա անվան վրա (`os.replace`). անունը միշտ ամբողջ ֆայլ ա ցույց տալիս։ Թեստը երկու իրական պրոցեսով ա։
2. **Հին INDEX-ը նոր նկարը WITHDRAWN էր դարձնում։** Index այլևս չկա։ Հետկանչը էդ նկարի սեփական գրառումն ա՝ `<id>.withdrawn`, որը կաբինետը գրում ա ֆայլերը հանելուց առաջ։ Բացակայությունը ոչինչ չի ապացուցում։
3. **Մաքրման ընդհատումը թողնում էր տող առանց ֆայլի։** Նախ տողերը, հետո ֆայլերը՝ բազայում պահվող ցուցակով (`media_work_deletions`). ընդհատվի որտեղ ուզում ա՝ մնում ա անանուն ֆայլ կամ ցուցակի տող, երբեք՝ տող առանց ֆայլի. հաջորդ գործարկումը ավարտում ա։
4. **Արդեն փոխանցված նկարը նորից չէր կարդացվում։** Ամեն փոխանցում հիմա ամեն փոխանցված ֆայլ հետ ա կարդում ու համեմատում sha256-ի հետ. չհամընկնողը կորցնում ա իր փաստերն ու զեկուցվում ա։
5. **`null` պարունակող metadata-ն կանգնեցնում էր ամբողջ ընդունումը։** Վնասված գրառումը հաշվվում ու բաց ա թողնվում, կողքի նկարները ընդունվում են։

Նույն դասի ևս մեկը գտա ուղղելիս, review-ում չկար. մաքրումը ավլում էր «տող չունեցող ֆայլերը» բնօրինակի կողքին, որոնք կարող էին ուրիշի ընթացիկ գրածը լինել։ Հիմա հանում ա միայն էն, ինչ տողը կամ ջնջման ցուցակն ա ասում, որ հոսքինն ա։

Review-ած կոդի վրա նոր թեստերն ընկնում են (հոսքի 32-ից 8-ը, կաբինետի 28-ից 3-ը). էս head-ի վրա երկու հավաքածուն էլ անցնում են Windows-ում ու սերվերում (Linux, ներառյալ երկու պրոցեսով թեստը)։ Փորձը նորից քշվել ա 12:32 UTC-ին։

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
4. `/opt/kryuk24-media`-ն իր Python-ով. 32 թեստը սերվերում։
5. Media պանակը. `storage` մեկ անգամ (ստեղծում ա չորս աղյուսակը). snapshot-ը համեմատվում ա 1-ին քայլի հետ։
6. Էստեղից Արմենի իրական նկարը. upload → outbox → `intake` → ագենտը վերցնում ա, նայում, նշում տեղերը → տարբերակներ → `submit` → սևագիր Գևի վահանակում։ Ձեռքով. ծառայություն ու timer չկա։
7. Նորից փաստեր. evidence. `docs/CURRENT_STATE.md`։

### 10. Ինչը էս պլանում չկա, ուղիղ

- Հրապարակումից հետո կաբինետի սեփական ֆայլը հանելը։ Այսօր նկարը կա որպես մեկ ֆայլ կաբինետում (երկու անունով) ու մեկը inbox-ում։ Հոսքը կաբինետում գրելու իրավունք չունի, դիտմամբ։
- Ագենտների HTTP ճանապարհ, timer, օրը մեկից ավել սևագիր, կաբինետի տվյալների պահուստի ռեժիմ։
- Հայտնաբերում. համարանիշների ու դեմքերի փակումը հենվում ա ագենտի հայտարարածի ու Գևի նայելու վրա։
- Մինչև դնելը ստուգված չի. կենդանի վահանակը էս հոսքի սարքած նկարներով սևագիրը ցույց տալիս ա։
