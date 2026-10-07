# Operator page in KRYUK24 colours / Աշխատանքների էջը КРЮК24-ի գույներով

**Status:** prepared and checked locally, **not installed**. Gev's yes for the colours: 07.10.2026 22:58 UTC. Installing it is Gev's step, after he has looked at the screenshots.

## English

### What changes

Only colours in `ops_views.py`: the azure / cyan palette becomes KRYUK24's navy / orange from `design/tokens/`. Layout, sizes, corners, texts, icons, images (the MenQ logo and Bro's avatar at the top stay as they are), behaviour and every line of Python are unchanged. Buttons become orange with navy text, as everywhere in KRYUK24.

`make_patch.py` makes the file from the installed one (`runtime/server/ops_views.py`, sha256 `f5f6e9d8…`) by exact replacements; a different source stops it. `runtime/server/` itself is not edited: it stays the record of the server.

### Checked

- `python runtime/wip/dashboard_colours/make_patch.py --check` → up to date; no azure or cyan value is left.
- The server's own tests (102) pass with the new file in place of the old one (copy of `runtime/server/`, 07.10.2026).
- Rendered from a throwaway test database in Chromium: axe (WCAG 2 A/AA) 0 violations in light, dark and at 390 px. The current page has 1 contrast failure in light and 2 at 390 px.

### Install (Gev)

From the repository folder on Windows:

```
scp -r runtime/wip/dashboard_colours kryuk@<VPS>:/tmp/
ssh -t kryuk@<VPS> "sudo bash /tmp/dashboard_colours/install.sh"
```

The script checks both files by sha256, keeps the original as `/opt/kryuk24/ops_views.py.before-kryuk-colours`, restarts `kryuk-capture` and checks `/health`; it rolls back by itself if the import or the health check fails. To go back later: `sudo bash /tmp/dashboard_colours/install.sh rollback`. After installing, `runtime/server/` is refreshed from the server in a separate step.

## Հայերեն

**Ինչ է փոխվում.** `ops_views.py`-ում միայն գույները. ազուր և cyan գույները դառնում են КРЮК24-ի navy և նարնջագույն։ Դասավորությունը, չափերը, տեքստերը, իկոնները, նկարները (վերևի MenQ լոգոն և Bro-ի ավատարը) և Python կոդը նույնն են մնում։ Կոճակները նարնջագույն են՝ navy տեքստով։

**Ստուգված է.** Սերվերի 102 թեստն անցնում են նոր ֆայլով։ axe-ը 0 սխալ է տալիս light-ում, dark-ում և 390px-ում (ներկայիս էջում light-ում 1 սխալ կա, 390px-ում՝ 2)։

**Տեղադրում (Գև).** Վերևի երկու հրամանը Windows-ից։ Սկրիպտը ստուգում է ֆայլերը, պահում է հինը, վերագործարկում է `kryuk-capture`-ը։ Սխալի դեպքում ինքն է հետ բերում հինը։ Հետ գնալու համար՝ `install.sh rollback`։

<!-- END: DASHBOARD_COLOURS -->
