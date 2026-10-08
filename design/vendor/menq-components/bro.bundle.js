/* @ds-bundle: {"format":4,"namespace":"MenQ.Bro","components":[{"name":"Timeline"},{"name":"ChatMessage"},{"name":"AgentCard"},{"name":"ApprovalCard"},{"name":"CommandComposer"}]} */
/* MenQ product extension: Bro (D-027). Requires window.React and the brand-expression core bundle (window.MenQ). */
(function () {
  var React = window.React, M = window.MenQ;
  if (!React || !M) throw new Error('MenQ Bro extension: load React and brand-expression/components/bundle.js first');
  var h = React.createElement, useState = React.useState, useRef = React.useRef;
  var Avatar = M.Avatar, Badge = M.Badge, Button = M.Button, Card = M.Card, StatusDot = M.StatusDot;
  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(' '); }
  function pct(v) { return Math.max(0, Math.min(100, Number(v) || 0)); }
  M.Bro = { avatarSrc: null };
  function Timeline(p) {
    return h('ol', { className: 'mq-timeline' }, (p.items || []).map(function (it, i) {
      return h('li', { key: i, className: 'mq-tl-item mq-tl--' + (it.state || 'done') },
        h('span', { className: 'mq-tl-marker', 'aria-hidden': 'true' }),
        h('div', { className: 'mq-tl-body' }, h('div', { className: 'mq-tl-title' }, it.title), it.meta ? h('div', { className: 'mq-tl-meta' }, it.meta) : null, it.detail ? h('div', { className: 'run-step-result' }, it.detail) : null));
    }));
  }
  function ChatMessage(p) {
    var role = p.role || 'human';
    return h('div', { className: cx('chat-msg', 'mq-msg--' + role, p.mine && 'chat-msg--mine') },
      h(Avatar, { name: p.author, kind: role, src: role === 'bro' ? (p.avatarSrc || M.Bro.avatarSrc) : p.avatarSrc }),
      h('div', { className: 'mq-msg-col' },
        h('div', { className: 'chat-author' }, h('span', { className: 'mq-msg-name' }, p.author), p.scope ? h('span', { className: 'mq-msg-scope' }, p.scope) : null, p.time ? h('span', null, ' · ' + p.time) : null),
        h('div', { className: 'chat-bubble' }, p.children),
        p.state ? h('div', { className: 'mq-msg-state' }, h(StatusDot, { status: p.state === 'running' ? 'busy' : p.state === 'failed' ? 'error' : 'online', label: p.stateLabel || p.state })) : null));
  }
  function AgentCard(p) {
    return h(Card, { className: 'mq-agent', variant: 'elevated' },
      h('div', { className: 'row between' }, h('div', { className: 'row' }, h(Avatar, { name: p.name, kind: 'agent' }), h('div', null, h('div', { className: 'panel-title' }, p.name), h('div', { className: 'muted', style: { fontSize: 12 } }, p.role))), h(StatusDot, { status: p.status, label: p.statusLabel })),
      p.scope ? h('div', { className: 'mq-agent-scope' }, p.scope.map(function (s) { return h(Badge, { key: s, tone: 'accent' }, s); })) : null,
      p.task ? h('div', { className: 'mq-agent-task' }, h('span', { className: 'field-label' }, p.taskLabel || 'Current task'), h('div', null, p.task)) : null,
      p.progress != null ? h('div', { className: 'mq-progress', role: 'progressbar', 'aria-label': (p.progressLabel || 'Progress') + ': ' + p.name, 'aria-valuenow': pct(p.progress), 'aria-valuemin': 0, 'aria-valuemax': 100 }, h('span', { style: { width: pct(p.progress) + '%' } })) : null);
  }
  function ApprovalCard(p) {
    var risk = p.risk || 'medium', tone = risk === 'high' ? 'danger' : risk === 'low' ? 'success' : 'warning';
    return h(Card, { className: 'mq-approval mq-approval--' + risk, variant: 'elevated' },
      h('div', { className: 'row between' }, h('div', { className: 'field-label' }, p.kicker || 'Approval required'), h(Badge, { tone: tone }, p.riskLabel || risk + ' risk')),
      h('div', { className: 'panel-title', style: { marginTop: 8 } }, p.title),
      p.description ? h('div', { className: 'muted', style: { marginTop: 4 } }, p.description) : null,
      p.requestedBy ? h('div', { className: 'row', style: { marginTop: 12, fontSize: 12 } }, h(Avatar, { name: p.requestedBy, kind: 'agent' }), h('span', { className: 'muted' }, p.requestedBy)) : null,
      h('div', { className: 'form-actions', style: { marginTop: 16 } }, h(Button, { variant: 'ghost', small: true, onClick: p.onReject }, p.rejectLabel || 'Reject'), h(Button, { variant: 'primary', small: true, onClick: p.onApprove }, p.approveLabel || 'Approve')));
  }
  function CommandComposer(p) {
    var st = useState(''), ref = useRef(null);
    function send() { var v = st[0].trim(); if (!v) return; if (p.onSubmit) p.onSubmit(v); st[1](''); }
    return h('div', { className: 'mq-composer' },
      h('span', { className: 'mq-composer-prompt', 'aria-hidden': 'true' }, '›'),
      h('textarea', { ref: ref, rows: 1, value: st[0], placeholder: p.placeholder || 'Ask Bro…', 'aria-label': p.label || p.placeholder || 'Command',
        onChange: function (e) { st[1](e.target.value); },
        onKeyDown: function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } } }),
      p.hint ? h('kbd', { className: 'mq-kbd' }, p.hint) : null,
      h(Button, { variant: 'primary', small: true, onClick: send, disabled: !st[0].trim() }, p.sendLabel || 'Send'));
  }
  M.Bro.Timeline = Timeline; M.Bro.ChatMessage = ChatMessage; M.Bro.AgentCard = AgentCard; M.Bro.ApprovalCard = ApprovalCard; M.Bro.CommandComposer = CommandComposer;
})();
