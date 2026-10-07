# KRYUK24 (kryuk24.ru)

Tow-truck service in Moscow and the Moscow region, public number +7 985 893-06-06. This repository holds the live site, the server-side runtime ("Bro": a daily queue of checks, an operator dashboard, machine readers), the tools that build brand and site material, and the documents that say what is true today.

People: **Armen** owns the business and decides prices, terms, geography and the upper budget limit. **Gev** has the final word on every public and money step. **Claude** builds, operates and verifies. **GPT** reviews, challenges and accepts packages.

First business goal (Gev, 04.10.2026): five profitable completed orders a day on average. Orders, revenue, cost per order and margin are **UNKNOWN** today, not zero: no real request or order is recorded anywhere.

## State in ten lines (07.10.2026, details and evidence in [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md))

1. The live site equals git tag `v33.1-live` (checked 06.10.2026: 57 of 58 file hashes equal, the 58th is `.htaccess`, which the hosting does not serve).
2. A VPS runs the runtime in **STAGING** at `runtime.kryuk24.ru`; sending is off; every request in its database is a test one.
3. The server plans ten daily tasks at 06:00 UTC (`kryuk-operations.timer`); the backup timer runs separately around 00:00–00:05 UTC.
4. API reader v0.3.2 r2 is **installed** on the staging server (steps 1–10, 07.10.2026 13:00–13:02 UTC, all verified). Step 11, one supervised write run, is **pending** for 08.10.2026 after the 06:00 UTC planning. No timer for it.
5. Beget, Yandex Metrica and Yandex Webmaster are read by API. Yandex Direct API is blocked (access request sent, status "new"). Avito API reads, but Avito is on hold by Gev.
6. The owner approves one thing today: the daily report draft, by its digest. That is not an approval of any action. No executor of actions exists.
7. The mailbox connector does not exist (no app, no credential). Browser reading by an unattended model does not exist (proxy package waits for GPT).
8. Credentials clean-up on Windows is **not closed**: Yandex and Avito secrets are still in the Windows user environment and the local `.mcp.json` hands them to four third-party MCP programs.
9. Nothing is pushed and no git remote exists. The full history is in a verified git bundle on the same physical disk; a copy off this disk does not exist yet.
10. Nearest deadlines: Avito listings expire 11.10 and 15.10 (hold, nothing paid); address confirmation for the Yandex card by 13.10; hosting balance lasts until about 15.11.2026 (calculated).

## Where things are

| Path | What it is |
| --- | --- |
| `site/` | The live site exactly as deployed. How to deploy: `site/README.md` |
| `runtime/api_reader/` | API reader v0.3.2 r2: collector, queue side, installer, tests, evidence |
| `runtime/server/` | The code exactly as installed on the VPS in `/opt/kryuk24`, fetched read-only on 07.10.2026 13:08 UTC, with `MANIFEST.md`. No database, no credentials |
| `runtime/received/` | Packages as received from GPT, with `MAPPING.md` (which version is installed, which is superseded) |
| `runtime/wip/chrome_proxy/` | WIP. Proxy in front of the Chrome tools; never run with a real model |
| `runtime/wip/adapter_preflight/` | WIP. Gate hook, Windows job runner, tool schemas |
| `runtime/wip/trial/` | WIP. Supervised trial harness v5.3 and its plan |
| `tools/` | Site checks (`tools/tests/`), brand and media generators, API setup scripts (`tools/api_setup/`) |
| `research/` | Owner's prices and answers, Yandex rules, Direct launch package |
| `brand/`, `offers/`, `reports/`, `photo/01_real_polished/` | Brand sources, texts for the owner, reports, the processed photo set that may be published |
| `docs/` | The six documents below, `LESSONS.md`, `history/`, `inventory/`, `cleanup/`, `media-index.md` |
| `_drive_staging/` | Git-ignored. Media and archives that go to Drive, not to GitHub, kept locally until Gev names the Drive. Index: `docs/media-index.md` |
| `_private/` | Not in git. Private notes (the VPS address is there). Not read by AI sessions |

Zip packages for hand-over are placed in `C:\Users\Admin\Desktop\ZIP`, not in the repository.

## How to run the tests

| Suite | Command | Last recorded result |
| --- | --- | --- |
| Site, local | `tools/.venv/Scripts/python.exe tools/tests/run_checks.py` | expected: issues 0, errors [], links_bad [] |
| Site, live (read-only against kryuk24.ru) | same command with `live` | 06.10.2026: issues 0, errors [], links_bad [] |
| API reader | in `runtime/api_reader/`: `python -m unittest test_bro_api_reader test_ops_api` | 18 + 27 OK on Windows (Python 3.12.10) and on the server (Python 3.14.4), 07.10.2026 |
| Gate and job runner (Windows only) | in `runtime/wip/adapter_preflight/`: `test_bro_gate_hook`, `test_win_job` | 50 + 31 OK, 07.10.2026; not rerun in the clean-up |
| Chrome proxy (Windows) | in `runtime/wip/chrome_proxy/`: `test_bro_chrome_proxy` | 12 OK, 07.10.2026 |
| Trial harness (Windows only) | in `runtime/wip/trial/`: `test_trial_harness` | 68 OK, 07.10.2026 |

The commands below were run from a fresh clone of this branch on 07.10.2026, on Windows (Python 3.12.10) and, for the Linux-capable part, on the server in a temporary folder (Python 3.14.4). The runtime code uses the standard library only. `tools/` needs a virtual environment (`tools/.venv`, git-ignored); its packages are listed in `tools/requirements.txt`. A CI file exists (`.github/workflows/ci.yml`) with the same commands; **it has not run on GitHub yet**, because no repository exists. `runtime/server/` is tested on Linux: `python3 -m unittest discover -p "test_*.py"` there, 102 pass.

## The other six documents

| Document | Answers |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | What the components are and where the boundaries run: installed today versus target |
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | What is true today, each item with status and evidence |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | What was decided, when and by whom; resolved and open contradictions |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | The one prioritised queue with owners, dependencies, next steps and deadlines |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Install, backup, recovery, rollback, and whether each was really executed |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Where secrets live (never a value), authority limits, what an AI session may not hold, known gaps |

Also: [`docs/LESSONS.md`](docs/LESSONS.md) (what went wrong and what to do instead; read at session start), `docs/history/` (reports delivered to GPT, manual run records).

## Scope of instructions

- These seven documents are the project's canonical instructions. When they disagree with an older note, a memory entry or a package README, the documents win; for a fact about today, `docs/CURRENT_STATE.md` is the only source.
- The earlier state documents (`00_STATE.md`, `01_TASKS.md`, `HISTORY.md`, `MISSION.md`, `RULES.md`, `BUSINESS_STATE.md`, `GPT_HANDOFF_CURRENT.md`) are merged here and kept only in the private materials and in the git bundle.
- `RULES.md` was an unapproved draft and is not a rule. The one rule in force by practice: every public step and every money step needs Gev's separate yes.
- Status words: IMPLEMENTED (written), VERIFIED (seen working, with evidence), BLOCKED (cannot proceed, with the reason), PLANNED (nothing written). For facts: verified, unverified, UNKNOWN. Nothing unverified is written as fact.
- Each document is bilingual: English first, Armenian after the rule. Text for the owner and for customers is Russian, without the letter "ё".

---

# Հայերեն

**KRYUK24 (kryuk24.ru)**. էվակուատորի ծառայություն Մոսկվայում ու մարզում, հանրային համարը՝ +7 985 893-06-06։ Էս repo-ում են կենդանի կայքը, սերվերի runtime-ը («Bro». օրվա ստուգումների հերթ, օպերատորի վահանակ, մեքենայական կարդացողներ), բրենդի ու կայքի գործիքները ու էն փաստաթղթերը, որ ասում են՝ ինչն ա այսօր ճիշտ։

Մարդիկ. **Արմենը** բիզնեսի տերն ա, որոշում ա գները, պայմանները, աշխարհագրությունը, բյուջեի վերին սահմանը։ **Գևինն** ա վերջին խոսքը ամեն հրապարակային ու փողային քայլի համար։ **Claude-ը** կառուցում, վարում ու ստուգում ա։ **GPT-ն** review ա անում, առարկում ու ընդունում փաթեթները։

Առաջին նպատակը (Գև, 04.10.2026)՝ միջինը օրը հինգ շահութաբեր ավարտված պատվեր։ Պատվերները, հասույթը, մեկ պատվերի ծախսն ու մարժան այսօր **UNKNOWN** են, ոչ թե զրո. իրական դիմում կամ պատվեր ոչ մի տեղ չի գրվում։

## Վիճակը տասը տողով (07.10.2026, մանրամասնն ու ապացույցը՝ [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md))

1. Կենդանի կայքը նույնն ա, ինչ git-ի `v33.1-live` պիտակը (ստուգված 06.10.2026. 58 ֆայլից 57-ի hash-ը համընկնում ա, 58-րդը `.htaccess`-ն ա, որ հոստինգը դրսից չի տալիս)։
2. VPS-ում runtime-ը աշխատում ա **STAGING** ռեժիմով՝ `runtime.kryuk24.ru`. ուղարկելը անջատված ա. բազայի բոլոր հայտերը թեստային են։
3. Սերվերը ամեն օր 06:00 UTC-ին պլանավորում ա տասը գործ (`kryuk-operations.timer`). պահուստի timer-ը առանձին ա, մոտ 00:00–00:05 UTC։
4. API reader v0.3.2 r2-ը **դրված ա** staging սերվերում (1–10 քայլերը, 07.10.2026 13:00–13:02 UTC, բոլորը ստուգված)։ 11-րդ քայլը՝ մեկ հսկվող գրող գործարկում, **սպասում ա** 08.10.2026-ին, 06:00 UTC-ի պլանավորումից հետո։ Timer չկա։
5. Beget-ը, Yandex Metrica-ն ու Webmaster-ը կարդացվում են API-ով։ Yandex Direct-ի API-ն փակ ա (հայտը ուղարկված ա, վիճակը «новая»)։ Avito-ի API-ն կարդում ա, բայց Avito-ն Գևի HOLD-ի տակ ա։
6. Այսօր տերը հաստատում ա մի բան՝ օրվա հաշվետվության սևագիրը, digest-ով։ Դա ոչ մի գործողության թույլտվություն չի։ Գործողությունների executor չկա։
7. Փոստի connector չկա (ոչ հավելված, ոչ credential)։ Առանց հսկողության մոդելով զննարկիչ կարդալը չկա (proxy-ի փաթեթը սպասում ա GPT-ին)։
8. Windows-ում credential-ների մաքրումը **փակված չի**. Yandex-ի ու Avito-ի գաղտնիքները դեռ Windows-ի user environment-ում են, ու տեղային `.mcp.json`-ը դրանք տալիս ա չորս կողմնակի MCP ծրագրի։
9. Ոչինչ push արված չի, git remote չկա։ Ամբողջ պատմությունը ստուգված git bundle-ում ա՝ նույն ֆիզիկական սկավառակի վրա. էս սկավառակից դուրս պատճեն դեռ չկա։
10. Մոտակա ժամկետները. Avito-ի հայտարարությունները փակվում են 11.10-ին ու 15.10-ին (HOLD, ոչինչ չի վճարվել). Yandex-ի քարտի հասցեի հաստատումը՝ մինչև 13.10. հոստինգի մնացորդը հերիքում ա մոտ մինչև 15.11.2026 (հաշվարկ)։

## Որտեղ ինչն ա

| Ճանապարհ | Ինչ ա |
| --- | --- |
| `site/` | Կենդանի կայքը, ոնց որ դրված ա։ Հրապարակելու կարգը՝ `site/README.md` |
| `runtime/api_reader/` | API reader v0.3.2 r2. collector, հերթի կողմը, installer, թեստեր, ապացույցներ |
| `runtime/server/` | Կոդը ճիշտ էնպես, ոնց դրված ա VPS-ում `/opt/kryuk24`-ում, վերցված միայն կարդալով 07.10.2026 13:08 UTC-ին, `MANIFEST.md`-ով։ Ոչ բազա կա, ոչ credential |
| `runtime/received/` | GPT-ից ստացված փաթեթները, ոնց եկել են, `MAPPING.md`-ով (որ տարբերակն ա դրված, որը՝ փոխարինված) |
| `runtime/wip/chrome_proxy/` | WIP. Chrome-ի գործիքների առաջ դրված proxy. իսկական մոդելով չի աշխատել |
| `runtime/wip/adapter_preflight/` | WIP. gate hook, Windows-ի job runner, գործիքների սխեմաներ |
| `runtime/wip/trial/` | WIP. հսկվող փորձի harness v5.3-ն ու պլանը |
| `tools/` | Կայքի ստուգումները (`tools/tests/`), բրենդի ու մեդիայի գեներատորները, API-ի setup սկրիպտները (`tools/api_setup/`) |
| `research/` | Տիրոջ գներն ու պատասխանները, Yandex-ի կանոնները, Direct-ի գործարկման փաթեթը |
| `brand/`, `offers/`, `reports/`, `photo/01_real_polished/` | Բրենդի աղբյուրները, տեքստեր տիրոջ համար, հաշվետվություններ, մշակված նկարների սեթը, որ կարելի ա հրապարակել |
| `docs/` | Ներքևի վեց փաստաթուղթը, `LESSONS.md`, `history/`, `inventory/`, `cleanup/`, `media-index.md` |
| `_drive_staging/` | Git-ում չի։ Մեդիան ու արխիվները, որ գնում են Drive, ոչ GitHub. տեղում են, մինչև Գևը ասի՝ որ Drive-ը։ Ցուցակը՝ `docs/media-index.md` |
| `_private/` | Git-ում չի։ Անձնական նշումներ (VPS-ի հասցեն էնտեղ ա)։ AI նիստերը չեն կարդում |

Փոխանցման zip-երը դրվում են `C:\Users\Admin\Desktop\ZIP`-ում, ոչ repo-ում։

## Թեստերը ոնց աշխատացնել

| Ինչ | Հրաման | Վերջին գրանցված արդյունք |
| --- | --- | --- |
| Կայք, տեղում | `tools/.venv/Scripts/python.exe tools/tests/run_checks.py` | սպասվում ա՝ issues 0, errors [], links_bad [] |
| Կայք, կենդանի (միայն կարդում ա kryuk24.ru-ն) | նույն հրամանը՝ `live`-ով | 06.10.2026՝ issues 0, errors [], links_bad [] |
| API reader | `runtime/api_reader/`-ում՝ `python -m unittest test_bro_api_reader test_ops_api` | 18 + 27 OK Windows-ում (Python 3.12.10) ու սերվերում (Python 3.14.4), 07.10.2026 |
| Gate ու job runner (միայն Windows) | `runtime/wip/adapter_preflight/`-ում՝ `test_bro_gate_hook`, `test_win_job` | 50 + 31 OK, 07.10.2026. մաքրման ժամանակ նորից չեն քշվել |
| Chrome proxy (Windows) | `runtime/wip/chrome_proxy/`-ում՝ `test_bro_chrome_proxy` | 12 OK, 07.10.2026 |
| Trial harness (միայն Windows) | `runtime/wip/trial/`-ում՝ `test_trial_harness` | 68 OK, 07.10.2026 |

Ներքևի հրամանները աշխատացվել են այս ճյուղի թարմ clone-ից 07.10.2026-ին՝ Windows-ում (Python 3.12.10) ու, Linux-ին հարմար մասը, սերվերի ժամանակավոր թղթապանակում (Python 3.14.4)։ Runtime-ի կոդը միայն ստանդարտ գրադարանով ա։ `tools/`-ին պետք ա virtual environment (`tools/.venv`, git-ում չի). փաթեթների ցուցակը՝ `tools/requirements.txt`։ CI-ի ֆայլ կա (`.github/workflows/ci.yml`) նույն հրամաններով. **GitHub-ում դեռ չի աշխատել**, որովհետև repo չկա։ `runtime/server/`-ը ստուգվում ա Linux-ում. `python3 -m unittest discover -p "test_*.py"`, 102-ն անցնում ա։

## Մնացած վեց փաստաթուղթը

| Փաստաթուղթ | Ինչին ա պատասխանում |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Ինչ բաղադրիչներ կան ու որտեղով են անցնում սահմանները. այսօր դրվածը ու թիրախը՝ առանձին |
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | Ինչն ա այսօր ճիշտ, ամեն կետը՝ վիճակով ու ապացույցով |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Ինչ ա որոշվել, երբ ու ով. լուծված ու բաց հակասությունները |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Մեկ առաջնահերթ հերթ՝ տերերով, կախվածություններով, հաջորդ քայլով ու ժամկետներով |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Դնել, պահուստ, վերականգնում, հետ գնալ, ու ամեն մեկը իրոք արվե՞լ ա |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Որտեղ են գաղտնիքները (երբեք արժեք), լիազորությունների սահմանները, ինչ չպիտի ունենա AI նիստը, հայտնի բացերը |

Նաև՝ [`docs/LESSONS.md`](docs/LESSONS.md) (ինչն ա սխալ գնացել ու ոնց անել հաջորդ անգամ. կարդացվում ա նիստի սկզբում), `docs/history/` (GPT-ին տրված զեկույցները, ձեռքով շրջայցերի գրառումները)։

## Հրահանգների շրջանակը

- Էս յոթ փաստաթուղթը նախագծի կանոնական հրահանգներն են։ Երբ հին նշումի, հիշողության գրառման կամ փաթեթի README-ի հետ չեն համընկնում, հաղթում են սրանք. այսօրվա փաստի համար միակ աղբյուրը `docs/CURRENT_STATE.md`-ն ա։
- Հին վիճակի փաստաթղթերը (`00_STATE.md`, `01_TASKS.md`, `HISTORY.md`, `MISSION.md`, `RULES.md`, `BUSINESS_STATE.md`, `GPT_HANDOFF_CURRENT.md`) միացված են էստեղ ու մնում են միայն անձնական նյութերում ու git bundle-ում։
- `RULES.md`-ն չհաստատված սևագիր էր, կանոն չի։ Փաստացի գործող կանոնը մեկն ա. ամեն հրապարակային ու ամեն փողային քայլ՝ Գևի առանձին «հա»-ով։
- Վիճակի բառերը. IMPLEMENTED (գրված ա), VERIFIED (տեսել ենք աշխատելիս, ապացույցով), BLOCKED (առաջ չի գնում, պատճառով), PLANNED (ոչինչ գրված չի)։ Փաստերի համար՝ ստուգված, չստուգված, UNKNOWN։ Չստուգածը որպես փաստ չի գրվում։
- Ամեն փաստաթուղթ երկլեզու ա. նախ անգլերեն, գծից հետո՝ հայերեն։ Տիրոջ ու հաճախորդների համար տեքստը ռուսերեն ա, առանց «ё»-ի։
