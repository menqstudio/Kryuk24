"""Screenshot a local HTML file with headless Chromium.

Usage: shot.py <html-path> <out.png> [width]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": width, "height": 900}, device_scale_factor=2)
        p.goto(src.as_uri())
        p.wait_for_timeout(700)
        p.screenshot(path=str(out), full_page=True)
        b.close()
    print("saved", out)


if __name__ == "__main__":
    main()
