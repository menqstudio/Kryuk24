"""kryuk-logo-dark.webp: the official lockup for dark grounds, for the operator page header.

The image is brand/02_lockups/lockup_horizontal_transparent_dark.svg (the approved logo, fonts embedded) cropped to
its lockup box and rendered at 2x a 44 px hook (260 x 88), transparent, lossless. Nothing is redrawn.

    python runtime/wip/dashboard_colours/make_logo.py
"""
import base64
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
SVG = ROOT / "brand" / "02_lockups" / "lockup_horizontal_transparent_dark.svg"
OUT = Path(__file__).resolve().parent / "kryuk-logo-dark.webp"
H = 88          # 2x the site header's 44 px hook; the file draws the hook 120 px high at (40, 40), lockup 355 wide

uri = "data:image/svg+xml;base64," + base64.b64encode(SVG.read_bytes()).decode()
k = H / 120
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 800, "height": 300}, device_scale_factor=1)
    page.set_content("<html><body style='margin:0;background:transparent'><img src='%s' style='display:block;width:%.3fpx;height:%.3fpx;margin:%.3fpx 0 0 %.3fpx'></body></html>"
                     % (uri, 435 * k, 200 * k, -40 * k, -40 * k))
    page.wait_for_function("document.images[0].complete")
    page.wait_for_timeout(300)
    png = page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 355 * k, "height": H})
    browser.close()
buf = io.BytesIO()
Image.open(io.BytesIO(png)).save(buf, "WEBP", lossless=True)
OUT.write_bytes(buf.getvalue())
print("written", OUT.name, len(buf.getvalue()), "bytes")
