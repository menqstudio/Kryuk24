"""Страницы городов и услуг: заголовок, ошибки JS, 404 ресурсов, горизонтальный скролл."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT
PAGES = ["evakuator-domodedovo","evakuator-khimki","evakuator-balashikha","evakuator-lyubertsy","evakuator-podolsk","manipulyator","perevozka-spetstekhniki"]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for slug in PAGES:
        for name, vp in (("desk", {"width": 1440, "height": 900}), ("mob", {"width": 390, "height": 844})):
            pg = b.new_page(viewport=vp); errs=[]; bad=[]
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("response", lambda r: bad.append(r.url) if r.status >= 400 else None)
            pg.goto(f"{BASE}/{slug}/"); pg.wait_for_timeout(1200)
            ov = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            # icons inside buttons keep their size (an unsized svg once filled the whole WhatsApp button)
            big = pg.evaluate("[...document.querySelectorAll('.btn svg')].filter(s=>s.getBoundingClientRect().width>32).length")
            print(slug, name, "| title:", pg.title()[:70], "| errors:", errs, "| 404:", bad, "| h-overflow:", ov, "| oversized icons:", big)
            if slug == "evakuator-khimki" or (slug == "manipulyator" and name == "desk"):
                pg.screenshot(path=str(SHOTS / f"seo_{slug}_{name}.png"), full_page=True)
            pg.close()
    b.close()
