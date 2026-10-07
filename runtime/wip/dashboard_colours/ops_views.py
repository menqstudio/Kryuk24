"""Private internal dashboard/report. Escapes all operator-supplied content."""
import html, json
from datetime import datetime, timedelta, timezone

YEREVAN=timezone(timedelta(hours=4));MOSCOW=timezone(timedelta(hours=3))
STATUS={'PENDING':(('Սպասում է','Ждет'),'wait'),'CLAIMED':(('Ընթացքում է','В работе'),'work'),'BLOCKED':(('Խանգարում է','Мешает'),'block'),'READY_REVIEW':(('Սպասում է քեզ','Ждет тебя'),'review'),'APPROVED':(('Հաստատված է','Одобрено'),'ok'),'DONE':(('Արված է','Сделано'),'ok')}
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
AVATAR='data:image/webp;base64,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'
def icon(name,size=22):return _S.format(size,PATHS.get(name,PATHS['dot']))
CSS='''
:root{color-scheme:light;
--neutral-0:#ffffff;--neutral-50:#f4f6f8;--neutral-100:#eef1f4;--neutral-200:#dde3ea;--neutral-300:#c5cdd7;--neutral-400:#9aa6b6;--neutral-500:#5a6676;--neutral-700:#3e4a5a;--neutral-800:#1c3150;--neutral-900:#13233a;--neutral-950:#0b1524;
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
body{font:16px/1.5 "Inter","Noto Sans Armenian",system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);margin:0;-webkit-font-smoothing:antialiased}
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
.menq{height:36px;width:auto;display:block;border:0;border-radius:0;max-width:none}
.proj{display:inline-flex;align-items:center;gap:6px;border-radius:var(--r-pill);border:1px solid rgba(241,138,75,.40);background:rgba(239,91,0,.14);color:var(--orange-300);padding:4px 12px;font-size:12px;font-weight:600;letter-spacing:.12em}
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
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:var(--r-pill);padding:4px 12px;font-size:13px;font-weight:600;letter-spacing:.02em;white-space:nowrap}
.ok{background:var(--okbg);color:var(--ok)}.wait{background:var(--waitbg);color:var(--wait)}.block{background:var(--blockbg);color:var(--block)}.review{background:var(--reviewbg);color:var(--review)}.work{background:var(--workbg);color:var(--work)}
.bar{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:16px;align-items:center;border-top:1px solid var(--line);margin-top:18px;padding-top:18px}
h2{display:flex;align-items:center;gap:12px;font-size:12px;margin:36px 0 12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h2::after{content:"";flex:0 0 40px;height:1px;background:linear-gradient(90deg,var(--line2),transparent)}
.hint{margin:0 0 10px;color:var(--muted);font-size:14px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.tile{position:relative;isolation:isolate;overflow:hidden;display:flex;flex-direction:column;align-items:center;gap:6px;width:100%;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 10px 14px;text-align:center;color:var(--text);font:inherit;font-weight:400;cursor:pointer;box-shadow:var(--shadow-sm);
 transition:transform var(--slow) var(--ease),box-shadow var(--slow) var(--ease),border-color var(--slow) var(--ease)}
button.tile{height:auto;border-radius:20px;font-size:inherit}button.tile:hover,button.tile:focus-visible{transform:translateY(-4px);box-shadow:var(--shadow-hover);border-color:var(--line2);filter:none}
.tile .ico{width:46px;height:46px;border-radius:14px;display:grid;place-items:center}
.tile .nm{font-size:15px;font-weight:600;line-height:1.25}
.tile .st{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.tile.wide{flex-direction:row;text-align:left;padding:18px 20px;gap:16px;border-color:var(--reviewfill);box-shadow:0 0 0 4px var(--reviewbg),var(--shadow)}
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
.x{background:transparent;color:var(--muted);border:0;padding:8px;border-radius:var(--r-pill);display:grid;place-items:center;height:auto}
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
@media (max-width:620px){body{font-size:15px}.side{width:100%;justify-content:space-between}.clocks{flex:1}.clock{flex:1;min-width:0}.hero{grid-template-columns:1fr;padding:20px}.ring{width:88px;height:88px}.ring b{font-size:21px}.grid{grid-template-columns:repeat(2,1fr)}.facts{grid-template-columns:1fr}.facts dt{margin-top:6px}.head{padding:14px 16px}.inner{padding:0 16px 16px}.wrap{padding-left:16px;padding-right:16px}}
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
 body='<span class="ico '+kind+'">'+icon(ico,24)+'</span>'+('<span><span class="nm">'+P(name)+'</span><br><span class="st">'+P(label)+time+'</span></span><span class="go">'+icon('review',20)+'</span>' if wide else '<span class="nm">'+P(short)+'</span><span class="st">'+P(label)+time+'</span>')
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
 out=['<!doctype html><html lang="hy" data-lang="hy"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>MenQ · KRYUK24 — աշխատանքների հերթ</title><style>'+CSS+'</style>']
 switch='<div class="lang" role="group" aria-label="Լեզու / Язык"><button type="button" data-lang="hy" aria-pressed="true">Հայ</button><button type="button" data-lang="ru" aria-pressed="false">Рус</button></div><button type="button" class="theme" id="theme" aria-label="Բաց / մուգ · Светлая / темная"><span class="moon">'+icon('moon',18)+'</span><span class="sun">'+icon('sun',18)+'</span></button>' if interactive else ''
 out.append('<div class="top"><div class="wrap"><div class="bar0"><img class="menq" src="'+LOGO+'" alt="MenQ" width="112" height="36"><span class="proj">'+icon('hook',16)+'КРЮК24</span></div><div class="brand"><span class="bro"><img class="avatar" src="'+AVATAR+'" alt="Bro" width="56" height="56"><i>Bro</i></span><div><b id="hello">'+L(hello[0]+', Գև',hello[1]+', Гев')+'</b><span>'+L('աշխատանքների հերթ','очередь работ')+' · '+L(str(y.day)+' '+MONTHS[y.month-1],str(y.day)+' '+MONTHS_RU[y.month-1])+'</span></div></div><div class="side">'+switch+'<div class="clocks">'+clock('yerevan',('Երևան','Ереван'),y)+clock('moscow',('Մոսկվա','Москва'),m)+'</div></div></div></div><div class="wrap">')
 if total:
  head,sub=_headline(total,done,review,blocked,left)
  full=263.89;gap=round(full*(1-done/total),2)
  out.append('<div class="hero"><div class="ring" style="--full:'+e(full)+'"><svg viewBox="0 0 100 100" width="100%" height="100%"><defs><linearGradient id="ringgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ef5b00"/><stop offset="1" stop-color="#f18a4b"/></linearGradient></defs><circle class="bgc" cx="50" cy="50" r="42"/><circle class="fg" cx="50" cy="50" r="42" stroke-dasharray="'+e(full)+'" stroke-dashoffset="'+e(gap)+'"/></svg><b>'+e(done)+'/'+e(total)+'</b></div><div><h1>'+P(head)+'</h1><p>'+P(sub)+'</p><div class="sum">')
  for status in ('READY_REVIEW','BLOCKED','CLAIMED','PENDING','APPROVED','DONE'):
   if count(status):out.append('<span class="pill '+STATUS[status][1]+'">'+icon(STATUS[status][1],15)+e(count(status))+' · '+P(STATUS[status][0])+'</span>')
  out.append('</div></div>')
 else:out.append('<div class="hero"><div class="ring"><b>—</b></div><div><h1>'+L('Հերթը դեռ չի ստեղծվել','Очередь еще не создана')+'</h1><p>'+L('Սա ստուգված օր չէ։','Этот день не проверен.')+'</p></div>')
 if interactive:out.append('<div class="bar"><button id="plan" class="second">'+L('Ստեղծել այսօրվա հերթը','Создать очередь на сегодня')+'</button><a href="/operator">'+L('Հայտերի մատյան','Журнал заявок')+'</a></div><p id="status" role="status"></p>')
 out.append('</div>')
 if interactive:
  waiting=[t for t in today if t['status']=='READY_REVIEW']
  if waiting:out.append('<h2>'+L('Քեզնից սպասվում է','Ждет тебя')+'</h2><div class="list">'+''.join(_tile(t,True,True) for t in waiting)+'</div>')
  if today:out.append('<h2>'+L('Այսօրվա գործերը','Дела на сегодня')+'</h2><div class="grid">'+''.join(_tile(t,True) for t in today)+'</div>')
  if len(days)>1:
   out.append('<details class="old"><summary>'+L('Նախորդ օրերը','Прошлые дни')+'</summary>')
   for day in days[1:]:out.append('<p class="day">'+e(day)+'</p><div class="grid">'+''.join(_tile(t,True) for t in tasks if t['day']==day)+'</div>')
   out.append('</details>')
 else:
  if today:out.append('<h2>'+L('Այսօրվա գործերը','Дела на сегодня')+'</h2><div class="grid">'+''.join(_tile(t,False) for t in today)+'</div>')
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
function setTheme(theme){if(theme==='dark')document.documentElement.dataset.theme='dark';else delete document.documentElement.dataset.theme;try{localStorage.setItem('kryuk-theme',theme);}catch(error){}}
document.getElementById('theme').onclick=()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');
let savedTheme=null;try{savedTheme=localStorage.getItem('kryuk-theme');}catch(error){}
if(savedTheme==='dark')setTheme('dark');
function tick(){const now=Date.now();for(const [city,offset] of [['yerevan',4],['moscow',3]]){const t=new Date(now+offset*3600000),h=t.getUTCHours();document.getElementById('clock-'+city).textContent=String(h).padStart(2,'0')+':'+String(t.getUTCMinutes()).padStart(2,'0');document.getElementById('box-'+city).classList.toggle('night',!(h>=7&&h<19));if(city==='yerevan'){const i=h>=5&&h<12?0:h>=12&&h<18?1:h>=18&&h<23?2:3;const el=document.getElementById('hello');el.querySelector('.hy').textContent=HELLO.hy[i]+WHO.hy;el.querySelector('.ru').textContent=HELLO.ru[i]+WHO.ru;}}}
tick();setInterval(tick,15000);
</script>''')
 return ''.join(out)+'</html>'
