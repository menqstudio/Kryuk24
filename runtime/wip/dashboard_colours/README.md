# Operator page in KRYUK24 colours / Աշխատանքների էջը КРЮК24-ի գույներով

**Status:** prepared and checked locally, **not installed**. Gev's yes for the colours: 07.10.2026 22:58 UTC. Installing it is Gev's step, after he has looked at the screenshots.

## English

### What changes

Made by `make_patch.py` from the installed file (`runtime/server/ops_views.py`, sha256 `f5f6e9d8…`) by exact replacements, in three stages; a different source stops it. `runtime/server/` itself is not edited.

1. **Colours** (Gev's yes, 07.10.2026 22:58 UTC): azure / cyan become KRYUK24 navy / orange from `design/tokens/`; buttons orange with navy text.
2. **UX** (Gev's yes, 08.10.2026 00:07 UTC): the official KRYUK24 lockup in the header instead of the MenQ logo (`kryuk-logo-dark.webp`, rendered from `brand/02_lockups/lockup_horizontal_transparent_dark.svg` by `make_logo.py`, nothing redrawn); a summary-card button that opens what waits for Gev; every tile shows its state as an icon and a word; today's tiles ordered by what needs attention.
3. **Daily use** (independent design review by a second model, checked here): switches on the logo row; no sentence repeating the pills; the button names what it opens; no triple listing of one waiting task; queue-creation is primary only when no queue exists; "In the queue" instead of a second "Waiting"; tiles that need action are outlined, done tiles recede; 44 px tap targets; one-line task rows on phones.

Routes, forms, scripts, data and every server-side rule stay as they are. Bro's avatar stays.

### Checked

- `python runtime/wip/dashboard_colours/make_patch.py --check` → up to date; no azure or cyan value is left.
- The server's own tests (102) pass with the new file in place of the old one.
- `render_sample.py` page in Chromium: axe (WCAG 2 A/AA) 0 violations in light, dark and at 390 px; the summary button opens the waiting task's window; tiles come in the order waiting → blocked → in queue → done.

### Install (Gev)

From the repository folder on Windows:

```
scp -r runtime/wip/dashboard_colours kryuk@<VPS>:/tmp/
ssh -t kryuk@<VPS> "sudo bash /tmp/dashboard_colours/install.sh"
```

The script checks both files by sha256, keeps the original as `/opt/kryuk24/ops_views.py.before-kryuk-colours`, restarts `kryuk-capture` and checks `/health`; it rolls back by itself if the import or the health check fails. To go back later: `sudo bash /tmp/dashboard_colours/install.sh rollback`. After installing, `runtime/server/` is refreshed from the server in a separate step.

## Հայերեն

**Ինչ է փոխվում.** Երեք փուլ. (1) գույները՝ КРЮК24-ի navy և նարնջագույն, (2) վերևում КРЮК24-ի պաշտոնական լոգոն, «Բացել» կոճակ քեզ սպասող գործի համար, ամեն սալիկի վիճակը՝ իկոն և բառ, գործերը՝ ըստ կարևորության, (3) ամենօրյա օգտագործման մանրուքներ՝ հեռախոսում մեկ տողով գործեր, 44px կոճակներ, կրկնությունների հեռացում։ Route-ները, ձևերը, տվյալները և սերվերի կանոնները նույնն են։

**Ստուգված է.** Սերվերի 102 թեստն անցնում են նոր ֆայլով։ axe-ը 0 սխալ է տալիս light-ում, dark-ում և 390px-ում (ներկայիս էջում light-ում 1 սխալ կա, 390px-ում՝ 2)։

**Տեղադրում (Գև).** Վերևի երկու հրամանը Windows-ից։ Սկրիպտը ստուգում է ֆայլերը, պահում է հինը, վերագործարկում է `kryuk-capture`-ը։ Սխալի դեպքում ինքն է հետ բերում հինը։ Հետ գնալու համար՝ `install.sh rollback`։

<!-- END: DASHBOARD_COLOURS -->
