"""Живой маршрут: подсказки адресов (Photon), км (OSRM), цена и карта. Химки → Дмитровское ш. 100 ≈ 11 км / 5 100 ₽."""
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (1440, 390):
        pg = b.new_page(viewport={"width": w, "height": 900}, locale="ru-RU"); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(1000)
        pg.locator(".vehicle-choice").first.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(300)  # clear of the fixed header and call bar
        pg.locator("input[name=vehicle][value=car]").check(force=True)
        pg.evaluate("""()=>{const s=document.querySelector('[data-class]');s.value='4000';s.dispatchEvent(new Event('change',{bubbles:true}))}""")
        for sel, q in (("[data-from]", "Химки"), ("[data-to]", "Москва, Дмитровское шоссе 100")):
            pg.locator(sel).scroll_into_view_if_needed()
            pg.locator(sel).press_sequentially(q, delay=50)
            opts = pg.locator(sel).locator("xpath=ancestor::*[contains(@class,'field')][1]").locator(".address-results button").filter(visible=True)
            try:  # Photon answers in 3-13 s from here, a fixed short pause reported "0 suggestions" on a working site
                opts.first.wait_for(state="visible", timeout=20000)
            except Exception:
                pass
            pg.wait_for_timeout(500)
            n = opts.count()
            print(w, sel, "suggestions:", n, [t[:45] for t in opts.all_inner_texts()[:3]])
            if w == 390 and sel == "[data-to]":
                pg.screenshot(path=str(SHOTS / "after_390_suggest.png"))
            if n: opts.first.click(); pg.wait_for_timeout(500)
        pg.wait_for_timeout(6000)
        href = pg.get_attribute("[data-request-wa]", "href")
        print(w, "km:", pg.input_value("[data-km]"), "| note:", pg.inner_text("#km-note")[:80], "| price:", pg.inner_text("[data-quote]"))
        print(w, "frame:", urllib.parse.unquote(pg.get_attribute("[data-route-frame]", "src"))[:120])
        print(w, "msg:", urllib.parse.unquote(href.split("text=")[1]).replace("\n", " / ")[:420] if "text=" in href else href)
        print(w, "errors:", errs)
        if w == 1440:
            pg.locator(".request").screenshot(path=str(SHOTS / "after_1440_request_route.png"))
        pg.close()
    b.close()
