# KRYUK24: roadmap

One prioritised queue. Order: dated items first, then GPT's order of work of 07.10.2026 (credentials → API reader → real requests and orders → mailbox and approval contract → executor → reports; the proxy separately), then everything that waits for a person. An item moves only when its dependency is met. Status of each item is in [`CURRENT_STATE.md`](CURRENT_STATE.md).

Owners: **Gev**, **Armen** (owner of the business), **Claude**, **GPT**, **Yandex** (external).

## Deadlines

| Date | What | Owner |
| --- | --- | --- |
| 08.10.2026, after 06:00 UTC (10:00 Yerevan) | Step 11 of the API reader install | Claude |
| before 10.10.2026 | One answer from Armen about Avito prolongation (Claude's proposal for the timing) | Gev asks Armen |
| 11.10.2026 | Avito: 24 listings expire, balance 0 ₽ | Gev (decision) |
| 13.10.2026 | Address confirmation video for the Yandex Business card | Armen |
| 13.10.2026 | Webmaster: check how many pages are in search | Claude |
| 14.10 and 15.10.2026 | Avito: 1 and then 20 more listings expire | Gev (decision) |
| 26.10.2026 | Avito: 1 listing expires | Gev (decision) |
| about 15.11.2026 (calculated) | Top up the hosting account | Gev / Armen |
| 30.12.2026 | Site SSL certificate (auto-renewal unverified) | hosting; check by Claude |
| 04.01.2027 | Certificate of `runtime.kryuk24.ru` | `certbot.timer`; check by Claude |
| 01.10.2027 | Domain kryuk24.ru (unverified after 01.10.2026) | Gev / Armen |

## The queue

| # | Item | Owner | Depends on | Next step |
| --- | --- | --- | --- | --- |
| 1 | **API reader, step 11:** one supervised write run | Claude | The 06:00 UTC planning of 08.10.2026 wrote the new day (ten tasks, three `API_READ`); `runtime.sqlite*` still shows group `kryuk-db` | Check the plan; install `kryuk-api-read.service`; one `systemctl start`; check three `DONE` with `MACHINE_OBSERVED`, seven others untouched, the dashboard opens. No timer. Then the factual report to GPT |
| 2 | **Avito before 11.10** (on hold) | Gev | Armen's answer: is prolongation in his cabinet free or paid, and who holds the autoload file | Claude's proposal: if free, permission for prolongation only, texts unchanged; if paid, decide after the figure. Until Gev's word nothing is changed or paid |
| 3 | **Address confirmation by 13.10** | Armen | Signage sizes question (his screenshot and voice messages of 06.10.2026, content unknown) → print → video | Gev finds out what is wrong with the sizes; Claude corrects the files; Armen films and sends the video |
| 4 | **Credentials clean-up on Windows** | Gev (decision on the store), Claude (preparation without values) | GPT fixed the placement; open is the store for the action and Avito secrets: the VPS or a separate Windows user | Claude prepares the move-and-verify plan, the list of everything that reads the user variables (`tools/api_setup/*.ps1`, `provision_from_windows.ps1`, `bro_api_reader.py --windows-user-store`, `.mcp.json`) and a canary check for each AI start. Gev starts the script; Claude and editor sessions are restarted |
| 5 | **Off-disk copy: done 07.10.2026** | Gev, Claude | none | External disk `E:\Kryuk24\backup_2026-10-07\`, every file compared by sha256. Left: decide how often it is refreshed |
| 6 | **Old database backups on the server into `0700 kryuk-run`** | Claude | A word for the server change (who gives it is not stated in the sources) | Move the `.sqlite` and `.json` backups into a subfolder; check the collector's group can no longer read them; nothing is deleted |
| 7 | **GitHub and Drive** | Gev (names the account and the Drive), Claude (import) | Item 5; Gev's answers on photo originals and personal data | Clean initial import into a separate private KRYUK24 repository; the old history stays in the bundle; each file moved to Drive is checked by sha256 against `docs/media-index.md` |
| 8 | **Clean-up: what is left after the push** | Claude | none | Published 07.10.2026 (`menqstudio/Kryuk24`, CI green on `main`). The harness self-test is back in CI (pull request #2: a logging race in the trial fixture server). Left: look at the recorded T1 and T2 attempts for the same race; read the 21 generator scripts one by one; verify the Drive copy file by file (needs Drive API access); decide on GitHub Pro for the protection of `main` (Gev) |
| 9 | **Real requests and orders** | Claude (reads the code, proposes), GPT (writes the owner's cabinet), Armen (uses it) | Item 1 closed | First read what the runtime already has (`orders`, `contact_interactions`, capture, the test flag); then a proposal; nothing built from zero. The owner's cabinet: read-only role, Russian page, one-tap question of the day without money, upload of real photos; STAGING only |
| 10 | **Approval contract and stale drafts** | Claude (draft for GPT), GPT (decision) | — | A design based on `runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`. The current draft is not changed or approved without Gev |
| 11 | **Mailbox for Bro** | Gev (creates the app), Claude (connector) | The Yandex app "KRYUK24 Bro Mail" with `mail:imap_full` and `mail:smtp`; IMAP switched on in the mailbox | After the app exists: the token by script, then a read check of the Business folder. Sending stays closed |
| 12 | **Executor of approved actions** | GPT (acceptance), Claude (build) | Items 4 and 10 | Nothing is written. Idempotency and reconciliation of an uncertain result are part of the first version |
| 13 | **Monitor without AI** (health, backup, hosting balance, certificate) | Claude | — for the preparation; Gev's separate yes for the schedule and the channel | Prepare the deterministic checks |
| 14 | **Reports**: daily in the runtime, weekly, monthly, budget | Claude | Item 9 (without recorded orders the numbers are UNKNOWN) | — |
| 15 | **Chrome proxy and trials** | GPT (decisions), Claude | GPT's answers on package v5.3: accept the proxy as the restriction layer; the form of trials with the proxy; stay on Windows until the first run with the proxy | Then: a harness adapted to the proxy, a separate `--user-data-dir` for the trial Chrome. T2 is rerun only on GPT's decision and Gev's new yes; T3 is not started |
| 16 | **Debian worker** | Gev (says when), Claude | Access to the machine; item 15 | Not started. A Linux variant of the harness; the Windows trials are run again there |
| 17 | **Yandex Direct API** | Yandex, then Claude | The answer to the full-access request (sent 07.10.2026, status "new"); it comes to the owner's mailbox | After the answer: `tools/api_setup/yandex_check.ps1 -Kind actions`. If Yandex asks for a real screenshot instead of the mock-up, make it once the Direct section of the dashboard exists |
| 18 | **Direct launch** (only after Gev's yes) | Gev (decisions), Claude (cabinet) | Item 9 (a working record of requests), VAT in the budget field, stop thresholds for the new budget, call tracking, competitor brand queries, account funded | Into the draft: maximum bid from the forecast, start date, goal values; narrow one broad phrase; quick links and clarifications. Checklist: `research/Direct_launch_package_2026-10-04.md` |
| 19 | **Answers from Armen** | Armen (Gev passes the questions) | — | Is "просто дернуть от 4 000" still valid (open contradiction 6); which districts he wants instead of the present city pages; is "50 machines" his own fleet or a partner network; where orders come from now and what one order costs (fuel, driver); the 20 questions of 02.10.2026; real photos of his equipment and jobs |
| 20 | **Reply to Sergey's review: closed by Gev's decision (07.10.2026)** | Claude | none | The read-back of the posted text stays UNVERIFIED; read it the next time a browser session in the working profile is open. It blocks nothing |
| 21 | **Two unopened letters** | Claude, on Gev's word | Mail access in the session | "We partly accepted the edits" (what was refused is UNKNOWN); the request to link the counter in Webmaster (confirming is a button and needs a separate yes) |
| 22 | **New photos and the card** | Gev (decision), Claude | — | Three processed frames of 07.10.2026: put them on the card and the site or not; the video of 07.10.2026 has not been watched. When real equipment photos exist, replace the eight generated ones in "Equipment" (deletion by Gev's hand) |
| 23 | **Site, next deploy** | Claude, Gev (yes) | — | `logo-dark.png` and `theme-color` in blue; correct the stale tag line in `site/README.md` |
| 24 | **WhatsApp Business on the phone** | Armen | — | Name "Kruk24" → "КРЮК24"; the map pin; greeting and "driving" messages. Texts: `offers/whatsapp_business_setup_2026-10-07.md`. Statuses from `offers/whatsapp_kit/`, one a day, chosen by a person |
| 25 | **Small items for Gev** | Gev | — | Approve or comment the new dashboard design (phone width and dark mode unverified); "previously open tabs" at start in the working profile; allow the mail site to the extension; switch the extension back on in the main profile after the trials; decide a separate Chrome profile for Bro; decide whether unattended runs may spend the subscription allowance; decide on the merged branches `navy-v32` and `v33`; a separate WhatsApp number for Claude and transcription of voice messages |
| 26 | **Small items for Claude** | Claude | — | Recheck the call-tracking numbers in Direct; check the status of the Business ad subscription and of the old Business landing; fix the encoding of the Direct error text in `yandex_check.ps1`; the daily check stays manual (first record in `docs/history/`) until one run without Gev's open session has passed with the right profile |

## Not in the queue

| Item | Why |
| --- | --- |
| A timer or autostart for Bro or for the API reader | Not created without Gev's separate yes |
| Avito changes, payments, prolongation | On hold by Gev |
| The Google form for the owner | Replaced by the owner's cabinet in the runtime; stays an unpublished draft |
| Call-log export from the owner's phone | Only with Armen's consent: the log holds his personal calls |
| New district pages | Wait for Armen's list (item 19) |

---

# Հայերեն

Մեկ առաջնահերթ հերթ։ Կարգը. նախ օր ունեցողները, հետո GPT-ի 07.10.2026-ի աշխատանքի հերթը (credential-ներ → API reader → իրական դիմումներ ու պատվերներ → փոստ ու approval contract → executor → հաշվետվություններ. proxy-ն առանձին), հետո էն ամենը, ինչ մարդու ա սպասում։ Կետը շարժվում ա միայն, երբ իրա կախվածությունը փակված ա։ Ամեն կետի վիճակը՝ [`CURRENT_STATE.md`](CURRENT_STATE.md)-ում։

Տերեր. **Գև**, **Արմեն** (բիզնեսի տերը), **Claude**, **GPT**, **Yandex** (դրսի)։

## Ժամկետներ

| Օր | Ինչ | Ով |
| --- | --- | --- |
| 08.10.2026, 06:00 UTC-ից հետո (10:00 Երևան) | API reader-ի install-ի 11-րդ քայլը | Claude |
| մինչև 10.10.2026 | Արմենի մեկ պատասխանը Avito-ի երկարաձգման մասին (ժամկետը Claude-ի առաջարկն ա) | Գևը հարցնում ա Արմենին |
| 11.10.2026 | Avito. 24 հայտարարություն փակվում ա, մնացորդ 0 ₽ | Գև (որոշում) |
| 13.10.2026 | Հասցեի հաստատման վիդեոն Yandex Բիզնեսի քարտի համար | Արմեն |
| 13.10.2026 | Webmaster. նայել՝ քանի էջ կա որոնման մեջ | Claude |
| 14.10 ու 15.10.2026 | Avito. փակվում ա 1-ը, հետո ևս 20-ը | Գև (որոշում) |
| 26.10.2026 | Avito. փակվում ա 1-ը | Գև (որոշում) |
| մոտ 15.11.2026 (հաշվարկ) | Լիցքավորել հոստինգի հաշիվը | Գև / Արմեն |
| 30.12.2026 | Կայքի SSL վկայականը (ինքնաթարմացումը չստուգված) | հոստինգ. ստուգում ա Claude-ը |
| 04.01.2027 | `runtime.kryuk24.ru`-ի վկայականը | `certbot.timer`. ստուգում ա Claude-ը |
| 01.10.2027 | Դոմեն kryuk24.ru (չստուգված 01.10.2026-ից հետո) | Գև / Արմեն |

## Հերթը

| # | Կետ | Ով | Կախված ա | Հաջորդ քայլ |
| --- | --- | --- | --- | --- |
| 1 | **API reader, քայլ 11.** մեկ հսկվող գրող գործարկում | Claude | 08.10.2026-ի 06:00 UTC-ի պլանավորումը գրել ա նոր օրը (տասը գործ, երեքը `API_READ`). `runtime.sqlite*`-ը դեռ `kryuk-db` խմբով ա | Ստուգել պլանը. դնել `kryuk-api-read.service`-ը. մեկ `systemctl start`. ստուգել երեք `DONE`՝ `MACHINE_OBSERVED`-ով, մնացած յոթը անփոփոխ, վահանակը բացվում ա։ Timer չկա։ Հետո՝ փաստացի զեկույց GPT-ին |
| 2 | **Avito մինչև 11.10** (HOLD) | Գև | Արմենի պատասխանը. երկարաձգումը իրա կաբինետում անվճա՞ր ա, թե վճարովի, ու ում մոտ ա autoload-ի ֆայլը | Claude-ի առաջարկը. եթե անվճար ա՝ թույլտվություն միայն երկարաձգման համար, տեքստերը չեն փոխվում. եթե վճարովի ա՝ որոշել թիվը իմանալուց հետո։ Մինչև Գևի խոսքը ոչինչ չի փոխվում ու չի վճարվում |
| 3 | **Հասցեի հաստատում մինչև 13.10** | Արմեն | Ցուցանակների չափերի հարցը (06.10.2026-ի սքրինշոթն ու ձայնայինները, բովանդակությունը հայտնի չի) → տպել → վիդեո | Գևը պարզում ա՝ չափերի հետ ինչն ա սխալ. Claude-ը ուղղում ա ֆայլերը. Արմենը նկարում ու ուղարկում ա վիդեոն |
| 4 | **Credential-ների մաքրում Windows-ում** | Գև (պահոցի որոշումը), Claude (պատրաստում առանց արժեքների) | GPT-ն տեղերը ֆիքսել ա. բաց ա գործող ու Avito-ի գաղտնիքների պահոցը՝ VPS, թե առանձին Windows օգտատեր | Claude-ը պատրաստում ա տեղափոխման ու ստուգման պլանը, user փոփոխականները կարդացողների ցուցակը (`tools/api_setup/*.ps1`, `provision_from_windows.ps1`, `bro_api_reader.py --windows-user-store`, `.mcp.json`) ու canary ստուգում ամեն AI մեկնարկի համար։ Սկրիպտը գործարկում ա Գևը. Claude-ի ու editor-ի նիստերը վերամեկնարկվում են |
| 5 | **Պատճեն սկավառակից դուրս. արված ա 07.10.2026** | Գև, Claude | չկա | Արտաքին սկավառակ `E:\Kryuk24\backup_2026-10-07\`, ամեն ֆայլ sha256-ով համեմատված։ Մնում ա որոշել՝ ինչ հաճախությամբ թարմացվի |
| 6 | **Սերվերի հին բազայի պահուստները տանել `0700 kryuk-run`** | Claude | Սերվերի փոփոխության խոսք (ով ա տալիս՝ աղբյուրներում գրված չի) | `.sqlite` ու `.json` պահուստները տանել ենթաթղթապանակ. ստուգել, որ collector-ի խումբը էլ չի կարդում. ոչինչ չի ջնջվում |
| 7 | **GitHub ու Drive** | Գև (ասում ա հաշիվն ու Drive-ը), Claude (import) | 5-րդ կետը. Գևի պատասխանները բնօրինակ նկարների ու անձնական տվյալի մասին | Մաքուր սկզբնական import առանձին private KRYUK24 repo. հին պատմությունը մնում ա bundle-ում. Drive տարված ամեն ֆայլ ստուգվում ա sha256-ով `docs/media-index.md`-ի հետ |
| 8 | **Մաքրում. ինչ ա մնում push-ից հետո** | Claude | չկա | Հրապարակված ա 07.10.2026 (`menqstudio/Kryuk24`, `main`-ի CI-ն կանաչ)։ Harness-ի self-test-ը նորից CI-ում ա (pull request #2. մատյանի մրցավազք trial-ի թեստային սերվերում)։ Մնում ա. նայել գրանցված T1 ու T2 փորձերը նույն մրցավազքի համար. 21 գեներատոր սկրիպտը մեկ-մեկ կարդալ. Drive-ի պատճենը ստուգել ֆայլ առ ֆայլ (Drive API ա պետք). որոշել GitHub Pro-ն `main`-ի պաշտպանության համար (Գև) |
| 9 | **Իրական դիմումներ ու պատվերներ** | Claude (կարդում ա կոդը, առաջարկում), GPT (գրում ա տիրոջ կաբինետը), Արմեն (օգտագործում ա) | 1-ին կետը փակված | Նախ կարդալ՝ runtime-ում ինչ կա (`orders`, `contact_interactions`, capture, թեստային դրոշ). հետո առաջարկ. զրոյից ոչինչ չի կառուցվում։ Տիրոջ կաբինետը. միայն-կարդալու դեր, ռուսերեն էջ, օրվա հարց մեկ սեղմումով՝ առանց փողի, իսկական նկարների վերբեռնում. միայն STAGING |
| 10 | **Approval contract ու հնացած սևագրեր** | Claude (նախագիծ GPT-ի համար), GPT (որոշում) | — | Նախագիծ `runtime/wip/adapter_preflight/REPORT_DRAFT_staleness.md`-ի հիմքով։ Գործող սևագիրը առանց Գևի չի փոխվում ու չի հաստատվում |
| 11 | **Փոստը Bro-ի համար** | Գև (ստեղծում ա հավելվածը), Claude (connector) | Yandex-ի հավելված «KRYUK24 Bro Mail»՝ `mail:imap_full` ու `mail:smtp` իրավունքներով. փոստարկղում IMAP-ը միացված | Հավելվածից հետո. token սկրիպտով, հետո Բիզնեսի թղթապանակի կարդալու ստուգում։ Ուղարկելը մնում ա փակ |
| 12 | **Հաստատված գործողությունների executor** | GPT (ընդունում), Claude (սարքում) | 4-րդ ու 10-րդ կետերը | Ոչինչ գրված չի։ Idempotency-ն ու անորոշ արդյունքի reconciliation-ը առաջին տարբերակի մաս են |
| 13 | **Մոնիտոր առանց AI-ի** (health, backup, հոստինգի մնացորդ, վկայական) | Claude | պատրաստելու համար՝ ոչինչ. ժամանակացույցի ու ալիքի համար՝ Գևի առանձին «հա» | Պատրաստել deterministic ստուգումները |
| 14 | **Հաշվետվություններ.** օրական runtime-ում, շաբաթական, ամսական, բյուջե | Claude | 9-րդ կետը (առանց գրանցված պատվերների թվերը UNKNOWN են) | — |
| 15 | **Chrome proxy ու փորձեր** | GPT (որոշումներ), Claude | GPT-ի պատասխանները v5.3 փաթեթի վրա. ընդունե՞լ proxy-ն որպես սահմանափակող շերտ. proxy-ով փորձերի ձևը. մնա՞լ Windows-ում մինչև proxy-ով առաջին run-ը | Հետո. proxy-ին հարմարեցված harness, առանձին `--user-data-dir` փորձի Chrome-ի համար։ T2-ը կրկնվում ա միայն GPT-ի որոշմամբ ու Գևի նոր «հա»-ով. T3-ը չի սկսվում |
| 16 | **Debian worker** | Գև (կասի՝ երբ), Claude | Մուտք մեքենա. 15-րդ կետը | Չի սկսվել։ Harness-ի Linux տարբերակ. Windows-ի փորձերը էնտեղ նորից են քշվում |
| 17 | **Yandex Direct-ի API** | Yandex, հետո Claude | Լրիվ մուտքի հայտի պատասխանը (ուղարկված 07.10.2026, վիճակը «новая»). կգա տիրոջ փոստարկղ | Պատասխանից հետո՝ `tools/api_setup/yandex_check.ps1 -Kind actions`։ Եթե Yandex-ը մակետի փոխարեն իսկական սքրինշոթ ուզի՝ անել, երբ վահանակում Direct-ի բաժինը լինի |
| 18 | **Direct-ի գործարկում** (միայն Գևի «հա»-ից հետո) | Գև (որոշումներ), Claude (կաբինետ) | 9-րդ կետը (դիմումների աշխատող գրանցում), НДС-ը բյուջեի դաշտում, կանգառի շեմերը նոր բյուջեի համար, коллтрекинг, մրցակիցների բրենդներով հարցումներ, լիցքավորված հաշիվ | Սևագրում. առավելագույն ստավկան կանխատեսումից, սկզբի օրը, նպատակների արժեքները. նեղացնել մեկ լայն ֆրազը. быстрые ссылки ու уточнения։ Չեկ-լիստը՝ `research/Direct_launch_package_2026-10-04.md` |
| 19 | **Արմենի պատասխանները** | Արմեն (հարցերը փոխանցում ա Գևը) | — | «Просто дернуть от 4 000»-ը դեռ գործո՞ւմ ա (բաց հակասություն 6). որ շրջաններն ա ուզում ներկա քաղաքների էջերի փոխարեն. «50 մեքենա»-ն իրա պա՞րկն ա, թե գործընկերների ցանց. որտեղից են գալիս պատվերները ու ինչ արժի մեկ պատվերը (վառելիք, վարորդ). 02.10.2026-ի 20 հարցը. իրա տեխնիկայի ու գործերի իսկական նկարներ |
| 20 | **Սերգեյի կարծիքի պատասխանը. փակված ա Գևի որոշմամբ (07.10.2026)** | Claude | չկա | Դրված տեքստի հետ կարդալը մնում ա ՉՍՏՈՒԳՎԱԾ. կարդալ, երբ աշխատանքային պրոֆիլում զննարկչի նիստ բաց լինի։ Ոչինչ չի կանգնեցնում |
| 21 | **Երկու չբացված նամակ** | Claude, Գևի խոսքով | Փոստի մուտք նիստում | «Մասամբ ընդունեցինք ուղղումները» (ինչն ա մերժվել՝ UNKNOWN). հաշվիչը Webmaster-ում կապելու հարցումը (հաստատելը կոճակ ա, առանձին «հա» ա պետք) |
| 22 | **Նոր նկարներն ու քարտը** | Գև (որոշում), Claude | — | 07.10.2026-ի երեք մշակված կադրը. դնե՞լ քարտում ու կայքում. 07.10.2026-ի վիդեոն չի դիտվել։ Երբ տեխնիկայի իսկական նկարներ լինեն՝ փոխել «Оборудование»-ի ութ գեներացվածը (ջնջում ա Գևը իրա ձեռքով) |
| 23 | **Կայք, հաջորդ հրապարակում** | Claude, Գև («հա») | — | `logo-dark.png`-ն ու `theme-color`-ը կապույտ. ուղղել `site/README.md`-ի հնացած պիտակի տողը |
| 24 | **WhatsApp Business հեռախոսում** | Արմեն | — | Անունը «Kruk24» → «КРЮК24». քարտեզի նշանը. ողջույնի ու «ղեկին եմ» հաղորդագրությունները։ Տեքստերը՝ `offers/whatsapp_business_setup_2026-10-07.md`։ Ստատուսները `offers/whatsapp_kit/`-ից, օրը մեկ, ընտրում ա մարդը |
| 25 | **Մանր կետեր Գևի համար** | Գև | — | Հաստատել կամ ասել՝ ինչ ուղղել վահանակի նոր դիզայնում (հեռախոսի լայնությունն ու մուգ ռեժիմը չստուգված են). աշխատանքային պրոֆիլում մեկնարկին «նախկինում բաց թաբերը». extension-ին թողնել փոստի կայքը. փորձերից հետո հիմնական պրոֆիլում extension-ը նորից միացնել. որոշել Bro-ի առանձին Chrome պրոֆիլը. որոշել՝ կարա՞ն առանց հսկողության run-երը ծախսեն բաժանորդագրության սահմանաչափը. որոշել merge արված `navy-v32` ու `v33` ճյուղերի հարցը. առանձին WhatsApp համար Claude-ի համար ու ձայնայինների տառադարձում |
| 26 | **Մանր կետեր Claude-ի համար** | Claude | — | Direct-ում վերաստուգել коллтрекинг-ի համարները. ստուգել Բիզնեսի գովազդային բաժանորդագրության ու Բիզնեսի հին լենդինգի վիճակը. ուղղել Direct-ի սխալի տեքստի կոդավորումը `yandex_check.ps1`-ում. ամենօրյա ստուգումը մնում ա ձեռքով (առաջին գրառումը `docs/history/`-ում), մինչև մեկ run առանց Գևի բաց նիստի անցնի ճիշտ պրոֆիլով |

## Հերթում չկա

| Կետ | Ինչու |
| --- | --- |
| Timer կամ autostart Bro-ի կամ API reader-ի համար | Առանց Գևի առանձին «հա»-ի չի ստեղծվում |
| Avito-ում փոփոխություն, վճարում, երկարաձգում | Գևի HOLD-ի տակ ա |
| Google ձևը տիրոջ համար | Փոխարինված ա runtime-ում տիրոջ կաբինետով. մնում ա չհրապարակված սևագիր |
| Զանգերի մատյանի արտահանում տիրոջ հեռախոսից | Միայն Արմենի համաձայնությամբ. մատյանում իրա անձնական զանգերն էլ կան |
| Նոր շրջանների էջեր | Սպասում են Արմենի ցուցակին (կետ 19) |
