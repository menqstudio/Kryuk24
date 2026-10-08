"""logo-light.webp of the portal: the official lockup for light grounds.

logo-dark.webp is not made here: it is the operator page's own file, runtime/wip/dashboard_colours/kryuk-logo-dark.webp,
copied byte for byte (checked by design/scripts/check_shared_design.py), so both pages show one logo file.

It is brand/02_lockups/lockup_horizontal_transparent_light.svg (the approved logo, fonts embedded) cropped to
its lockup box and rendered at 2x a 44 px hook (260 x 88), transparent, lossless. Nothing is redrawn. The same
method and numbers as runtime/wip/dashboard_colours/make_logo.py, which makes the operator page's dark logo.

    python runtime/armen_portal/deploy/make_logo.py
"""
import base64
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
H = 88  # the file draws the hook 120 px high at (40, 40), lockup 355 wide
k = H / 120

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for theme in ("light",):
        svg = ROOT / "brand" / "02_lockups" / ("lockup_horizontal_transparent_%s.svg" % theme)
        uri = "data:image/svg+xml;base64," + base64.b64encode(svg.read_bytes()).decode()
        page = browser.new_page(viewport={"width": 800, "height": 300}, device_scale_factor=1)
        page.set_content("<html><body style='margin:0;background:transparent'><img src='%s' style='display:block;width:%.3fpx;height:%.3fpx;margin:%.3fpx 0 0 %.3fpx'></body></html>"
                         % (uri, 435 * k, 200 * k, -40 * k, -40 * k))
        page.wait_for_function("document.images[0].complete")
        page.wait_for_timeout(300)
        png = page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 355 * k, "height": H})
        page.close()
        buf = io.BytesIO()
        Image.open(io.BytesIO(png)).save(buf, "WEBP", lossless=True)
        (OUT / ("logo-%s.webp" % theme)).write_bytes(buf.getvalue())
        print("written logo-%s.webp" % theme, len(buf.getvalue()), "bytes")
    browser.close()
