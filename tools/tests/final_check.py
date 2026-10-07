"""Главная: 5 ширин, все виды транспорта, сообщение WhatsApp, выпадающие списки, окно записи, галерея, ссылки."""
import json
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT



def wa_text(href):
    return urllib.parse.unquote(href.split("text=")[1]) if href and "text=" in href else ""

res = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (360, 390, 768, 1024, 1440):
        ctx = b.new_context(viewport={"width": w, "height": 900}, locale="ru-RU")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
        r = {"initial": pg.evaluate(LAYOUT)}
        # disabled fields before any choice
        r["disabled_initial"] = pg.evaluate("()=>[...document.querySelectorAll('.request-fields select,.request-fields .choice-trigger,.request-fields input[data-model]')].map(e=>(e.dataset.class!==undefined?'class':e.name||e.className)+':'+e.disabled)")
        # every transport
        tr = {}
        for v in ("car", "moto", "commercial", "special"):
            pg.evaluate(f"()=>document.querySelector('input[name=vehicle][value={v}]').click()"); pg.wait_for_timeout(250)
            tr[v] = pg.evaluate("""()=>({cls:document.querySelector('[data-class]').disabled,model:document.querySelector('[data-model]').disabled,
              wheels:document.querySelector('[data-wheels]').disabled,blocked:document.querySelector('[data-blocked]').disabled,
              price:document.querySelector('[data-quote]').textContent})""")
            tr[v]["layout"] = pg.evaluate(LAYOUT)
        r["transports"] = tr
        # car + class + situation + wheels Нет + blocked 2 → message
        pg.evaluate("()=>{const i=document.querySelector('input[name=vehicle][value=car]');if(!i.checked)i.click()}")
        pg.evaluate("""()=>{const set=(s,v)=>{const e=document.querySelector(s);e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}))};
          set('[data-class]','4500');set('[data-situation]','Не заводится / не едет');set('[data-wheels]','Нет');set('[data-blocked]','2');}""")
        pg.wait_for_timeout(300)
        r["car_price"] = pg.inner_text("[data-quote]")
        r["car_msg"] = wa_text(pg.get_attribute("[data-request-wa]", "href"))
        r["tg_msg_same"] = wa_text(pg.get_attribute("[data-request-tg]", "href")) == r["car_msg"]
        # switch to moto: class/blocked values must leave the message
        pg.evaluate("()=>document.querySelector('input[name=vehicle][value=moto]').click()"); pg.wait_for_timeout(250)
        r["moto_msg"] = wa_text(pg.get_attribute("[data-request-wa]", "href"))
        # dropdown open
        pg.evaluate("()=>{const i=document.querySelector('input[name=vehicle][value=car]');if(!i.checked)i.click()}"); pg.wait_for_timeout(200)
        trig = pg.locator(".request-fields .choice-trigger:not([disabled])").first
        trig.scroll_into_view_if_needed(); trig.click(); pg.wait_for_timeout(300)
        r["dropdown"] = pg.evaluate("()=>{const l=document.querySelector('.choice-options:not([hidden])');return l?[l.children.length,getComputedStyle(l).position]:null}")
        r["dropdown_layout"] = pg.evaluate(LAYOUT)
        if w in (390, 1440):
            pg.screenshot(path=str(SHOTS / f"after_{w}_dropdown.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        r["dropdown_closed_by_esc"] = pg.evaluate("()=>!document.querySelector('.choice-options:not([hidden])')")
        # booking modal
        pg.evaluate("window.scrollTo(0,0)")
        pg.click("[data-booking-open]"); pg.wait_for_timeout(400)
        r["booking_open"] = pg.evaluate("()=>document.querySelector('#booking-dialog').open")
        r["booking_layout"] = pg.evaluate(LAYOUT)
        pg.evaluate("""()=>{const d=document.querySelector('[data-booking-when]');d.value='2020-01-01T10:00';d.dispatchEvent(new Event('input',{bubbles:true}))}""")
        pg.wait_for_timeout(200)
        r["booking_past_error"] = pg.inner_text("#booking-when-error")
        if w in (390, 1440):
            pg.screenshot(path=str(SHOTS / f"after_{w}_booking.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        r["booking_closed_focus"] = pg.evaluate("()=>[!document.querySelector('#booking-dialog').open, document.activeElement.matches('[data-booking-open]')]")
        # gallery
        pg.evaluate("()=>document.querySelector('[data-work-open]').click()"); pg.wait_for_timeout(400)
        c1 = pg.inner_text("[data-work-count]")
        pg.click("[data-work-next]"); pg.wait_for_timeout(250); c2 = pg.inner_text("[data-work-count]")
        pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(250); c3 = pg.inner_text("[data-work-count]")
        r["gallery"] = [c1, c2, c3]
        r["gallery_layout"] = pg.evaluate(LAYOUT)
        if w in (390, 1440):
            pg.screenshot(path=str(SHOTS / f"after_{w}_gallery.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        r["gallery_closed_focus"] = pg.evaluate("()=>[!document.querySelector('#work-viewer').open, document.activeElement.matches('[data-work-open]')]")
        r["errors"] = errs
        if w in (390, 1440):
            pg2 = ctx.new_page(); pg2.goto(BASE + "/"); pg2.wait_for_timeout(1500)
            pg2.screenshot(path=str(SHOTS / f"after_{w}_full.png"), full_page=True); pg2.close()
        res[w] = r
        ctx.close()
    # links on the main page and city pages
    pg = b.new_page(); pg.goto(BASE + "/"); pg.wait_for_timeout(800)
    hrefs = set(pg.evaluate("()=>[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href'))"))
    for u in ("/evakuator-domodedovo/", "/manipulyator/"):
        pg.goto(BASE + u); pg.wait_for_timeout(500)
        hrefs |= set(pg.evaluate("()=>[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href'))"))
    b.close()
bad = []
for h in sorted(hrefs):
    if h.startswith("#"):
        continue
    if h.startswith(("tel:", "https://wa.me", "https://t.me")):
        continue
    url = h if h.startswith("http") else BASE + (h if h.startswith("/") else "/" + h)
    try:
        code = urllib.request.urlopen(urllib.request.Request(url.split("#")[0], headers={"User-Agent": "Mozilla/5.0"}), timeout=15).status
    except Exception as e:
        code = str(e)[:40]
    if code != 200:
        bad.append((h, code))
res["links_checked"] = len(hrefs)
res["links_bad"] = bad
Path(SHOTS / "final_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({w: {"issues": len(res[w]["initial"] + res[w]["dropdown_layout"] + res[w]["booking_layout"] + res[w]["gallery_layout"] + sum((t["layout"] for t in res[w]["transports"].values()), [])), "errors": res[w]["errors"], "gallery": res[w]["gallery"], "price": res[w]["car_price"]} for w in (360, 390, 768, 1024, 1440)} | {"links_checked": res["links_checked"], "links_bad": res["links_bad"]}, ensure_ascii=False, indent=1))
