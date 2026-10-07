"""Браузерная проверка для css_clean.py.

  matches  <css> <out.json>   — какие селекторы находят элементы хотя бы на одной странице/в одном состоянии
  computed <out.json>         — вычисленные стили всех элементов (+ ::before/::after) на всех страницах,
                                ширинах и состояниях
  compare  <a.json> <b.json>  — различия между двумя снимками

Сайт должен отдаваться локально: py -m http.server 8765 --bind 127.0.0.1 (из site).
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
PAGES = ["/", "/evakuator-domodedovo/", "/evakuator-balashikha/", "/evakuator-lyubertsy/", "/evakuator-podolsk/",
         "/manipulyator/", "/perevozka-spetstekhniki/", "/_ready/evakuator-khimki/", "/404.html"]
WIDTHS = [360, 390, 768, 1024, 1440]

STATES = {
    "initial": "",
    "car_nowheels": """
      const c=document.querySelector('input[name=vehicle][value=car]'); if(c){c.click();}
      const w=document.querySelector('[data-wheels]'); if(w){w.value='Нет'; w.dispatchEvent(new Event('change',{bubbles:true}));}
    """,
    "dropdown": """
      const c=document.querySelector('input[name=vehicle][value=car]'); if(c){c.click();}
      const t=document.querySelector('.choice-trigger:not(:disabled)'); if(t) t.click();
    """,
    "booking": "const b=document.querySelector('[data-booking-open]'); if(b) b.click();",
    "gallery": "const g=document.querySelector('[data-work-open]'); if(g) g.click();",
}

SNAP = r"""() => {
  const out = [];
  const all = [...document.querySelectorAll('*')];
  all.forEach((el, i) => {
    const key = el.tagName + '#' + i + '.' + (el.className && el.className.baseVal === undefined ? el.className : '');
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      const o = {};
      for (let k = 0; k < cs.length; k++) { const p = cs[k]; o[p] = cs.getPropertyValue(p); }
      out.push([key + (pseudo || ''), o]);
    }
  });
  return out;
}"""


def strip_sel(sel):
    s = re.sub(r"::?(before|after|placeholder|backdrop|selection|marker|-webkit-[\w-]+|-moz-[\w-]+)(\([^)]*\))?", "", sel)
    s = re.sub(r":(hover|focus-visible|focus-within|focus|active|visited|checked|disabled|enabled|invalid|valid|placeholder-shown|target|read-only|required)\b", "", s)
    s = re.sub(r"\[(aria-[\w-]+|open|hidden|disabled|data-[\w-]+)(=[^\]]*)?\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(^|[\s>+~])(?=$|[\s>+~])", r"\1*", s)
    return s or "*"


def run_states(page, url, fn):
    for name, js in STATES.items():
        if name != "initial" and url != "/":
            continue
        page.goto(BASE + url)
        page.wait_for_timeout(700)
        if js:
            page.evaluate("()=>{" + js + "}")
            page.wait_for_timeout(500)
        fn(name)


def cmd_matches(css_path, out_path):
    sys.path.insert(0, str(Path(__file__).parent))
    import css_clean as cc
    css = cc.strip_comments(Path(css_path).read_text(encoding="utf-8"))
    nodes, _ = cc.parse_block(css)
    sels = sorted({it["sel"] for it in cc.flatten(nodes) if it["kind"] == "rule"})
    probe = {s: strip_sel(s) for s in sels}
    found = {s: False for s in sels}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        for url in PAGES:
            def check(_):
                res = pg.evaluate("""(list)=>list.map(s=>{try{return !!document.querySelector(s)}catch(e){return null}})""",
                                  list(probe.values()))
                for (s, _p), r in zip(probe.items(), res):
                    if r is None or r:
                        found[s] = True  # invalid probe → keep
            run_states(pg, url, check)
        b.close()
    Path(out_path).write_text(json.dumps(found, ensure_ascii=False, indent=0), encoding="utf-8")
    print("selectors:", len(found), "unmatched:", sum(1 for v in found.values() if not v))


def cmd_computed(out_path):
    snap = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for w in WIDTHS:
            pg = b.new_page(viewport={"width": w, "height": 900}, reduced_motion="reduce")
            for url in PAGES:
                def grab(state):
                    pg.wait_for_timeout(300)
                    snap[f"{w}|{url}|{state}"] = pg.evaluate(SNAP)
                run_states(pg, url, grab)
            pg.close()
        b.close()
    Path(out_path).write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    print("snapshots:", len(snap))


def cmd_compare(a_path, b_path):
    A = json.loads(Path(a_path).read_text(encoding="utf-8"))
    B = json.loads(Path(b_path).read_text(encoding="utf-8"))
    diffs = 0
    shown = 0
    for k in A:
        a, b = dict(A[k]), dict(B.get(k, []))
        for el in a:
            if el not in b:
                diffs += 1
                if shown < 25:
                    print("missing", k, el); shown += 1
                continue
            for p, v in a[el].items():
                if b[el].get(p) != v:
                    diffs += 1
                    if shown < 25:
                        print("DIFF", k, el, p, repr(v), "->", repr(b[el].get(p))); shown += 1
    print("total differences:", diffs)


if __name__ == "__main__":
    {"matches": lambda: cmd_matches(sys.argv[2], sys.argv[3]),
     "computed": lambda: cmd_computed(sys.argv[2]),
     "compare": lambda: cmd_compare(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
