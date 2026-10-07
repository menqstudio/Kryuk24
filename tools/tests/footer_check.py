"""Подвал и F5: раскладка на 4 ширинах, ссылки, «Наши работы» ведет к разделу страницы, «Наверх»,
/#raboty со страницы города ведет к тому же разделу, обновление страницы — всегда сверху."""
import json
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT

out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (360, 390, 768, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(900)
        r = {}
        foot = pg.locator("footer.foot")
        foot.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        foot.screenshot(path=str(SHOTS / f"footer_{w}.png"))
        r["layout"] = pg.evaluate(LAYOUT)
        r["links"] = pg.evaluate("""()=>[...document.querySelectorAll('footer.foot a, footer.foot button')].map(a=>[a.textContent.trim(),a.getAttribute('href')||'(button)',a.target||'',a.rel||''])""")
        # every in-page anchor points to an existing section
        r["anchors_ok"] = pg.evaluate("""()=>[...document.querySelectorAll('footer.foot a[href^="#"]')].every(a=>!!document.querySelector(a.getAttribute('href')))""")
        # «Тарифы» from the footer opens the tariff tab and scrolls to it
        pg.click("#tab-goroda"); pg.wait_for_timeout(100)
        pg.locator('footer.foot a[href="#cena"]').click(); pg.wait_for_timeout(600)
        r["tariffs"] = pg.evaluate("()=>[document.querySelector('#cena-tarify').hidden===false, Math.round(document.querySelector('#cena').getBoundingClientRect().top)]")
        # «Наши работы» from the footer scrolls to the section, below the fixed header
        pg.locator('footer.foot a[href="#raboty"]').click(); pg.wait_for_timeout(1500)
        r["works"] = pg.evaluate("()=>[Math.round(document.querySelector('#raboty').getBoundingClientRect().top),Math.round(document.querySelector('.hdr').getBoundingClientRect().bottom),document.querySelector('#work-viewer').open]")
        # «Наверх»
        pg.locator("footer.foot .foot__up").click(); pg.wait_for_timeout(2000)  # smooth scroll
        r["up_scrollY"] = pg.evaluate("Math.round(scrollY)")
        # F5 after scrolling with a hash in the address → top, hash removed
        pg.evaluate("location.hash='#voprosy'"); pg.wait_for_timeout(2000)
        before = pg.evaluate("Math.round(scrollY)")
        pg.reload(); pg.wait_for_timeout(1200)
        r["reload"] = {"before": before, "after": pg.evaluate("Math.round(scrollY)"), "hash": pg.evaluate("location.hash")}
        r["errors"] = errs
        out[w] = r; pg.close()
    # city page: footer layout + «Наши работы» → the section on the main page (the gallery stays closed)
    pg = b.new_page(viewport={"width": 390, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/evakuator-domodedovo/"); pg.wait_for_timeout(800)
    pg.locator("footer.foot").scroll_into_view_if_needed(); pg.locator("footer.foot").screenshot(path=str(SHOTS / "footer_city_390.png"))
    city_layout = pg.evaluate(LAYOUT)
    pg.locator('footer.foot a[href="/#raboty"]').click(); pg.wait_for_timeout(1500)
    out["city"] = {"layout": city_layout, "url": pg.url.replace(BASE, ""), "gallery_open": pg.evaluate("()=>document.querySelector('#work-viewer').open"), "errors": errs}
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
