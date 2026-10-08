"""Private internal dashboard/report. Escapes all operator-supplied content."""
import html, json
from datetime import datetime, timedelta, timezone

YEREVAN=timezone(timedelta(hours=4));MOSCOW=timezone(timedelta(hours=3))
STATUS={'PENDING':(('Հերթում է','В очереди'),'wait'),'CLAIMED':(('Ընթացքում է','В работе'),'work'),'BLOCKED':(('Խանգարում է','Мешает'),'block'),'READY_REVIEW':(('Սպասում է քեզ','Ждет тебя'),'review'),'APPROVED':(('Հաստատված է','Одобрено'),'ok'),'DONE':(('Արված է','Сделано'),'ok')}
TRUST={'MACHINE_OBSERVED':('ստուգել է սերվերն ինքը','проверил сам сервер'),'OPERATOR_REPORTED':('կարդացել է կատարողը էկրանից','исполнитель прочитал с экрана')}
ACTIONS={'REPORT_DRAFT':('Հաշվետվության սևագիր','Черновик отчета'),'PHOTO_BATCH':('Նկարների խումբ','Набор фото'),'PUBLICATION':('Հրապարակում','Публикация'),'MESSAGE':('Հաղորդագրություն','Сообщение'),'AD_CHANGE':('Գովազդի փոփոխություն','Изменение рекламы')}
JOBS={'LOCAL_LEDGER':('book',('Մատյան','Журнал')),'RUNTIME_HEALTH':('server',('Սերվեր','Сервер')),'YANDEX_BUSINESS':('pin',('Քարտ','Карточка')),'YANDEX_DIRECT':('horn',('Գովազդ','Реклама')),'METRICA':('bars',('Մետրիկա','Метрика')),'WEBMASTER':('search',('Որոնում','Поиск')),'AVITO':('tag',('Ավիտո','Авито')),'HOSTING_DEADLINES':('card',('Հոսթինգ','Хостинг')),'MEDIA_INBOX':('camera',('Նկարներ','Фото')),'DAILY_REPORT':('doc',('Հաշվետվություն','Отчет'))}
TITLES={'LOCAL_LEDGER':('Մատյանի ամփոփում','Сводка журнала'),'RUNTIME_HEALTH':('Սերվերի վիճակ','Состояние сервера'),'YANDEX_BUSINESS':('Քարտ, կարծիքներ, մոդերացիա','Карточка, отзывы, модерация'),'YANDEX_DIRECT':('Գովազդի վիճակ և ծախս','Реклама: состояние и расход'),'METRICA':('Նպատակների թվեր','Цели Метрики'),'WEBMASTER':('Ինդեքսավորում','Индексация'),'AVITO':('Հայտարարությունների վիճակ','Объявления Авито'),'HOSTING_DEADLINES':('Վճար և ժամկետներ','Оплата и сроки'),'MEDIA_INBOX':('Նոր իրական նկարներ','Новые настоящие фото'),'DAILY_REPORT':('Օրվա հաշվետվության պատրաստում','Подготовка отчета за день')}
GROUPS=((('Քեզնից սպասվում է','Ждет тебя'),('READY_REVIEW',)),(('Խանգարում է','Мешает'),('BLOCKED',)),(('Դեռ անելու','Еще впереди'),('CLAIMED','PENDING')),(('Արված է','Сделано'),('APPROVED','DONE')))
MONTHS=('հունվարի','փետրվարի','մարտի','ապրիլի','մայիսի','հունիսի','հուլիսի','օգոստոսի','սեպտեմբերի','հոկտեմբերի','նոյեմբերի','դեկտեմբերի')
MONTHS_RU=('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря')
KEYS={'period':('Ժամանակահատված','Период'),'timezone':('Ժամային գոտի','Часовой пояс'),'recorded_contact_clicks':('Գրանցված սեղմումներ','Записанные нажатия'),'recorded_forms':('Գրանցված հայտեր','Записанные заявки'),'operator_reported_phone_records':('Զանգերի գրառումներ','Записи о звонках'),'test_excluded':('Թեստայինները հանված են','Тестовые исключены'),'meaning':('Ինչ է նշանակում','Что это значит'),'http_status':('Սերվերի պատասխան','Ответ сервера'),'mode':('Ռեժիմ','Режим'),'sending_enabled':('Ուղարկումը միացված է','Отправка включена'),'scope':('Ինչ է ստուգվել','Что проверено'),'date':('օր','день'),'call':('զանգ','звонок'),'wa':('WhatsApp','WhatsApp'),'tg':('Telegram','Telegram')}
VALUES={'Recorded rows only; click is not a call/message. Tracking not live: zero is not zero actual demand. Revenue/profit UNKNOWN.':('Միայն գրանցված տողերն են․ սեղմումը զանգ կամ հաղորդագրություն չէ։ Հաշվառումը կենդանի կայքին միացված չէ, ուստի զրոն չի նշանակում, որ դիմում չի եղել։ Եկամուտն ու շահույթը անհայտ են։','Только записанные строки: нажатие не равно звонку или сообщению. Учет не подключен к живому сайту, поэтому ноль не значит, что обращений не было. Выручка и прибыль неизвестны.'),
        'Process endpoint only; not public HTTPS, database writability or message delivery':('Ստուգվել է միայն ծառայության ներքին հասցեն, ոչ թե հանրային HTTPS-ը, բազայում գրելը կամ հաղորդագրության հասնելը։','Проверен только внутренний адрес службы, а не публичный HTTPS, запись в базу или доставка сообщений.'),
        'Europe/Moscow':('Մոսկվա','Москва'),'STAGING':('փորձնական','тестовый'),'LIVE_CAPTURE':('կենդանի','боевой'),'local SQLite / recorded ledger':('սերվերի բազա, գրանցված մատյան','база сервера, записанный журнал'),'loopback /health':('ծառայության ներքին ստուգում','внутренняя проверка службы')}
_S='<svg viewBox="0 0 24 24" width="{0}" height="{0}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{1}</svg>'
PATHS={'book':'<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/><path d="M9 8h6"/>',
 'server':'<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6"/>',
 'pin':'<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
 'horn':'<path d="M4 10v4a1 1 0 0 0 1 1h2l6 4V5L7 9H5a1 1 0 0 0-1 1z"/><path d="M17 9a4 4 0 0 1 0 6"/>',
 'bars':'<path d="M3 20h18"/><path d="M6 20v-8M12 20V5M18 20v-6"/>',
 'search':'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
 'tag':'<path d="M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9z"/><circle cx="8" cy="8" r="1.4"/>',
 'card':'<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 10h18M7 15h4"/>',
 'camera':'<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/>',
 'doc':'<path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
 'dot':'<circle cx="12" cy="12" r="3"/>',
 'ok':'<path d="M5 12.5l4.5 4.5L19 7.5"/>','block':'<path d="M12 6.5v7M12 17h.01"/>','review':'<path d="M5 12h14M13 6l6 6-6 6"/>','work':'<path d="M12 7v5l3 2"/><circle cx="12" cy="12" r="8"/>','wait':'<circle cx="12" cy="12" r="8"/>',
 'sun':'<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>',
 'moon':'<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
 'close':'<path d="M6 6l12 12M18 6L6 18"/>','clock':'<circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 2"/>',
 'hook':'<circle cx="12.5" cy="5" r="2.9"/><path d="M12.5 8v6.2a4.6 4.6 0 1 1-7.8-3.3"/>'}
LOGO='data:image/webp;base64,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'
ORDER={'READY_REVIEW':0,'BLOCKED':1,'CLAIMED':2,'PENDING':3,'APPROVED':4,'DONE':5}
AVATAR='data:image/webp;base64,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'
def icon(name,size=22):return _S.format(size,PATHS.get(name,PATHS['dot']))
CSS='''
:root{color-scheme:light;
--neutral-0:var(--grey-0,#ffffff);--neutral-50:var(--grey-50,#f4f6f8);--neutral-100:var(--grey-100,#eef1f4);--neutral-200:var(--grey-200,#dde3ea);--neutral-300:var(--grey-300,#c5cdd7);--neutral-400:var(--grey-400,#9aa6b6);--neutral-500:var(--grey-600,#5a6676);--neutral-700:var(--grey-700,#3e4a5a);--neutral-800:var(--navy-800,#1c3150);--neutral-900:var(--navy-900,#13233a);--neutral-950:var(--navy-950,#0b1524);
--orange-300:#f18a4b;--orange-350:#ff8a4c;--orange-400:#ff7424;--orange-500:#ef5b00;--orange-700:#a33d00;
--bg:var(--neutral-50);--card:var(--neutral-0);--soft:var(--neutral-50);--elev:var(--neutral-0);
--text:var(--neutral-900);--text2:var(--neutral-700);--muted:var(--neutral-500);--inverse:var(--neutral-0);--on-action:var(--neutral-900);
--line:var(--neutral-200);--line2:var(--neutral-300);
--action:var(--orange-500);--action-strong:var(--orange-700);--accent:var(--orange-300);--accent-soft:rgba(239,91,0,.10);--focus:var(--orange-500);
--ok:#166534;--okbg:rgba(22,163,74,.12);--okfill:#16a34a;
--wait:var(--neutral-500);--waitbg:var(--neutral-100);
--block:#b91c1c;--blockbg:rgba(239,68,68,.10);--blockfill:#ef4444;
--review:#92400e;--reviewbg:rgba(245,158,11,.14);--reviewfill:#f59e0b;
--work:#2a4466;--workbg:rgba(19,35,58,.08);
--hover:rgba(19,35,58,.06);--selected:rgba(239,91,0,.12);--overlay:rgba(11,21,36,.56);
--grad:linear-gradient(var(--action),var(--action));
--shadow-sm:0 1px 2px rgba(19,35,58,.08);--shadow:0 12px 30px rgba(19,35,58,.10);--shadow-lg:0 24px 70px rgba(19,35,58,.16);
--glow:0 0 0 3px rgba(239,91,0,.18);--shadow-hover:0 18px 44px rgba(19,35,58,.14);
--r-card:24px;--r-lg:12px;--r-xl:16px;--r-pill:999px;
--ease:cubic-bezier(.2,0,0,1);--fast:150ms;--base:240ms;--slow:420ms}
html[data-theme=dark]{color-scheme:dark;
--bg:var(--neutral-950);--card:var(--neutral-900);--soft:var(--neutral-800);--elev:var(--neutral-800);
--text:var(--neutral-0);--text2:var(--neutral-200);--muted:var(--neutral-400);--inverse:var(--neutral-950);
--line:rgba(255,255,255,.10);--line2:rgba(241,138,75,.32);
--action:var(--orange-500);--action-strong:var(--orange-350);--accent:var(--orange-300);--accent-soft:rgba(241,138,75,.14);--focus:var(--orange-300);
--ok:#4ade80;--okbg:rgba(34,197,94,.16);--wait:var(--neutral-400);--waitbg:rgba(255,255,255,.06);
--block:#f87171;--blockbg:rgba(239,68,68,.16);--review:#fbbf24;--reviewbg:rgba(245,158,11,.16);--work:var(--neutral-300);--workbg:rgba(255,255,255,.06);
--hover:rgba(255,255,255,.06);--selected:rgba(241,138,75,.16);--overlay:rgba(3,8,16,.72);
--glow:0 0 0 3px rgba(241,138,75,.24);--shadow-hover:0 18px 44px rgba(0,0,0,.45);--shadow:0 12px 30px rgba(0,0,0,.35);--shadow-lg:0 24px 70px rgba(0,0,0,.5)}
*{box-sizing:border-box}
body{font:16px/1.5 var(--font-sans,"Inter","Noto Sans Armenian",system-ui,-apple-system,"Segoe UI",sans-serif);background:var(--bg);color:var(--text);margin:0;-webkit-font-smoothing:antialiased}
svg{flex:none;vertical-align:middle}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.wrap{max-width:960px;margin:auto;padding:0 20px 56px}
/* top: dark navy contrast band in both themes, grid + soft orange spotlight (KRYUK24 colours) */
.top{position:relative;color:var(--neutral-0);padding-bottom:72px;background-color:var(--neutral-950);
 background-image:radial-gradient(90% 140% at 100% 0%,rgba(239,91,0,.20) 0%,transparent 55%),radial-gradient(70% 120% at 0% 100%,rgba(241,138,75,.10) 0%,transparent 55%),linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
 background-size:auto,auto,48px 48px,48px 48px}
.top .wrap{display:flex;flex-wrap:wrap;gap:18px 24px;align-items:center;justify-content:space-between;padding:28px 20px 0}
.brand{display:flex;align-items:center;gap:14px}
.logo{width:52px;height:52px;border-radius:var(--r-pill);background:var(--orange-500);color:var(--neutral-900);display:grid;place-items:center}
.brand b{display:block;font-size:24px;line-height:1.15;font-weight:700;letter-spacing:-.02em}
.brand div>span{font-size:13px;color:var(--neutral-400);letter-spacing:.02em}
.bar0{flex-basis:100%;display:flex;align-items:center;gap:14px;padding-bottom:18px;margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,.08)}
.klogo{height:44px;width:auto;display:block;border:0;border-radius:0;max-width:none;margin-right:auto}
.avatar{border:0;max-width:none;width:56px;height:56px;border-radius:var(--r-pill);display:block;object-fit:cover;padding:2px;background:var(--orange-500)}
.bro{position:relative;display:block}.bro i{position:absolute;left:50%;bottom:-8px;transform:translateX(-50%);font-style:normal;font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--neutral-900);background:var(--orange-500);border-radius:var(--r-pill);padding:1px 7px}
.clocks{display:flex;gap:8px}
.clock{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(18px);border-radius:var(--r-xl);padding:8px 16px;min-width:120px}
.clock small{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:11px;font-weight:600;color:var(--neutral-400);letter-spacing:.12em;text-transform:uppercase}
.clock strong{font-size:26px;line-height:1.15;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.clock .sun{color:var(--orange-300)}.clock .moon{color:var(--neutral-300)}
.clock .moon,.clock.night .sun{display:none}.clock.night .moon{display:inline}
/* hero: premium card overlapping the band */
.hero{position:relative;isolation:isolate;overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:var(--r-card);padding:24px 26px;margin-top:-48px;box-shadow:var(--shadow-lg);display:grid;grid-template-columns:auto 1fr;gap:6px 26px;align-items:center}
.hero::before,.tile::before,.card::before{content:"";position:absolute;inset:0 0 auto;height:1px;z-index:-1;background:linear-gradient(90deg,transparent,var(--line2),transparent)}
.ring{position:relative;width:112px;height:112px}
.ring svg{transform:rotate(-90deg)}
.ring circle{fill:none;stroke-width:10}
.ring .bgc{stroke:var(--waitbg)}.ring .fg{stroke:url(#ringgrad);stroke-linecap:round;animation:grow .9s var(--ease);filter:none}
.ring b{position:absolute;inset:0;display:grid;place-items:center;font-size:26px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
@keyframes grow{from{stroke-dashoffset:var(--full)}}
.hero h1{font-size:24px;line-height:1.2;margin:0 0 4px;font-weight:700;letter-spacing:-.02em}
.hero p{margin:0;color:var(--text2);font-size:15px}
.sum{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:var(--r-pill);padding:4px 12px;font-size:13px;font-weight:600;letter-spacing:.02em;white-space:nowrap}.pill.sm{padding:2px 9px;font-size:12px;gap:4px;margin-top:2px}button.next{margin-top:14px}@media (max-width:620px){button.next{width:100%}}
.ok{background:var(--okbg);color:var(--ok)}.wait{background:var(--waitbg);color:var(--wait)}.block{background:var(--blockbg);color:var(--block)}.review{background:var(--reviewbg);color:var(--review)}.work{background:var(--workbg);color:var(--work)}
.bar{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:16px;align-items:center;border-top:1px solid var(--line);margin-top:18px;padding-top:18px}.bar a{display:inline-flex;align-items:center;min-height:44px}
h2{display:flex;align-items:center;gap:12px;font-size:12px;margin:36px 0 12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h2::after{content:"";flex:0 0 40px;height:1px;background:linear-gradient(90deg,var(--line2),transparent)}
.hint{margin:0 0 10px;color:var(--muted);font-size:14px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.tile{position:relative;isolation:isolate;overflow:hidden;display:flex;flex-direction:column;align-items:center;gap:6px;width:100%;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 10px 14px;text-align:center;color:var(--text);font:inherit;font-weight:400;cursor:pointer;box-shadow:var(--shadow-sm);
 transition:transform var(--slow) var(--ease),box-shadow var(--slow) var(--ease),border-color var(--slow) var(--ease)}
button.tile{height:auto;border-radius:20px;font-size:inherit}button.tile:hover,button.tile:focus-visible{transform:translateY(-4px);box-shadow:var(--shadow-hover);border-color:var(--line2);filter:none}
.tile .ico{width:46px;height:46px;border-radius:14px;display:grid;place-items:center}
.tile .nm{font-size:15px;font-weight:600;line-height:1.25}
.tile .st{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.tile:has(.pill.review){border-color:var(--review)}.tile:has(.pill.block){border-color:var(--block)}.tile:has(.pill.ok){background:transparent;box-shadow:none}.tile:has(.pill.ok) .nm{color:var(--text2);font-weight:500}
.tile.wide{flex-direction:row;text-align:left;padding:18px 20px;gap:16px;border-color:var(--review);box-shadow:0 0 0 4px var(--reviewbg),var(--shadow)}
.tile.wide .nm{font-size:17px}.tile.wide .go{margin-left:auto;flex:none;width:40px;height:40px;border-radius:var(--r-pill);display:grid;place-items:center;background:var(--grad);color:var(--on-action)}
.list{display:grid;gap:12px}
.card{position:relative;isolation:isolate;overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:var(--r-card);margin:12px 0;overflow-wrap:anywhere;box-shadow:var(--shadow-sm)}
.head{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;justify-content:space-between;padding:18px 22px}
.head h3{font-size:18px;line-height:1.3;margin:0;font-weight:600;display:flex;align-items:center;gap:12px}
.inner{padding:0 22px 20px}
.meta,.tech{color:var(--muted);font-size:13px}.meta{margin:6px 0;display:flex;gap:8px;align-items:flex-start}
.obs{border-top:1px solid var(--line);padding-top:12px;margin-top:6px}.obs:first-child{border-top:0;padding-top:0}
.facts{margin:10px 0 0;display:grid;grid-template-columns:minmax(120px,max-content) 1fr;gap:6px 16px;font-size:15px}
.facts dt{color:var(--muted);font-size:13px;padding-top:2px}.facts dd{margin:0}
.body{background:var(--soft);border:1px solid var(--line);border-radius:var(--r-lg);padding:12px 14px;white-space:pre-wrap;margin:10px 0;font-size:15px;line-height:1.6}
.draft{border:1px solid var(--line2);background:var(--accent-soft);border-radius:var(--r-xl);padding:14px 16px;margin:0 0 14px}
.draft .body{background:var(--card)}
.from{display:flex;align-items:center;gap:10px;margin-bottom:6px;font-size:13px;color:var(--muted)}.from img{width:32px;height:32px;border-radius:var(--r-pill);border:0;max-width:none;padding:2px;background:var(--orange-500)}.from b{color:var(--text);font-size:15px}
.techbox{margin-top:14px}.techbox summary{cursor:pointer;color:var(--muted);font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase}
.tech{font-family:"JetBrains Mono",ui-monospace,Consolas,monospace;font-size:12px;margin:6px 0 0}
dialog{border:1px solid var(--line);border-radius:var(--r-card);padding:0;width:min(700px,calc(100vw - 24px));max-height:calc(100vh - 32px);background:var(--elev);color:var(--text);box-shadow:var(--shadow-lg)}
dialog::backdrop{background:var(--overlay);backdrop-filter:blur(4px)}
dialog[open]{display:flex;flex-direction:column;animation:pop var(--base) var(--ease)}
@keyframes pop{from{transform:translateY(12px) scale(.98);opacity:0}}
.mhead{display:flex;align-items:center;gap:12px;padding:18px 22px;border-bottom:1px solid var(--line)}
.mhead h3{font-size:18px;margin:0;font-weight:600;flex:1;line-height:1.3}
.mhead .ico{width:42px;height:42px;border-radius:14px;display:grid;place-items:center}
.mbody{padding:18px 22px 22px;overflow:auto}
.x{background:transparent;color:var(--muted);border:0;padding:0;width:44px;height:44px;border-radius:var(--r-pill);display:grid;place-items:center}
.x:hover{background:var(--soft);color:var(--text);transform:none;box-shadow:none}
input,textarea{font:inherit;font-size:15px;padding:12px 14px;max-width:100%;border-radius:var(--r-lg);border:1px solid var(--line);color:inherit;background:var(--card);box-shadow:var(--shadow-sm);transition:border-color var(--fast) var(--ease),box-shadow var(--fast) var(--ease)}
input:focus,textarea:focus{outline:none;border-color:var(--focus);box-shadow:0 0 0 3px var(--selected)}
input[type=checkbox]{width:18px;height:18px;accent-color:var(--action);box-shadow:none;vertical-align:-3px;margin-right:6px}
label{display:block;margin:12px 0;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
label input:not([type=checkbox]),label textarea{display:block;margin-top:6px;text-transform:none;letter-spacing:0;font-weight:400;color:var(--text)}
input:not([type=checkbox]),textarea{width:100%}textarea{min-height:110px}
button{font:inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;height:48px;padding:0 22px;border-radius:var(--r-pill);border:0;background:var(--grad);color:var(--on-action);font-weight:600;font-size:16px;
 transition:transform var(--base) var(--ease),box-shadow var(--base) var(--ease),background var(--base) var(--ease)}
button:hover{transform:translateY(-2px);box-shadow:var(--glow);background:var(--orange-400)}
button.second,button.second:hover{background:var(--soft);color:var(--text);border:1px solid var(--line);box-shadow:var(--shadow-sm)}
button.second:hover{border-color:var(--line2);box-shadow:var(--shadow-sm)}
button:disabled{opacity:.5;cursor:not-allowed;transform:none}
a{color:var(--action-strong);font-weight:600;text-decoration:none}a:hover{text-decoration:underline}
img{max-width:320px;max-height:240px;border-radius:var(--r-lg);border:1px solid var(--line)}
.old{margin-top:32px}.old>summary{cursor:pointer;font-weight:600;color:var(--text2)}
.day{font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:20px 0 10px}
.note{font-size:12px;color:var(--muted);border-top:1px solid var(--line);margin-top:40px;padding-top:14px}
#status{color:var(--block);font-weight:600;margin:6px 0 0;grid-column:1/-1}
.ru{display:none}html[data-lang=ru] .ru{display:revert}html[data-lang=ru] .hy{display:none}
.side{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:flex-end}
.lang{display:flex;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:var(--r-pill);padding:4px;gap:2px}
.lang button{background:transparent;color:var(--neutral-400);height:34px;padding:0 14px;font-size:13px;letter-spacing:.04em;box-shadow:none}
.lang button[aria-pressed=true]{background:rgba(255,255,255,.14);color:var(--neutral-0)}
.lang button:hover{transform:none;box-shadow:none;color:var(--neutral-0)}
.theme{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:var(--neutral-400);height:44px;width:44px;padding:0;box-shadow:none}.theme:hover{color:var(--neutral-0);transform:none;box-shadow:none}
.theme .sun,html[data-theme=dark] .theme .moon{display:none}html[data-theme=dark] .theme .sun{display:inline}
@media (max-width:760px){.grid{grid-template-columns:repeat(3,1fr)}}
@media (max-width:620px){body{font-size:15px}.side{width:100%;justify-content:space-between}.clocks{flex:1}.clock{flex:1;min-width:0;padding:6px 12px}.clock strong{font-size:20px}.hero{grid-template-columns:1fr;padding:20px}.ring{width:88px;height:88px}.ring b{font-size:21px}.grid{grid-template-columns:1fr;gap:8px}.tile{flex-direction:row;text-align:left;padding:10px 14px;gap:12px;border-radius:14px}.tile .ico{width:36px;height:36px;border-radius:10px}.tile .nm{flex:1;min-width:0}.tile .pill.sm{margin-top:0}.tile .st{min-width:40px;text-align:right}.tile.wide{padding:14px 16px}.facts{grid-template-columns:1fr}.facts dt{margin-top:6px}.head{padding:14px 16px}.inner{padding:0 16px 16px}.wrap{padding-left:16px;padding-right:16px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
'''

def _parse(value):
 try:
  t=datetime.fromisoformat(value)
  return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t
 except (TypeError,ValueError):return None

def _esc(x):return html.escape(str(x),quote=True)

def L(hy,ru,tag='span'):
 """Both languages in the page; CSS shows one. Content is escaped here."""
 return '<'+tag+' class="hy" lang="hy">'+_esc(hy)+'</'+tag+'><'+tag+' class="ru" lang="ru">'+_esc(ru)+'</'+tag+'>'

def P(pair,tag='span'):return L(pair[0],pair[1],tag)

def _both(text):
 """Stored text may be plain, or JSON {"hy": "...", "ru": "..."} written by the operator."""
 try:data=json.loads(text)
 except (TypeError,ValueError):data=None
 if isinstance(data,dict) and set(data)=={'hy','ru'} and all(isinstance(v,str) for v in data.values()):return data['hy'],data['ru']
 return None

def _text(text,tag='span'):
 pair=_both(text)
 if pair:return L(pair[0],pair[1],tag)
 known=VALUES.get(str(text))
 if known:return L(known[0],known[1],tag)
 return '<'+tag+'>'+_esc(text)+'</'+tag+'>'

def _when(value):
 t=_parse(value)
 if t is None:return _esc(value)
 y=t.astimezone(YEREVAN);m=t.astimezone(MOSCOW)
 return _esc(y.strftime('%d.%m')+' · '+y.strftime('%H:%M'))+' '+L('Երևան','Ереван')+' · '+_esc(m.strftime('%H:%M'))+' '+L('Մոսկվա','Москва')

def _greeting(hour):
 return ('Բարի լույս','Доброе утро') if 5<=hour<12 else ('Բարի օր','Добрый день') if 12<=hour<18 else ('Բարի երեկո','Добрый вечер') if 18<=hour<23 else ('Բարի գիշեր','Доброй ночи')

def _value(value,lang):
 if isinstance(value,bool):return (('այո','да') if value else ('ոչ','нет'))[lang]
 if isinstance(value,dict):return ' · '.join(KEYS.get(str(k),(str(k),str(k)))[lang]+' '+_value(v,lang) for k,v in value.items())
 if isinstance(value,list):return ', '.join(_value(v,lang) for v in value)
 return VALUES.get(str(value),(str(value),str(value)))[lang]

def _summary(text):
 pair=_both(text)
 if pair:return L(pair[0],pair[1],'div').replace('class="hy"','class="hy body"').replace('class="ru"','class="ru body"')
 try:data=json.loads(text)
 except (TypeError,ValueError):data=None
 if isinstance(data,dict):
  return '<dl class="facts">'+''.join('<dt>'+P(KEYS.get(str(k),(str(k),str(k))))+'</dt><dd>'+L(_value(v,0),_value(v,1))+'</dd>' for k,v in data.items())+'</dl>'
 return '<div class="body">'+_esc(text)+'</div>'

def _look(task):
 label,kind=STATUS.get(task['status'],((task['status'],task['status']),'wait'))
 plain=str(task['title']).partition(' / ')[0]
 name=TITLES.get(task.get('job'),(plain,plain))
 ico,short=JOBS.get(task.get('job'),('dot',name))
 stamp=_parse(task['observations'][-1]['observed_at']) if task['observations'] else None
 return label,kind,name,ico,short,stamp

def _inner(task,report,interactive):
 e=_esc;out=[]
 if task['lease_expired']:out.append('<p class="meta">'+L('Կատարողի ժամանակը լրացել է․ կարդալու կամ պատրաստելու աշխատանքը կարելի է նորից վերցնել։','Время исполнителя истекло: задачу на чтение или подготовку можно взять снова.')+'</p>')
 if task['draft']:
  d=task['draft'];act=ACTIONS.get(d['action'],(d['action'],d['action']))
  out.append('<div class="draft"><div class="from"><img src="'+AVATAR+'" alt="" width="32" height="32"><b>Bro</b><span>'+L('պատրաստել է սևագիրը','подготовил черновик')+'</span></div><dl class="facts"><dt>'+L('Ինչ է','Что это')+'</dt><dd>'+P(act)+'</dd><dt>'+L('Որտեղից','Откуда')+'</dt><dd>'+_text(d['account'])+'</dd><dt>'+L('Ում','Кому')+'</dt><dd>'+_text(d['destination'])+'</dd></dl><div class="body">'+e(d['body'])+'</div>')
  for asset in d.get('assets',[]):
   if interactive:out.append('<img src="/operator/media/'+e(asset['id'])+'" alt=""><p class="tech">'+e(asset['id'])+' / '+e(asset['sha256'])+'</p>')
   else:out.append('<p class="tech">'+e(asset['id'])+' / '+e(asset['sha256'])+'</p>')
  out.append('</div>')
 for obs in task['observations']:
  seen=_parse(obs['observed_at']);age=(datetime.now(timezone.utc)-seen).total_seconds() if seen else 0
  trust=TRUST.get(obs['trust'],(obs['trust'],obs['trust']))
  out.append('<div class="obs"><p class="meta">'+icon('clock',18)+'<span>'+_when(obs['observed_at'])+'<br>'+_text(obs['source'])+' · '+P(trust)+(' · <strong>'+L('հին է, 24 ժամից ավելի','старше 24 часов')+'</strong>' if age>86400 else '')+'</span></p>'+_summary(obs['summary'])+'</div>')
 if not task['observations'] and not task['draft']:out.append('<p class="meta">'+L('Դիտարկում դեռ չկա։','Наблюдений пока нет.')+'</p>')
 if interactive:
  tid=e(task['id'])
  if task['status'] in ('PENDING','BLOCKED') or task['lease_expired']:out.append('<p><button class="second" data-claim="'+tid+'">'+L('Վերցնել աշխատանքը','Взять задачу')+'</button></p>')
  if task['status']=='CLAIMED' and task['worker']=='AUTHENTICATED_OPERATOR' and not task['lease_expired']:out.append('<form data-observe="'+tid+'"><label>'+L('Աղբյուր','Источник')+' <input name="source" required maxlength="500"></label><label>'+L('Դիտարկման պահը','Время наблюдения')+' <input name="observed_at" value="'+e(report['generated'])+'" required></label><label>'+L('Ինչ է իրականում ստուգվել կամ ինչն է խանգարում','Что на самом деле проверено или что мешает')+' <textarea name="summary" required maxlength="4000"></textarea></label><label><input type="checkbox" name="blocked"> '+L('Խանգարում է, չի արվել','Мешает, не сделано')+'</label><button>'+L('Գրանցել արդյունքը','Записать результат')+'</button></form>')
  if task['status']=='READY_REVIEW':out.append('<form data-approve="'+tid+'" data-digest="'+e(task['digest'])+'"><button>'+L('Հաստատել այս տարբերակը','Одобрить этот вариант')+'</button></form>')
  if task['status']=='APPROVED':out.append('<p class="meta">'+L('Հաստատված է','Одобрено')+'</p>')
 out.append('<details class="techbox"><summary>'+L('Տեխնիկական','Техническое')+'</summary><p class="tech">'+e(task['id'])+' · '+e(task['job'])+' · '+e(task['status'])+(' · SHA256 '+e(task['digest']) if task.get('digest') else '')+'</p></details>')
 return ''.join(out)

def _tile(task,interactive,wide=False):
 e=_esc;label,kind,name,ico,short,stamp=_look(task)
 time=e(' · '+stamp.astimezone(YEREVAN).strftime('%H:%M')) if stamp else ''
 body='<span class="ico '+kind+'">'+icon(ico,24)+'</span>'+('<span><span class="nm">'+P(name)+'</span><br><span class="st">'+P(label)+time+'</span></span><span class="go">'+icon('review',20)+'</span>' if wide else '<span class="nm">'+P(short)+'</span><span class="pill sm '+kind+'">'+icon(kind,13)+P(label)+'</span>'+('<span class="st">'+e(stamp.astimezone(YEREVAN).strftime('%H:%M'))+'</span>' if stamp else ''))
 cls='tile wide' if wide else 'tile'
 if interactive:return '<button type="button" class="'+cls+'" data-open="m-'+e(task['id'])+'">'+body+'</button>'
 return '<div class="'+cls+'">'+body+'</div>'

def _static_card(task,report):
 label,kind,name,ico,short,stamp=_look(task)
 return '<div class="card"><div class="head"><h3><span class="'+kind+'" style="border-radius:10px;padding:6px;display:grid">'+icon(ico,20)+'</span>'+P(name)+'</h3><span class="pill '+kind+'">'+P(label)+'</span></div><div class="inner">'+_inner(task,report,False)+'</div></div>'

def _modal(task,report):
 e=_esc;label,kind,name,ico,short,stamp=_look(task)
 return '<dialog id="m-'+e(task['id'])+'" aria-label="'+e(name[0])+'"><div class="mhead"><span class="ico '+kind+'">'+icon(ico,22)+'</span><h3>'+P(name)+'</h3><span class="pill '+kind+'">'+P(label)+'</span><button type="button" class="x" data-close aria-label="Փակել / Закрыть">'+icon('close',20)+'</button></div><div class="mbody">'+_inner(task,report,True)+'</div></dialog>'

def _headline(total,done,review,blocked,left):
 hy=[];ru=[]
 if review:hy.append(str(review)+'-ը սպասում է քեզ');ru.append(str(review)+' ждет тебя')
 if blocked:hy.append(str(blocked)+'-ին բան է խանգարում');ru.append(str(blocked)+': что-то мешает')
 if left:hy.append(str(left)+'-ը դեռ անելու է');ru.append(str(left)+' еще впереди')
 head=('Այսօր '+str(total)+' գործից '+str(done)+'-ը արված է','Сегодня сделано '+str(done)+' из '+str(total)) if done<total else ('Այսօրվա բոլոր '+str(total)+' գործը արված է','Сегодня сделано все: '+str(total)+' из '+str(total))
 sub=(', '.join(hy)+'։',', '.join(ru)+'.') if hy else ('Քեզնից ոչինչ չի սպասվում։','От тебя ничего не ждут.')
 return head,sub

def dashboard(report,interactive=True):
 e=_esc
 tasks=report['tasks'];made=_parse(report['generated']) or datetime.now(timezone.utc)
 y=made.astimezone(YEREVAN);m=made.astimezone(MOSCOW)
 days=[]
 for task in tasks:
  if task['day'] not in days:days.append(task['day'])
 today=[t for t in tasks if days and t['day']==days[0]]
 count=lambda *names:sum(t['status'] in names for t in today)
 total=len(today);done=count('DONE','APPROVED');review=count('READY_REVIEW');blocked=count('BLOCKED');left=count('PENDING','CLAIMED')
 night=lambda hour:'' if 7<=hour<19 else ' night'
 clock=lambda key,name,t:'<div class="clock'+night(t.hour)+'" id="box-'+key+'"><small>'+P(name)+'<span><span class="sun">'+icon('sun',15)+'</span><span class="moon">'+icon('moon',15)+'</span></span></small><strong id="clock-'+key+'">'+e(t.strftime('%H:%M'))+'</strong></div>'
 hello=_greeting(y.hour)
 out=['<!doctype html><html lang="hy" data-lang="hy" data-theme="light"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>КРЮК24 — աշխատանքների հերթ</title><style>'+CSS+'</style><link rel="stylesheet" href="/operator/work/armen/tokens.css"><link rel="stylesheet" href="/operator/work/armen/fonts.css">']
 switch='<div class="lang" role="group" aria-label="Լեզու / Язык"><button type="button" data-lang="hy" aria-pressed="true">Հայ</button><button type="button" data-lang="ru" aria-pressed="false">Рус</button></div><button type="button" class="theme" id="theme" aria-label="Բաց / մուգ · Светлая / темная"><span class="moon">'+icon('moon',18)+'</span><span class="sun">'+icon('sun',18)+'</span></button>' if interactive else ''
 out.append('<div class="top"><div class="wrap"><div class="bar0"><img class="klogo" src="'+LOGO+'" alt="КРЮК24 · эвакуатор" width="130" height="44">'+switch+'</div><div class="brand"><span class="bro"><img class="avatar" src="'+AVATAR+'" alt="Bro" width="56" height="56"><i>Bro</i></span><div><b id="hello">'+L(hello[0]+', Գև',hello[1]+', Гев')+'</b><span>'+L('աշխատանքների հերթ','очередь работ')+' · '+L(str(y.day)+' '+MONTHS[y.month-1],str(y.day)+' '+MONTHS_RU[y.month-1])+'</span></div></div><div class="side"><div class="clocks">'+clock('yerevan',('Երևան','Ереван'),y)+clock('moscow',('Մոսկվա','Москва'),m)+'</div></div></div></div><div class="wrap">')
 if total:
  head,sub=_headline(total,done,review,blocked,left)
  full=263.89;gap=round(full*(1-done/total),2)
  out.append('<div class="hero"><div class="ring" style="--full:'+e(full)+'"><svg viewBox="0 0 100 100" width="100%" height="100%"><defs><linearGradient id="ringgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ef5b00"/><stop offset="1" stop-color="#f18a4b"/></linearGradient></defs><circle class="bgc" cx="50" cy="50" r="42"/><circle class="fg" cx="50" cy="50" r="42" stroke-dasharray="'+e(full)+'" stroke-dashoffset="'+e(gap)+'"/></svg><b>'+e(done)+'/'+e(total)+'</b></div><div><h1>'+P(head)+'</h1>'+('' if review or blocked else '<p>'+L('Քեզնից ոչինչ չի սպասվում։','От тебя ничего не ждут.')+'</p>')+'<div class="sum">')
  for status in ('READY_REVIEW','BLOCKED','CLAIMED','PENDING','APPROVED','DONE'):
   if count(status):out.append('<span class="pill '+STATUS[status][1]+'">'+icon(STATUS[status][1],15)+e(count(status))+' · '+P(STATUS[status][0])+'</span>')
  first=[t for t in today if t['status']=='READY_REVIEW']
  out.append('</div>'+('<button type="button" class="next" data-open="m-'+e(first[0]['id'])+'">'+icon('review',18)+L('Բացել՝ '+_look(first[0])[4][0],'Открыть: '+_look(first[0])[4][1])+'</button>' if interactive and first else '')+'</div>')
 else:out.append('<div class="hero"><div class="ring"><b>—</b></div><div><h1>'+L('Հերթը դեռ չի ստեղծվել','Очередь еще не создана')+'</h1><p>'+L('Սա ստուգված օր չէ։','Этот день не проверен.')+'</p></div>')
 if interactive:out.append('<div class="bar"><button id="plan"'+(' class="second"' if total else '')+'>'+L('Ստեղծել այսօրվա հերթը','Создать очередь на сегодня')+'</button><a href="/operator">'+L('Հայտերի մատյան','Журнал заявок')+'</a></div><p id="status" role="status"></p>')
 out.append('</div>')
 if interactive:
  waiting=[t for t in today if t['status']=='READY_REVIEW']
  if len(waiting)>1:out.append('<h2>'+L('Քեզնից սպասվում է','Ждет тебя')+'</h2><div class="list">'+''.join(_tile(t,True,True) for t in waiting)+'</div>')
  if today:out.append('<h2>'+L('Այսօրվա գործերը','Дела на сегодня')+'</h2><div class="grid">'+''.join(_tile(t,True) for t in sorted(today,key=lambda t:ORDER.get(t['status'],9)))+'</div>')
  if len(days)>1:
   out.append('<details class="old"><summary>'+L('Նախորդ օրերը','Прошлые дни')+'</summary>')
   for day in days[1:]:out.append('<p class="day">'+e(day)+'</p><div class="grid">'+''.join(_tile(t,True) for t in tasks if t['day']==day)+'</div>')
   out.append('</details>')
 else:
  if today:out.append('<h2>'+L('Այսօրվա գործերը','Дела на сегодня')+'</h2><div class="grid">'+''.join(_tile(t,False) for t in sorted(today,key=lambda t:ORDER.get(t['status'],9)))+'</div>')
  for title,statuses in GROUPS:
   group=[t for t in today if t['status'] in statuses]
   if group:out.append('<h2>'+P(title)+' · '+e(len(group))+'</h2>'+''.join(_static_card(t,report) for t in group))
  for day in days[1:]:out.append('<p class="day">'+e(day)+'</p>'+''.join(_static_card(t,report) for t in tasks if t['day']==day))
 out.append('<p class="note">'+L('Էջը կազմվել է','Страница собрана')+' '+_when(report['generated'])+'</p></div>')
 if interactive:
  out.append(''.join(_modal(t,report) for t in tasks))
  out.append('''<script>
async function action(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw Error(d.error||'Failed');location.reload();}
function safe(fn){return async e=>{e.preventDefault();const b=e.target.closest('form')?.querySelector('button')||e.target.closest('button')||e.target;b.disabled=true;try{await fn(e);}catch(error){document.getElementById('status').textContent=error.message;b.disabled=false;}};}
document.getElementById('plan').onclick=safe(()=>action('/operator/work/plan',{}));
for(const b of document.querySelectorAll('[data-claim]'))b.onclick=safe(()=>action('/operator/work/claim',{task_id:b.dataset.claim}));
for(const f of document.querySelectorAll('[data-observe]'))f.onsubmit=safe(()=>{const d=Object.fromEntries(new FormData(f));d.task_id=f.dataset.observe;d.blocked=f.querySelector('[name=blocked]').checked;return action('/operator/work/observe',d);});
for(const f of document.querySelectorAll('[data-approve]'))f.onsubmit=safe(()=>action('/operator/work/approve',{task_id:f.dataset.approve,digest:f.dataset.digest,reference:'Գևի հաստատումը վահանակի կոճակով'}));
for(const b of document.querySelectorAll('[data-open]'))b.onclick=()=>document.getElementById(b.dataset.open).showModal();
for(const d of document.querySelectorAll('dialog')){d.querySelector('[data-close]').onclick=()=>d.close();d.addEventListener('click',e=>{if(e.target===d)d.close();});}
const HELLO={hy:['Բարի լույս','Բարի օր','Բարի երեկո','Բարի գիշեր'],ru:['Доброе утро','Добрый день','Добрый вечер','Доброй ночи']},WHO={hy:', Գև',ru:', Гев'};
function setLang(lang){document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;for(const b of document.querySelectorAll('.lang button'))b.setAttribute('aria-pressed',String(b.dataset.lang===lang));try{localStorage.setItem('kryuk-lang',lang);}catch(error){}}
for(const b of document.querySelectorAll('.lang button'))b.onclick=()=>setLang(b.dataset.lang);
let saved=null;try{saved=localStorage.getItem('kryuk-lang');}catch(error){}
if(saved==='ru'||saved==='hy')setLang(saved);
function setTheme(theme){document.documentElement.dataset.theme=theme==='dark'?'dark':'light';try{localStorage.setItem('kryuk-theme',theme);}catch(error){}}
document.getElementById('theme').onclick=()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');
let savedTheme=null;try{savedTheme=localStorage.getItem('kryuk-theme');}catch(error){}
if(savedTheme==='dark')setTheme('dark');
function tick(){const now=Date.now();for(const [city,offset] of [['yerevan',4],['moscow',3]]){const t=new Date(now+offset*3600000),h=t.getUTCHours();document.getElementById('clock-'+city).textContent=String(h).padStart(2,'0')+':'+String(t.getUTCMinutes()).padStart(2,'0');document.getElementById('box-'+city).classList.toggle('night',!(h>=7&&h<19));if(city==='yerevan'){const i=h>=5&&h<12?0:h>=12&&h<18?1:h>=18&&h<23?2:3;const el=document.getElementById('hello');el.querySelector('.hy').textContent=HELLO.hy[i]+WHO.hy;el.querySelector('.ru').textContent=HELLO.ru[i]+WHO.ru;}}}
tick();setInterval(tick,15000);
</script>''')
 return ''.join(out)+'</html>'
