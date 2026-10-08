# Media pipeline v0.1 / Մեդիայի հոսք v0.1

## EN

Gev's requirement of 08.10.2026: Armen puts his photos into his portal instead of WhatsApp; they become available to the internal agents, are processed and prepared for publication; Gev approves; nothing piles up.

This module is the part between the portal's upload and Gev's approval. It is built on what the runtime already has and changes none of it:

- `ops_media.MediaStore` is the shared media inbox: one original for one sha256, prepared assets beside it.
- `ops_work.Operations` holds the day's `MEDIA_INBOX` task, its draft, Gev's approval in his dashboard and the recorded result.

**State: in the repository, with tests, and rehearsed on the server in a temporary place. Not installed: on the server nothing connects the real portal to the runtime's inbox yet.**

### What it does

| Step | What happens | What it never does |
| --- | --- | --- |
| 1. Intake (`intake_portal`) | Reads the portal's photo list read-only. Every new photo becomes one original of the inbox and one work of the queue, with the portal's photo id, sha256, who uploaded, when, the purpose and a status. Checks the file against the sha256 the portal recorded | A photo already taken in, or the same bytes under another portal id, makes no second original and no second work. A file that is not what the portal recorded is not taken in. Nothing new is taken in at the storage limit |
| 2. Agent's queue (`queue`, `claim`, `original_bytes`, `release`) | An agent sees fixed fields only: id, sha256, format, who, when, purpose, status, attempts. It claims one work for a limited time and only then may read that one original | No path, no free text. No original for a worker without the lease. An expired lease gives the work to the next worker; the late one is refused |
| 3. Processing (`prepare`) | Turns the picture upright, covers the regions the worker declares (kind `PLATE`, `FACE` or `PERSONAL`, a box in pixels) with blocks and a blur that cannot be undone, makes two sizes, writes fresh JPEG files without EXIF (so no GPS). Sizes are the ones in use on 08.10.2026: `FULL` 1600 px on the long edge (the card), `WEB` 747 px (the site) | **Nothing is detected by the code.** The worker looks at the picture and declares the regions, or says outright that there is nothing to cover; without one of the two no variant is made. No colour change, no retouching, nothing generated. A small original is not blown up. The original is never rewritten |
| 4. Review (`submit`, `sync`) | Puts prepared pictures before Gev as the draft of the day's `MEDIA_INBOX` task, action `PHOTO_BATCH`, with the platform named (`YANDEX_BUSINESS`, `AVITO` or `SITE`) and the exact asset ids and hashes. It waits in `READY_REVIEW` until Gev approves that digest in his dashboard; then follows his decision: approved, sent back, result recorded | **Publishes nothing.** An upload is not a publication permission. The publication is the recorded result of the existing approval path (`finish_approved`), done by a person after Gev's yes |
| 5. Clean-up and storage (`cleanup`, `storage`) | Removes temporary folders of work nobody holds, files an interrupted attempt left behind, variants no work and no draft names. After the publication is recorded: the variant that was not used and the portal's second copy of the original. Reports sizes by kind against a limit (5 GiB by default): `OK`, `WARN` from 80 %, `FULL` | Never an original of the inbox. Never anything of unfinished work. The portal's copy goes only when the inbox copy is there and both match the recorded sha256 |

What stays after a finished work: one original (the inbox copy), the final variant the approved draft names, the approval and the recorded result.

### Limits, said outright

- Covering depends on the worker's declaration. The assets are recorded with trust `AGENT_DECLARED_MASKS`; the human check is Gev looking at the pictures when he approves.
- One draft a day and one platform a draft: the existing `MEDIA_INBOX` task is one per day. A second platform on the same day waits for the next day's task.
- No HTTP route for agents. The access is the library and `media_cli.py` on the server. The Bro worker's HTTP sidecar has no media route; adding one changes installed code and is a separate step.
- No timer and no service: intake, sync and clean-up run when somebody starts them.
- Removing the portal's second copy needs write access to the portal's photo folder; how the two services share files on the server is not decided or installed.

### Verification

16 tests, on Windows (Python 3.12.10) and on the server (Python 3.14.4), 08.10.2026: intake facts, repeats, a tampered file, the storage limit; the lease on the original; covered region, sizes, no EXIF, an uncovered control, a small PNG; no variant without regions or a declaration; the draft and Gev's approval path; sent back and redone; an interrupted attempt taken over; a failed attempt; nothing of unfinished work removed; what stays after a recorded publication; the portal's copy kept when the inbox original is damaged.

Rehearsal of the whole chain on the server, 08.10.2026 10:16 UTC (`deploy/chain_rehearsal.sh`, output in `evidence/`): a temporary portal instance with the installed portal code, sample pictures uploaded over HTTP on the loopback address, a temporary runtime database. **It is not a phone, not Armen's account, not HTTPS and not the real data.**

```bash
python -m pip install -r runtime/armen_portal/requirements.txt
PYTHONPATH=runtime/server:runtime/armen_portal python -m unittest discover -s runtime/media_pipeline -p "test_*.py"
```

## HY

Գևի պահանջը (08.10.2026). Արմենը նկարները դնում ա իր կաբինետում՝ WhatsApp-ի փոխարեն. դրանք հասանելի են դառնում ներքին ագենտներին, մշակվում ու պատրաստվում են հրապարակման. Գևը հաստատում ա. աղբ չի կուտակվում։

Էս մոդուլը կաբինետի upload-ի ու Գևի հաստատման մեջտեղն ա։ Կառուցված ա runtime-ի եղածի վրա ու դրանից ոչինչ չի փոխում. `ops_media.MediaStore`-ը ընդհանուր media inbox-ն ա (մեկ sha256՝ մեկ բնօրինակ), `ops_work.Operations`-ը պահում ա օրվա `MEDIA_INBOX` գործը, սևագիրը, Գևի հաստատումը վահանակում ու գրանցված արդյունքը։

**Վիճակը. repo-ում ա, թեստերով, ու սերվերում փորձարկված ա ժամանակավոր տեղում։ Դրված չի. սերվերում դեռ ոչինչ իրական կաբինետը runtime-ի inbox-ին չի կապում։**

| Քայլ | Ինչ ա լինում | Ինչ երբեք չի անում |
| --- | --- | --- |
| 1. Ընդունում | Կարդում ա կաբինետի նկարների ցուցակը (միայն կարդալով)։ Ամեն նոր նկար դառնում ա inbox-ի մեկ բնօրինակ ու հերթի մեկ գործ՝ նկարի ID-ով, sha256-ով, ով ա դրել, երբ, նպատակը, վիճակը։ Ֆայլը ստուգում ա կաբինետի գրանցած sha256-ով | Արդեն ընդունված նկարը կամ նույն բայթերը ուրիշ ID-ով երկրորդ բնօրինակ ու երկրորդ գործ չեն սարքում։ Գրանցածից տարբեր ֆայլը չի ընդունվում։ Պահեստի սահմանին նոր բան չի ընդունվում |
| 2. Ագենտի հերթ | Ագենտը տեսնում ա միայն ֆիքսված դաշտեր։ Գործը վերցնում ա սահմանափակ ժամանակով, ու միայն էդ ժամանակ կարող ա կարդալ էդ մեկ բնօրինակը | Ճանապարհ ու ազատ տեքստ չկա։ Առանց lease-ի բնօրինակ չի տրվում։ Ժամկետն անցած lease-ը գործը տալիս ա հաջորդին, ուշացածը մերժվում ա |
| 3. Մշակում | Նկարը ուղղում ա, ագենտի նշած տեղերը (`PLATE`, `FACE`, `PERSONAL`. ուղղանկյուն՝ պիքսելներով) փակում ա բլոկներով ու բլուրով, որ հետ չի բերվում, սարքում ա երկու չափ, գրում ա նոր JPEG՝ առանց EXIF-ի (ուրեմն առանց GPS-ի)։ Չափերը 08.10.2026-ին գործածվողներն են. `FULL` 1600 px (քարտ), `WEB` 747 px (կայք) | **Կոդը ոչինչ չի հայտնաբերում։** Ագենտը նայում ա նկարին ու նշում տեղերը, կամ ուղիղ ասում ա, որ փակելու բան չկա. առանց դրանցից մեկի տարբերակ չի սարքվում։ Գույն չի փոխում, ռետուշ չի անում, բան չի գեներացնում։ Փոքր բնօրինակը չի մեծացնում։ Բնօրինակը երբեք չի վերագրվում |
| 4. Հաստատում | Պատրաստ նկարները դնում ա Գևի առաջ որպես օրվա `MEDIA_INBOX` գործի սևագիր (`PHOTO_BATCH`)՝ հարթակը նշած (`YANDEX_BUSINESS`, `AVITO` կամ `SITE`) ու ճշգրիտ asset-ների ID-ներով ու hash-երով։ Սպասում ա `READY_REVIEW`-ում, մինչև Գևը վահանակում հաստատի հենց էդ digest-ը | **Ոչինչ չի հրապարակում։** Upload-ը հրապարակման թույլտվություն չի։ Հրապարակումը եղած հաստատման ճանապարհի գրանցված արդյունքն ա, որ մարդն ա անում Գևի «հա»-ից հետո |
| 5. Մաքրում ու պահեստ | Հանում ա ոչ մեկի չբռնած գործերի ժամանակավոր պանակները, ընդհատված փորձի թողածը, ոչ մի գործի ու սևագրի չնշած տարբերակները։ Հրապարակման գրանցումից հետո՝ չօգտագործված տարբերակն ու կաբինետի երկրորդ պատճենը։ Ցույց ա տալիս չափերը ըստ տեսակի՝ սահմանի դիմաց (լռելյայն 5 GiB). `OK`, `WARN` 80 %-ից, `FULL` | Inbox-ի բնօրինակը՝ երբեք։ Չավարտված գործից՝ ոչինչ։ Կաբինետի պատճենը հանվում ա միայն երբ inbox-ի պատճենը տեղում ա ու երկուսն էլ համընկնում են գրանցած sha256-ին |

Ավարտած գործից մնում ա. մեկ բնօրինակ (inbox-ինը), հաստատված սևագրի նշած վերջնական տարբերակը, հաստատումն ու գրանցված արդյունքը։

Սահմանները, ուղիղ ասած.

- Փակումը կախված ա ագենտի հայտարարածից։ Asset-ները գրանցվում են `AGENT_DECLARED_MASKS` վստահությամբ. մարդու ստուգումը Գևի նայելն ա հաստատելիս։
- Օրը մեկ սևագիր, սևագիրը մեկ հարթակ. `MEDIA_INBOX` գործը օրը մեկն ա։
- Ագենտների համար HTTP ճանապարհ չկա։ Հասանելիությունը գրադարանն ու `media_cli.py`-ն են սերվերում։ Bro-ի HTTP sidecar-ը media-ի ճանապարհ չունի. ավելացնելը դրված կոդ ա փոխում ու առանձին քայլ ա։
- Timer ու ծառայություն չկա. ընդունումը, sync-ն ու մաքրումը աշխատում են, երբ մեկը գործարկում ա։
- Կաբինետի երկրորդ պատճենը հանելը գրելու իրավունք ա ուզում կաբինետի նկարների պանակում. թե երկու ծառայությունը սերվերում ոնց են ֆայլ կիսում՝ որոշված ու դրված չի։

Ստուգում. 16 թեստ՝ Windows-ում (Python 3.12.10) ու սերվերում (Python 3.14.4), 08.10.2026։ Ամբողջ շղթայի փորձ սերվերում, 08.10.2026 10:16 UTC (`deploy/chain_rehearsal.sh`, ելքը `evidence/`-ում). ժամանակավոր կաբինետ՝ դրված կոդով, փորձնական նկարներ՝ HTTP-ով loopback հասցեով, ժամանակավոր runtime բազա։ **Դա հեռախոս չի, Արմենի հաշիվը չի, HTTPS չի ու իրական տվյալ չի։**
