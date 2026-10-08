/* @ds-bundle: {"format":4,"namespace":"Kryuk","components":[{"name":"KryukMark"},{"name":"ContactButtons"},{"name":"CallBar"},{"name":"Price"},{"name":"TariffList"},{"name":"ChoiceTiles"},{"name":"OrderStatus"},{"name":"OrderCard"}]} */
/* KRYUK24 components. Requires window.React, the vendored component library (window.MenQ, used only as building blocks)
   and lockup.generated.js (window.KryukLockup, the official logo artwork). Customer-facing text is Russian; owner-facing labels can be passed in Armenian. */
(function () {
  var React = window.React, M = window.MenQ, LOGO = window.KryukLockup;
  if (!React || !M || !LOGO) throw new Error('KRYUK24 components: load React, vendor/menq-components/bundle.js and lockup.generated.js first');
  var h = React.createElement, useId = React.useId || function () { return 'kr' + Math.random().toString(36).slice(2, 8); };
  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(' '); }

  var PHONE = '+7 985 893-06-06';
  var ICON = {
    phone: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z',
    chat: 'M7.9 20A9 9 0 1 0 4 16.1L2 22Z',
    send: 'm22 2-7 20-4-9-9-4Z M22 2 11 13',
    check: 'M20 6 9 17l-5-5'
  };
  function icon(name, size) { return h(M.Icon, { size: size || 'md' }, ICON[name].split(' M').map(function (d, i) { return h('path', { key: i, d: i ? 'M' + d : d }); })); }
  function telHref(phone) { return 'tel:' + String(phone).replace(/[^\d+]/g, ''); }
  function rub(n) { return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n) + ' ₽'; }

  // KryukMark: the official lockup, placed as is. The artwork is generated from tools/brand.py lockup()
  // (lockup.generated.js); this component only sizes it. Never redraw or restyle the logo here.
  function KryukMark(p) {
    var w = p.markOnly ? LOGO.hookW : LOGO.w;
    var svg = h('svg', { className: 'kr-mark-art', viewBox: LOGO.x + ' ' + LOGO.y + ' ' + w + ' ' + LOGO.h, 'aria-hidden': 'true', focusable: 'false', dangerouslySetInnerHTML: { __html: LOGO.svg } });
    var props = { className: cx('kr-mark', p.size && 'kr-mark--' + p.size, p.markOnly && 'kr-mark--hook', p.className), 'aria-label': p.label || 'КРЮК24, эвакуатор' };
    return p.href ? h('a', Object.assign(props, { href: p.href }), svg) : h('span', Object.assign(props, { role: 'img' }), svg);
  }

  // ContactButtons: call (primary, with the number), WhatsApp, Telegram. Every button is a real link.
  function ContactButtons(p) {
    var phone = p.phone || PHONE;
    var items = [h(M.Button, { key: 'call', variant: 'primary', href: telHref(phone), icon: icon('phone') },
      h('span', { className: 'kr-contact-call-txt' }, p.callLabel || 'Позвонить', p.showNumber === false ? null : h('small', null, phone)))];
    if (p.whatsapp) items.push(h(M.Button, { key: 'wa', variant: 'outline', href: p.whatsapp, icon: icon('chat') }, p.whatsappLabel || 'WhatsApp'));
    if (p.telegram) items.push(h(M.Button, { key: 'tg', variant: 'outline', href: p.telegram, icon: icon('send') }, p.telegramLabel || 'Telegram'));
    return h('div', { className: cx('kr-contact', p.stack && 'kr-contact--stack'), style: p.stack ? null : { '--kr-cols': items.length } }, items);
  }

  // CallBar: the same actions fixed to the bottom of a phone screen (hidden from 1024 px). `static` shows it in place.
  function CallBar(p) {
    return h('nav', { className: cx('kr-callbar', p.static && 'kr-callbar--static'), 'aria-label': p.label || 'Связаться' },
      h(ContactButtons, Object.assign({}, p, { showNumber: false })));
  }

  // Price: «от 4 000 ₽», formatted for ru-RU, the ruble sign after the number.
  function Price(p) {
    return h('div', { className: cx('kr-price', p.size === 'lg' && 'kr-price--lg') },
      h('span', { className: 'kr-price-value' }, p.from === false ? null : h('small', null, p.fromLabel || 'от'), rub(p.value)),
      p.note ? h('span', { className: 'kr-price-note' }, p.note) : null);
  }

  // TariffList: rows of «what — from price, per km».
  function TariffList(p) {
    return h('ul', { className: 'kr-tariffs', 'aria-label': p.label }, (p.items || []).map(function (it) {
      return h('li', { key: it.name, className: 'kr-tariff' },
        h('span', { className: 'kr-tariff-name' }, it.name),
        h('span', { className: 'kr-tariff-price' }, h('b', null, (it.from === false ? '' : 'от ') + rub(it.price)), it.perKm ? h('span', null, '+ ' + rub(it.perKm) + '/км') : null));
    }));
  }

  // ChoiceTiles: one choice from a few, as native radio buttons inside a fieldset.
  function ChoiceTiles(p) {
    var name = useId(), st = React.useState(p.defaultValue || null), cur = p.value !== undefined ? p.value : st[0];
    return h('fieldset', { className: 'kr-choice' }, h('legend', null, p.legend),
      (p.options || []).map(function (o) {
        return h('label', { key: o.value, className: 'kr-choice-tile' },
          h('input', { type: 'radio', name: name, value: o.value, checked: cur === o.value, onChange: function () { st[1](o.value); if (p.onChange) p.onChange(o.value); } }),
          o.icon || null, h('span', null, o.label));
      }));
  }

  // OrderStatus: the six operational statuses of runtime/order_flow (DRIVER_ASSIGNED → … → DELIVERED). Labels default to Russian; pass `lang: 'hy'` for Gev's screens.
  var STEPS = ['DRIVER_ASSIGNED', 'EN_ROUTE', 'ARRIVED', 'LOADED', 'TRANSPORTING', 'DELIVERED'];
  var STEP_LABELS = {
    ru: ['Назначен', 'В пути', 'На месте', 'Погружен', 'Везём', 'Доставлен'],
    hy: ['Նշանակված', 'Ճանապարհին', 'Տեղում', 'Բարձված', 'Տանում ենք', 'Հասցված']
  };
  function OrderStatus(p) {
    var labels = p.labels || STEP_LABELS[p.lang || 'ru'], at = STEPS.indexOf(p.status);
    return h('ol', { className: 'kr-steps', 'aria-label': p.label || (p.lang === 'hy' ? 'Պատվերի վիճակը' : 'Статус заказа') }, STEPS.map(function (s, i) {
      var state = at < 0 ? 'todo' : i < at || (i === at && s === 'DELIVERED') ? 'done' : i === at ? 'current' : 'todo';
      return h('li', { key: s, className: cx('kr-step', state !== 'todo' && 'kr-step--' + state), 'aria-current': state === 'current' ? 'step' : undefined },
        h('span', { className: 'kr-step-dot', 'aria-hidden': 'true' }, state === 'done' ? icon('check', 'sm') : null),
        h('span', { className: 'kr-step-label' }, labels[i]));
    }));
  }

  // OrderCard: one order for the dispatcher — id, vehicle, route, confirmed price, status. Contacts stay out of owner views.
  function OrderCard(p) {
    var o = p.order || {}, hy = p.lang === 'hy';
    return h(M.Card, { variant: 'solid', className: 'kr-order' }, h('div', { className: 'panel kr-order' },
      h('div', { className: 'kr-order-head' },
        h('div', null, h('div', { className: 'kr-order-id' }, o.id), h('div', { className: 'panel-title' }, o.vehicle)),
        o.price ? h(Price, { value: o.price, from: false, note: o.priceNote || (hy ? 'հաստատված գին' : 'подтверждённая цена') }) : null),
      h('dl', { className: 'kr-order-route' },
        h('dt', null, hy ? 'Որտեղից' : 'Откуда'), h('dd', null, o.from),
        h('dt', null, hy ? 'Ուր' : 'Куда'), h('dd', null, o.to)),
      h(OrderStatus, { status: o.status, lang: p.lang }),
      o.test ? h('div', null, h(M.Badge, { tone: 'warning' }, hy ? 'Թեստային' : 'Тестовый')) : null));
  }

  window.Kryuk = { KryukMark: KryukMark, ContactButtons: ContactButtons, CallBar: CallBar, Price: Price, TariffList: TariffList, ChoiceTiles: ChoiceTiles, OrderStatus: OrderStatus, OrderCard: OrderCard, steps: STEPS };
})();
