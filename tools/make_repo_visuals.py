"""Visuals of the repository README: cover, architecture, roadmap phases, status board. Light and dark, EN and HY.

    python tools/make_repo_visuals.py            writes docs/assets/readme/*.svg

Needs Pillow and OpenCV (tools/requirements.txt). The output is committed; rerun after a fact below changes.

Rules the files follow:
  - identity is KRYUK24's own: the hook and the «КРЮК24 / ЭВАКУАТОР+» lockup, navy, orange, soft orange, white
    (tools/brand.py). The lockup letters are outlines traced from the brand fonts, so no font has to load;
  - structure follows the MenQ design platform's conventions for a product layer: 960x300 cover with the text block
    bottom-left and a 48 px hairline grid, cards with a 1 px border, pill badges with a dot AND a word (status is
    never carried by colour alone), light and dark as equals, text contrast 4.5:1 or better;
  - no script, no foreignObject, no external resource, no embedded or remote font: every other text uses the
    reader's system fonts, which is also what covers Armenian;
  - every status word here must be backed by docs/CURRENT_STATE.md. AS_OF is printed in each picture.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand as B  # noqa: E402

OUT = B.ROOT / "docs" / "assets" / "readme"
AS_OF = "07.10.2026"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans','Noto Sans Armenian',Helvetica,Arial,sans-serif"

THEMES = {
    "light": {"surface": "#FFFFFF", "surface2": "#F3F5F8", "border": "#D5DBE3", "grid": "#E4E8EE", "text": B.INK, "text2": "#44536A",
              "muted": "#5E6B7E", "accent": B.ORANGE, "sub": B.ORANGE, "on": "light",
              "ok": ("#15803D", "#E8F5EC"), "progress": ("#B45309", "#FBF1E1"), "blocked": ("#B91C1C", "#FBEAEA"), "neutral": ("#44536A", "#EDF0F4")},
    "dark": {"surface": B.INK, "surface2": "#1B2F4C", "border": "#34475F", "grid": "#1E3350", "text": B.WHITE, "text2": "#C9D3E0",
             "muted": "#9FB0C5", "accent": B.ORANGE, "sub": B.ORANGE_SOFT, "on": "dark",
             "ok": ("#4ADE80", "#17382F"), "progress": ("#FBBF24", "#3A3320"), "blocked": ("#F87171", "#3D2530"), "neutral": ("#C9D3E0", "#263A56")},
}


# ---------------------------------------------------------------- brand letters as outlines
def outline(s, family, weight, size=420, ls=0.0):
    """Path data of `s` set in a brand font, baseline at y=0, in units of 1/size. Returns (d, advance width per unit)."""
    width = B.measure(s, size, family, weight, ls)
    pad = 40
    canvas = Image.new("L", (int(width) + 2 * pad, int(size * 1.5) + 2 * pad), 0)
    base = pad + int(size * 1.1)
    B.draw_text(ImageDraw.Draw(canvas), (pad, base), s, size, family, weight, fill=255, ls=ls)
    _, mask = cv2.threshold(np.array(canvas), 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in contours:
        if cv2.contourArea(c) < 12:
            continue
        poly = cv2.approxPolyDP(c, 0.45, True)[:, 0, :].astype(float)
        pts = ["%.4g %.4g" % ((x - pad) / size, (y - base) / size) for x, y in poly]
        parts.append("M" + "L".join(pts) + "Z")
    return "".join(parts), width / size


def letters(x, y, s, size, family, weight, fill, ls=0.0):
    d, w = outline(s, family, weight, ls=ls / size * 420 if ls else 0.0)
    return '<path transform="translate(%.2f,%.2f) scale(%.4f)" fill="%s" fill-rule="evenodd" d="%s"/>' % (x, y, size, fill, d), w * size


def lockup(x, y, h, t):
    """The logo as in tools/brand.py lockup(), with the letters outlined. Returns (svg, width)."""
    main = B.WHITE if t["on"] == "dark" else B.INK
    k = h / 44.0
    hook, hw = B.hook(x, y, h)
    tx = x + hw + 7 * k
    name_size = 28 * k
    asc, desc, _ = B.metrics("display", 700)
    name_base = y + (name_size - (asc + desc) * name_size) / 2 + asc * name_size
    name, name_w = letters(tx, name_base, "КРЮК24", name_size, "display", 700, main)
    sub_size = 12 * k
    a2, d2, _ = B.metrics("text", 400)
    sub_base = y + name_size + 3 * k + (1.1 * sub_size - (a2 + d2) * sub_size) / 2 + a2 * sub_size
    glyphs = B.measure("ЭВАКУАТОР", sub_size, "text", 400) + B.measure("+", sub_size, "text", 700)
    ls = (name_w - glyphs) / 9
    word, word_w = letters(tx, sub_base, "ЭВАКУАТОР", sub_size, "text", 400, t["sub"], ls=ls)
    plus, _ = letters(tx + word_w + ls, sub_base, "+", sub_size, "text", 700, main)
    return hook + name + word + plus, (tx - x) + name_w


# ---------------------------------------------------------------- drawing helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size, fill, weight=400, anchor="start", ls=0.0, caps=False):
    extra = ' letter-spacing="%.2f"' % ls if ls else ""
    return '<text x="%.1f" y="%.1f" font-family="%s" font-size="%d" font-weight="%d" fill="%s" text-anchor="%s"%s>%s</text>' % (
        x, y, SANS, size, weight, fill, anchor, extra, esc(s.upper() if caps else s))


def box(x, y, w, h, fill, stroke=None, r=16):
    s = ' stroke="%s" stroke-width="1"' % stroke if stroke else ""
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s"%s/>' % (x, y, w, h, r, fill, s)


def badge(right, cy, word, tone, t):
    """Pill with a dot and a word, right edge at `right`, centred on cy. Returns (svg, width)."""
    fg, bg = t[tone]
    w = 30 + sum(9.6 if ord(ch) > 0x52F else 7.3 for ch in word)      # Armenian capitals are wider than Latin ones
    x = right - w
    return (box(x, cy - 12, w, 24, bg, r=12) + '<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x + 13, cy, fg)
            + text(x + 23, cy + 4, word, 11, fg, 700, ls=0.5, caps=True)), w


def doc(w, h, body, label, t, bg=True):
    back = box(0.5, 0.5, w - 1, h - 1, t["surface"], t["border"], 24) if bg else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n') % (w, h, w, h, esc(label), esc(label), back, "".join(body))


def head(title, sub, t, w=640):
    return [text(32, 50, title, 22, t["text"], 700), text(32, 74, sub, 13, t["muted"]),
            '<rect x="32" y="88" width="%d" height="1" fill="%s"/>' % (w - 64, t["border"])]


# ---------------------------------------------------------------- content (every status: docs/CURRENT_STATE.md)
L = {
    "en": {
        "cover": ("Bro: the business operating assistant", "Tow-truck service in Moscow and the Moscow region", "inspect → analyse → propose → prepare → approval → execute → verify → report",
                  "KRYUK24 Bro: the business operating assistant for a tow-truck service in Moscow and the Moscow region"),
        "as_of": "State on %s. Source: docs/CURRENT_STATE.md" % AS_OF,
        "arch": ("Where each part lives", "Target placement and what is there today",
                 "KRYUK24 architecture: GitHub holds code and documents; the VPS holds the runtime, with the queue, dashboard, Bro bridge and API reader installed and the mailbox, approvals, executor and monitoring planned; the Debian desktop worker is planned; Windows is for development and supervised trials"),
        "zones": [("GitHub", "Canonical code, documents, decisions, roadmap", [("Private repository, CI on every change", "in place", "ok")]),
                  ("VPS", "The runtime. STAGING, sending is off", [("Daily queue, dashboard, Bro bridge", "installed", "ok"),
                                                                   ("API reader: hosting, Metrica, Webmaster", "installed", "ok"),
                                                                   ("Its first supervised write", "pending", "progress"),
                                                                   ("Mailbox, approvals, executor, monitoring", "planned", "neutral")]),
                  ("Debian desktop", "Browser and media worker", [("Bounded worker that takes runtime jobs", "planned", "neutral")]),
                  ("Windows", "Development and supervised trials only", [("Chrome proxy, gate, trial harness", "in progress", "progress")])],
        "outside": ["Outside the runtime: the live site kryuk24.ru is not connected to it yet.",
                    "Every public or paid action needs Gev's approval for that exact action."],
        "phases": ("Roadmap phases", "Approved 07.10.2026. A phase closes on its acceptor's word, not on a file",
                   "KRYUK24 roadmap phases 0 to 8 with owner, acceptor and state: phase 0 awaits acceptance, phases 1, 2 and 6 are started, phases 3, 4, 5, 7 and 8 are not started"),
        "phase_rows": [("0", "Canonical state", "Claude / GPT", "awaits acceptance", "progress"), ("1", "Security and recovery", "Claude / GPT", "started", "progress"),
                       ("2", "Reliable collection", "Claude / GPT", "started", "progress"), ("3", "Real business flow", "GPT / Armen", "not started", "neutral"),
                       ("4", "Action approval", "GPT / Claude", "not started", "neutral"), ("5", "Executor", "Claude / GPT", "not started", "neutral"),
                       ("6", "Browser and Debian", "Claude / GPT", "started", "progress"), ("7", "Analysis, reporting, control", "Claude / Gev", "not started", "neutral"),
                       ("8", "Controlled operation, v1.0", "Gev / GPT", "not started", "neutral")],
        "owner": "owner / acceptor",
        "status": ("What Bro can read today", "A source that is not read is UNKNOWN, never \"no problem\"",
                   "KRYUK24 sources: hosting, Metrica and Webmaster are read by an installed API reader; Yandex Direct is blocked by Yandex; Avito is on hold; the mailbox is blocked; the Yandex Business card has no API; real requests and orders are not recorded"),
        "status_rows": [("Hosting account", "balance, days left", "installed", "ok"), ("Yandex Metrica", "site and Maps card, separately", "installed", "ok"),
                        ("Yandex Webmaster", "indexing of the site", "installed", "ok"), ("Yandex Direct", "waits for Yandex to grant API access", "blocked", "blocked"),
                        ("Avito", "reading works; nothing is changed", "on hold", "neutral"), ("Mailbox", "no mail application, no credential", "blocked", "blocked"),
                        ("Yandex Business card", "no API; browser route is work in progress", "in progress", "progress"),
                        ("Real requests and orders", "nothing real is recorded yet", "not built", "neutral")],
        "status_foot": "A click is not a call, a call is not an order, an order is not a paid completion.",
    },
    "hy": {
        "as_of": "Վիճակը %s-ին։ Աղբյուր՝ docs/CURRENT_STATE.md" % AS_OF,
        "arch": ("Որտեղ ինչն ա ապրում", "Նպատակային տեղաբաշխումը ու ինչ կա այսօր",
                 "KRYUK24-ի ճարտարապետությունը. GitHub-ում կոդն ու փաստաթղթերն են. VPS-ում runtime-ն ա՝ հերթը, վահանակը, Bro-ի կամուրջն ու API reader-ը դրված են, փոստը, հաստատումները, executor-ն ու monitoring-ը պլանավորված են. Debian-ի worker-ը պլանավորված ա. Windows-ը մշակման ու հսկվող փորձերի համար ա"),
        "zones": [("GitHub", "Հիմնական կոդը, փաստաթղթերը, որոշումները, քարտեզը", [("Փակ repo, CI ամեն փոփոխության վրա", "կա", "ok")]),
                  ("VPS", "Runtime-ը։ STAGING, ուղարկելը անջատված ա", [("Օրվա հերթ, վահանակ, Bro-ի կամուրջ", "դրված ա", "ok"),
                                                                    ("API reader. հոստինգ, Metrica, Webmaster", "դրված ա", "ok"),
                                                                    ("Դրա առաջին հսկվող գրելը", "սպասվում ա", "progress"),
                                                                    ("Փոստ, հաստատումներ, executor, monitoring", "պլանում ա", "neutral")]),
                  ("Debian desktop", "Browser ու media worker", [("Սահմանափակ worker, որ վերցնում ա runtime-ի գործերը", "պլանում ա", "neutral")]),
                  ("Windows", "Միայն մշակում ու հսկվող փորձեր", [("Chrome proxy, gate, trial harness", "ընթացքում ա", "progress")])],
        "outside": ["Runtime-ից դուրս. կենդանի կայքը՝ kryuk24.ru, դեռ կապված չի runtime-ին։",
                    "Հրապարակային կամ վճարովի ամեն քայլ՝ Գևի հաստատումով հենց էդ քայլի համար։"],
        "phases": ("Քարտեզի փուլերը", "Հաստատված ա 07.10.2026-ին։ Փուլը փակում ա ընդունողը, ոչ թե ֆայլը",
                   "KRYUK24-ի քարտեզի 0–8 փուլերը՝ պատասխանատուով, ընդունողով ու վիճակով. 0-րդը սպասում ա ընդունման, 1, 2 ու 6 փուլերը սկսված են, 3, 4, 5, 7 ու 8 փուլերը սկսված չեն"),
        "phase_rows": [("0", "Հիմնական վիճակ", "Claude / GPT", "սպասում ա ընդունման", "progress"), ("1", "Անվտանգություն ու վերականգնում", "Claude / GPT", "սկսված ա", "progress"),
                       ("2", "Հուսալի հավաքում", "Claude / GPT", "սկսված ա", "progress"), ("3", "Իրական բիզնես հոսք", "GPT / Արմեն", "սկսված չի", "neutral"),
                       ("4", "Գործողության հաստատում", "GPT / Claude", "սկսված չի", "neutral"), ("5", "Executor", "Claude / GPT", "սկսված չի", "neutral"),
                       ("6", "Զննարկիչ ու Debian", "Claude / GPT", "սկսված ա", "progress"), ("7", "Վերլուծություն, հաշվետվություն", "Claude / Գև", "սկսված չի", "neutral"),
                       ("8", "Հսկվող շահագործում, v1.0", "Գև / GPT", "սկսված չի", "neutral")],
        "owner": "պատասխանատու / ընդունող",
        "status": ("Ինչ կարա կարդա Bro-ն այսօր", "Չկարդացված աղբյուրը UNKNOWN ա, ոչ թե «խնդիր չկա»",
                   "KRYUK24-ի աղբյուրները. հոստինգը, Metrica-ն ու Webmaster-ը կարդում ա դրված API reader-ը. Yandex Direct-ը փակ ա Yandex-ի կողմից. Avito-ն HOLD ա. փոստը փակ ա. Yandex Բիզնեսի քարտը API չունի. իրական դիմումներն ու պատվերները չեն գրանցվում"),
        "status_rows": [("Հոստինգի հաշիվ", "մնացորդ, մնացած օրեր", "դրված ա", "ok"), ("Yandex Metrica", "կայքն ու Քարտեզի քարտը՝ առանձին", "դրված ա", "ok"),
                        ("Yandex Webmaster", "կայքի ինդեքսավորում", "դրված ա", "ok"), ("Yandex Direct", "սպասում ա Yandex-ի API թույլտվությանը", "փակ ա", "blocked"),
                        ("Avito", "կարդալը աշխատում ա. ոչինչ չի փոխվում", "HOLD", "neutral"), ("Փոստարկղ", "փոստի հավելված ու բանալի չկա", "փակ ա", "blocked"),
                        ("Yandex Բիզնեսի քարտ", "API չկա. զննարկչի ճանապարհը ընթացքում ա", "ընթացքում ա", "progress"),
                        ("Իրական դիմումներ ու պատվերներ", "իրական ոչինչ դեռ չի գրանցվում", "չկա", "neutral")],
        "status_foot": "Սեղմումը զանգ չի, զանգը պատվեր չի, պատվերը վճարված ավարտ չի։",
    },
}


# ---------------------------------------------------------------- the four pictures
def cover(t):
    w, h = 960, 300
    title, sub, cycle, label = L["en"]["cover"]
    clip = '<clipPath id="c"><rect x="0.5" y="0.5" width="%d" height="%d" rx="32"/></clipPath>' % (w - 1, h - 1)
    grid = "".join('<path d="M%d 0V%d" stroke="%s" stroke-width="1"/>' % (x, h, t["grid"]) for x in range(48, w, 48))
    grid += "".join('<path d="M0 %dH%d" stroke="%s" stroke-width="1"/>' % (y, w, t["grid"]) for y in range(48, h, 48))
    big, _ = B.hook(742, -34, 392)                                    # the hook bleeds off the top and the right, as art
    logo, _ = lockup(40, 36, 58, t)
    body = [clip, '<g clip-path="url(#c)">', box(0, 0, w, h, t["surface"], r=0), grid,
            '<g opacity="%s">%s</g>' % ("0.95" if t["on"] == "dark" else "1", big), "</g>",
            box(0.5, 0.5, w - 1, h - 1, "none", t["border"], 32), logo,
            text(40, 196, title, 30, t["text"], 700, ls=-0.4), text(40, 226, sub, 16, t["text2"]),
            text(40, 262, cycle, 13, t["muted"], 500)]
    return doc(w, h, body, label, t, bg=False)


def architecture(t, lang):
    c = L[lang]
    title, sub, label = c["arch"]
    w, y, body = 640, 108, []
    for name, what, rows in c["zones"]:
        hgt = 64 + 34 * len(rows)
        body += [box(32, y, w - 64, hgt, t["surface2"], t["border"]), '<rect x="32" y="%d" width="4" height="%d" fill="%s"/>' % (y + 16, 28, t["accent"]),
                 text(52, y + 30, name, 17, t["text"], 700), text(52, y + 50, what, 13, t["text2"])]
        for i, (item, word, tone) in enumerate(rows):
            cy = y + 76 + 34 * i
            b, _ = badge(w - 48, cy, word, tone, t)
            body += ['<rect x="52" y="%d" width="%d" height="1" fill="%s"/>' % (cy - 17, w - 104, t["border"]), text(52, cy + 5, item, 14, t["text"]), b]
        y += hgt + 12
    for i, line in enumerate(c["outside"]):
        body.append(text(32, y + 16 + 20 * i, line, 13, t["text2"]))
    y += 20 * len(c["outside"]) + 22
    body.append(text(32, y, c["as_of"], 12, t["muted"]))
    return doc(w, y + 24, head(title, sub, t) + body, label, t)


def phases(t, lang):
    c = L[lang]
    title, sub, label = c["phases"]
    w = 640
    body = [text(w - 48, 112, c["owner"], 11, t["muted"], 600, "end", 0.5, True)]
    for i, (num, name, who, word, tone) in enumerate(c["phase_rows"]):
        y = 124 + 58 * i
        b, bw = badge(w - 48, y + 23, word, tone, t)
        body += [box(32, y, w - 64, 48, t["surface2"], t["border"], 12),
                 '<circle cx="60" cy="%d" r="15" fill="%s"/>' % (y + 24, t["surface"]), '<circle cx="60" cy="%d" r="15" fill="none" stroke="%s" stroke-width="2"/>' % (y + 24, t["accent"]),
                 text(60, y + 29, num, 15, t["text"], 700, "middle"), text(88, y + 21, name, 15, t["text"], 600),
                 text(88, y + 39, who, 12, t["muted"]), b]
    y = 124 + 58 * len(c["phase_rows"]) + 14
    body.append(text(32, y, c["as_of"], 12, t["muted"]))
    return doc(w, y + 24, head(title, sub, t) + body, label, t)


def status(t, lang):
    c = L[lang]
    title, sub, label = c["status"]
    w, body = 640, []
    for i, (name, note, word, tone) in enumerate(c["status_rows"]):
        y = 108 + 56 * i
        b, _ = badge(w - 48, y + 23, word, tone, t)
        body += [box(32, y, w - 64, 46, t["surface2"], t["border"], 12), text(48, y + 20, name, 15, t["text"], 600), text(48, y + 37, note, 12, t["text2"]), b]
    y = 108 + 56 * len(c["status_rows"]) + 16
    body += [text(32, y, c["status_foot"], 13, t["text2"], 500), text(32, y + 24, c["as_of"], 12, t["muted"])]
    return doc(w, y + 48, head(title, sub, t) + body, label, t)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for theme, t in THEMES.items():
        made.append(("cover-%s.svg" % theme, cover(t)))
        for lang in ("en", "hy"):
            for name, fn in (("architecture", architecture), ("phases", phases), ("status", status)):
                made.append(("%s-%s-%s.svg" % (name, lang, theme), fn(t, lang)))
    for name, svg in made:
        for banned in ("<script", "foreignObject", "@font-face", "href=", "url(http", "<image"):
            assert banned not in svg, (name, banned)
        (OUT / name).write_bytes(svg.encode("utf-8"))
        print("%-32s %6.1f KB" % (name, len(svg.encode("utf-8")) / 1024))


if __name__ == "__main__":
    main()
