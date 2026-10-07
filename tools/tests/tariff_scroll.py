"""Колесо мыши над тарифом: на десктопе листается страница, на телефоне сначала тариф, потом страница."""
import sys
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT
with sync_playwright() as pw:
    b=pw.chromium.launch()
    for w,h in ((1440,900),(390,844)):
        pg=b.new_page(viewport={"width":w,"height":h}); pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
        pl=pg.locator("#cena-tarify"); pl.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        info=pg.evaluate("""()=>{const p=document.querySelector('#cena-tarify'),c=getComputedStyle(p);return {h:p.clientHeight,sh:p.scrollHeight,ov:c.overflowY,osb:c.overscrollBehaviorY}}""")
        box=pl.bounding_box(); pg.mouse.move(box["x"]+box["width"]/2, box["y"]+min(150,box["height"]/2))
        y0=pg.evaluate("scrollY"); s0=pg.evaluate("document.querySelector('#cena-tarify').scrollTop")
        for _ in range(6): pg.mouse.wheel(0,250); pg.wait_for_timeout(120)
        pg.wait_for_timeout(400)
        y1=pg.evaluate("scrollY"); s1=pg.evaluate("document.querySelector('#cena-tarify').scrollTop")
        print(w, info, "| page scrolled:", y1-y0, "| tariff scrolled:", s1-s0)
        pg.close()
    b.close()
