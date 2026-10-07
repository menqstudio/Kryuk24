"""Build the owner report: reports/report_<day>.src.html -> one standalone HTML file.

Usage: make_report.py 2026-10-05 [artifact-body-out]

The result needs no network and no JavaScript, because it is sent as a file over WhatsApp
and some phone viewers open HTML with scripts and remote resources switched off:
- {{KIA}} and {{IMG:file.jpg}} become data URIs;
- {{FONTS}} becomes @font-face rules with the site's own fonts embedded;
- charts and lists that the page script draws are rendered once here (phone width) and
  written into the markup; with scripts on, the page redraws them at the real width.
The optional second argument writes the same page without the html/head/body skeleton.
"""
import base64
import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reports"  # the reports themselves are kept on Drive (docs/media-index.md)
FONTS = ROOT / "site" / "assets" / "fonts"
CYR = "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"
LAT = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, "
       "U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")
# Script-drawn containers to pre-render: ids of elements the page script fills.
DRAWN = ["legend", "chart", "tbl", "share", "sharelist", "calls", "queries", "sources"]


def uri(path, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def fonts_css():
    faces = [("Golos Text", "400 700", "golos-400-cyrillic.woff2", CYR), ("Golos Text", "400 700", "golos-400-latin.woff2", LAT),
             ("Roboto Condensed", "600 700", "robotocond-700-cyrillic.woff2", CYR), ("Roboto Condensed", "600 700", "robotocond-700-latin.woff2", LAT)]
    return "\n".join(
        f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
        f"src:url({uri(FONTS / f, 'font/woff2')}) format('woff2');unicode-range:{rng}}}" for fam, w, f, rng in faces)


def wrap(body):
    cut = body.index('<div class="band">')
    return ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="robots" content="noindex">\n' + body[:cut] + '</head>\n<body>\n' + body[cut:] + '\n</body>\n</html>\n')


def prerender(body):
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.html"
        f.write_text(wrap(body), encoding="utf-8", newline="")
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 400, "height": 800})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(800)
            drawn = {i: pg.evaluate("i=>document.getElementById(i).innerHTML", i) for i in DRAWN}
            b.close()
    for i, html in drawn.items():
        m = re.search(r'(<div [^>]*\bid="%s"[^>]*>)(</div>)' % i, body)
        assert m and html, i
        body = body[:m.end(1)] + html + body[m.start(2):]
    return body


def main():
    day = sys.argv[1]
    src = (REP / f"report_{day}.src.html").read_text(encoding="utf-8")
    img = REP / f"img_{day}"
    body = src.replace("{{KIA}}", uri(ROOT / "site/assets/img/rabota-19-miniven-kia.jpg"))
    body = re.sub(r"\{\{IMG:([\w.-]+)\}\}", lambda m: uri(img / m.group(1)), body)
    body = body.replace("{{FONTS}}", fonts_css())
    body = prerender(body)
    out = REP / f"KRYUK24_otchet_{day}.html"
    out.write_text(wrap(body), encoding="utf-8", newline="")
    print(out.name, round(out.stat().st_size / 1024), "KB")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(body, encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
