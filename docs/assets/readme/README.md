# README visuals

Made by `tools/make_repo_visuals.py`; do not edit the SVG files by hand. After a fact changes, change it in the script, run it, and check the pictures on GitHub in the light and the dark theme.

| File | What |
| --- | --- |
| `cover-light.svg`, `cover-dark.svg` | the cover of the root README |
| `architecture-<en|hy>-<light|dark>.svg` | where each part lives, with what is there today |
| `phases-<en|hy>-<light|dark>.svg` | roadmap phases 0 to 8 with owner, acceptor and state |
| `status-<en|hy>-<light|dark>.svg` | what Bro can read today |

## Rules

- **Identity is KRYUK24's own.** The hook and the «КРЮК24 / ЭВАКУАТОР+» lockup, navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, white, all from `tools/brand.py`. The lockup letters are outlines traced from the brand fonts (Roboto Condensed, Golos Text), so the logo looks the same everywhere and no font has to load. All other text uses the reader's system fonts; that is also what shows Armenian.
- **Structure follows the MenQ design platform** as far as it applies to a product: a 960 by 300 cover with the text block at the bottom left and a 48 px hairline grid; cards with a 1 px border; pill badges that carry a dot and a word, so a status is never colour alone; light and dark as equals; text contrast of 4.5:1 or better; both languages with the same content. MenQ's own colours, fonts and logo are not used: the platform says that product identity is the product's own. Read from `menqstudio/MenQ-Standard`, branch `main`, commit `78f86cb`, folder `platforms/design/` (the branch name `menq-design-system-v1` given in issue #3 does not exist in that repository). The platform itself was not changed. This repository installs no package of the platform and claims no adoption level.
- **Safe for GitHub.** No script, no `foreignObject`, no external resource, no embedded or remote font, no raster image inside. The generator refuses to write a file that has one, and CI checks the committed files.
- **No progress claim without evidence.** Every status word in a picture is in `docs/CURRENT_STATE.md` or `docs/ROADMAP.md`. The date is printed in each picture.
- **Pictures supplement text.** Everything a picture says is in Markdown next to it and in its alt text.

## Not verified

On a phone the README pictures scale down with the page; at 390 px the small labels are about 8 px high. The text next to each picture carries the same content. Rendering was checked in Chromium (desktop and phone width, light and dark) and on the GitHub page of the pull request; other browsers and the GitHub mobile app were not checked.

---

# Հայերեն

Սարքում ա `tools/make_repo_visuals.py`-ն. SVG ֆայլերը ձեռքով չեն խմբագրվում։ Երբ փաստ ա փոխվում, փոխում ենք սկրիպտում, աշխատացնում ու նայում GitHub-ում՝ light ու dark թեմայով։

- **Ինքնությունը КРЮК24-ինն ա.** կեռիկը, «КРЮК24 / ЭВАКУАТОР+» lockup-ը, navy `#13233A`, orange `#EF5B00`, soft orange `#F18A4B`, սպիտակ՝ բոլորը `tools/brand.py`-ից։ Lockup-ի տառերը բրենդի տառատեսակներից հանած ուրվագծեր են, դրա համար լոգոն ամեն տեղ նույնն ա ու font բեռնել պետք չի։ Մնացած տեքստը ընթերցողի համակարգի font-ով ա. հայերենն էլ էդպես ա երևում։
- **Կառուցվածքը MenQ-ի design platform-ի կանոններով ա**, ինչքան դա վերաբերում ա պրոդուկտին. 960×300 շապիկ՝ տեքստը ներքևի ձախ անկյունում ու 48 px ցանցով. քարտեր 1 px եզրագծով. պիտակներ՝ կետով ու բառով, այսինքն կարգավիճակը երբեք միայն գույն չի. light ու dark հավասար. տեքստի կոնտրաստը 4.5:1 կամ ավելի. երկու լեզուն նույն բովանդակությամբ։ MenQ-ի սեփական գույները, font-երն ու լոգոն չեն օգտագործվում։ Կարդացված ա `menqstudio/MenQ-Standard`-ի `main` ճյուղից, commit `78f86cb`, `platforms/design/` (issue #3-ում նշված `menq-design-system-v1` ճյուղը էդ repo-ում չկա)։ Հարթակը չի փոխվել։
- **GitHub-ի համար անվտանգ.** script, `foreignObject`, դրսի ռեսուրս, ներդրված կամ դրսի font, ներսում raster նկար չկա։ Generator-ը էդպիսի ֆայլ չի գրում, CI-ն էլ ստուգում ա։
- **Առանց ապացույցի առաջընթաց չի գրվում.** նկարի ամեն կարգավիճակ կա `docs/CURRENT_STATE.md`-ում կամ `docs/ROADMAP.md`-ում։ Ամսաթիվը գրված ա ամեն նկարում։
- **Նկարը լրացնում ա տեքստը.** ինչ ասում ա նկարը, կա կողքի Markdown-ում ու alt տեքստում։

**Չստուգված.** Հեռախոսում նկարները փոքրանում են էջի հետ. 390 px լայնքում փոքր գրերը մոտ 8 px են։ Նույն բովանդակությունը կա կողքի տեքստում։ Տեսքը ստուգված ա Chromium-ում (desktop ու հեռախոսի լայնք, light ու dark) ու pull request-ի GitHub էջում. ուրիշ զննարկիչներ ու GitHub-ի հեռախոսի հավելվածը ստուգված չեն։
