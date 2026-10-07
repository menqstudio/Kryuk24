"""Visuals of the repository README: cover, where each part lives, what runs on the server, roadmap phases, sources.
Light and dark, EN and HY.

    python tools/make_repo_visuals.py            writes docs/assets/readme/*.svg
    python tools/make_repo_visuals.py --check    the committed diagrams are what README.md says today (no file written)

The four diagrams hold no content of their own: title, names, states, the date and the label of each are read from
README.md (the heading, the list under the picture, the alt text). To change a picture, change the README and run
this script; CI runs --check, so a README that moved without its pictures fails there. What stays here is how a
diagram looks, the cover, and the list of state words with their tone (STATES): a state the list does not know, or a
name too long for its card, stops the script with a message.

Writing the files needs Pillow and OpenCV (tools/requirements.txt), for the cover. --check needs only Python.

Rules the files follow:
  - identity is KRYUK24's own: the hook and the «КРЮК24 / ЭВАКУАТОР+» lockup, navy, orange, soft orange, white
    (tools/brand.py). The lockup letters are outlines traced from the brand fonts, so no font has to load;
  - structure follows the MenQ design platform's conventions for a product layer: 960x300 cover with the text block
    bottom-left and a 48 px hairline grid, cards with a 1 px border, a status shown as a dot AND a word (never by
    colour alone), light and dark as equals, text contrast 4.5:1 or better;
  - readable on a phone: a picture carries only the main idea in large labels. The narrow diagrams are 480 units
    wide and no text in them is smaller than MIN_TEXT, which is about 12 px when the picture is 330 px wide. Details
    (owners, notes, evidence) are in the Markdown next to the picture. There is a narrow cover for small screens;
  - on a wide screen the same content fills the column: every diagram also has a `-wide` file, WIDE units across,
    with the cards in equal columns and a short last row centred. The README shows the wide file by default and
    the narrow one up to 600 px;
  - no script, no foreignObject, no external resource, no embedded or remote font: every other text uses the
    reader's system fonts, which is also what covers Armenian;
  - every status word comes from README.md and must be backed by docs/CURRENT_STATE.md or docs/ROADMAP.md. The date
    of the README's "State on" sentence is printed in each diagram.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand as B  # noqa: E402

OUT = B.ROOT / "docs" / "assets" / "readme"
README = B.ROOT / "README.md"
W = 480                   # width of a diagram in its own units
WIDE = 960                # width of the wide variant, the same as the cover
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
    import cv2                                    # only the cover needs these, so --check runs without them
    import numpy as np
    from PIL import Image, ImageDraw
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


def state(x, base, word, tone, t, anchor="end"):
    """A status: a dot and a word in its tone, right-aligned unless told otherwise. Both always, never the colour alone.
    The dot is a character of the same text, so it sits next to the word whatever font the reader has."""
    return text(x, base, "● " + word, MIN_TEXT, t[tone], 600, anchor)


def doc(w, h, body, label, t, frame=True):
    back = box(0.5, 0.5, w - 1, h - 1, t["surface"], t["border"], 24) if frame else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n') % (w, h, w, h, esc(label), esc(label), back, "".join(body))


def rows_picture(t, title, label, rows, foot):
    """A titled list: each row is a name on the left and a status on the right. `rows` = (name, word, tone)."""
    body = [text(28, 50, title, 26, t["text"], 700), '<rect x="28" y="68" width="%d" height="2" fill="%s"/>' % (56, t["accent"])]
    y = 88
    for name, word, tone in rows:
        if width(name, 18) + width("● " + word, MIN_TEXT) > W - 72 - 12:
            sys.exit("name and state do not fit one row of the narrow picture, shorten the name in README.md: %s" % name)
        body += [box(20, y, W - 40, 50, t["surface2"], t["border"], 12), text(36, y + 32, name, 18, t["text"], 600), state(W - 36, y + 32, word, tone, t)]
        y += 58
    body.append(text(28, y + 22, foot, MIN_TEXT, t["muted"]))
    return doc(W, y + 44, body, label, t)


def width(s, size):
    return len(s) * size * (0.62 if any(ord(ch) > 0x530 for ch in s) else 0.53)


def columns(labels):
    """How many equal columns the wide variant takes: the most (4, 3 or 2) in which the longest label still fits.
    `labels` = (text, font size). The width is an estimate (a little over what Segoe UI semibold takes), because the
    reader's font is not known."""
    longest = max(width(s, size) for s, size in labels)
    for n in (4, 3, 2):
        if longest <= (WIDE - 40 - 12 * (n - 1)) / n - 36:
            return n
    sys.exit("too long for a card even in two columns, shorten it in README.md: %s" % max(labels, key=lambda x: width(*x))[0])


def cells(count, n, height):
    """Top-left corners and the width of `count` cards in `n` equal columns; a short last row is centred."""
    cw = (WIDE - 40 - 12 * (n - 1)) / n
    out = []
    for i in range(count):
        row, col = divmod(i, n)
        in_row = min(n, count - row * n)
        left = 20 + (WIDE - 40 - (in_row * cw + (in_row - 1) * 12)) / 2
        out.append((left + col * (cw + 12), 88 + row * (height + 12)))
    return out, cw, 88 + ((count + n - 1) // n) * (height + 12)


def rows_picture_wide(t, title, label, rows, foot):
    """The same list for a wide screen: cards in equal columns, the name above its status."""
    body = [text(28, 50, title, 26, t["text"], 700), '<rect x="28" y="68" width="%d" height="2" fill="%s"/>' % (56, t["accent"])]
    spots, cw, y = cells(len(rows), columns([(r[0], 18) for r in rows]), 78)
    for (x, top), (name, word, tone) in zip(spots, rows):
        body += [box(x, top, cw, 78, t["surface2"], t["border"], 12), text(x + 18, top + 32, name, 18, t["text"], 600),
                 state(x + 18, top + 60, word, tone, t, "start")]
    body.append(text(28, y + 14, foot, MIN_TEXT, t["muted"]))
    return doc(WIDE, y + 36, body, label, t)


# ---------------------------------------------------------------- content: read from README.md
# State words the README may use, with the tone each is drawn in. The first one a state line starts with is taken.
STATES = {
    "en": (("in place", "ok"), ("in use", "ok"), ("installed", "ok"), ("STAGING", "progress"), ("in review", "progress"),
           ("in progress", "progress"), ("started", "progress"), ("planned", "neutral"), ("not started", "neutral"),
           ("on hold", "neutral"), ("not built", "neutral"), ("blocked", "blocked")),
    "hy": (("կա", "ok"), ("գործածվում ա", "ok"), ("դրված ա", "ok"), ("STAGING", "progress"), ("ընդունման մեջ", "progress"),
           ("ընթացքում ա", "progress"), ("սկսված ա", "progress"), ("պլանում ա", "neutral"), ("սկսված չի", "neutral"),
           ("HOLD", "neutral"), ("չկա", "neutral"), ("փակ ա", "blocked")),
}
FOOT = {"en": "State on %s", "hy": "Վիճակը %s-ին"}
PICTURE = re.compile(r'<picture>.*?srcset="docs/assets/readme/(placement|server|phases|sources)-(en|hy)-dark\.svg".*?alt="([^"]*)"')
ITEM = re.compile(r"^- \*\*(.+?)\*\*(?:: (.*))?$")
SUB = re.compile(r"^  - [^:]+: (.*)$")
DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")


def state_of(line, lang, where):
    for word, tone in STATES[lang]:
        if line.startswith(word) and not line[len(word):len(word) + 1].isalnum():
            return word, tone
    sys.exit("README.md, %s: the state %r starts with no word of STATES[%r] in tools/make_repo_visuals.py" % (where, line[:40], lang))


def short(s):
    """The part of a line before its first separator: what a card has room for."""
    return re.split(r":|;|\. |\.$|՝", s, maxsplit=1)[0].strip()


def read_readme(source=None):
    """{(picture, lang): {"title", "label", "date", "rows"}} from README.md. A row is (name, what, state word, tone):
    the bold name without a bracketed remark, the short form of the first sub-line, and the state from the last line."""
    lines = (source if source is not None else README.read_bytes().decode("utf-8")).split("\n")
    found, dates = {}, {}
    for i, line in enumerate(lines):
        m = PICTURE.search(line)
        if not m:
            continue
        key, lang, label = m.groups()
        where = "%s (%s)" % (key, lang)
        head = next((lines[j][4:].strip() for j in range(i - 1, -1, -1) if lines[j].startswith("### ")), None)
        if head is None:
            sys.exit("README.md, %s: no ### heading above the picture" % where)
        if lang not in dates:                                  # the date is in the paragraph above the first picture
            d = next((DATE.search(lines[j]) for j in range(i - 1, -1, -1) if DATE.search(lines[j]) and not lines[j].startswith(("#", "-", " "))), None)
            if d is None:
                sys.exit("README.md, %s: no date (dd.mm.yyyy) in the text above the first picture" % where)
            dates[lang] = d.group(1)
        rows, j = [], i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        while j < len(lines) and ITEM.match(lines[j]):
            name, inline = ITEM.match(lines[j]).groups()
            subs, j = [], j + 1
            while j < len(lines) and SUB.match(lines[j]):
                subs.append(SUB.match(lines[j]).group(1))
                j += 1
            said = inline if inline else (subs[-1] if subs else "")
            word, tone = state_of(said, lang, "%s, %s" % (where, name))
            rows.append((re.sub(r"\s*\(.*\)$", "", name), short(subs[0]) if len(subs) > 1 else "", word, tone))
        if not rows:
            sys.exit("README.md, %s: no list under the picture" % where)
        found[(key, lang)] = {"title": head, "label": label, "rows": rows, "lang": lang}
    for c in found.values():
        c["foot"] = FOOT[c["lang"]] % dates[c["lang"]]
    missing = [(k, lang) for k in ("placement", "server", "phases", "sources") for lang in ("en", "hy") if (k, lang) not in found]
    if missing:
        sys.exit("README.md: no picture found for %s" % missing)
    return found


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


def placement(t, c):
    body = [text(28, 50, c["title"], 26, t["text"], 700), '<rect x="28" y="68" width="56" height="2" fill="%s"/>' % t["accent"]]
    y = 88
    for name, what, word, tone in c["rows"]:
        if width(name, 21) + width("● " + word, MIN_TEXT) > W - 76 - 12 or width(what, MIN_TEXT) > W - 76:
            sys.exit("too long for the narrow picture, shorten it in README.md: %s / %s" % (name, what))
        body += [box(20, y, W - 40, 78, t["surface2"], t["border"], 14), '<rect x="20" y="%d" width="4" height="46" fill="%s"/>' % (y + 16, t["accent"]),
                 text(40, y + 34, name, 21, t["text"], 700), text(40, y + 60, what, MIN_TEXT, t["text2"]), state(W - 36, y + 34, word, tone, t)]
        y += 88
    body.append(text(28, y + 20, c["foot"], MIN_TEXT, t["muted"]))
    return doc(W, y + 42, body, c["label"], t)


def placement_wide(t, c):
    zones = c["rows"]
    body = [text(28, 50, c["title"], 26, t["text"], 700), '<rect x="28" y="68" width="56" height="2" fill="%s"/>' % t["accent"]]
    spots, cw, y = cells(len(zones), columns([(z[0], 21) for z in zones] + [(z[1], MIN_TEXT) for z in zones]), 116)
    for (x, top), (name, what, word, tone) in zip(spots, zones):
        body += [box(x, top, cw, 116, t["surface2"], t["border"], 14), '<rect x="%.1f" y="%d" width="4" height="46" fill="%s"/>' % (x, top + 16, t["accent"]),
                 text(x + 20, top + 34, name, 21, t["text"], 700), text(x + 20, top + 60, what, MIN_TEXT, t["text2"]),
                 state(x + 20, top + 96, word, tone, t, "start")]
    body.append(text(28, y + 14, c["foot"], MIN_TEXT, t["muted"]))
    return doc(WIDE, y + 36, body, c["label"], t)


def listed(wide=False):
    def make(t, c):
        rows = [(name, word, tone) for name, _, word, tone in c["rows"]]
        return (rows_picture_wide if wide else rows_picture)(t, c["title"], c["label"], rows, c["foot"])
    return make


PICTURES = (("placement", "placement", placement), ("server", "server", listed()), ("phases", "phases", listed()), ("sources", "sources", listed()),
            ("placement-wide", "placement", placement_wide), ("server-wide", "server", listed(True)), ("phases-wide", "phases", listed(True)),
            ("sources-wide", "sources", listed(True)))


def diagrams():
    content = read_readme()
    return [("%s-%s-%s.svg" % (name, lang, theme), fn(t, content[(key, lang)]))
            for theme, t in THEMES.items() for lang in ("en", "hy") for name, key, fn in PICTURES]


def check():
    stale = [name for name, svg in diagrams() if not (OUT / name).exists() or (OUT / name).read_bytes() != svg.encode("utf-8")]
    if stale:
        sys.exit("README.md and its pictures differ; run python tools/make_repo_visuals.py and commit the result:\n  " + "\n  ".join(stale))
    print("%d diagrams match README.md" % len(diagrams()))


def main():
    if sys.argv[1:] == ["--check"]:
        return check()
    made = diagrams()                                  # first, so that a README the script cannot read deletes nothing
    for theme, t in THEMES.items():
        made += [("cover-%s.svg" % theme, cover(t)), ("cover-narrow-%s.svg" % theme, cover_narrow(t))]
    for name, svg in made:
        for banned in ("<script", "foreignObject", "@font-face", "href=", "url(http", "<image"):
            assert banned not in svg, (name, banned)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, svg in made:
        (OUT / name).write_bytes(svg.encode("utf-8"))
    print("%d files, %.0f KB in all" % (len(made), sum(len(s.encode("utf-8")) for _, s in made) / 1024))


if __name__ == "__main__":
    main()
