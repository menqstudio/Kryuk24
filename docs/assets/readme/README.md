# README visuals

Made by `tools/make_repo_visuals.py`; do not edit the SVG files by hand.

**The root `README.md` is the source of the four diagrams.** The script holds none of their content: it reads the title from the `###` heading above a picture, the names and states from the list under it, the date from the "State on" sentence, and the label from the alt text. After a fact changes, change it in the README, run `python tools/make_repo_visuals.py`, commit both, and look at the pictures on GitHub in the light and the dark theme. CI runs `python tools/make_repo_visuals.py --check` and fails when the README and the committed pictures differ.

What a card shows: the bold name of a list item (a remark in brackets is left out); the state word its last line starts with, which must be one of the words in `STATES` in the script, because that list gives each word its tone; and, in the first diagram, the first sub-line up to its first colon, semicolon or full stop. A name too long for its card stops the script with a message; shorten it in the README. The cover is not read from the README: its words are in the script.

| File | What |
| --- | --- |
| `cover-<light|dark>.svg`, `cover-narrow-<light|dark>.svg` | the cover of the root README; the narrow one is shown on screens up to 600 px wide |
| `placement-<en|hy>-<light|dark>.svg` | where each part lives |
| `server-<en|hy>-<light|dark>.svg` | what is on the server today |
| `phases-<en|hy>-<light|dark>.svg` | roadmap phases 0 to 8 with their state |
| `sources-<en|hy>-<light|dark>.svg` | what Bro reads today |
| `<placement|server|phases|sources>-wide-<en|hy>-<light|dark>.svg` | the same four for a wide screen; the README shows these by default and the four above on screens up to 600 px wide |

## Rules

- **Identity is KRYUK24's own.** The hook and the «КРЮК24 / ЭВАКУАТОР+» lockup, navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, white, all from `tools/brand.py`. The lockup letters are outlines traced from the brand fonts (Roboto Condensed, Golos Text), so the logo looks the same everywhere and no font has to load. All other text uses the reader's system fonts; that is also what shows Armenian.
- **Structure follows the MenQ design platform** as far as it applies to a product: a 960 by 300 cover with the text block at the bottom left and a 48 px hairline grid; cards with a 1 px border; pill badges that carry a dot and a word, so a status is never colour alone; light and dark as equals; text contrast of 4.5:1 or better; both languages with the same content. MenQ's own colours, fonts and logo are not used: the platform says that product identity is the product's own. Read from `menqstudio/MenQ-Standard`, branch `main`, commit `78f86cbc346cf005211ee461b8dea22c8478b27e`, folder `platforms/design/` (the branch name `menq-design-system-v1` given in issue #3 does not exist in that repository). The platform itself was not changed. This repository installs no package of the platform and claims no adoption level.
- **Safe for GitHub.** No script, no `foreignObject`, no external resource, no embedded or remote font, no raster image inside. The generator refuses to write a file that has one, and CI checks the committed files.
- **No progress claim without evidence.** Every status word in a picture is in `docs/CURRENT_STATE.md` or `docs/ROADMAP.md`. The date is printed in each picture.
- **Readable on a phone.** A picture carries one idea in large labels: the diagrams are 480 units wide and no text in them is smaller than 17 units, which is about 12 px when the picture is 330 px wide. Owners, notes and evidence are not in the pictures; they are in the Markdown list under each one.
- **A wide screen is filled.** Each diagram also has a `-wide` file, 960 units across like the cover: the same cards in equal columns (4, 3 or 2, the most in which the longest label fits), a short last row centred. No text in them is smaller than 17 units either.
- **Pictures supplement text.** Everything a picture says is in Markdown next to it and in its alt text.

## Not verified

Rendering was checked this way: the README was passed through GitHub's own Markdown API, and the resulting HTML was shot in Chromium at 1280 px and at 390 px, in the light and in the dark colour scheme. The live GitHub page, other browsers and the GitHub mobile app were not checked. Whether GitHub's mobile app honours the `max-width` source of the cover is not known; if it does not, the wide cover is shown scaled down.

---

# Հայերեն

Սարքում ա `tools/make_repo_visuals.py`-ն. SVG ֆայլերը ձեռքով չեն խմբագրվում։

**Չորս սխեմայի աղբյուրը արմատի `README.md`-ն ա։** Սկրիպտի մեջ դրանց բովանդակությունից ոչինչ չկա. վերնագիրը կարդում ա նկարի վերևի `###` տողից, անուններն ու վիճակները՝ տակի ցանկից, ամսաթիվը՝ «Վիճակը՝ …» նախադասությունից, պիտակը՝ alt տեքստից։ Երբ փաստ ա փոխվում, փոխում ենք README-ում, աշխատացնում `python tools/make_repo_visuals.py`, commit անում երկուսն էլ ու նայում GitHub-ում՝ light ու dark թեմայով։ CI-ն աշխատացնում ա `python tools/make_repo_visuals.py --check` ու կարմրում ա, եթե README-ն ու նկարները տարբեր են։

Ինչ ա երևում քարտում. ցանկի կետի թավ անունը (փակագծի դիտողությունը չի մտնում). վիճակի բառը, որով սկսվում ա կետի վերջին տողը, ու որը պիտի լինի սկրիպտի `STATES` ցանկում, որովհետև էդ ցանկն ա տալիս բառի երանգը. առաջին սխեմայում նաև առաջին ենթատողը՝ մինչև առաջին վերջակետը, միջակետը կամ կետը։ Քարտում չտեղավորվող անունը սկրիպտը կանգնեցնում ա հաղորդագրությամբ. կարճացնում ենք README-ում։ Շապիկը README-ից չի կարդացվում. դրա բառերը սկրիպտում են։

- **Ինքնությունը КРЮК24-ինն ա.** կեռիկը, «КРЮК24 / ЭВАКУАТОР+» lockup-ը, navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, սպիտակ՝ բոլորը `tools/brand.py`-ից։ Lockup-ի տառերը բրենդի տառատեսակներից հանած ուրվագծեր են, դրա համար լոգոն ամեն տեղ նույնն ա ու font բեռնել պետք չի։ Մնացած տեքստը ընթերցողի համակարգի font-ով ա. հայերենն էլ էդպես ա երևում։
- **Կառուցվածքը MenQ-ի design platform-ի կանոններով ա**, ինչքան դա վերաբերում ա պրոդուկտին. 960×300 շապիկ՝ տեքստը ներքևի ձախ անկյունում ու 48 px ցանցով. քարտեր 1 px եզրագծով. պիտակներ՝ կետով ու բառով, այսինքն կարգավիճակը երբեք միայն գույն չի. light ու dark հավասար. տեքստի կոնտրաստը 4.5:1 կամ ավելի. երկու լեզուն նույն բովանդակությամբ։ MenQ-ի սեփական գույները, font-երն ու լոգոն չեն օգտագործվում։ Կարդացված ա `menqstudio/MenQ-Standard`-ի `main` ճյուղից, commit `78f86cbc346cf005211ee461b8dea22c8478b27e`, `platforms/design/` (issue #3-ում նշված `menq-design-system-v1` ճյուղը էդ repo-ում չկա)։ Հարթակը չի փոխվել։
- **GitHub-ի համար անվտանգ.** script, `foreignObject`, դրսի ռեսուրս, ներդրված կամ դրսի font, ներսում raster նկար չկա։ Generator-ը էդպիսի ֆայլ չի գրում, CI-ն էլ ստուգում ա։
- **Առանց ապացույցի առաջընթաց չի գրվում.** նկարի ամեն կարգավիճակ կա `docs/CURRENT_STATE.md`-ում կամ `docs/ROADMAP.md`-ում։ Ամսաթիվը գրված ա ամեն նկարում։
- **Հեռախոսում կարդացվող.** նկարը մեկ միտք ա տանում խոշոր գրերով. սխեմաները 480 միավոր լայն են, ու մեջի ոչ մի գիր 17 միավորից փոքր չի, այսինքն մոտ 12 px, երբ նկարը 330 px լայն ա։ Պատասխանատուները, նշումներն ու ապացույցը նկարում չեն, ամեն նկարի տակի Markdown ցանկում են։
- **Լայն էկրանը լցվում ա.** ամեն սխեմա ունի նաև `-wide` ֆայլ՝ 960 միավոր լայն, ոնց շապիկը. նույն քարտերը հավասար սյուներով (4, 3 կամ 2՝ ամենաշատը, որի մեջ ամենաերկար գիրը տեղավորվում ա), կարճ վերջին շարքը՝ կենտրոնում։ README-ն լռելյայն ցույց ա տալիս սրանք, իսկ մինչև 600 px էկրաններում՝ նեղերը։ Էստեղ էլ ոչ մի գիր 17 միավորից փոքր չի։
- **Նկարը լրացնում ա տեքստը.** ինչ ասում ա նկարը, կա կողքի Markdown-ում ու alt տեքստում։

**Չստուգված.** Տեսքը ստուգվել ա էսպես. README-ն անցել ա GitHub-ի սեփական Markdown API-ով, ու ստացված HTML-ը նկարվել ա Chromium-ում 1280 ու 390 px լայնքով, light ու dark։ GitHub-ի կենդանի էջը, ուրիշ զննարկիչներն ու GitHub-ի հեռախոսի հավելվածը ստուգված չեն։ Հայտնի չի՝ հեռախոսի հավելվածը հարգո՞ւմ ա շապիկի `max-width` աղբյուրը. եթե չէ, ցույց ա տրվում լայն շապիկը՝ փոքրացված։
