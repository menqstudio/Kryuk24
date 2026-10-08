"""Полный логотип «крюк + КРЮК24 / ЭВАКУАТОР» в PNG 540×180.

Знак берется из site/assets/mark-orange.svg, шрифты — из site/assets/fonts.css.
Нужен локальный сервер site на 127.0.0.1:8765 (python -m http.server 8765 в папке site).
Выход: brand/00_hook_master/logo-transparent.png (прозрачный фон, для макетов).
site/assets/logo-dark.png теперь делает tools/make_site_logo.py из официального файла логотипа (08.10.2026).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = {"logo-transparent.png": ROOT / "brand" / "00_hook_master" / "logo-transparent.png"}
HTML = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/assets/fonts.css">
<style>html,body{margin:0;background:%s}
.l{width:540px;height:180px;display:flex;align-items:center;gap:26px;padding:0 24px;box-sizing:border-box}
.l img{height:150px;width:auto}
.t{display:flex;flex-direction:column;justify-content:center}
.n{font:700 104px/0.92 'Roboto Condensed','Arial Narrow',sans-serif;color:#fff;letter-spacing:.005em}
.s{font:400 40px/1 'Golos Text','Golos',sans-serif;color:#EF5B00;letter-spacing:.27em;margin-top:18px;margin-left:4px}
.s b{color:#fff;font-weight:700}</style></head>
<body><div class="l"><img src="/assets/mark-orange.svg?v=18"><div class="t"><div class="n">КРЮК24</div><div class="s">ЭВАКУАТОР<b>+</b></div></div></div></body></html>"""

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 540, "height": 180}, device_scale_factor=1)
    for bg, name, transp in (("transparent", "logo-transparent.png", True),):
        pg.unroute_all()
        html = HTML.replace("%s", bg)
        # route handler gets (route, request): keep html as a default arg after them, or the request overwrites it
        pg.route("**/__lockup*", lambda r, req=None, html=html: r.fulfill(content_type="text/html; charset=utf-8", body=html))
        pg.goto("http://127.0.0.1:8765/__lockup?" + name); pg.wait_for_timeout(800)
        print(name, pg.evaluate("[getComputedStyle(document.body).backgroundColor, document.fonts.check('700 104px \"Roboto Condensed\"')]"))
        pg.screenshot(path=str(OUT[name]), omit_background=transp, clip={"x": 0, "y": 0, "width": 540, "height": 180})
    b.close()
