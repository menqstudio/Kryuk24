"""Header и первый экран: высоты, одна ось у логотипа/меню/телефона, меню-гамбургер на узких экранах,
переходы к разделам с учетом закрепленного header («Наши работы» — раздел страницы), галерея с нужного кадра, звонок,
без наложений и горизонтального скролла."""
import json
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT

SIZES = ((360, 780), (390, 844), (768, 1024), (1280, 800), (1440, 900))
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h in SIZES:
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(1000)
        r = {}
        r["sizes"] = pg.evaluate("""()=>{const q=s=>document.querySelector(s),R=s=>q(s).getBoundingClientRect(),c=s=>{const b=R(s);return Math.round(b.top+b.height/2)};
          const navShown=getComputedStyle(q('.nav')).display!=='none';
          return {hdr:Math.round(R('.hdr').height),hero:Math.round(R('#top').height),nextSectionTop:Math.round(R('.service-strip').top),
                  axis:{logo:c('.logo'),nav:navShown?c('.nav'):null,call:c('.hdr__call'),toggle:getComputedStyle(q('.nav-toggle')).display!=='none'?c('.nav-toggle'):null},
                  navFont:getComputedStyle(q('.nav a')).fontSize+' '+getComputedStyle(q('.nav a')).fontWeight}}""")
        r["layout_top"] = pg.evaluate(LAYOUT)
        pg.screenshot(path=str(SHOTS / f"header_{w}.png"))
        menu = pg.evaluate("getComputedStyle(document.querySelector('.nav-toggle')).display!=='none'")
        if menu:
            pg.click(".nav-toggle"); pg.wait_for_timeout(250)
            r["menu_open"] = pg.evaluate("()=>[document.querySelector('.hdr').classList.contains('is-menu'),document.querySelector('.nav-toggle').getAttribute('aria-expanded'),getComputedStyle(document.querySelector('.nav a')).fontSize]")
            r["layout_menu"] = pg.evaluate(LAYOUT)
            pg.screenshot(path=str(SHOTS / f"header_{w}_menu.png"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            r["menu_esc"] = pg.evaluate("()=>!document.querySelector('.hdr').classList.contains('is-menu')")
        # jump to each section from the menu: section top must sit below the fixed header
        jumps = {}
        for href in ("#zayavka", "#raboty", "#voprosy", "#cena"):
            if menu:
                pg.click(".nav-toggle"); pg.wait_for_timeout(200)
            pg.locator(f'.nav a[href="{href}"]').click(); pg.wait_for_timeout(1500)
            jumps[href] = pg.evaluate(f"()=>[Math.round(document.querySelector('{href}').getBoundingClientRect().top),Math.round(document.querySelector('.hdr').getBoundingClientRect().bottom),document.querySelector('.hdr').classList.contains('is-menu')]")
        r["jumps"] = jumps
        r["scrolled_bg"] = pg.evaluate("getComputedStyle(document.querySelector('.hdr')).backgroundColor")
        r["is_on"] = pg.evaluate("[...document.querySelectorAll('.nav a.is-on')].map(a=>a.textContent)")
        # gallery: «Все работы» opens it, a photo opens it on that frame
        pg.locator(".proof__all").click(); pg.wait_for_timeout(400)
        r["gallery"] = pg.evaluate("()=>document.querySelector('#work-viewer').open")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        tile = pg.locator(".proof__tile").nth(2); frame = tile.get_attribute("data-frame"); label = tile.inner_text().strip()
        tile.click(); pg.wait_for_timeout(400)
        r["gallery_frame"] = pg.evaluate("()=>[document.querySelector('#work-viewer figcaption').textContent,document.querySelector('[data-work-count]').textContent]") + [label, int(frame) + 1]
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        r["call_href"] = pg.get_attribute(".hdr__call", "href")
        r["hero_call_href"] = pg.get_attribute(".hero-call", "href")
        r["errors"] = errs
        out[w] = r; pg.close()
    # city page header
    pg = b.new_page(viewport={"width": 390, "height": 844}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/evakuator-domodedovo/"); pg.wait_for_timeout(800)
    pg.click(".nav-toggle"); pg.wait_for_timeout(250)
    pg.screenshot(path=str(SHOTS / "header_city_390_menu.png"))
    city = {"menu": pg.evaluate("document.querySelector('.hdr').classList.contains('is-menu')"), "layout": pg.evaluate(LAYOUT)}
    pg.locator('.nav a[href="/#raboty"]').click(); pg.wait_for_timeout(1500)
    # «Наши работы» from a city page → the section on the main page (the gallery stays closed)
    city["works"] = [pg.url.replace(BASE, ""), pg.evaluate("document.querySelector('#work-viewer').open"),
                     pg.evaluate("[Math.round(document.querySelector('#raboty').getBoundingClientRect().top),Math.round(document.querySelector('.hdr').getBoundingClientRect().bottom)]")]
    city["errors"] = errs
    out["city"] = city
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
