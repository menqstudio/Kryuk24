"""site/assets/logo-dark.png (540x180), the logo search engines show (schema.org "logo" on the main page).

The image is the official lockup file brand/02_lockups/lockup_horizontal_on_ink.svg (navy #13233A ground, the
approved logo of 04.10.2026) placed unchanged in the middle of a navy 540x180 canvas. Nothing of the logo is
redrawn. Fonts are embedded in the SVG, so no server is needed.

    python tools/make_site_logo.py
"""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "brand" / "02_lockups" / "lockup_horizontal_on_ink.svg"
OUT = ROOT / "site" / "assets" / "logo-dark.png"
HTML = ("<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#13233A}"
        "div{width:540px;height:180px;display:flex;align-items:center;justify-content:center}img{height:180px;width:auto;display:block}"
        "</style></head><body><div><img src='%s'></div></body></html>")

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 540, "height": 180}, device_scale_factor=1)
    page.set_content(HTML % ("data:image/svg+xml;base64," + base64.b64encode(SVG.read_bytes()).decode()))
    page.wait_for_function("document.images[0].complete && document.images[0].naturalWidth > 0")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT), clip={"x": 0, "y": 0, "width": 540, "height": 180})
    browser.close()
print("written", OUT.relative_to(ROOT))
