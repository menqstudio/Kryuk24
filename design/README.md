# КРЮК24 · Design system

**Status:** v1, 08.10.2026. Source of truth for how KRYUK24 looks on every screen: the site, the owner's cabinet, the dispatcher's views and Bro's screens.
**Owner:** KRYUK24 (Armen). Kept by Gev.

## English

### What this is, and what it is not

KRYUK24 is its own business with its own brand. This folder is its design system: tokens, rules and components. It uses a **pinned copy** of the MenQ component library (`vendor/menq-components/`) only as building blocks; nothing of MenQ's identity appears. No MenQ colour, logo or name is shown, and `validate_design.py` fails if one leaks in. Nothing in this folder changes the MenQ repositories, and nothing here is written there.

### Files and load order

| Order | File | What |
| --- | --- | --- |
| 1 | `tokens/kryuk.tokens.css` | All values: primitives, scales, light, dark, contrast scope. Generated from `tokens/kryuk-tokens.source.json` |
| 2 | `vendor/menq-components/bundle.css`, `bro.css` | The pinned library (never edited; sha256 in `UPSTREAM.json`) |
| 3 | `components/kryuk.css` | The library in KRYUK24 colours, plus KRYUK24's own components |
| 4 | `../site/assets/fonts.css`, `fonts/armenian.css` | Golos Text, Roboto Condensed (site files), Noto Sans Armenian for owner screens |
| JS | React 18 → `vendor/menq-components/bundle.js` → `bro.bundle.js` → `components/lockup.generated.js` → `components/kryuk.bundle.js` | `window.Kryuk` (own components), the library under its own namespace |

`preview/index.html` shows everything in both themes. Commands: `python design/scripts/build_tokens.py` after any change of the token source, `python design/scripts/build_lockup.py` if the logo file is ever regenerated; `python design/scripts/validate_design.py` before every commit (also in CI).

### Logo

- The lockup is **hook + «КРЮК24» / «ЭВАКУАТОР+»**, approved by Gev on 04.10.2026. **It does not change.** In code use `KryukMark`: it places the official file `brand/02_lockups/lockup_horizontal_transparent_light.svg` as it is (copied by `design/scripts/build_lockup.py`, checked byte-for-byte in CI; only the colours switch for dark grounds). Elsewhere use the files in `brand/02_lockups/`.
- Hook: orange `#EF5B00`, vector of `brand/00_hook_master/hook_path.txt`. «КРЮК24»: Roboto Condensed Bold, navy on light, white on dark. «ЭВАКУАТОР»: Golos Text, letter-spaced to the width of «КРЮК24», orange on light, soft orange `#F18A4B` on dark. «+»: bold, same colour as «КРЮК24».
- Proportions of the site header: hook 44, name 28, sub 12, gap 7. Clear space at least the height of the hook's ring. Never stretch, tilt, outline or fill the hook with a gradient.
- **Ink is navy `#13233A`** (Gev, 06.10.2026; `tools/brand.py`, site v32). The `#111111` in `brand/README.md` is the earlier value and is superseded.

### Colour

| Role | Light | Dark | Rule |
| --- | --- | --- | --- |
| Call to action | orange `#EF5B00` | same | One per view. Text on it is **navy** (4.7:1), never white |
| Selected, active, secondary action | navy `#13233A` | white `#F4F6F8` | Tabs, chosen tiles, outline buttons |
| Accent | soft orange `#F18A4B` | same | Highlights only, never text on light |
| Orange as text | `#A33D00` | `#FF8A4C` | Links and emphasis |
| Page / card / well | `#F4F6F8` / `#FFFFFF` / `#EEF1F4` | `#0B1524` / `#13233A` / `#1C3150` | Light theme starts from soft grey, not pure white |
| Text / secondary / muted | `#13233A` / `#3E4A5A` / `#5A6676` | `#F4F6F8` / `#C5CDD7` / `#9AA6B6` | |
| Success, warning, danger | text `#166534`, `#92400E`, `#B91C1C` | `#4ADE80`, `#FBBF24`, `#F87171` | A state always carries a word or icon too |

Components use only the semantic `--color-*` tokens, never a primitive. `.section-contrast` gives a dark navy block inside either theme.

### Type

- Golos Text: body, interface, forms. Roboto Condensed Bold: headings, buttons, prices.
- Owner and Bro screens are in Armenian: Noto Sans Armenian fills the glyphs Golos and Roboto lack.
- Prices: `от 4 000 ₽`, Russian grouping, the ruble sign after the number with a non-breaking space (`Price`, `TariffList`).

### Shape, space, motion

- Corners: buttons and fields 8 px, cards 12 px, large blocks 16 px. Not pills.
- Spacing: `--space-*` steps only. Touch targets at least 48 px; the main call button on a phone is 72 px.
- Motion: 160 ms state changes, 240 ms panels; no decoration; reduced motion switches every animation off. No glow.

### Icons and photos

- Line icons, 24 grid, stroke 2, round caps (Lucide geometry), one size scale (`--icon-size-sm/md/lg`), colour `currentColor`. No emoji in interfaces.
- Photos follow `photo/DESIGN_SYSTEM.md` and `photo/CANON.md`: real jobs only, plates and faces covered, black ГАЗон NEXT with the livery.

### Components

**From the library, in KRYUK24 colours:** Button, Card, Panel, Badge, StatusDot, Avatar, FormRow, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Tabs, Accordion (FAQ), Nav, Tooltip, Modal, ConfirmDialog, Drawer, Toast, Table, EmptyState, Skeleton, KpiStat, Icon, Reveal.

**KRYUK24's own (`window.Kryuk`):**

| Component | Use |
| --- | --- |
| `KryukMark` | The official lockup file placed as is; `size` sm / md / lg (hook 33 / 44 / 66 px), `markOnly` for the hook alone |
| `ContactButtons` | Call (with the number), WhatsApp, Telegram: real `tel:` and chat links |
| `CallBar` | The same three actions fixed to the bottom of a phone screen |
| `Price`, `TariffList` | «от 4 000 ₽» and tariff rows with the per-km price |
| `ChoiceTiles` | One choice from a few (transport type), native radio buttons |
| `OrderStatus` | The six operational statuses of `runtime/order_flow`, Russian or Armenian labels |
| `OrderCard` | One order for the dispatcher: id, vehicle, route, confirmed price, status, test mark |

Never use the library's `BrandMark` (it is MenQ's logo) or its `LocaleSwitch` defaults.

### Bro, the governed orchestrator

Bro works inside KRYUK24 under control: it reads, plans and drafts; **every outside action goes through Gev's approval**.

- Bro's screens use the Bro components of the library (`ChatMessage`, `Timeline`, `AgentCard`, `ApprovalCard`, `CommandComposer`) in KRYUK24 colours. Bro's avatar is a plain initial on orange; no other product's face is used.
- One proposal = one `ApprovalCard`: the exact action, account, text or amount, and its risk. A changed proposal needs a new approval (`runtime/action_approval`). The card is never hidden or animated away.
- Everything Gev reads is Armenian; text going to Armen or to customers is Russian.
- Gev's screens show the fact and one button; explanations stay in the data (`docs/LESSONS.md`, "What Gev reads").

### Accessibility

- Text 4.5:1, borders of controls and focus 3:1, in both themes: 22 pairs × 2 themes checked by `validate_design.py`. The logo lettering is exempt (logotype), as WCAG allows.
- Visible focus: 3 px orange ring. Every control works from the keyboard. Every icon-only control has a label.

### What is not applied yet

The design system does not change anything live by itself.

- **Site** (`site/`): already close to it (v32 navy). Remaining gaps: `assets/logo-dark.png` and the `theme-color` of the SEO pages are still black, and the header mark is a PNG inside an SVG. They go with the next site release, on Gev's yes.
- **Dashboard** (`ops_views.py` on the server): it is Gev's own design and protected. It still uses azure and cyan, not KRYUK24 colours. Moving it to these tokens needs Gev's yes.

### Updating the library copy

Copy the six files from a newer commit of the library, refresh `vendor/menq-components/UPSTREAM.json`, run both scripts and look at `preview/index.html` in both themes.

## Հայերեն

### Ինչ է սա, և ինչ չէ

КРЮК24-ը առանձին բիզնես է՝ իր բրենդով։ Այս թղթապանակը նրա դիզայն սիստեմն է՝ token-ներ, կանոններ և կոմպոնենտներ։ MenQ-ի կոմպոնենտների գրադարանից վերցված է **ամրագրված պատճեն** (`vendor/menq-components/`), միայն որպես շինանյութ։ MenQ-ի գույնը, լոգոն կամ անունը ոչ մի տեղ չեն երևում, և եթե երևան՝ `validate_design.py`-ը RED կտա։ Այս թղթապանակը MenQ-ի repo-ներում ոչինչ չի փոխում ու այնտեղ ոչինչ չի գրում։

### Ֆայլեր և միացման հերթականություն

1. `tokens/kryuk.tokens.css`՝ բոլոր արժեքները (light, dark, contrast)։ Գեներացվում է `tokens/kryuk-tokens.source.json`-ից։
2. `vendor/menq-components/bundle.css`, `bro.css`՝ ամրագրված գրադարանը։ Ձեռքով չի փոխվում, sha256-ը `UPSTREAM.json`-ում է։
3. `components/kryuk.css`՝ գրադարանը КРЮК24-ի գույներով և КРЮК24-ի սեփական կոմպոնենտները։
4. Տառատեսակներ՝ կայքի Golos Text և Roboto Condensed, Noto Sans Armenian՝ Գևի էկրանների համար։

`preview/index.html`-ը ցույց է տալիս ամեն ինչ երկու թեմայում։ Token-ի կամ կեռիկի փոփոխությունից հետո՝ `python design/scripts/build_tokens.py`, ամեն commit-ից առաջ՝ `python design/scripts/validate_design.py` (CI-ում էլ է)։

### Լոգո

- Lockup՝ **կեռիկ + «КРЮК24» / «ЭВАКУАТОР+»** (Գևի հաստատում, 04.10.2026)։ **Լոգոն չի փոխվում։** Կոդում՝ `KryukMark`, որը դնում է պաշտոնական `brand/02_lockups/` ֆայլը հենց այնպես, ինչպես կա (CI-ն ստուգում է). միայն մուգ ֆոնին գույներն են փոխվում՝ ըստ բրենդի կանոնի։ Մնացած տեղերում՝ `brand/02_lockups/`-ի ֆայլերը։
- Կեռիկը նարնջագույն է՝ `#EF5B00`։ «КРЮК24»-ը բաց ֆոնին navy է, մուգ ֆոնին՝ սպիտակ։ «ЭВАКУАТОР»-ը բաց ֆոնին նարնջագույն է, մուգ ֆոնին՝ `#F18A4B`։
- Չձգել, չթեքել, եզրագիծ չտալ, գրադիենտ չլցնել։
- **Ink-ը navy `#13233A`-ն է** (Գև, 06.10.2026)։ `brand/README.md`-ի `#111111`-ը հին արժեքն է, փոխարինված է։

### Գույն

- Գործողության կոճակը նարնջագույն է, տեքստը նրա վրա **navy** է (4.7:1), երբեք սպիտակ։ Մեկ էկրանին՝ մեկ գլխավոր գործողություն։
- Ընտրված, ակտիվ, երկրորդական՝ navy (մուգ թեմայում՝ սպիտակ)։
- Բաց թեման սկսվում է փափուկ մոխրագույնից (`#F4F6F8`), ոչ մաքուր սպիտակից։
- Կոմպոնենտները օգտագործում են միայն իմաստային `--color-*` token-ները։

### Տառատեսակ, ձև, շարժում

- Golos Text՝ տեքստ և ինտերֆեյս, Roboto Condensed Bold՝ վերնագրեր, կոճակներ, գներ։ Գինը՝ `от 4 000 ₽`։
- Կլորացում՝ կոճակ և դաշտ 8px, քարտ 12px։ Pill չկա։ Սեղմվող տարածքը առնվազն 48px է։
- Շարժում՝ 160ms և 240ms, առանց զարդի և glow-ի։ Reduced motion-ի դեպքում ամեն անիմացիա անջատված է։

### Իկոններ և նկարներ

- Գծային իկոններ, 24 grid, հաստությունը 2, մեկ չափերի սանդղակ, emoji չկա։
- Նկարները՝ ըստ `photo/DESIGN_SYSTEM.md`-ի. միայն իրական գործեր, համարանիշներն ու դեմքերը փակված։

### Կոմպոնենտներ

Գրադարանից՝ КРЮК24-ի գույներով՝ Button, Card, FormRow, Input, Select, Tabs, Accordion, Modal, Drawer, Toast, Table և մյուսները։ КРЮК24-ի սեփականները (`window.Kryuk`)՝ `KryukMark`, `ContactButtons`, `CallBar`, `Price`, `TariffList`, `ChoiceTiles`, `OrderStatus` (`runtime/order_flow`-ի 6 վիճակը), `OrderCard`։ Գրադարանի `BrandMark`-ը (MenQ-ի լոգոն) երբեք չի օգտագործվում։

### Bro՝ կառավարվող օրկեստրատոր

- Bro-ն կարդում է, պլանավորում և սևագրում։ **Դեպի դուրս ամեն գործողություն անցնում է Գևի հաստատմամբ**։
- Մեկ առաջարկ = մեկ `ApprovalCard`՝ ճշգրիտ գործողությունով, հաշվով, տեքստով կամ գումարով և ռիսկով։ Փոխված առաջարկը նոր հաստատում է պահանջում (`runtime/action_approval`)։
- Գևի կարդացածը հայերեն է, Արմենին և հաճախորդներին գնացողը՝ ռուսերեն։ Գևի էկրանին՝ փաստը և մեկ կոճակ։

### Մատչելիություն

Տեքստ՝ 4.5:1, control-ների եզրեր և focus՝ 3:1, երկու թեմայում. 22 զույգ × 2 թեմա, ստուգում է `validate_design.py`-ը։ Focus-ը տեսանելի է՝ 3px նարնջագույն շրջանակ։

### Ինչը դեռ կիրառված չէ

- **Կայք**՝ արդեն մոտ է։ Մնացել են սև `logo-dark.png`-ն և SEO էջերի `theme-color`-ը. կգնան հաջորդ հրապարակմամբ, Գևի «հա»-ով։
- **Dashboard** (`ops_views.py`)՝ Գևի դիզայնն է, պաշտպանված է։ Դեռ ազուր և cyan գույներով է։ КРЮК24-ի token-ներին անցնելը Գևի «հա»-ն է պահանջում։

<!-- END: KRYUK24_DESIGN_README -->
