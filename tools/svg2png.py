"""Rasterise SVG files to PNG at a given width, transparent where the SVG is.

Usage: svg2png.py <out-dir> <width> <svg> [svg ...]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    out_dir = Path(sys.argv[1]).resolve()
    width = int(sys.argv[2])
    files = [Path(p).resolve() for p in sys.argv[3:]]
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for f in files:
            svg = f.read_text(encoding="utf-8")
            # keep the SVG's own aspect ratio
            import re
            m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
            vw, vh = (float(m.group(1)), float(m.group(2))) if m else (240.0, 240.0)
            h = round(width * vh / vw)
            svg = re.sub(r'width="\d+" height="\d+"', f'width="{width}" height="{h}"', svg, count=1)
            page = b.new_page(viewport={"width": width, "height": h}, device_scale_factor=1)
            page.set_content(
                f'<style>html,body{{margin:0;padding:0;background:transparent}}</style>{svg}')
            page.wait_for_timeout(250)
            dst = out_dir / (f.stem + ".png")
            page.screenshot(path=str(dst), omit_background=True)
            page.close()
            print("->", dst.name, f"{width}x{h}")
        b.close()


if __name__ == "__main__":
    main()
