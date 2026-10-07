"""Общие настройки проверок сайта kryuk24.ru.

Каждая проверка запускается так:  python <проверка>.py [BASE]
BASE — http://127.0.0.1:8765 (локальная копия site) или https://kryuk24.ru (живой сайт).
Скриншоты складываются в tools/tests/_shots/ (в git не попадают).
"""
import sys
from pathlib import Path

LOCAL = "http://127.0.0.1:8765"
LIVE = "https://kryuk24.ru"
BASE = (sys.argv[1] if len(sys.argv) > 1 else LOCAL).rstrip("/")
SHOTS = Path(__file__).parent / "_shots"
SHOTS.mkdir(exist_ok=True)

# Проверки не должны попадать в Метрику: до 04.10.2026 каждый прогон (и локальный, и live) записывался
# как десятки «прямых заходов» и кликов по целям. Любая страница, открытая из проверок, счетчик не грузит.
import re  # noqa: E402
from playwright.sync_api import Browser  # noqa: E402

_new_page = Browser.new_page


def _quiet_page(self, **kw):
    pg = _new_page(self, **kw)
    pg.route(re.compile(r"^https?://mc\.yandex\.(ru|com)/"), lambda route: route.abort())
    return pg


Browser.new_page = _quiet_page

# Ищет на открытой странице: горизонтальный скролл, вылезающий текст, элементы за краем экрана,
# наложение соседних элементов в ключевых сетках. Возвращает список проблем (пустой = чисто).
LAYOUT = r"""()=>{
 const W=document.documentElement.clientWidth, issues=[];
 if(document.documentElement.scrollWidth>W+1) issues.push('page h-scroll '+document.documentElement.scrollWidth+'>'+W);
 const vis=e=>{const r=e.getBoundingClientRect();const c=getComputedStyle(e);return r.width>0&&r.height>0&&c.visibility!=='hidden'&&!e.closest('[hidden]')&&!e.closest('dialog:not([open])')};
 document.querySelectorAll('h1,h2,h3,p,span,strong,a,button,label,legend,summary,dt,dd,small,li').forEach(e=>{
   if(!vis(e)||e.closest('.band__run,.service-strip,.work-thumbs,.pl,[data-fit],.choice-options')) return;
   const c=getComputedStyle(e); if(c.overflow==='hidden'&&c.textOverflow==='ellipsis') return;
   if(e.scrollWidth>e.clientWidth+2 && c.display!=='inline' && e.clientWidth>0) issues.push('text overflow: '+e.tagName+'.'+e.className+' «'+e.textContent.trim().slice(0,40)+'»');
   const r=e.getBoundingClientRect(); if(r.right>W+1&&!e.closest('.case__tabs')) issues.push('beyond viewport: '+e.tagName+'.'+e.className+' «'+e.textContent.trim().slice(0,30)+'»');
 });
 for(const g of document.querySelectorAll('.form-grid,.route-row,.vehicle-choice,.request-actions,.hero-actions,.booking-grid,.contact-facts,.faq__list,.request')){
   if(!vis(g)) continue; const k=[...g.children].filter(vis).map(c=>c.getBoundingClientRect());
   for(let i=0;i<k.length;i++)for(let j=i+1;j<k.length;j++){const a=k[i],b=k[j];
     if(a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1) issues.push('overlap in .'+g.className);}
 }
 return [...new Set(issues)];
}"""
