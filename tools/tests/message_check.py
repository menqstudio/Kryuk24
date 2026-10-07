"""Сообщения WhatsApp/Telegram из расчета и окна записи: только заполненные и активные поля,
без «не указано» и канцелярской строки; кнопки транспорта без обрезки текста на всех ширинах."""
import json
import urllib.parse
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT

BAD = ["не указан", "не указана", "не указано", "требуют согласования", "вращаются"]


def msg(pg, sel):
    h = pg.get_attribute(sel, "href") or ""
    return urllib.parse.unquote(h.split("text=")[1]) if "text=" in h else ""


def pick(pg, sel, value):
    pg.evaluate(f"""()=>{{const e=document.querySelector('{sel}');e.value='{value}';e.dispatchEvent(new Event('change',{{bubbles:true}}))}}""")


out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/"); pg.wait_for_timeout(1000)
    out["1_empty"] = msg(pg, "[data-request-wa]")
    pg.evaluate("()=>document.querySelector('input[name=vehicle][value=car]').click()"); pg.wait_for_timeout(200)
    out["2_car_only"] = msg(pg, "[data-request-wa]")
    pick(pg, "[data-class]", "4500"); pick(pg, "[data-situation]", "После ДТП"); pick(pg, "[data-wheels]", "Нет"); pick(pg, "[data-blocked]", "2")
    pg.wait_for_timeout(200)
    out["3_car_full"] = msg(pg, "[data-request-wa]")
    out["3_tg_same"] = msg(pg, "[data-request-tg]") == out["3_car_full"]
    pg.evaluate("()=>document.querySelector('input[name=vehicle][value=commercial]').click()"); pg.wait_for_timeout(200)
    pg.fill("[data-model]", "ГАЗель NEXT"); pg.wait_for_timeout(200)
    out["4_commercial"] = msg(pg, "[data-request-wa]")
    out["4_placeholder"] = pg.get_attribute("[data-model]", "placeholder")
    out["labels"] = pg.evaluate("()=>[document.querySelector('[data-class-box]').childNodes[0].textContent.trim(),document.querySelector('[data-wheels-box]').childNodes[0].textContent.trim(),document.querySelector('.request-fields .field-note')?.textContent]")
    # booking dialog
    pg.evaluate("window.scrollTo(0,0)"); pg.click("[data-booking-open]"); pg.wait_for_timeout(400)
    out["5_booking_empty"] = msg(pg, "#booking-dialog a[href*='wa.me']")
    pg.evaluate("()=>{document.querySelector('#booking-dialog input[name=booking-vehicle][value=moto]')?.click()}"); pg.wait_for_timeout(200)
    pg.click(".when-day >> nth=1"); pg.wait_for_timeout(200)
    pg.click("[data-when-trigger]"); pg.wait_for_timeout(200); pg.click("[data-when-times] button:has-text('10:00')"); pg.wait_for_timeout(200)
    pg.fill("#booking-dialog textarea", "Нужно к сервису на Варшавке"); pg.wait_for_timeout(200)
    out["6_booking_full"] = msg(pg, "#booking-dialog a[href*='wa.me']")
    out["errors"] = errs
    pg.close()
    # buttons: no clipped text at any width (calculator, booking dialog, tariff tab)
    fit = {}
    for w in (360, 390, 768, 1024, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.goto(BASE + "/"); pg.wait_for_timeout(800)
        r = {"calc": pg.evaluate(LAYOUT)}
        pg.locator(".request .vehicle-choice").scroll_into_view_if_needed()
        clip = """()=>[...document.querySelectorAll('.vehicle-choice span, .case__tab')].filter(e=>e.offsetParent).map(e=>[e.textContent.trim(),e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1]).filter(x=>x[1]).map(x=>x[0])"""
        r["clipped_calc"] = pg.evaluate(clip)
        if w in (360, 1440):
            pg.locator(".request .vehicle-choice").screenshot(path=str(SHOTS / f"vehicle_{w}.png"))
        pg.click("[data-booking-open]"); pg.wait_for_timeout(400)
        r["clipped_booking"] = pg.evaluate(clip)
        r["booking"] = pg.evaluate(LAYOUT)
        if w == 360:
            pg.locator("#booking-dialog .vehicle-choice").screenshot(path=str(SHOTS / "vehicle_booking_360.png"))
        fit[w] = r; pg.close()
    out["fit"] = fit
    b.close()
bad = {k: [x for x in BAD if x in v] for k, v in out.items() if isinstance(v, str) and k[0].isdigit()}
out["bad_words"] = {k: v for k, v in bad.items() if v}
print(json.dumps(out, ensure_ascii=False, indent=1))
