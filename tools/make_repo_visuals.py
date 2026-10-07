"""Visuals of the repository README: cover, where each part lives, what runs on the server, roadmap phases, sources.
Light and dark, EN and HY.

    python tools/make_repo_visuals.py            writes docs/assets/readme/*.svg

Needs Pillow and OpenCV (tools/requirements.txt). The output is committed; rerun after a fact below changes.

Rules the files follow:
  - identity is KRYUK24's own: the hook and the «КРЮК24 / ЭВАКУАТОР+» lockup, navy, orange, soft orange, white
    (tools/brand.py). The lockup letters are outlines traced from the brand fonts, so no font has to load;
  - structure follows the MenQ design platform's conventions for a product layer: 960x300 cover with the text block
    bottom-left and a 48 px hairline grid, cards with a 1 px border, a status shown as a dot AND a word (never by
    colour alone), light and dark as equals, text contrast 4.5:1 or better;
  - readable on a phone: a picture carries only the main idea in large labels. The diagrams are 480 units wide and
    no text in them is smaller than MIN_TEXT, which is about 12 px when the picture is 330 px wide. Details (owners,
    notes, evidence) are in the Markdown next to the picture. There is a narrow cover for small screens;
  - no script, no foreignObject, no external resource, no embedded or remote font: every other text uses the
    reader's system fonts, which is also what covers Armenian;
  - every status word here must be backed by docs/CURRENT_STATE.md or docs/ROADMAP.md. AS_OF is printed in each.
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
W = 480                   # width of a diagram in its own units
MIN_TEXT = 17             # smallest text in a diagram
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans','Noto Sans Armenian',Helvetica,Arial,sans-serif"

THEMES = {
    "light": {"surface": "#FFFFFF", "surface2": "#F3F5F8", "border": "#D5DBE3", "grid": "#E4E8EE", "text": B.INK, "text2": "#44536A",
              "muted": "#5E6B7E", "accent": B.ORANGE, "sub": B.ORANGE, "on": "light",
              "ok": "#15803D", "progress": "#B45309", "blocked": "#B91C1C", "neutral": "#44536A"},
    "dark": {"surface": B.INK, "surface2": "#1B2F4C", "border": "#34475F", "grid": "#1E3350", "text": B.WHITE, "text2": "#C9D3E0",
             "muted": "#9FB0C5", "accent": B.ORANGE, "sub": B.ORANGE_SOFT, "on": "dark",
             "ok": "#4ADE80", "progress": "#FBBF24", "blocked": "#F87171", "neutral": "#C9D3E0"},
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


def text(x, y, s, size, fill, weight=400, anchor="start", ls=0.0):
    extra = ' letter-spacing="%.2f"' % ls if ls else ""
    return '<text x="%.1f" y="%.1f" font-family="%s" font-size="%d" font-weight="%d" fill="%s" text-anchor="%s"%s>%s</text>' % (
        x, y, SANS, size, weight, fill, anchor, extra, esc(s))


def box(x, y, w, h, fill, stroke=None, r=16):
    s = ' stroke="%s" stroke-width="1"' % stroke if stroke else ""
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s"%s/>' % (x, y, w, h, r, fill, s)


def state(right, base, word, tone, t):
    """A status: a dot and a word in its tone, right-aligned. Both always, never the colour alone.
    The dot is a character of the same text, so it sits next to the word whatever font the reader has."""
    return text(right, base, "● " + word, MIN_TEXT, t[tone], 600, "end")


def doc(w, h, body, label, t, frame=True):
    back = box(0.5, 0.5, w - 1, h - 1, t["surface"], t["border"], 24) if frame else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n') % (w, h, w, h, esc(label), esc(label), back, "".join(body))


def rows_picture(t, title, label, rows, foot):
    """A titled list: each row is a name on the left and a status on the right. `rows` = (name, word, tone)."""
    body = [text(28, 50, title, 26, t["text"], 700), '<rect x="28" y="68" width="%d" height="2" fill="%s"/>' % (56, t["accent"])]
    y = 88
    for name, word, tone in rows:
        body += [box(20, y, W - 40, 50, t["surface2"], t["border"], 12), text(36, y + 32, name, 18, t["text"], 600), state(W - 36, y + 32, word, tone, t)]
        y += 58
    body.append(text(28, y + 22, foot, MIN_TEXT, t["muted"]))
    return doc(W, y + 44, body, label, t)


# ---------------------------------------------------------------- content (every status: docs/CURRENT_STATE.md, docs/ROADMAP.md)
L = {
    "en": {
        "foot": "State on %s" % AS_OF,
        "placement": ("Where each part lives", "Where each part of KRYUK24 Bro lives: GitHub is in place, the VPS runtime is in STAGING, the Debian worker is planned, Windows is for trials",
                      [("GitHub", "code, documents", "in place", "ok"), ("VPS", "the runtime", "STAGING", "progress"),
                       ("Debian desktop", "browser worker", "planned", "neutral"), ("Windows", "development, trials", "in use", "ok")]),
        "server": ("On the server today", "On the server today: queue and dashboard, Bro bridge and API reader are installed; mailbox, approvals, executor and monitoring are planned",
                   [("Queue and dashboard", "installed", "ok"), ("Bro bridge", "installed", "ok"), ("API reader", "installed", "ok"),
                    ("Mailbox", "planned", "neutral"), ("Approvals", "planned", "neutral"), ("Executor", "planned", "neutral"), ("Monitoring", "planned", "neutral")]),
        "phases": ("Roadmap phases", "Roadmap phases: 0 in review; 1, 2 and 6 started; 3, 4, 5, 7 and 8 not started",
                   [("0  Canonical state", "in review", "progress"), ("1  Security, recovery", "started", "progress"), ("2  Collection", "started", "progress"),
                    ("3  Business flow", "not started", "neutral"), ("4  Action approval", "not started", "neutral"), ("5  Executor", "not started", "neutral"),
                    ("6  Browser, Debian", "started", "progress"), ("7  Reports, control", "not started", "neutral"), ("8  Operation, v1.0", "not started", "neutral")]),
        "sources": ("What Bro reads today", "What Bro reads today: hosting, Metrica and Webmaster are installed; Direct and the mailbox are blocked; Avito is on hold; the Business card is in progress; orders are not built",
                    [("Hosting", "installed", "ok"), ("Yandex Metrica", "installed", "ok"), ("Yandex Webmaster", "installed", "ok"), ("Yandex Direct", "blocked", "blocked"),
                     ("Avito", "on hold", "neutral"), ("Mailbox", "blocked", "blocked"), ("Business card", "in progress", "progress"), ("Requests, orders", "not built", "neutral")]),
    },
    "hy": {
        "foot": "Վիճակը %s-ին" % AS_OF,
        "placement": ("Որտեղ ինչն ա ապրում", "Որտեղ ա ապրում KRYUK24 Bro-ի ամեն մասը. GitHub-ը կա, VPS-ի runtime-ը STAGING ա, Debian-ի worker-ը պլանում ա, Windows-ը փորձերի համար ա",
                      [("GitHub", "կոդ, փաստաթղթեր", "կա", "ok"), ("VPS", "runtime-ը", "STAGING", "progress"),
                       ("Debian desktop", "browser worker", "պլանում ա", "neutral"), ("Windows", "մշակում, փորձեր", "գործածվում ա", "ok")]),
        "server": ("Սերվերում այսօր", "Սերվերում այսօր. հերթն ու վահանակը, Bro-ի կամուրջն ու API reader-ը դրված են. փոստը, հաստատումները, executor-ն ու monitoring-ը պլանում են",
                   [("Հերթ ու վահանակ", "դրված ա", "ok"), ("Bro-ի կամուրջ", "դրված ա", "ok"), ("API reader", "դրված ա", "ok"),
                    ("Փոստ", "պլանում ա", "neutral"), ("Հաստատումներ", "պլանում ա", "neutral"), ("Executor", "պլանում ա", "neutral"), ("Monitoring", "պլանում ա", "neutral")]),
        "phases": ("Քարտեզի փուլերը", "Քարտեզի փուլերը. 0-րդը ընդունման մեջ ա. 1, 2 ու 6-ը սկսված են. 3, 4, 5, 7 ու 8-ը սկսված չեն",
                   [("0  Հիմնական վիճակ", "ընդունման մեջ", "progress"), ("1  Անվտանգություն", "սկսված ա", "progress"), ("2  Հավաքում", "սկսված ա", "progress"),
                    ("3  Բիզնես հոսք", "սկսված չի", "neutral"), ("4  Հաստատում", "սկսված չի", "neutral"), ("5  Executor", "սկսված չի", "neutral"),
                    ("6  Զննարկիչ, Debian", "սկսված ա", "progress"), ("7  Հաշվետվություն", "սկսված չի", "neutral"), ("8  Շահագործում, v1.0", "սկսված չի", "neutral")]),
        "sources": ("Ինչ ա կարդում Bro-ն այսօր", "Ինչ ա կարդում Bro-ն այսօր. հոստինգը, Metrica-ն ու Webmaster-ը դրված են. Direct-ն ու փոստը փակ են. Avito-ն HOLD ա. Բիզնեսի քարտը ընթացքում ա. պատվերները չկան",
                    [("Հոստինգ", "դրված ա", "ok"), ("Yandex Metrica", "դրված ա", "ok"), ("Yandex Webmaster", "դրված ա", "ok"), ("Yandex Direct", "փակ ա", "blocked"),
                     ("Avito", "HOLD", "neutral"), ("Փոստարկղ", "փակ ա", "blocked"), ("Բիզնեսի քարտ", "ընթացքում ա", "progress"), ("Դիմումներ, պատվերներ", "չկա", "neutral")]),
    },
}
COVER = ("Bro: the business operating assistant", "Tow-truck service in Moscow and the Moscow region",
         "inspect → analyse → propose → prepare → approval → execute → verify → report",
         "KRYUK24 Bro: the business operating assistant for a tow-truck service in Moscow and the Moscow region")


# ---------------------------------------------------------------- the pictures
def grid(w, h, t):
    return ("".join('<path d="M%d 0V%d" stroke="%s" stroke-width="1"/>' % (x, h, t["grid"]) for x in range(48, w, 48))
            + "".join('<path d="M0 %dH%d" stroke="%s" stroke-width="1"/>' % (y, w, t["grid"]) for y in range(48, h, 48)))


def cover(t):
    w, h = 960, 300
    title, sub, cycle, label = COVER
    big, _ = B.hook(742, -34, 392)                                    # the hook bleeds off the top and the right, as art
    logo, _ = lockup(40, 36, 58, t)
    body = ['<clipPath id="c"><rect x="0.5" y="0.5" width="%d" height="%d" rx="32"/></clipPath>' % (w - 1, h - 1),
            '<g clip-path="url(#c)">', box(0, 0, w, h, t["surface"], r=0), grid(w, h, t), big, "</g>",
            box(0.5, 0.5, w - 1, h - 1, "none", t["border"], 32), logo,
            text(40, 196, title, 30, t["text"], 700, ls=-0.4), text(40, 226, sub, 16, t["text2"]), text(40, 262, cycle, 13, t["muted"], 500)]
    return doc(w, h, body, label, t, frame=False)


def cover_narrow(t):
    """The cover for a small screen: same parts, set for 480 units so that the words stay readable."""
    w, h = W, 300
    label = COVER[3]
    big, _ = B.hook(322, 128, 300)
    logo, _ = lockup(28, 30, 64, t)
    body = ['<clipPath id="c"><rect x="0.5" y="0.5" width="%d" height="%d" rx="28"/></clipPath>' % (w - 1, h - 1),
            '<g clip-path="url(#c)">', box(0, 0, w, h, t["surface"], r=0), grid(w, h, t), big, "</g>",
            box(0.5, 0.5, w - 1, h - 1, "none", t["border"], 28), logo,
            text(28, 170, "Bro", 44, t["text"], 700, ls=-0.6), text(28, 204, "The business", 22, t["text"], 600),
            text(28, 232, "operating assistant", 22, t["text"], 600), text(28, 268, "Moscow and the region", 18, t["text2"])]
    return doc(w, h, body, label, t, frame=False)


def placement(t, lang):
    c = L[lang]
    title, label, zones = c["placement"]
    body = [text(28, 50, title, 26, t["text"], 700), '<rect x="28" y="68" width="56" height="2" fill="%s"/>' % t["accent"]]
    y = 88
    for name, what, word, tone in zones:
        body += [box(20, y, W - 40, 78, t["surface2"], t["border"], 14), '<rect x="20" y="%d" width="4" height="46" fill="%s"/>' % (y + 16, t["accent"]),
                 text(40, y + 34, name, 21, t["text"], 700), text(40, y + 60, what, MIN_TEXT, t["text2"]), state(W - 36, y + 34, word, tone, t)]
        y += 88
    body.append(text(28, y + 20, c["foot"], MIN_TEXT, t["muted"]))
    return doc(W, y + 42, body, label, t)


def listed(key):
    def make(t, lang):
        title, label, rows = L[lang][key]
        return rows_picture(t, title, label, rows, L[lang]["foot"])
    return make


PICTURES = (("placement", placement), ("server", listed("server")), ("phases", listed("phases")), ("sources", listed("sources")))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    made = []
    for theme, t in THEMES.items():
        made += [("cover-%s.svg" % theme, cover(t)), ("cover-narrow-%s.svg" % theme, cover_narrow(t))]
        for lang in ("en", "hy"):
            made += [("%s-%s-%s.svg" % (name, lang, theme), fn(t, lang)) for name, fn in PICTURES]
    for name, svg in made:
        for banned in ("<script", "foreignObject", "@font-face", "href=", "url(http", "<image"):
            assert banned not in svg, (name, banned)
        (OUT / name).write_bytes(svg.encode("utf-8"))
    print("%d files, %.0f KB in all" % (len(made), sum(len(s.encode("utf-8")) for _, s in made) / 1024))


if __name__ == "__main__":
    main()
