/* @ds-bundle: {"format":4,"namespace":"MenQ","components":[{"name":"BrandMark"},{"name":"Button"},{"name":"Card"},{"name":"Panel"},{"name":"PageHeader"},{"name":"SectionHeading"},{"name":"Badge"},{"name":"StatusDot"},{"name":"Avatar"},{"name":"Field"},{"name":"Input"},{"name":"Textarea"},{"name":"Select"},{"name":"FormRow"},{"name":"Checkbox"},{"name":"RadioGroup"},{"name":"Switch"},{"name":"Icon"},{"name":"Accordion"},{"name":"Nav"},{"name":"Tooltip"},{"name":"Reveal"},{"name":"Tabs"},{"name":"LocaleSwitch"},{"name":"ThemeSwitch"},{"name":"EmptyState"},{"name":"Skeleton"},{"name":"Toast"},{"name":"Modal"},{"name":"ConfirmDialog"},{"name":"Drawer"},{"name":"KpiStat"},{"name":"MetricBar"},{"name":"Table"},{"name":"ContrastSection"}]} */
/* MenQ brand expression components (D-027). Core layer: product-neutral. Product extensions (e.g. Bro) live under platforms/design/product-extensions/. */
(function () {
  var React = window.React;
  var h = React.createElement;
  var useState = React.useState, useEffect = React.useEffect, useRef = React.useRef;
  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(' '); }
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }

  /* ── App components (adapted from BroPS src/components/ui.tsx) ── */
  function Button(p) {
    var v = p.variant || 'primary', size = p.small ? 'sm' : (p.size || 'md');
    var props = { title: p.title, onClick: p.onClick, 'aria-busy': p.loading ? 'true' : undefined,
      className: cx('btn', v !== 'secondary' && 'btn--' + v, size !== 'md' && 'btn--' + size, p.loading && 'btn--loading', p.className) };
    // Forward ARIA and data attributes so wrappers (Tooltip, menus) can describe the button.
    Object.keys(p).forEach(function (k) { if (k.indexOf('aria-') === 0 || k.indexOf('data-') === 0) props[k] = p[k]; });
    if (p.loading) props['aria-busy'] = 'true';
    var kids = [p.loading ? h('span', { key: 's', className: 'mq-spinner', 'aria-hidden': 'true' }) : null, p.icon ? h('span', { key: 'i', 'aria-hidden': 'true', style: { display: 'inline-flex' } }, p.icon) : null, p.children];
    if (p.href) return h('a', Object.assign(props, { href: p.href }), kids);
    return h('button', Object.assign(props, { type: p.type || 'button', disabled: p.disabled || p.loading }), kids);
  }
  function Card(p) { var v = p.variant || 'solid'; return h('div', { className: cx('card', v !== 'solid' && 'card--' + v, p.className), style: p.style, 'data-interactive': p.interactive ? 'true' : undefined }, p.children); }
  function Panel(p) {
    return h(Card, null, h('div', { className: 'panel' },
      (p.title || p.actions) ? h('div', { className: 'panel-head' }, p.title ? h('div', { className: 'panel-title' }, p.title) : null, p.actions) : null,
      p.children));
  }
  function PageHeader(p) {
    return h('div', { className: 'page-header' }, h('div', null, h('div', { className: 'page-title' }, p.title), p.subtitle ? h('div', { className: 'page-subtitle' }, p.subtitle) : null), p.actions);
  }
  function Badge(p) { var t = p.tone || p.variant || 'neutral', status = ['info', 'success', 'warning', 'danger'].indexOf(t) >= 0; return h('span', { className: cx('badge', t !== 'neutral' && 'badge--' + t, (p.dot || status) && 'badge--dot') }, p.children); }
  function EmptyState(p) {
    return h('div', { className: 'empty' }, h('div', { className: 'empty-glyph', 'aria-hidden': 'true' }, p.glyph || '◍'), h('div', { className: 'empty-title' }, p.title),
      p.hint ? h('div', { className: 'muted', style: { marginTop: 4 } }, p.hint) : null, p.action ? h('div', { style: { marginTop: 12 } }, p.action) : null);
  }
  function Avatar(p) {
    var label = p.name || '?';
    if (p.src) return h('img', { className: cx('avatar', 'avatar--img', p.kind && 'mq-avatar--' + p.kind), src: p.src, alt: label, width: 28, height: 28 });
    return h('span', { className: cx('avatar', p.kind && 'mq-avatar--' + p.kind), role: 'img', 'aria-label': label }, String(label).slice(0, 1).toUpperCase());
  }
  function Field(p) { return h('div', { className: 'field' }, h('span', { className: 'field-label' }, p.label), h('span', null, p.children)); }
  function Skeleton(p) {
    var rows = p.rows || 3, out = [];
    for (var i = 0; i < rows; i++) out.push(h('div', { key: i, className: 'skeleton', style: { height: 18, width: (90 - i * 8) + '%' } }));
    return h('div', { className: 'stack', 'aria-busy': 'true' }, out);
  }
  var mqFieldSeq = 0;
  function useFieldId(given) { var r = useRef(null); if (r.current === null) r.current = given || 'mq-f' + (++mqFieldSeq); return r.current; }
  function withoutInvalid(p) { var rest = Object.assign({}, p); delete rest.invalid; return rest; }
  // FormRow wires the label, hint and error to its single control: id, aria-describedby, aria-invalid.
  function FormRow(p) {
    var id = useFieldId(p.id), hintId = id + '-hint', errId = id + '-err';
    var described = [p.hint ? hintId : null, p.error ? errId : null].filter(Boolean).join(' ') || undefined;
    var child = React.Children.only(p.children);
    var control = React.cloneElement(child, { id: child.props.id || id, 'aria-describedby': described, invalid: child.props.invalid || !!p.error, required: child.props.required || p.required });
    return h('div', { className: 'form-row' },
      h('label', { className: 'field-label', htmlFor: child.props.id || id }, p.label, p.required ? h('span', { className: 'mq-required', 'aria-hidden': 'true' }, ' *') : null),
      control,
      p.hint ? h('span', { id: hintId, className: 'form-hint' }, p.hint) : null,
      p.error ? h('span', { id: errId, className: 'form-error', role: 'alert' }, p.error) : null);
  }
  function Input(p) { return h('input', Object.assign(withoutInvalid(p), { className: cx('input', p.invalid && 'mq-invalid', p.className), 'aria-invalid': p.invalid ? 'true' : undefined })); }
  function Textarea(p) { return h('textarea', Object.assign(withoutInvalid(p), { className: cx('textarea', p.invalid && 'mq-invalid', p.className), 'aria-invalid': p.invalid ? 'true' : undefined })); }
  function Select(p) { return h('select', Object.assign(withoutInvalid(p), { className: cx('select input', p.invalid && 'mq-invalid', p.className), 'aria-invalid': p.invalid ? 'true' : undefined })); }
  // Native inputs keep keyboard, form submission and screen-reader semantics; the visual is CSS only.
  function Checkbox(p) {
    var rest = withoutInvalid(p); delete rest.label; delete rest.hint;
    return h('label', { className: cx('mq-check', p.disabled && 'mq-check--disabled') },
      h('input', Object.assign(rest, { type: 'checkbox', className: 'mq-check-input', 'aria-invalid': p.invalid ? 'true' : undefined })),
      h('span', { className: 'mq-check-box', 'aria-hidden': 'true' }),
      h('span', { className: 'mq-check-text' }, p.label, p.hint ? h('span', { className: 'form-hint' }, p.hint) : null));
  }
  function RadioGroup(p) {
    var name = useFieldId(p.name), st = useState(p.defaultValue), cur = p.value !== undefined ? p.value : st[0], errId = name + '-err';
    return h('fieldset', { className: 'mq-radio-group', 'aria-describedby': p.error ? errId : undefined, 'aria-invalid': p.error ? 'true' : undefined },
      h('legend', { className: 'field-label' }, p.label),
      p.options.map(function (o) {
        return h('label', { key: o.value, className: cx('mq-check', 'mq-radio', (p.disabled || o.disabled) && 'mq-check--disabled') },
          h('input', { type: 'radio', name: name, value: o.value, checked: cur === o.value, disabled: p.disabled || o.disabled, className: 'mq-check-input',
            onChange: function () { st[1](o.value); if (p.onChange) p.onChange(o.value); } }),
          h('span', { className: 'mq-check-box', 'aria-hidden': 'true' }),
          h('span', { className: 'mq-check-text' }, o.label, o.hint ? h('span', { className: 'form-hint' }, o.hint) : null));
      }),
      p.error ? h('span', { id: errId, className: 'form-error', role: 'alert' }, p.error) : null);
  }
  function Switch(p) {
    var st = useState(!!p.defaultChecked), on = p.checked !== undefined ? p.checked : st[0];
    return h('label', { className: cx('mq-switch', p.disabled && 'mq-check--disabled') },
      h('button', { type: 'button', role: 'switch', 'aria-checked': on ? 'true' : 'false', disabled: p.disabled, className: 'mq-switch-track',
        onClick: function () { st[1](!on); if (p.onChange) p.onChange(!on); } }, h('span', { className: 'mq-switch-thumb', 'aria-hidden': 'true' })),
      h('span', { className: 'mq-check-text' }, p.label, p.hint ? h('span', { className: 'form-hint' }, p.hint) : null));
  }
  function useDialog(ref, active, onClose) {
    useEffect(function () {
      if (!active) return undefined;
      var previous = document.activeElement, node = ref.current;
      var focusables = function () { return node ? Array.prototype.slice.call(node.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(function (el) { return !el.disabled; }) : []; };
      var first = focusables()[0]; if (first) first.focus();
      function onKey(e) {
        if (e.key === 'Escape' && onClose) { e.preventDefault(); onClose(); return; }
        if (e.key === 'Tab') {
          var list = focusables(); if (!list.length) return;
          var a = list[0], z = list[list.length - 1];
          if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
          else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
        }
      }
      document.addEventListener('keydown', onKey);
      return function () { document.removeEventListener('keydown', onKey); if (previous && previous.focus) previous.focus(); };
    }, [active, onClose]);
  }
  /* ── Iconography, disclosure, navigation, tooltip (CR-0009) ── */
  // Icon: a 24-grid stroke icon (Lucide geometry). Decorative by default; pass `label` when it carries meaning.
  function Icon(p) {
    var size = { sm: 'var(--icon-size-sm)', md: 'var(--icon-size-md)', lg: 'var(--icon-size-lg)' }[p.size || 'md'];
    return h('svg', { viewBox: '0 0 24 24', width: '1em', height: '1em', fill: 'none', stroke: 'currentColor', strokeWidth: p.strokeWidth || 'var(--icon-stroke)',
      strokeLinecap: 'round', strokeLinejoin: 'round', className: cx('mq-icon', p.className), style: { fontSize: size },
      role: p.label ? 'img' : undefined, 'aria-label': p.label, 'aria-hidden': p.label ? undefined : 'true', focusable: 'false' }, p.children);
  }
  // Accordion: WAI-ARIA disclosure buttons (aria-expanded / aria-controls) + labelled regions.
  function Accordion(p) {
    var base = useFieldId(p.id), st = useState(p.defaultOpen || []), open = p.open !== undefined ? p.open : st[0];
    var Heading = 'h' + (p.headingLevel || 3);
    function toggle(id) {
      var isOpen = open.indexOf(id) >= 0;
      var next = isOpen ? open.filter(function (x) { return x !== id; }) : (p.multiple ? open.concat([id]) : [id]);
      st[1](next); if (p.onChange) p.onChange(next);
    }
    return h('div', { className: 'mq-accordion' }, p.items.map(function (it) {
      var on = open.indexOf(it.id) >= 0, btn = base + '-' + it.id + '-btn', panel = base + '-' + it.id + '-panel';
      return h('div', { key: it.id, className: cx('mq-acc-item', on && 'mq-acc-item--open') },
        h(Heading, { className: 'mq-acc-heading' },
          h('button', { type: 'button', id: btn, className: 'mq-acc-trigger', 'aria-expanded': on ? 'true' : 'false', 'aria-controls': panel, onClick: function () { toggle(it.id); } },
            h('span', null, it.title),
            h(Icon, { size: 'md', className: 'mq-acc-chevron' }, h('path', { d: 'm6 9 6 6 6-6' })))),
        h('div', { id: panel, role: 'region', 'aria-labelledby': btn, className: 'mq-acc-panel', hidden: !on }, it.content));
    }));
  }
  // Nav: a labelled navigation landmark; the current page gets aria-current="page".
  function Nav(p) {
    return h('nav', { className: cx('mq-nav', p.orientation === 'vertical' && 'mq-nav--vertical', p.className), 'aria-label': p.label },
      h('ul', { className: 'mq-nav-list' }, p.items.map(function (it) {
        return h('li', { key: it.href }, h('a', { href: it.href, className: 'mq-nav-link', 'aria-current': it.current ? 'page' : undefined, onClick: it.onClick }, it.icon ? h('span', { className: 'mq-nav-icon', 'aria-hidden': 'true' }, it.icon) : null, it.label));
      })));
  }
  // Tooltip: supplementary text on hover and keyboard focus; Escape dismisses; linked with aria-describedby.
  function Tooltip(p) {
    var id = useFieldId(p.id), st = useState(false), timer = useRef(0);
    function show() { clearTimeout(timer.current); timer.current = setTimeout(function () { st[1](true); }, p.delay != null ? p.delay : 300); }
    function hide() { clearTimeout(timer.current); st[1](false); }
    useEffect(function () {
      if (!st[0]) return undefined;
      function onKey(e) { if (e.key === 'Escape') hide(); }
      document.addEventListener('keydown', onKey); return function () { document.removeEventListener('keydown', onKey); };
    }, [st[0]]);
    useEffect(function () { return function () { clearTimeout(timer.current); }; }, []);
    var child = React.Children.only(p.children);
    var trigger = React.cloneElement(child, { 'aria-describedby': cx(child.props['aria-describedby'], id) || undefined });
    return h('span', { className: 'mq-tip-wrap', onMouseEnter: show, onMouseLeave: hide, onFocus: show, onBlur: hide },
      trigger,
      h('span', { id: id, role: 'tooltip', className: cx('mq-tip', 'mq-tip--' + (p.placement || 'top'), st[0] && 'mq-tip--open') }, p.content));
  }
  /* ── Motion (CR-0010) ── */
  // Reveal: plays a named entrance pattern once, when the element first enters the viewport.
  // Reduced motion (or no IntersectionObserver) shows the content immediately, without animation.
  function Reveal(p) {
    var ref = useRef(null), st = useState(false), shown = st[0];
    useEffect(function () {
      if (shown) return undefined;
      var el = ref.current;
      if (!el || reducedMotion() || typeof IntersectionObserver === 'undefined') { st[1](true); return undefined; }
      var io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) { st[1](true); io.disconnect(); }
      }, { rootMargin: '0px 0px -10% 0px' });
      io.observe(el);
      return function () { io.disconnect(); };
    }, [shown]);
    var T = p.as || 'div', style = Object.assign({ '--mq-i': Math.min(p.index || 0, 8) }, p.style);
    return h(T, { ref: ref, id: p.id, className: cx('mq-reveal', 'mq-reveal--' + (p.pattern || 'rise'), p.className), style: style, 'data-mq-in': shown ? 'true' : undefined }, p.children);
  }
  function Modal(p) {
    var ref = useRef(null);
    useDialog(ref, !p.inline, p.onClose);
    var dialog = h('div', { ref: ref, className: 'modal', role: 'dialog', 'aria-modal': p.inline ? undefined : 'true', 'aria-label': p.title, onClick: function (e) { e.stopPropagation(); } }, h('div', { className: 'modal-title' }, p.title), p.children);
    return p.inline ? dialog : h('div', { className: 'modal-scrim', onClick: p.onClose }, dialog);
  }
  function ConfirmDialog(p) {
    return h(Modal, { title: p.title, onClose: p.onCancel, inline: p.inline },
      h('div', { className: 'muted', style: { marginBottom: 16 } }, p.message),
      h('div', { className: 'form-actions' }, h(Button, { variant: 'ghost', small: true, onClick: p.onCancel }, p.cancelLabel), h(Button, { variant: 'danger', small: true, onClick: p.onConfirm }, p.confirmLabel)));
  }
  function Toast(p) {
    return h('div', { className: 'toast toast--' + (p.tone || 'info'), role: 'status' },
      h('span', { className: 'toast-text' }, p.children),
      p.onDismiss ? h('button', { type: 'button', className: 'toast-close', onClick: p.onDismiss, 'aria-label': p.dismissLabel || 'Dismiss' }, '✕') : null);
  }

  /* ── MenQ additions ── */
  function StatusDot(p) {
    var s = p.status || 'offline';
    return h('span', { className: 'mq-status' }, h('span', { className: 'mq-status-dot mq-status-dot--' + s, 'aria-hidden': 'true' }), p.label || s);
  }
  function Tabs(p) {
    var items = p.items || [], st = useState(p.defaultValue || (items[0] && items[0].value)), cur = p.value !== undefined ? p.value : st[0], list = useRef(null);
    function pick(v, focus) {
      st[1](v); if (p.onChange) p.onChange(v);
      if (focus && list.current) { var el = list.current.querySelector('[data-value="' + String(v).replace(/"/g, '') + '"]'); if (el) el.focus(); }
    }
    function onKey(e) {
      if (!items.length) return;
      var i = items.findIndex(function (t) { return t.value === cur; }), n = items.length, next = null;
      if (e.key === 'ArrowRight') next = (i + 1) % n;
      else if (e.key === 'ArrowLeft') next = (i - 1 + n) % n;
      else if (e.key === 'Home') next = 0;
      else if (e.key === 'End') next = n - 1;
      if (next !== null) { e.preventDefault(); pick(items[next].value, true); }
    }
    return h('div', { ref: list, className: 'mq-tabs', role: 'tablist', 'aria-label': p.label, onKeyDown: onKey }, items.map(function (t) {
      var on = t.value === cur;
      return h('button', { key: t.value, 'data-value': t.value, type: 'button', role: 'tab', id: t.id, 'aria-controls': t.controls, 'aria-selected': on ? 'true' : 'false', tabIndex: on ? 0 : -1, className: cx('mq-tab', on && 'mq-tab--active'), onClick: function () { pick(t.value); } },
        t.label, t.count != null ? h('span', { className: 'mq-tab-count' }, t.count) : null);
    }));
  }
  function Drawer(p) {
    var ref = useRef(null);
    useDialog(ref, !p.inline, p.onClose);
    var panel = h('aside', { ref: ref, className: 'mq-drawer', role: 'dialog', 'aria-modal': p.inline ? undefined : 'true', 'aria-label': p.title },
      h('div', { className: 'mq-drawer-head' }, h('div', { className: 'panel-title' }, p.title), h(Button, { variant: 'ghost', small: true, onClick: p.onClose, title: p.closeLabel || 'Close' }, '✕')),
      h('div', { className: 'mq-drawer-body' }, p.children));
    return p.inline ? panel : h('div', { className: 'mq-drawer-scrim', onClick: p.onClose }, h('div', { onClick: function (e) { e.stopPropagation(); } }, panel));
  }
  function KpiStat(p) {
    var target = Number(p.value) || 0, st = useState(reducedMotion() ? target : 0), raf = useRef(0);
    useEffect(function () {
      if (reducedMotion()) { st[1](target); return; }
      var t0 = performance.now(), dur = 800;
      function tick(now) { var k = Math.min(1, (now - t0) / dur); st[1](Math.round(target * (1 - Math.pow(1 - k, 3)))); if (k < 1) raf.current = requestAnimationFrame(tick); }
      raf.current = requestAnimationFrame(tick); return function () { cancelAnimationFrame(raf.current); };
    }, [target]);
    var fmt = new Intl.NumberFormat(p.locale || 'hy-AM').format(st[0]);
    return h(Card, { className: 'mq-kpi', variant: p.variant || 'elevated' }, h('div', { className: 'field-label' }, p.label), h('div', { className: 'stat' }, fmt, p.unit ? h('span', { className: 'mq-kpi-unit' }, p.unit) : null),
      p.delta != null ? h('div', { className: cx('mq-kpi-delta', p.delta >= 0 ? 'mq-up' : 'mq-down') }, (p.delta >= 0 ? '▲ ' : '▼ ') + Math.abs(p.delta) + '%', p.deltaLabel ? h('span', { className: 'muted' }, ' ' + p.deltaLabel) : null) : null);
  }
  function Table(p) {
    var columns = p.columns || [], rows = p.rows || [];
    return h('div', { className: 'mq-table-wrap' }, h('table', { className: 'mq-table' },
      p.caption ? h('caption', null, p.caption) : null,
      h('thead', null, h('tr', null, columns.map(function (c) { return h('th', { key: c.key, scope: 'col', style: { textAlign: c.align || 'left' } }, c.label); }))),
      h('tbody', null, rows.map(function (r, i) {
        return h('tr', { key: r.id || i }, columns.map(function (c) { return h('td', { key: c.key, style: { textAlign: c.align || 'left' } }, c.render ? c.render(r) : r[c.key]); }));
      }))));
  }
  /* ── Brand + marketing (Webpage) ── */
  // Official MenQ mark (Owner-supplied logo, CR-0005): rounded "Men" + neon power-ring Q.
  // "Men" takes --color-content-primary, so it is ink on light grounds and white on dark / contrast grounds.
  var MQ_MEN = 'M808.3 530.5 C841.9 525.9 862.0 517.9 876.6 503.5 C884.8 495.4 888.4 488.8 890.7 477.5 C893.9 461.7 888.5 444.2 876.5 431.2 C873.3 427.7 869.9 424.5 868.9 424.0 C867.6 423.3 864.8 424.2 857.8 427.5 C845.7 433.2 824.4 440.3 811.0 443.0 C804.1 444.4 794.9 445.4 784.1 445.7 C759.4 446.6 746.4 444.2 728.4 435.4 C717.5 430.1 708.1 421.1 703.1 411.3 C699.4 403.9 699.3 402.2 702.2 401.5 C703.5 401.2 738.9 395.6 781.0 389.0 C823.1 382.4 860.6 376.3 864.4 375.4 C885.7 370.7 900.3 357.4 904.1 339.2 C905.6 331.8 904.7 306.4 902.5 295.2 C897.4 269.2 885.5 246.1 867.1 226.7 C836.4 194.5 789.9 177.9 740.7 181.9 C709.5 184.3 681.6 193.2 660.5 207.3 C636.0 223.7 620.1 241.8 608.0 267.2 C594.9 294.7 590.3 320.4 591.3 359.9 C592.2 394.7 596.7 416.5 608.0 440.7 C618.5 463.0 637.9 486.5 657.3 500.3 C681.7 517.8 714.5 529.1 750.0 532.4 C759.1 533.2 797.8 532.0 808.3 530.5 Z M173.0 525.9 C184.2 524.4 202.1 520.0 202.5 518.6 C203.3 516.0 205.1 458.3 206.5 390.0 C208.3 303.4 210.3 250.3 211.8 248.8 C213.3 247.3 214.1 249.4 219.9 271.5 C222.6 281.9 229.2 304.4 234.5 321.5 C239.8 338.6 248.2 366.0 253.1 382.4 C258.1 398.9 262.8 413.7 263.7 415.3 C266.5 420.9 273.9 427.7 279.9 430.4 C290.3 435.1 299.6 436.5 319.0 436.4 C338.9 436.3 346.0 434.9 359.1 428.5 C372.3 422.1 370.5 425.6 383.4 380.5 C389.7 358.5 398.5 328.4 403.0 313.5 C407.4 298.6 412.9 279.5 415.1 271.0 C419.6 253.7 420.6 250.6 421.9 251.4 C423.4 252.4 424.0 264.0 425.0 313.0 C426.8 404.1 430.2 486.1 432.6 495.4 C435.8 508.4 442.1 515.8 454.4 520.9 C465.5 525.5 475.5 527.2 492.0 527.1 C512.7 527.1 524.5 524.9 537.0 518.5 C544.3 514.8 544.1 515.5 543.0 495.4 C538.0 408.4 521.6 213.8 515.0 163.0 C511.8 138.9 509.9 133.8 500.3 124.8 C480.6 106.4 432.3 101.6 393.5 114.1 C378.2 119.0 379.7 116.8 369.8 147.6 C358.7 181.8 340.7 243.0 321.8 311.0 C320.2 316.7 319.0 319.5 318.0 319.5 C316.9 319.5 311.5 302.8 298.3 259.0 C276.4 186.2 266.1 154.4 260.7 143.6 C255.2 132.5 244.5 121.7 234.0 116.7 C219.3 109.7 198.7 106.3 177.0 107.3 C163.0 108.0 157.0 109.0 145.6 112.7 C136.4 115.7 122.1 124.8 116.2 131.5 C112.4 135.9 112.2 136.3 111.6 145.3 C109.7 172.3 101.7 307.2 96.5 399.5 C93.9 445.2 92.9 482.8 94.0 491.3 C95.7 504.6 102.2 514.5 112.8 519.9 C126.2 526.7 149.9 529.1 173.0 525.9 Z M1036.4 526.5 C1045.6 526.0 1064.8 522.8 1067.0 521.5 C1067.7 521.1 1068.0 479.5 1068.0 402.5 L1068.0 284.0 L1071.8 282.1 C1088.8 273.5 1111.4 269.9 1126.2 273.4 C1140.9 276.9 1149.7 284.5 1154.3 297.5 C1155.1 299.5 1155.6 331.2 1156.0 394.5 C1156.7 495.4 1156.6 493.3 1161.8 504.2 C1166.8 514.4 1176.7 521.6 1190.5 525.0 C1206.6 528.9 1250.1 527.1 1263.5 522.0 L1266.0 521.0 L1266.0 410.8 C1265.9 291.4 1265.8 286.5 1260.5 268.5 C1255.5 250.9 1247.2 236.4 1235.1 223.7 C1218.3 206.0 1199.6 195.5 1171.0 187.6 C1139.3 178.9 1086.3 179.5 1048.9 189.0 C1028.8 194.1 1004.8 204.4 990.4 214.0 C980.1 220.9 968.4 232.9 964.3 240.6 C957.8 252.8 958.0 248.0 958.0 371.8 C958.0 494.2 958.0 493.0 963.7 504.5 C970.4 518.0 984.3 525.3 1007.0 527.0 C1012.2 527.4 1018.8 527.5 1021.5 527.4 C1024.2 527.2 1030.9 526.8 1036.4 526.5 Z M693.4 323.7 C692.4 321.0 697.1 304.7 701.3 296.7 C705.7 288.0 714.3 278.7 721.7 274.3 C738.5 264.5 762.7 263.3 778.9 271.4 C787.4 275.8 796.5 287.6 800.0 298.8 C802.0 305.2 801.7 307.0 798.6 307.0 C797.5 307.0 789.1 308.4 780.0 310.0 C770.9 311.7 748.9 315.6 731.0 318.6 C713.1 321.6 697.5 324.4 696.3 324.7 C694.8 325.0 693.8 324.7 693.4 323.7 Z';
  var MQ_ARC = 'M1479.9 520.0 A199.5 199.5 0 1 1 1687.1 520.0', MQ_STEM = 'M1584 403 V577', mqSeq = 0;
  function BrandMark(p) {
    var ref = useRef(null); if (ref.current === null) ref.current = 'mq' + (++mqSeq);
    var id = ref.current, ring = id + '-ring', glow = id + '-glow';
    return h('span', { className: cx('mq-brand', p.compact && 'mq-brand--compact', p.powerOn && 'mq-brand--power-on', p.className), 'aria-label': p.admin ? 'MenQ Admin' : 'MenQ', role: 'img' },
      h('svg', { className: 'mq-brand-mark', viewBox: '60 80 1800 560', 'aria-hidden': 'true', focusable: 'false' },
        h('defs', null,
          h('linearGradient', { id: ring, gradientUnits: 'userSpaceOnUse', x1: 0, y1: 140, x2: 0, y2: 560 },
            h('stop', { offset: 0, stopColor: '#0ea5e9' }), h('stop', { offset: 1, stopColor: '#67e8f9' })),
          h('filter', { id: glow, x: '-20%', y: '-20%', width: '140%', height: '140%' }, h('feGaussianBlur', { stdDeviation: 16 }))),
        h('path', { className: 'mq-brand-men', d: MQ_MEN, fillRule: 'evenodd' }),
        h('g', { className: 'mq-brand-glow', filter: 'url(#' + glow + ')' },
          h('path', { d: MQ_ARC, fill: 'none', stroke: '#22d3ee', strokeWidth: 64, strokeLinecap: 'round' }),
          h('path', { d: MQ_STEM, stroke: '#22d3ee', strokeWidth: 48, strokeLinecap: 'round' })),
        h('path', { className: 'mq-q-arc', pathLength: 1, d: MQ_ARC, fill: 'none', stroke: 'url(#' + ring + ')', strokeWidth: 56, strokeLinecap: 'round' }),
        h('path', { className: 'mq-q-arc', pathLength: 1, d: MQ_ARC, fill: 'none', stroke: '#c4f1fd', strokeWidth: 14, strokeLinecap: 'round', opacity: 0.9 }),
        h('path', { className: 'mq-q-stem', pathLength: 1, d: MQ_STEM, stroke: '#22d3ee', strokeWidth: 40, strokeLinecap: 'round' }),
        h('path', { className: 'mq-q-stem', pathLength: 1, d: MQ_STEM, stroke: '#c4f5fe', strokeWidth: 12, strokeLinecap: 'round' })),
      p.admin ? h('span', { className: 'mq-brand-tag' }, p.tag || 'Admin') : null);
  }
  function SectionHeading(p) {
    var T = p.as || 'h2';
    return h('div', { className: cx('mq-sh', (p.align || 'center') === 'center' && 'mq-sh--center') },
      (p.index || p.eyebrow) ? h('div', { className: 'mq-sh-kicker' }, p.index ? h('span', { className: 'mq-sh-index' }, p.index) : null, p.eyebrow ? h('span', null, p.eyebrow) : null, h('span', { className: 'mq-sh-rule', 'aria-hidden': 'true' })) : null,
      h(T, { className: cx('mq-sh-title', T === 'h1' && 'mq-sh-title--h1') }, p.title),
      p.description ? h('p', { className: 'mq-sh-desc' }, p.description) : null, p.children);
  }
  function Segmented(p) {
    var st = useState(p.defaultValue || p.items[0].value), cur = p.value !== undefined ? p.value : st[0];
    return h('div', { className: 'mq-seg', role: 'group', 'aria-label': p.label }, p.items.map(function (it) {
      return h('button', { key: it.value, type: 'button', className: 'mq-seg-btn', 'aria-pressed': it.value === cur ? 'true' : 'false', title: it.title,
        onClick: function () { st[1](it.value); if (p.onChange) p.onChange(it.value); } }, it.label);
    }));
  }
  function LocaleSwitch(p) {
    return h(Segmented, { label: p.label || 'Language', value: p.value, defaultValue: p.defaultValue || 'hy', onChange: p.onChange,
      items: [{ value: 'hy', label: 'ՀԱՅ', title: 'Հայերեն' }, { value: 'en', label: 'EN', title: 'English' }, { value: 'ru', label: 'РУС', title: 'Русский' }] });
  }
  function applyTheme(v) {
    var r = document.documentElement, mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    r.setAttribute('data-theme', v === 'system' ? (mq && mq.matches ? 'dark' : 'light') : v);
  }
  function ThemeSwitch(p) {
    var initial = p.value !== undefined ? p.value : (p.defaultValue || 'system'), pref = useState(initial);
    var current = p.value !== undefined ? p.value : pref[0];
    useEffect(function () {
      if (p.apply === false) return undefined;
      applyTheme(current);
      if (current !== 'system' || !window.matchMedia) return undefined;
      var mq = window.matchMedia('(prefers-color-scheme: dark)'), on = function () { applyTheme('system'); };
      if (mq.addEventListener) mq.addEventListener('change', on); else if (mq.addListener) mq.addListener(on);
      return function () { if (mq.removeEventListener) mq.removeEventListener('change', on); else if (mq.removeListener) mq.removeListener(on); };
    }, [current, p.apply]);
    function choose(v) { pref[1](v); if (p.onChange) p.onChange(v); }
    var L = p.labels || {};
    return h(Segmented, { label: p.label || 'Theme', value: current, onChange: choose,
      items: [{ value: 'system', label: L.system || 'System' }, { value: 'light', label: L.light || 'Light' }, { value: 'dark', label: L.dark || 'Dark' }] });
  }
  function MetricBar(p) {
    var pct = Math.max(0, Math.min(100, Number(p.value) || 0)), st = useState(reducedMotion() ? pct : 0);
    useEffect(function () { var t = setTimeout(function () { st[1](pct); }, 30); return function () { clearTimeout(t); }; }, [pct]);
    return h('div', { className: 'mq-metric' },
      h('div', { className: 'mq-metric-head' }, h('span', null, p.label), h('span', { className: 'muted' }, p.display || pct + '%')),
      h('div', { className: 'mq-metric-track', role: 'progressbar', 'aria-label': p.label, 'aria-valuenow': pct, 'aria-valuemin': 0, 'aria-valuemax': 100 }, h('div', { className: 'mq-metric-fill', style: { width: st[0] + '%' } })));
  }
  function ContrastSection(p) {
    return h('section', { className: cx('section-contrast', p.spotlight && 'section-spotlight', p.grid && 'mq-grid-bg', p.className), 'aria-labelledby': p.labelledBy }, p.children);
  }

  window.MenQ = { BrandMark: BrandMark, Button: Button, Card: Card, Panel: Panel, PageHeader: PageHeader, SectionHeading: SectionHeading, Badge: Badge, StatusDot: StatusDot, Avatar: Avatar,
    Field: Field, Input: Input, Textarea: Textarea, Select: Select, FormRow: FormRow, Checkbox: Checkbox, RadioGroup: RadioGroup, Switch: Switch, Icon: Icon, Accordion: Accordion, Nav: Nav, Tooltip: Tooltip, Reveal: Reveal, Tabs: Tabs, LocaleSwitch: LocaleSwitch, ThemeSwitch: ThemeSwitch, EmptyState: EmptyState, Skeleton: Skeleton,
    Toast: Toast, Modal: Modal, ConfirmDialog: ConfirmDialog, Drawer: Drawer, KpiStat: KpiStat, MetricBar: MetricBar, Table: Table, ContrastSection: ContrastSection, applyTheme: applyTheme };
})();
