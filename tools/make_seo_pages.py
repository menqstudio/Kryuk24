"""SEO-страницы КРЮК24: города Подмосковья и отдельные услуги.

Правила (Гев, 03.10.2026):
- каждая страница полезна сама по себе, а не «главная с другим названием города» —
  иначе Яндекс сочтет ее дорвеем: свой маршрут, свое реальное расстояние и цена по тарифу;
- цены только из действующего тарифа (research/Tariff_real_2026-10-02.md);
- расстояния — по дорогам (OSRM) от центра города до центра Москвы, посчитаны 03.10.2026;
- никаких выдуманных адресов, «дежурных машин в городе», минут подачи и отзывов;
- фото — только настоящие выезды.

Выход: site/<slug>/index.html, site/assets/pages.css, обновляет sitemap.xml.
Город с live=False (далеко от точки, ждем подтверждения Армена): готовая страница лежит в
site/_ready/<slug>/index.html, а по адресу на сайте — заглушка noindex с переходом на главную;
из sitemap и перекрестных ссылок такой город исключен. Вернуть: убрать live=False и перезапустить.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
SITE = "https://kryuk24.ru"
PHONE = "+7 985 893-06-06"
TEL = "tel:+79858930606"
VER = "33"

LIGHT, PARK, JEEP = 4000, 4500, 5000  # погрузка и выгрузка, ₽
PER_KM = 100

CITIES = [
    # slug, Им., Предл. (в …), Род. (из …), км до центра Москвы, трасса, фото
    dict(slug="evakuator-domodedovo", name="Домодедово", v="в Домодедово", iz="из Домодедово", km=44,
         road="по Каширскому шоссе (М-4 «Дон»)",
         note="Рядом аэропорт Домодедово: если машина сломалась по дороге в аэропорт или из него, скажите, на каком участке трассы вы стоите.",
         photos=["rabota-01-mercedes-cla", "rabota-13-mikroavtobus-osen", "rabota-06-posle-dtp"]),
    dict(slug="evakuator-khimki", name="Химки", v="в Химках", iz="из Химок", km=24,
         road="по Ленинградскому шоссе (М-10) или по платной трассе М-11 «Нева»",
         note="Если машина стоит на М-11 или на Ленинградке, назовите километр или ближайший съезд — так быстрее найти и подъехать.",
         photos=["rabota-03-bmw-x6", "rabota-10-volkswagen-golf", "rabota-17-pogruzka-po-apparelyam"]),
    dict(slug="evakuator-balashikha", name="Балашиха", v="в Балашихе", iz="из Балашихи", km=23,
         road="по Горьковскому шоссе (М-7), Щелковскому или Носовихинскому шоссе",
         note="Из разных районов Балашихи удобнее разные выезды на Москву — маршрут выбираем по адресу подачи.",
         photos=["rabota-05-audi-a8", "rabota-12-posle-dtp-pogruzka", "rabota-07-mikroavtobus"]),
    dict(slug="evakuator-lyubertsy", name="Люберцы", v="в Люберцах", iz="из Люберец", km=25,
         road="по Новорязанскому шоссе (М-5 «Урал»)",
         note="Новорязанка часто стоит в пробках — время подачи называем по телефону с учетом дороги, а цена от пробок не зависит: считаем километры, а не минуты.",
         photos=["rabota-06-posle-dtp", "rabota-08-rolls-royce", "rabota-03-bmw-x6"]),
    dict(slug="evakuator-podolsk", name="Подольск", v="в Подольске", iz="из Подольска", km=45,
         road="по Симферопольскому шоссе (М-2 «Крым») или Варшавскому шоссе",
         note="Если нужно не в Москву, а в сервис в самом Подольске или соседнем городе — расстояние будет короче и дешевле, посчитаем по вашему адресу.",
         photos=["rabota-13-mikroavtobus-osen", "rabota-01-mercedes-cla", "rabota-10-volkswagen-golf"]),
]

SERVICES = [
    dict(slug="manipulyator", title="Эвакуатор-манипулятор в Москве и области — от 10 000 ₽",
         h1=("Манипулятор", "Круглосуточно"),
         desc="Эвакуатор-манипулятор в Москве и Московской области 24/7: подъем машины из кювета, со двора, с парковки, после ДТП. Легковой — от 10 000 ₽ + 100 ₽/км, кроссовер — от 12 000 ₽ + 120 ₽/км. " + PHONE,
         lead="Когда к машине не подъехать платформой — кювет, плотный двор, высокий бордюр, машина после ДТП стоит неудобно — ее поднимают краном-манипулятором и ставят на борт.",
         when=["Машина в кювете, в снегу или в грязи, и к ней нет ровного подъезда",
               "Тесный двор или парковка: платформу не опустить, а кран дотянется",
               "После ДТП машину нельзя тянуть лебедкой без риска новых повреждений",
               "Нужно поднять машину через препятствие: бордюр, ограждение, ступени"],
         prices=[("Легковой автомобиль", "от 10 000 ₽", "+ 100 ₽ за км"),
                 ("Кроссовер (паркетник)", "от 12 000 ₽", "+ 120 ₽ за км"),
                 ("Погрузка со сферического ограждения — краном", "10 000 ₽", "")],
         photos=["rabota-02-iz-kyuveta", "rabota-14-manipulyator-posle-dtp", "rabota-11-manipulyator"],
         faq=[("Сколько стоит манипулятор?", "Легковой автомобиль — от 10 000 ₽ плюс 100 ₽ за километр, кроссовер (паркетник) — от 12 000 ₽ плюс 120 ₽ за километр. Точную сумму называем по телефону до выезда."),
              ("Чем манипулятор лучше обычного эвакуатора?", "Платформе нужен ровный подъезд и место, чтобы опустить ее до земли. Манипулятор поднимает машину краном — из кювета, через бордюр, из тесного двора."),
              ("Машину не повредят при подъеме?", "Поднимаем на штатных стропах и захватах за колеса, без зацепов за кузов. Если сомневаетесь в способе — скажите при звонке, обсудим заранее.")]),
    dict(slug="perevozka-spetstekhniki", title="Перевозка спецтехники эвакуатором — от 5000 ₽ · Москва и область",
         h1=("Перевозка спецтехники", "Круглосуточно"),
         desc="Перевозка спецтехники на эвакуаторе в Москве и Московской области: вилочные погрузчики, мини-погрузчики, малая техника. 2500 ₽ за тонну, не менее 5000 ₽, плюс 100 ₽/км. " + PHONE,
         lead="Возим малую спецтехнику на платформе: вилочные и фронтальные мини-погрузчики, компактную технику. Техника заезжает своим ходом или затягивается лебедкой и крепится ремнями.",
         when=["Вилочный погрузчик — со склада на склад, в ремонт или после покупки",
               "Мини-погрузчик с ковшом — на объект и обратно",
               "Неисправная техника, которая не может ехать своим ходом",
               "Перевозка по Москве, в область и между городами — по договоренности"],
         prices=[("За каждую тонну массы техники", "2500 ₽", "не менее 5000 ₽"),
                 ("Например, техника 3 тонны", "7500 ₽", "+ 100 ₽ за км"),
                 ("Перевозка", "100 ₽", "за километр")],
         photos=["rabota-16-vilochnyy-pogruzchik", "rabota-15-mini-pogruzchik-s-kovshom", "rabota-18-pogruzchik-na-platformu"],
         faq=[("Как считается цена перевозки спецтехники?", "2500 ₽ за каждую тонну массы техники, но не меньше 5000 ₽, плюс 100 ₽ за каждый километр пути. Например, техника массой 3 тонны — 7500 ₽ плюс километры."),
              ("Какую технику вы возите?", "Малую спецтехнику, которая помещается на платформу эвакуатора: вилочные погрузчики, мини-погрузчики, компактную технику. Скажите модель и массу — подтвердим, подходит ли."),
              ("Техника не заводится — сможете забрать?", "Да. Затягиваем лебедкой на платформу. Скажите об этом при звонке, чтобы взять подходящий такелаж.")]),
]

WA_ICON = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2m0 1.67c2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.82c0 4.54-3.7 8.24-8.25 8.24a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.26-8.24M8.4 6.98c-.17 0-.44.06-.67.31-.23.25-.88.86-.88 2.1s.9 2.44 1.03 2.6c.13.18 1.75 2.67 4.24 3.74.59.26 1.05.41 1.41.52.6.19 1.14.16 1.57.1.48-.07 1.47-.6 1.68-1.19.21-.58.21-1.08.14-1.18-.06-.11-.23-.17-.48-.29-.25-.13-1.48-.73-1.71-.81-.23-.09-.4-.13-.56.12-.17.25-.65.81-.79.98-.15.16-.29.19-.54.06-.25-.12-1.05-.39-2-1.23-.74-.66-1.24-1.47-1.38-1.72-.15-.25-.02-.38.11-.5.11-.11.25-.29.37-.44.13-.14.17-.25.25-.41.09-.17.05-.31-.02-.44-.06-.12-.55-1.36-.78-1.86-.19-.42-.38-.42-.55-.43h-.44"/></svg>'
PHONE_ICON = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25c1.12.37 2.33.57 3.6.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1.02z"/></svg>'

PHOTO_ALT = {
    "rabota-01-mercedes-cla": "Mercedes на платформе эвакуатора КРЮК24",
    "rabota-02-iz-kyuveta": "Манипулятор поднимает автомобиль из кювета",
    "rabota-03-bmw-x6": "Кроссовер BMW X6 на платформе",
    "rabota-05-audi-a8": "Седан Audi A8 на платформе",
    "rabota-06-posle-dtp": "Седан после ДТП на платформе",
    "rabota-07-mikroavtobus": "Грузовой микроавтобус на платформе",
    "rabota-08-rolls-royce": "Купе Rolls-Royce на платформе эвакуатора",
    "rabota-10-volkswagen-golf": "Volkswagen Golf на платформе",
    "rabota-11-manipulyator": "Эвакуатор-манипулятор с кроссовером",
    "rabota-12-posle-dtp-pogruzka": "Погрузка автомобиля после ДТП",
    "rabota-13-mikroavtobus-osen": "Микроавтобус на платформе, осень",
    "rabota-14-manipulyator-posle-dtp": "Манипулятор грузит автомобиль после ДТП",
    "rabota-15-mini-pogruzchik-s-kovshom": "Мини-погрузчик с ковшом на платформе",
    "rabota-16-vilochnyy-pogruzchik": "Вилочный погрузчик на платформе эвакуатора",
    "rabota-17-pogruzka-po-apparelyam": "Погрузка седана по аппарелям",
    "rabota-18-pogruzchik-na-platformu": "Погрузчик заезжает на платформу своим ходом",
}

METRIKA = """<script>
(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
m[i].l=1*new Date();
for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
ym(113277361, "init", {clickmap:true, trackLinks:true, accurateTrackBounce:true, webvisor:true});
document.addEventListener("click", function(ev){
  var a = ev.target.closest && ev.target.closest("a[href]");
  if (!a) return;
  var h = a.getAttribute("href") || "";
  var goal = h.indexOf("tel:") === 0 ? "call" : h.indexOf("wa.me") > -1 ? "whatsapp" : h.indexOf("t.me") > -1 ? "telegram" : null;
  if (goal && window.ym) ym(113277361, "reachGoal", goal);
}, {passive: true});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/113277361" style="position:absolute; left:-9999px;" alt=""></div></noscript>"""

FIT = """<script>
(function(){var box=document.querySelector('[data-fit]');if(!box)return;var ls=[].slice.call(box.querySelectorAll('[data-fit-line]'));
function fit(){var w=box.clientWidth;if(!w)return;ls.forEach(function(l){var fs=100;for(var i=0;i<3;i++){l.style.fontSize=fs+'px';var lw=l.getBoundingClientRect().width;if(!lw)return;fs=Math.min(110,fs*w/lw);}l.style.fontSize=Math.floor(fs*10)/10+'px';});}
fit();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);var t=0;window.addEventListener('resize',function(){clearTimeout(t);t=setTimeout(fit,80);});})();
</script>"""

e = html.escape
money = lambda n: f"{n:,}".replace(",", " ")


def wa(text):
    from urllib.parse import quote
    return "https://wa.me/79858930606?text=" + quote(text)


WA_URL = "https://wa.me/79858930606"
TG_URL = "https://t.me/+79858930606"
REVIEWS_URL = "https://yandex.ru/maps/org/1767605134/reviews/"
FOOT_WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2m0 1.67c2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.82c0 4.54-3.7 8.24-8.25 8.24a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.26-8.24M8.4 6.98c-.17 0-.44.06-.67.31-.23.25-.88.86-.88 2.1s.9 2.44 1.03 2.6c.13.18 1.75 2.67 4.24 3.74.59.26 1.05.41 1.41.52.6.19 1.14.16 1.57.1.48-.07 1.47-.6 1.68-1.19.21-.58.21-1.08.14-1.18-.06-.11-.23-.17-.48-.29-.25-.13-1.48-.73-1.71-.81-.23-.09-.4-.13-.56.12-.17.25-.65.81-.79.98-.15.16-.29.19-.54.06-.25-.12-1.05-.39-2-1.23-.74-.66-1.24-1.47-1.38-1.72-.15-.25-.02-.38.11-.5.11-.11.25-.29.37-.44.13-.14.17-.25.25-.41.09-.17.05-.31-.02-.44-.06-.12-.55-1.36-.78-1.86-.19-.42-.38-.42-.55-.43h-.44"/></svg>'
FOOT_TG_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M21.94 4.3 18.9 19.2c-.23 1.02-.84 1.27-1.7.79l-4.7-3.46-2.27 2.18c-.25.25-.46.46-.94.46l.33-4.78 8.7-7.86c.38-.34-.08-.53-.59-.19L6.98 13.1 2.33 11.6c-1.01-.32-1.03-1.01.21-1.5L20.63 3.1c.84-.31 1.58.2 1.31 1.2z"/></svg>'
EXT_ICON = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>'


def footer(main=False):
    """Общий подвал. main=True — главная (якоря на этой же странице, галерея — кнопкой);
    иначе — страницы городов/услуг (ссылки на разделы главной, галерея открывается по /#raboty)."""
    p = "" if main else "/"
    logo_href, logo_label = ("#top", "КРЮК24 — наверх") if main else ("/", "КРЮК24 — на главную")
    works = ('<button type="button" class="foot__link" data-work-open aria-haspopup="dialog" aria-controls="work-viewer">Наши работы</button>'
             if main else '<a class="foot__link" href="/#raboty">Наши работы</a>')
    ext = 'target="_blank" rel="noopener noreferrer"'
    return (
        f'<footer class="foot"><div class="wrap">'
        f'<div class="foot__grid">'
        f'<div class="foot__col foot__brand"><a class="logo logo--foot" href="{logo_href}" aria-label="{logo_label}">'
        f'<img class="logo__mark" src="{p}assets/mark-orange.svg?v=18" alt="" width="21" height="38" aria-hidden="true">'
        f'<span class="logo__txt"><span class="logo__name">КРЮК24</span><span class="logo__sub">ЭВАКУАТОР<span class="logo__plus">+</span></span></span></a>'
        f'<p class="foot__area">Москва и Московская область<span>Междугородние перевозки — по договоренности</span></p></div>'
        f'<nav class="foot__col" aria-label="Разделы"><p class="foot__h">Разделы</p><ul class="foot__nav">'
        f'<li><a class="foot__link" href="{p}#zayavka">Стоимость</a></li><li>{works}</li>'
        f'<li><a class="foot__link" href="{p}#cena">Тарифы</a></li><li><a class="foot__link" href="{p}#voprosy">Вопросы</a></li></ul></nav>'
        f'<div class="foot__col foot__contact"><p class="foot__h">Связаться</p>'
        f'<a class="foot__tel" href="{TEL}">{PHONE}</a>'
        f'<div class="foot__msg"><a href="{WA_URL}" {ext}>{FOOT_WA_ICON}<span>WhatsApp</span></a>'
        f'<a href="{TG_URL}" {ext}>{FOOT_TG_ICON}<span>Telegram</span></a></div></div>'
        f'</div>'
        f'<div class="foot__bottom"><span class="foot__copy">© 2026 КРЮК24</span>'
        f'<a class="btn btn--ghost btn--sm foot__review" href="{REVIEWS_URL}" {ext}>{EXT_ICON}<span>Оставить отзыв в Яндексе</span></a>'
        f'<a class="foot__up" href="#top">Наверх <span aria-hidden="true">↑</span></a></div>'
        f'</div></footer>')


# Обновление страницы (F5) всегда начинается с самого верха, без прежней прокрутки и без якоря в адресе.
TOP = """<script>
if('scrollRestoration' in history)history.scrollRestoration='manual';
(function(){var n=performance.getEntriesByType&&performance.getEntriesByType('navigation')[0];
if(n&&n.type==='reload'){if(location.hash)history.replaceState(null,'',location.pathname+location.search);
window.addEventListener('load',function(){window.scrollTo(0,0);});}})();
</script>"""

# Меню-«гамбургер» на узких экранах (одно и то же на главной и на страницах городов).
MENU = """<script>
(function(){var h=document.querySelector('.hdr'),t=h&&h.querySelector('.nav-toggle'),n=h&&h.querySelector('.nav');if(!t||!n)return;h.classList.add('has-menu');
function set(o){h.classList.toggle('is-menu',o);t.setAttribute('aria-expanded',String(o));t.setAttribute('aria-label',o?'Закрыть меню':'Открыть меню');}
t.addEventListener('click',function(){set(!h.classList.contains('is-menu'));});
n.addEventListener('click',function(e){if(e.target.closest('a,button'))set(false);});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&h.classList.contains('is-menu')){set(false);t.focus();}});
document.addEventListener('click',function(e){if(h.classList.contains('is-menu')&&!h.contains(e.target))set(false);});
window.addEventListener('resize',function(){if(window.innerWidth>=1024)set(false);});})();
document.querySelectorAll('.faq__i').forEach(function(d){var s=d.querySelector('summary');if(!s)return;var u=function(){s.setAttribute('aria-expanded',String(d.open));};u();d.addEventListener('toggle',u);});
</script>"""

def links_block(current):
    city = " · ".join(f'<a href="/{c["slug"]}/">Эвакуатор {e(c["v"])}</a>' for c in CITIES if c["slug"] != current and c.get("live", True))
    serv = " · ".join(f'<a href="/{s["slug"]}/">{e(s["h1"][0])}</a>' for s in SERVICES if s["slug"] != current)
    return f'''<section class="pg-sec pg-links" aria-label="Другие страницы"><div class="wrap">
 <p class="pg-kicker">ЕЩЕ</p>
 <p><a href="/">Главная — расчет стоимости по адресу</a></p>
 <p>{city}</p>
 <p>{serv}</p>
</div></section>'''


def page(slug, title, desc, h1, lead_html, hero_photo, sections, faq, schema_extra, wa_text, body_cls=""):
    url = f"{SITE}/{slug}/"
    faq_html = "".join(f'<details class="faq__i"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "КРЮК24", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": h1[0], "item": url}]}
    lds = "\n".join(f'<script type="application/ld+json">\n{json.dumps(x, ensure_ascii=False, indent=1)}\n</script>' for x in (schema_extra, faq_ld, crumbs))
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
{TOP}
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.ico?v=18" sizes="any">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v=18">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon-180.png?v=18">
<meta name="theme-color" content="#FFFFFF">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="КРЮК24">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{SITE}/assets/img/{hero_photo}.jpg">
<link rel="stylesheet" href="/assets/fonts.css">
<link rel="stylesheet" href="/styles.css?v={VER}">
<link rel="stylesheet" href="/assets/pages.css?v={VER}">
{lds}
</head>
<body class="pg{body_cls}">
<a class="skip" href="#main">Перейти к содержанию</a>
<header class="hdr"><div class="wrap hdr__in">
 <a class="logo" href="/" aria-label="КРЮК24 — на главную"><img class="logo__mark" src="/assets/mark-orange.svg?v=18" alt="" width="25" height="44" aria-hidden="true"><span class="logo__txt"><span class="logo__name">КРЮК24</span><span class="logo__sub">ЭВАКУАТОР<span class="logo__plus">+</span></span></span></a>
 <nav class="nav" id="site-nav" aria-label="Разделы"><a href="/#zayavka">Стоимость</a><a href="/#raboty">Наши работы</a><a href="/#voprosy">Вопросы</a><a href="/#cena">Тарифы</a></nav>
 <div class="header-contacts"><a class="btn btn--sm hdr__call" href="{TEL}">{PHONE_ICON}<span>{PHONE}</span></a></div>
 <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Открыть меню"><span class="nav-toggle__bars" aria-hidden="true"></span></button>
</div></header>
<main id="main">
<section class="hero" id="top"><div class="wrap hero__in">
 <div class="hero__text">
  <nav class="pg-crumbs" aria-label="Навигация"><a href="/">Главная</a> / <span>{e(h1[0])}</span></nav>
  <div class="hero-lockup" data-fit>
   <h1 class="hero__h1"><span class="hero__promise" data-fit-line>{e(h1[0])}</span><span class="hero__hours" data-fit-line>{e(h1[1])}</span></h1>
   <div class="hero-actions"><a class="btn btn--big hero-call" href="{TEL}" aria-label="Вызвать сейчас: позвонить {PHONE}">{PHONE_ICON}<span>Вызвать сейчас</span></a><a class="btn btn--ghost" href="{e(wa(wa_text))}" target="_blank" rel="noopener noreferrer">{WA_ICON}<span>Написать в WhatsApp</span></a></div>
  </div>
  <p class="pg-lead">{lead_html}</p>
 </div>
 <figure class="hero__fig"><img src="/assets/img/{hero_photo}.jpg" alt="{e(PHOTO_ALT[hero_photo])}" fetchpriority="high"><figcaption class="hero__tag"><span>НАСТОЯЩИЙ ВЫЕЗД КРЮК24</span><strong>Цену называем<br>до выезда.</strong></figcaption></figure>
</div></section>
{sections}
<section class="sec pg-sec" id="voprosy"><div class="wrap">
 <h2 class="sec__h2">Вопросы</h2>
 <div class="faq__list">{faq_html}</div>
</div></section>
{links_block(slug)}
</main>
{footer()}
<div class="callbar"><a class="callbar__tel" href="{TEL}">{PHONE.replace(" ", "&nbsp;")}</a><a class="callbar__wa" href="{e(wa(wa_text))}" target="_blank" rel="noopener noreferrer" aria-label="Написать в WhatsApp">{WA_ICON}<span>WhatsApp</span></a></div>
{FIT}
{MENU}
{METRIKA}
</body>
</html>
'''


def photos_block(names, heading):
    figs = "".join(f'<figure><img src="/assets/img/{n}.jpg" alt="{e(PHOTO_ALT[n])}" loading="lazy"><figcaption>{e(PHOTO_ALT[n])}</figcaption></figure>' for n in names)
    return f'''<section class="sec pg-sec pg-sec--dark"><div class="wrap">
 <h2 class="sec__h2">{e(heading)}</h2>
 <p class="sec__lead">Настоящие фото с наших выездов. Номера закрыты.</p>
 <div class="pg-photos">{figs}</div>
</div></section>'''


def business_service(name, area):
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "serviceType": "Эвакуация автомобилей",
            "provider": {"@type": "AutomotiveBusiness", "@id": SITE + "/#business", "name": "КРЮК24", "telephone": "+7-985-893-06-06", "url": SITE + "/"},
            "areaServed": area, "offers": {"@type": "Offer", "priceCurrency": "RUB", "price": "4000", "description": "Погрузка и выгрузка легкового автомобиля, плюс 100 ₽ за километр"}}


def city_page(c):
    km = c["km"]
    rows = [("Легковой автомобиль, мотоцикл", LIGHT), ("Кроссовер (паркетник)", PARK), ("Джип, минивэн, X5 / ML / Cayenne", JEEP)]
    trs = "".join(f'<tr><th scope="row">{e(n)}</th><td>{money(b)} ₽ + {km} км × {PER_KM} ₽</td><td><strong>от {money(b + PER_KM * km)} ₽</strong></td></tr>' for n, b in rows)
    sections = f'''<section class="sec pg-sec"><div class="wrap">
 <p class="pg-kicker">ЦЕНА</p>
 <h2 class="sec__h2">Сколько стоит эвакуатор {e(c["iz"])} в Москву</h2>
 <p class="sec__lead">От центра {e(c["name"] if c["name"] == "Домодедово" else c["iz"][3:])} до центра Москвы по дорогам ≈ {km} км. Считаем по тарифу: погрузка и выгрузка плюс {PER_KM} ₽ за километр.</p>
 <div class="pg-table-wrap"><table class="pg-table"><thead><tr><th scope="col">Что везем</th><th scope="col">Расчет</th><th scope="col">Итого</th></tr></thead><tbody>{trs}</tbody></table></div>
 <p class="pg-note">Это пример до центра Москвы. Если везти ближе — в сервис {e(c["v"])} или в соседний город — будет дешевле. Заблокированные колеса: тележка 1500 ₽, две — 3000 ₽. Точную сумму называем по телефону до выезда, и на месте она не меняется, если условия те же, что вы описали.</p>
 <a class="btn" href="/#zayavka">Рассчитать по своему адресу</a>
</div></section>
<section class="sec pg-sec pg-sec--paper"><div class="wrap pg-two">
 <div><p class="pg-kicker">МАРШРУТ</p><h2 class="sec__h2">Как едем {e(c["iz"])}</h2>
 <p>Обычно путь {e(c["iz"])} в Москву — {e(c["road"])}. Точный маршрут и пробки учитываем, когда называем время подачи.</p>
 <p>{e(c["note"])}</p></div>
 <div><p class="pg-kicker">ЧТО СКАЗАТЬ ПРИ ЗВОНКЕ</p><ul class="pg-list"><li>Где стоит машина {e(c["v"])}: улица, дом или километр трассы</li><li>Куда везти: сервис, дом, стоянка</li><li>Марка и модель, заводится ли</li><li>Крутятся ли колеса</li></ul></div>
</div></section>
{photos_block(c["photos"], "Так это выглядит на месте")}'''
    faq = [(f"Сколько стоит эвакуатор {c['v']}?",
            f"Легковой автомобиль — от {money(LIGHT)} ₽ за погрузку и выгрузку плюс {PER_KM} ₽ за километр. До центра Москвы ≈ {km} км — это от {money(LIGHT + PER_KM * km)} ₽. Точную сумму называем по телефону до выезда."),
           (f"Приедете {c['v']} ночью или в выходной?", "Да, заявки принимаем круглосуточно, без выходных. Время подачи называем по телефону сразу, вместе с ценой."),
           (f"Можно отвезти машину {c['iz']} в другой город?", "По Москве и Московской области — да. Междугородние перевозки — по договоренности, позвоните и обсудим.")]
    lead = f'Эвакуатор на платформе {e(c["v"])} и по всей Московской области. Погрузка и выгрузка — <b>от {money(LIGHT)} ₽</b>, плюс {PER_KM} ₽ за километр. Цену называем до выезда.'
    title = f"Эвакуатор {c['v']} — круглосуточно, от {money(LIGHT)} ₽ · КРЮК24"
    desc = f"Эвакуатор {c['v']} 24/7. Погрузка и выгрузка от {money(LIGHT)} ₽ + {PER_KM} ₽/км. {c['name']} → центр Москвы ≈ {km} км — от {money(LIGHT + PER_KM * km)} ₽ за легковой. {PHONE}"
    return page(c["slug"], title, desc, (f"Эвакуатор {c['v']}", "Круглосуточно"), lead, c["photos"][0], sections, faq,
                business_service(f"Эвакуатор {c['v']}", {"@type": "City", "name": c["name"]}), f"Здравствуйте! Нужен эвакуатор {c['v']}.", " pg-city")


def service_page(s):
    trs = "".join(f'<tr><th scope="row">{e(n)}</th><td><strong>{e(p)}</strong></td><td>{e(k)}</td></tr>' for n, p, k in s["prices"])
    when = "".join(f"<li>{e(w)}</li>" for w in s["when"])
    sections = f'''<section class="sec pg-sec"><div class="wrap pg-two">
 <div><p class="pg-kicker">КОГДА НУЖЕН</p><h2 class="sec__h2">{e(s["h1"][0])} — когда</h2><ul class="pg-list">{when}</ul></div>
 <div><p class="pg-kicker">ЦЕНА</p><h2 class="sec__h2">Тариф</h2>
 <div class="pg-table-wrap"><table class="pg-table"><tbody>{trs}</tbody></table></div>
 <p class="pg-note">Точную сумму называем по телефону до выезда. Сложная погрузка оценивается по месту — скажите заранее, что мешает.</p>
 <a class="btn" href="/#cena">Весь тариф</a></div>
</div></section>
{photos_block(s["photos"], "Наши выезды")}'''
    return page(s["slug"], s["title"], s["desc"], s["h1"], e(s["lead"]), s["photos"][0], sections, s["faq"],
                business_service(s["h1"][0], [{"@type": "City", "name": "Москва"}, {"@type": "AdministrativeArea", "name": "Московская область"}]),
                f"Здравствуйте! Нужен {s['h1'][0].lower()}.")


STUB = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://kryuk24.ru/">
<meta http-equiv="refresh" content="0; url=/">
<title>КРЮК24 — эвакуатор</title></head>
<body><p><a href="/">КРЮК24 — эвакуатор в Москве и Московской области</a></p></body></html>
"""

PAGES_CSS = """/* Страницы городов и услуг КРЮК24 (tools/make_seo_pages.py) */
.pg .hero__fig img{aspect-ratio:4/3;object-fit:cover}
.pg-crumbs{font-size:13px;color:#aab2b7;margin-bottom:18px}
.pg-crumbs a{color:#ff9c60;text-decoration:none}
.pg-lead{color:#c6cbce;font-size:17px;max-width:52ch;margin-top:22px}
.pg-lead b{color:#fff}
.pg-sec{padding-block:64px}
.pg-sec--paper{background:#F5F6F7}
.pg-sec--dark{background:var(--ink);color:#fff}
.pg-sec--dark .sec__lead{color:#b5bec3}
.pg-kicker{font-size:13px;font-weight:700;letter-spacing:.15em;color:#ab4000;margin-bottom:12px}
.pg-two{display:grid;grid-template-columns:1fr 1fr;gap:48px}
.pg-two>*{min-width:0}
.pg-two p{margin-bottom:14px;max-width:60ch}
.pg-list{padding-left:20px;margin:0 0 18px}
.pg-list li{margin-bottom:8px}
.pg-table-wrap{overflow-x:auto;margin:8px 0 18px}
.pg-table{width:100%;border-collapse:collapse;font-size:16px;min-width:420px}
.pg-table th,.pg-table td{padding:14px 12px;border-bottom:1px solid #D1D7DC;text-align:left;vertical-align:top}
.pg-table thead th{font-size:13px;color:#555d61;font-weight:700}
.pg-table td strong{font-family:var(--display);font-size:22px;white-space:nowrap}
.pg-note{font-size:14px;color:#555d61;max-width:80ch;margin-bottom:22px;padding-left:14px;border-left:2px solid var(--orange)}
.pg-photos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.pg-photos img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:8px}
.pg-photos figcaption{font-size:14px;color:#d6dde1;margin-top:10px}
.pg-links{padding-block:40px;background:#F5F6F7}
.pg-links p{margin-bottom:10px;line-height:1.9}
.pg-links a{color:var(--ink);text-underline-offset:4px}
@media (max-width:699px){
  .pg-sec{padding-block:44px}
  .pg-two{grid-template-columns:1fr;gap:28px}
  .pg-photos{grid-template-columns:1fr}
  .pg-table td strong{font-size:19px}
  .pg-table{min-width:0}
  .pg-table thead th:nth-child(2),.pg-city .pg-table td:nth-child(2){display:none}
}
.pg .faq__list{display:grid;grid-template-columns:1fr;gap:10px}
"""


def main():
    urls = []
    for c in CITIES:
        d = OUT / c["slug"]; d.mkdir(exist_ok=True)
        if c.get("live", True):
            (d / "index.html").write_text(city_page(c), encoding="utf-8", newline="\n"); urls.append(c["slug"])
        else:
            r = OUT / "_ready" / c["slug"]; r.mkdir(parents=True, exist_ok=True)
            (r / "index.html").write_text(city_page(c), encoding="utf-8", newline="\n")
            (d / "index.html").write_text(STUB, encoding="utf-8", newline="\n")
    for s in SERVICES:
        d = OUT / s["slug"]; d.mkdir(exist_ok=True)
        (d / "index.html").write_text(service_page(s), encoding="utf-8", newline="\n"); urls.append(s["slug"])
    (OUT / "assets" / "pages.css").write_text(PAGES_CSS, encoding="utf-8", newline="\n")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          f'  <url><loc>{SITE}/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>']
    sm += [f'  <url><loc>{SITE}/{u}/</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>' for u in urls]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8", newline="\n")
    print("pages:", urls)


if __name__ == "__main__":
    main()
