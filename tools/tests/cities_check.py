"""Тарифная карточка: вкладки «Тарифы | Где работаем», города со ссылками, высота = форме."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (360, 390, 768, 1024, 1280, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(1000)
        r = {}
        card = pg.locator(".tariff-full")
        card.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        if w in (390, 1280): card.screenshot(path=str(SHOTS / f"cities_{w}_tarify.png"))
        pg.click("#tab-goroda"); pg.wait_for_timeout(250)
        r["state"] = pg.evaluate("()=>[document.querySelector('#cena-tarify').hidden,document.querySelector('#cena-goroda').hidden,document.activeElement.id]")
        r["rows"] = pg.evaluate("()=>[...document.querySelectorAll('#cena-goroda .pl__c')].map(l=>l.innerText.replace(/\\n/g,' | '))")
        r["align"] = pg.evaluate("()=>Math.round(document.querySelector('.tariff-full').getBoundingClientRect().bottom-document.querySelector('.request .route-preview').getBoundingClientRect().bottom)")
        r["layout"] = pg.evaluate(LAYOUT)
        if w in (390, 1280): card.screenshot(path=str(SHOTS / f"cities_{w}_goroda.png"))
        pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(150)
        r["arrow_back"] = pg.evaluate("()=>[document.querySelector('#cena-tarify').hidden,document.activeElement.id]")
        pg.click("#tab-goroda"); pg.wait_for_timeout(150)
        # menu «Тарифы» resets to the tariff tab
        link = pg.locator('a[href="#cena"]:visible').first
        if link.count():
            link.click(); pg.wait_for_timeout(400)
            r["menu_reset"] = pg.evaluate("()=>document.querySelector('#cena-tarify').hidden===false")
        pg.click("#tab-goroda"); pg.wait_for_timeout(150)
        pg.locator("#cena-goroda .pl__c--link").nth(0).click(position={"x": 30, "y": 20}); pg.wait_for_load_state(); pg.wait_for_timeout(300)
        r["nav_to"] = pg.url.replace(BASE, "")
        r["errors"] = errs
        out[w] = r; pg.close()
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
