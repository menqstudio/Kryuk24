# Media pipeline v0.4 / Մեդիայի հոսք v0.4

## EN

Gev's requirement of 08.10.2026: Armen puts his photos into his portal instead of WhatsApp; they become available to the internal agents, are processed and prepared for publication; Gev approves; nothing piles up.

This module is the part between the portal's hand-over and Gev's approval. It is built on what the runtime already has and changes none of it: `ops_media.MediaStore` (the shared media inbox: one original for one sha256) and `ops_work.Operations` (the day's `MEDIA_INBOX` task, its draft, Gev's approval in his dashboard, the recorded result).

**State: in the repository, with tests, and rehearsed on the server in a temporary place. Not installed: the live portal hands nothing over (its unit has no outbox) and nothing in the live runtime knows this module.** The proposed install, its permissions, backup and rollback: [`INSTALL_PLAN.md`](INSTALL_PLAN.md).

### What it reads of the portal

One folder, the outbox, where the portal itself puts Armen's own photos: for each a file and a small metadata file (id, sha256, format, file, actor, uploaded, purpose). It has no code that opens the portal's database, its photo folder, an answer, a preview or a row of the test account, and it needs none (since v0.2; v0.1 of the same day read the portal's database). v0.3 is v0.2 with the seven fixes of GPT's review of head `02c21fb`, v0.4 adds the five of his review of head `a52d133`; both lists are in `INSTALL_PLAN.md`, sections 0 and 0b.

### What it does

| Step | What happens | What it never does |
| --- | --- | --- |
| 1. Intake (`intake`) | Every new photo in the outbox becomes one original of the inbox and one work of the queue, with the portal's photo id, sha256, who uploaded, when, the purpose and a status. The file is checked against its sha256 | A photo already taken in, or the same bytes under another id, makes no second original and no second work. A file that is not what its facts say is not taken in. Nothing new at the storage limit. A run cut off at any point is completed by the next one. Nothing under the name of an original is ever deleted: a whole, checked file is moved over the name in one step, so an importer outside the pipeline cannot lose its file; a registered original is never written over. A damaged entry is skipped, the others are taken in |
| 2. Agent's queue (`queue`, `claim`, `original_bytes`, `release`) | An agent sees fixed fields only. It claims one work for a limited time and only then may read that one original | No path, no free text. No original for a worker without the lease. An expired lease gives the work to the next worker; the late one is refused |
| 3. Processing (`prepare`) | Upright, the declared regions (kind `PLATE`, `FACE` or `PERSONAL`, a box in pixels) covered with blocks and a blur that cannot be undone, two sizes (`FULL` 1600 px, `WEB` 747 px: the sizes in use on 08.10.2026), fresh JPEG files without EXIF | **Nothing is detected by the code.** The worker declares the regions or says outright that there are none. No colour change, no retouching, nothing generated. A small original is not blown up. The original is never rewritten |
| 4. Review (`submit`, `sync`) | Prepared pictures go before Gev as the draft of the day's `MEDIA_INBOX` task, with the platform named (`YANDEX_BUSINESS`, `AVITO` or `SITE`) and the exact asset ids and hashes. It follows his decision: approved, sent back, result recorded | **Publishes nothing.** An upload is not a publication permission |
| 5. Clean-up and storage (`cleanup`, `storage`) | Removes temporary folders of work nobody holds, the files an interrupted processing left, variants no work and no draft names: rows first, files after, through a list kept in the database, so a run cut off never leaves a row without its file. Sizes against a limit (5 GiB by default): `OK`, `WARN` from 80 %, `FULL` | Never an original. Never anything of unfinished work. Never a file it cannot prove is its own. It writes nothing outside the runtime's media folder |
| Withdrawn | A photo the portal takes back (marked as a test after the hand-over) gets a record of its own, `<id>.withdrawn`, and leaves the queue when the next intake runs. Only that record proves a take-back: a missing file, an empty or wrong folder changes nothing | Work already before Gev, or published, is not touched: that is his to decide |

One operation at a time: intake, processing, submit, sync, clean-up and rollback take one lock across processes (`media_lock.py`); a second one is refused after a short wait and changes nothing.

`media_rollback.py`: `backup` (a checked copy of the database), `snapshot` (row count and content fingerprint of every table), `rollback` (alone, in one transaction; the history archived first; an original the pipeline did not make is never removed; an original that is the only copy stays; published work stays whole; refuses while a draft that names its variants is before Gev, read from the tasks themselves).

### Limits, said outright

- Covering depends on the worker's declaration (trust `AGENT_DECLARED_MASKS`); the human check is Gev looking at the pictures when he approves.
- One draft a day and one platform a draft: the existing `MEDIA_INBOX` task is one per day.
- No HTTP route for agents, no service, no timer: the library and `media_cli.py`, started by hand.
- After a publication the photo still exists twice: the portal's file and the inbox original. The pipeline has no right to write in the portal.
- It runs as the runtime's user, so in the runtime's database it can do what the runtime can.

### Verification

32 tests, on Windows (Python 3.12.10) and on the server (Python 3.14.4), 08.10.2026: 27 on the chain and 5 for backup and rollback; among them the regression tests of the two reviews, one of them with two real processes. The chain (intake facts, repeats, wrong files, the storage limit, the lease, covering, sizes, no EXIF, the draft and Gev's approval path, sent back, an interrupted attempt, a failed attempt, clean-up), the outbox as the only source (the intake run with the portal's database and photo folder deleted); the test account and marked photos never entering, a later mark withdrawing; an intake cut off after the copy and in the middle of it.

Rehearsal on the server, 08.10.2026 12:32 UTC (`deploy/chain_rehearsal.sh`, output in `evidence/`): the real users `kryuk-armen` and `kryuk-run` on temporary folders, a temporary portal instance with sample pictures, the live runtime data hidden from every process. **It is not a phone, not Armen's account, not HTTPS and not the real data.**

```bash
python -m pip install -r runtime/armen_portal/requirements.txt
PYTHONPATH=runtime/server:runtime/armen_portal python -m unittest discover -s runtime/media_pipeline -p "test_*.py"
```

## HY

Գևի պահանջը (08.10.2026). Արմենը նկարները դնում ա իր կաբինետում՝ WhatsApp-ի փոխարեն. դրանք հասանելի են դառնում ներքին ագենտներին, մշակվում ու պատրաստվում են հրապարակման. Գևը հաստատում ա. աղբ չի կուտակվում։

Էս մոդուլը կաբինետի փոխանցման ու Գևի հաստատման մեջտեղն ա։ Կառուցված ա runtime-ի եղածի վրա ու դրանից ոչինչ չի փոխում։

**Վիճակը. repo-ում ա, թեստերով, ու փորձարկված ա սերվերում ժամանակավոր տեղում։ Դրված չի. կենդանի կաբինետը ոչինչ չի փոխանցում (unit-ում outbox չկա), ու կենդանի runtime-ում ոչինչ էս մոդուլի մասին չգիտի։** Առաջարկվող տեղադրումը, իրավունքները, պահուստն ու rollback-ը՝ [`INSTALL_PLAN.md`](INSTALL_PLAN.md)։

**Ինչ ա կարդում կաբինետից.** մեկ պանակ՝ outbox-ը, որտեղ կաբինետն ինքն ա դնում Արմենի նկարները. ամեն մեկի համար ֆայլ ու փոքր metadata ֆայլ։ Կաբինետի բազան, նկարների պանակը, պատասխանները, preview-ները կամ test հաշվի տողերը բացող կոդ չունի ու դրա կարիքը չունի (v0.2-ից. նույն օրվա v0.1-ը կարդում էր կաբինետի բազան)։ v0.3-ը v0.2-ն ա՝ GPT-ի առաջին review-ի յոթ ուղղումով, v0.4-ը ավելացնում ա երկրորդի հինգը (`INSTALL_PLAN.md`, 0 ու 0բ բաժիններ). բնօրինակի անվան տակ ոչինչ չի ջնջվում, հետկանչը նկարի սեփական գրառումն ա, մաքրումը վերականգնվող ա. մեկ գործողություն միաժամանակ՝ միջպրոցեսային կողպեքով։

| Քայլ | Ինչ ա լինում | Ինչ երբեք չի անում |
| --- | --- | --- |
| 1. Ընդունում | outbox-ի ամեն նոր նկար դառնում ա inbox-ի մեկ բնօրինակ ու հերթի մեկ գործ՝ ID-ով, sha256-ով, ով, երբ, նպատակ, վիճակ | Կրկնությունը երկրորդ բնօրինակ ու երկրորդ գործ չի սարքում։ Ընդհատված գործարկումը ավարտում ա հաջորդը. գրանցված բնօրինակի վրա երբեք չի գրվում |
| 2. Ագենտի հերթ | Ֆիքսված դաշտեր. գործը վերցվում ա սահմանափակ ժամանակով, ու միայն էդ ժամանակ կարդացվում ա էդ մեկ բնօրինակը | Առանց lease-ի բնօրինակ չի տրվում |
| 3. Մշակում | Ուղղում, նշած տեղերի անդառնալի փակում, երկու չափ (1600 ու 747 px), նոր JPEG՝ առանց EXIF-ի | **Կոդը ոչինչ չի հայտնաբերում։** Գույն չի փոխում, բան չի գեներացնում, բնօրինակը չի վերագրում |
| 4. Հաստատում | Սևագիր Գևի առաջ՝ հարթակը նշած, ճշգրիտ asset-ներով | **Ոչինչ չի հրապարակում** |
| 5. Մաքրում ու պահեստ | Հանում ա ժամանակավորը, ընդհատվածի թողածը, ոչ մեկի չնշած տարբերակները. չափերը՝ սահմանի դիմաց | Բնօրինակը՝ երբեք։ Runtime-ի media պանակից դուրս ոչինչ չի գրում |
| Հետ վերցված | Կաբինետի outbox-ից հանած նկարը (փոխանցումից հետո թեստ նշված) դուրս ա գալիս հերթից | Գևի առաջ եղածին կամ հրապարակվածին չի դիպչում |

`media_rollback.py`. `backup` (բազայի ստուգված պատճեն), `snapshot` (ամեն աղյուսակի տողերի թիվն ու մատնահետքը), `rollback` (նախ պատմության արխիվ. միակ պատճեն բնօրինակը մնում ա. հրապարակվածը մնում ա ամբողջ. մերժում ա, քանի դեռ սևագիրը Գևի առաջ ա)։

Սահմանները. փակումը հենվում ա ագենտի հայտարարածի ու Գևի նայելու վրա. օրը մեկ սևագիր. HTTP ճանապարհ, ծառայություն, timer չկա. հրապարակումից հետո նկարը դեռ երկու տեղ կա (կաբինետի ֆայլն ու inbox-ի բնօրինակը). հոսքը աշխատում ա runtime-ի user-ով։

Ստուգում. 32 թեստ՝ Windows-ում ու սերվերում, 08.10.2026։ Փորձ սերվերում, 12:32 UTC (`deploy/chain_rehearsal.sh`, ելքը `evidence/`-ում). իրական `kryuk-armen` ու `kryuk-run` user-ները ժամանակավոր պանակների վրա, փորձնական նկարներ, կենդանի runtime-ի տվյալը թաքցված ամեն պրոցեսից։ **Դա հեռախոս չի, Արմենի հաշիվը չի, HTTPS չի ու իրական տվյալ չի։**
