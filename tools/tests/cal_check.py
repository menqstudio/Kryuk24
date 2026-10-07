"""Окно записи: 3 быстрых дня + календарь, стрелки, Esc, время, дата в сообщении."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (360, 390, 768, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900}, locale="ru-RU"); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(900)
        pg.click("[data-booking-open]"); pg.wait_for_timeout(400)
        r = {}
        r["chips"] = pg.evaluate("()=>[...document.querySelectorAll('.when-day')].map(b=>b.innerText.replace(/\\n/g,' ')+'|'+b.getAttribute('aria-checked'))")
        r["layout_closed"] = pg.evaluate(LAYOUT)
        pg.locator(".when-days").scroll_into_view_if_needed()
        if w in (360, 1440): pg.locator(".when-field").screenshot(path=str(SHOTS / f"cal_{w}_chips.png"))
        pg.click(".when-day--cal"); pg.wait_for_timeout(300)
        r["cal_open"] = pg.evaluate("()=>!document.querySelector('#when-cal').hidden")
        r["cal_title"] = pg.inner_text(".when-cal__head strong")
        r["focus"] = pg.evaluate("()=>document.activeElement.dataset.value||document.activeElement.className")
        r["layout_open"] = pg.evaluate(LAYOUT)
        if w in (360, 1440): pg.locator(".when-field").screenshot(path=str(SHOTS / f"cal_{w}_open.png"))
        # keyboard: right x2, down x1
        for k in ("ArrowRight", "ArrowRight", "ArrowDown"): pg.keyboard.press(k)
        r["after_keys"] = pg.evaluate("()=>document.activeElement.dataset.value")
        # next month then pick the 10th
        pg.click(".when-cal__nav >> nth=1"); pg.wait_for_timeout(200)
        r["next_title"] = pg.inner_text(".when-cal__head strong")
        pg.click(".when-cal__grid button:has-text('10') >> nth=0"); pg.wait_for_timeout(200)
        r["cal_closed"] = pg.evaluate("()=>document.querySelector('#when-cal').hidden")
        r["chips_after"] = pg.evaluate("()=>[...document.querySelectorAll('.when-day')].map(b=>b.innerText.replace(/\\n/g,' ')+'|'+b.getAttribute('aria-checked'))")
        pg.click("[data-when-trigger]"); pg.wait_for_timeout(200)
        pg.click("[data-when-times] button:has-text('14:30')"); pg.wait_for_timeout(200)
        r["value"] = pg.evaluate("()=>document.querySelector('[data-booking-when]').value")
        r["msg_has_date"] = pg.evaluate("()=>decodeURIComponent((document.querySelector('#booking-dialog a[href*=\"wa.me\"]')||{}).href||'').slice(-160)")
        if w in (360, 1440): pg.locator(".when-field").screenshot(path=str(SHOTS / f"cal_{w}_picked.png"))
        # quick chip still works and deselects the far date
        pg.click(".when-day >> nth=1"); pg.wait_for_timeout(200)
        r["tomorrow_value"] = pg.evaluate("()=>document.querySelector('[data-booking-when]').value")
        r["cal_chip_reset"] = pg.inner_text(".when-day--cal").replace("\n", " ")
        # Esc closes calendar, not dialog
        pg.click(".when-day--cal"); pg.wait_for_timeout(200); pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        r["esc"] = pg.evaluate("()=>[document.querySelector('#when-cal').hidden,document.querySelector('#booking-dialog').open]")
        r["errors"] = errs
        out[w] = r; pg.close()
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
