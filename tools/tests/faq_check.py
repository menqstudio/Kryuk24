"""Блок «Ответы на вопросы»: светлые вопросы сразу под заголовком (полосы фактов больше нет).
Проверяет: 9 вопросов в прежнем порядке, без категорий; 2 колонки на desktop, последний — во всю ширину;
закрытые карточки одной строки одной высоты; края совпадают с калькулятором; aria-expanded и клавиатура;
раскрытие длинных ответов; без горизонтального скролла."""
import json
from playwright.sync_api import sync_playwright
from common import BASE, SHOTS, LAYOUT

EXPECTED = ["Сколько стоит эвакуатор?", "Цена на месте может измениться?", "Через сколько приедете?",
            "Вы работаете ночью и в выходные?", "Что делать, если колеса не крутятся?", "Куда вы возите?",
            "Как оплатить?", "Вы даете документы на перевозку?", "Возите мотоциклы, микроавтобусы и спецтехнику?"]
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (360, 390, 768, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(900)
        sec = pg.locator("#voprosy"); sec.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        pg.add_style_tag(content=".hdr,.callbar{visibility:hidden!important}")  # fixed bars would cover the element screenshot
        r = {}
        r["questions_ok"] = pg.evaluate("()=>[...document.querySelectorAll('#voprosy .faq__i summary')].map(s=>s.textContent.trim())") == EXPECTED
        r["topics_left"] = pg.evaluate("document.querySelectorAll('#voprosy .faq-topic').length")
        r["geo"] = pg.evaluate("""()=>{const R=e=>e.getBoundingClientRect(),calc=R(document.querySelector('.request')),head=R(document.querySelector('#voprosy .sec__h2')),list=R(document.querySelector('#voprosy .faq__list'));
          const items=[...document.querySelectorAll('#voprosy .faq__i')].map(e=>{const b=R(e);return [Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height)]});
          const rows={};items.forEach(i=>{(rows[i[1]]=rows[i[1]]||[]).push(i[3])});
          return {edges:[Math.round(calc.left),Math.round(calc.right),Math.round(list.left),Math.round(list.right)],factsLeft:document.querySelectorAll('.contact-panel--facts').length,
                  gap:Math.round(list.top-head.bottom), cols:new Set(items.map(i=>i[0])).size, lastFull:items[8][2]===Math.round(list.width),
                  rowHeightsEqual:Object.values(rows).every(h=>Math.max(...h)-Math.min(...h)<=1),
                  qFont:getComputedStyle(document.querySelector('#voprosy .faq__i summary')).font.split(' ').slice(0,2).join(' ')}}""")
        r["layout"] = pg.evaluate(LAYOUT)
        sec.screenshot(path=str(SHOTS / f"faq_{w}_closed.png"))
        # keyboard: Tab focus to the first summary, Enter opens, aria-expanded follows
        pg.focus("#voprosy .faq__i summary")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
        r["kbd_open"] = pg.evaluate("()=>{const d=document.querySelector('#voprosy .faq__i');return [d.open,d.querySelector('summary').getAttribute('aria-expanded'),getComputedStyle(d).backgroundColor]}")
        # open the longest answers too
        pg.locator("#voprosy .faq__i summary").nth(8).click(); pg.wait_for_timeout(300)
        r["open_heights"] = pg.evaluate("()=>[...document.querySelectorAll('#voprosy .faq__i[open]')].map(d=>[d.querySelector('p').scrollHeight,Math.round(d.querySelector('p').getBoundingClientRect().height)])")
        r["layout_open"] = pg.evaluate(LAYOUT)
        sec.screenshot(path=str(SHOTS / f"faq_{w}_open.png"))
        pg.keyboard.press("Enter")  # focus is on the 9th summary after click → closes it
        pg.wait_for_timeout(300)
        r["kbd_close"] = pg.evaluate("()=>{const d=document.querySelectorAll('#voprosy .faq__i')[8];return [d.open,d.querySelector('summary').getAttribute('aria-expanded')]}")
        r["errors"] = errs
        out[w] = r; pg.close()
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
