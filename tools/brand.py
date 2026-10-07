"""Фирменный стиль КРЮК24 — один источник для всех генераторов (вывески, локапы, QR, WhatsApp, видео-гид).

Логотип (финальный, 04.10.2026, утвержден Гевором): крюк + «КРЮК24» / «ЭВАКУАТОР+».
  • крюк — Orange #EF5B00, вектор из brand/00_hook_master (tools/trace_hook.py);
  • «КРЮК24» — Roboto Condensed 700, белый на темном / Ink на светлом;
  • «ЭВАКУАТОР» — Golos Text 400, на темном #F18A4B (как в шапке сайта), на светлом Orange; ширина строки = ширине «КРЮК24»;
  • «+» — Golos Text 700, белый на темном / Ink на светлом.
Пропорции — как в шапке сайта (крюк 44 px, «КРЮК24» 28 px, «ЭВАКУАТОР+» 12 px, зазор 7 px).

Шрифты — те же файлы, что на сайте (site/assets/fonts, SIL OFL). Они разбиты на кириллицу и латиницу,
поэтому измерение и растровый текст идут по кускам: каждый символ — своим файлом.
"""
import base64
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "site" / "assets" / "fonts"
HOOK_FILE = ROOT / "brand" / "00_hook_master" / "hook_path.txt"

INK = "#13233A"  # Navy, as on the site since v32 (Gev, 06.10.2026); was #111111
ORANGE = "#EF5B00"
ORANGE_SOFT = "#F18A4B"  # «ЭВАКУАТОР» on dark backgrounds, as in the site header
WHITE = "#FFFFFF"
GREY = "#9AA3A9"

PHONE = "+7 985 893-06-06"
SITE = "kryuk24.ru"
ADDRESS = "ул. Бехтерева, 41 к1"  # as Yandex names the building (Gev, 06.10.2026)

DISPLAY = "'Roboto Condensed','Arial Narrow',sans-serif"
TEXT = "'Golos Text','Segoe UI',sans-serif"
FILES = {  # (family, weight) -> stem of the woff2 pair
    ("display", 700): "robotocond-700",
    ("text", 400): "golos-400",
    ("text", 500): "golos-500",
    ("text", 700): "golos-700",
}
FAMILY_CSS = {"display": DISPLAY, "text": TEXT}

_lines = HOOK_FILE.read_text(encoding="utf-8").split("\n")
HOOK_W, HOOK_H = (float(v) for v in _lines[0].split())
HOOK_D = _lines[1]


# ---------------------------------------------------------------- fonts
# Glyph coverage of the site font subsets (= their unicode-range in site/assets/fonts.css).
# Anything else (e.g. «₽») falls back to the same system fonts the browser uses on the site.
def _script(ch):
    o = ord(ch)
    if 0x400 <= o <= 0x45F or o in (0x490, 0x491, 0x4B0, 0x4B1, 0x2116, 0x301):
        return "cyrillic"
    if o <= 0xFF or 0x2000 <= o <= 0x206F or o in (0x131, 0x152, 0x153, 0x20AC, 0x2122, 0x2191, 0x2193, 0x2212, 0x2215):
        return "latin"
    return "fallback"


WIN = Path(r"C:\Windows\Fonts")
FALLBACK = {("display", 700): ["ARIALNB.TTF", "arialbd.ttf"], ("text", 400): ["segoeui.ttf", "arial.ttf"],
            ("text", 500): ["seguisb.ttf", "segoeui.ttf"], ("text", 700): ["segoeuib.ttf", "arialbd.ttf"]}


@lru_cache(maxsize=None)
def _pil(family, weight, script, size=1000):
    from PIL import ImageFont      # loaded only when a font is measured or drawn
    if script == "fallback":
        for name in FALLBACK[(family, weight)]:
            if (WIN / name).exists():
                return ImageFont.truetype(str(WIN / name), size)
    return ImageFont.truetype(str(FONTS / f"{FILES[(family, weight)]}-{script}.woff2"), size)


def _runs(s):
    out, cur, buf = [], None, ""
    for ch in s:
        sc = _script(ch)
        if sc != cur and buf:
            out.append((cur, buf)); buf = ""
        cur = sc; buf += ch
    if buf:
        out.append((cur, buf))
    return out


def measure(s, size, family="display", weight=700, ls=0.0):
    """Advance width of `s` at `size` (same units as size), with letter-spacing ls between glyphs."""
    w = sum(_pil(family, weight, sc).getlength(run) for sc, run in _runs(s)) * size / 1000
    return w + ls * max(0, len(s) - 1)


def fit(s, width, family="display", weight=700, ls_ratio=0.0):
    """Font size at which `s` is exactly `width` wide (letter-spacing = ls_ratio * size)."""
    return width / (measure(s, 1, family, weight) + ls_ratio * max(0, len(s) - 1))


def metrics(family="display", weight=700):
    """(ascent, descent, cap height) per 1 unit of font size."""
    f = _pil(family, weight, "cyrillic")
    asc, desc = f.getmetrics()
    cap = -f.getbbox("К", anchor="ls")[1]
    return asc / 1000, desc / 1000, cap / 1000


def draw_text(draw, xy, s, size, family="display", weight=700, fill=WHITE, ls=0.0, anchor="ls"):
    """Pillow text in the site fonts. anchor = horizontal (l/m/r) + vertical:
    s — baseline, t — top of capitals, m — middle of capitals."""
    x, y = xy
    total = measure(s, size, family, weight, ls)
    cap = metrics(family, weight)[2] * size
    if anchor[1] == "t":
        y += cap
    elif anchor[1] == "m":
        y += cap / 2
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for sc, run in _runs(s):
        f = _pil(family, weight, sc, max(1, round(size)))
        for ch in run:
            draw.text((x, y), ch, font=f, fill=fill, anchor="ls")
            x += f.getlength(ch) + ls
    return total


@lru_cache(maxsize=None)
def font_face_css():
    """@font-face with the woff2 embedded as data: URIs — makes SVG files self-contained."""
    css = []
    for (family, weight), stem in FILES.items():
        name = "Roboto Condensed" if family == "display" else "Golos Text"
        for script, rng in (("cyrillic", "U+0400-04FF,U+2116"), ("latin", "U+0000-00FF,U+2000-206F,U+20BD,U+2191,U+2192,U+2212")):
            b64 = base64.b64encode((FONTS / f"{stem}-{script}.woff2").read_bytes()).decode()
            css.append(f"@font-face{{font-family:'{name}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{rng}}}")
    return "".join(css)


def text(x, y, s, size, family="display", weight=700, fill=WHITE, anchor="start", ls=0.0, extra=""):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FAMILY_CSS[family]}" font-size="{size:.2f}" '
            f'font-weight="{weight}" letter-spacing="{ls:.3f}" fill="{fill}" text-anchor="{anchor}"{extra}>{s}</text>')


def rect(x, y, w, h, fill):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}"/>'


def svg_doc(w, h, body, bg=INK, label="", unit="mm"):
    bgr = rect(0, 0, w, h, bg) if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}{unit}" height="{h}{unit}" '
            f'role="img" aria-label="{label}"><style>{font_face_css()}</style>{bgr}{"".join(body)}</svg>')


# ---------------------------------------------------------------- logo
def hook(x, y, h, color=ORANGE):
    """The hook with its top-left at (x, y), `h` high. Returns (svg, width)."""
    k = h / HOOK_H
    return (f'<path transform="translate({x:.3f},{y:.3f}) scale({k:.6f})" fill="{color}" '
            f'fill-rule="evenodd" d="{HOOK_D}"/>', HOOK_W * k)


def lockup(x, y, h, on="dark"):
    """Final logo: hook + «КРЮК24» / «ЭВАКУАТОР+», top-left at (x, y), hook `h` high.
    on='dark' — white name and plus; on='light' — ink name and plus. Returns (svg, width)."""
    main = WHITE if on == "dark" else INK
    sub_c = ORANGE_SOFT if on == "dark" else ORANGE
    k = h / 44.0                                   # site header: hook 44
    hk, hw = hook(x, y, h)
    tx = x + hw + 7 * k
    name_size = 28 * k                             # «КРЮК24» 28, line-height 1
    asc, desc, _ = metrics("display", 700)
    name_base = y + (name_size - (asc + desc) * name_size) / 2 + asc * name_size
    name_w = measure("КРЮК24", name_size, "display", 700)
    sub_size = 12 * k                              # «ЭВАКУАТОР+» 12, line-height 1.1, margin-top 3
    a2, d2, _ = metrics("text", 400)
    lh = 1.1 * sub_size
    sub_base = y + name_size + 3 * k + (lh - (a2 + d2) * sub_size) / 2 + a2 * sub_size
    glyphs = measure("ЭВАКУАТОР", sub_size, "text", 400) + measure("+", sub_size, "text", 700)
    ls = (name_w - glyphs) / 9                     # spread the 10 glyphs to the width of «КРЮК24»
    out = [hk,
           text(tx, name_base, "КРЮК24", name_size, "display", 700, main),
           f'<text x="{tx:.2f}" y="{sub_base:.2f}" font-family="{TEXT}" font-size="{sub_size:.2f}" font-weight="400" '
           f'letter-spacing="{ls:.3f}" fill="{sub_c}">ЭВАКУАТОР<tspan font-weight="700" fill="{main}">+</tspan></text>']
    return "".join(out), (tx - x) + name_w


def lockup_size(h):
    """(width, height) of lockup() for hook height h."""
    k = h / 44.0
    return HOOK_W * h / HOOK_H + 7 * k + measure("КРЮК24", 28 * k, "display", 700), h


def lockup_vertical(cx, y, w, on="dark"):
    """Stacked logo for square formats: hook centred on top, «КРЮК24» / «ЭВАКУАТОР+» below, all `w` wide text."""
    main = WHITE if on == "dark" else INK
    sub_c = ORANGE_SOFT if on == "dark" else ORANGE
    name_size = fit("КРЮК24", w, "display", 700)
    hook_h = name_size * 2.1
    hk, hw = hook(cx - HOOK_W * hook_h / HOOK_H / 2, y, hook_h)
    asc, desc, cap = metrics("display", 700)
    name_base = y + hook_h + name_size * 0.35 + cap * name_size
    sub_size = name_size * 12 / 28
    glyphs = measure("ЭВАКУАТОР", sub_size, "text", 400) + measure("+", sub_size, "text", 700)
    ls = (w - glyphs) / 9
    a2, d2, cap2 = metrics("text", 400)
    sub_base = name_base + name_size * 0.18 + cap2 * sub_size + sub_size * 0.2
    out = [hk,
           text(cx - w / 2, name_base, "КРЮК24", name_size, "display", 700, main),
           f'<text x="{cx - w / 2:.2f}" y="{sub_base:.2f}" font-family="{TEXT}" font-size="{sub_size:.2f}" font-weight="400" '
           f'letter-spacing="{ls:.3f}" fill="{sub_c}">ЭВАКУАТОР<tspan font-weight="700" fill="{main}">+</tspan></text>']
    return "".join(out), sub_base + desc * sub_size - y


# ---------------------------------------------------------------- render (headless Chromium via Playwright)
def render(svg_text, png_path=None, pdf_path=None, png_width=1600, transparent=False):
    """SVG → PNG (png_width px wide) and/or 1:1 PDF (vector, fonts embedded)."""
    from playwright.sync_api import sync_playwright
    import re
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_text)
    vw, vh = float(m.group(1)), float(m.group(2))
    unit = re.search(r'width="[\d.]+(mm|px)?"', svg_text).group(1) or "px"
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        if png_path:
            ph = round(png_width * vh / vw)
            pg = b.new_page(viewport={"width": png_width, "height": ph})
            body = svg_text.replace(f'width="{vw:g}{unit}" height="{vh:g}{unit}"', f'width="{png_width}" height="{ph}"', 1)
            pg.set_content(f'<html><body style="margin:0;background:transparent">{body}</body></html>')
            pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
            Path(png_path).parent.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(png_path), omit_background=transparent, clip={"x": 0, "y": 0, "width": png_width, "height": ph})
            pg.close()
        if pdf_path:
            pg = b.new_page()
            pg.set_content(f'<html><head><style>@page{{size:{vw}{unit} {vh}{unit};margin:0}}html,body{{margin:0}}svg{{display:block}}</style></head><body>{svg_text}</body></html>')
            pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
            pg.pdf(path=str(pdf_path), width=f"{vw}{unit}", height=f"{vh}{unit}", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            pg.close()
        b.close()


def lockup_img(height=None, width=None, vertical=False, on="dark"):
    """The logo as a transparent Pillow image, trimmed to its ink and scaled to `height` or `width` px.
    Uses the master PNGs from brand/02_lockups (made by tools/make_brand.py)."""
    from PIL import Image
    name = ("lockup_vertical_transparent_" if vertical else "lockup_horizontal_transparent_") + on
    im = Image.open(ROOT / "brand" / "02_lockups" / "png" / f"{name}.png").convert("RGBA")
    im = im.crop(im.getbbox())
    k = (height / im.height) if height else (width / im.width)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
