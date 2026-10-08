'use strict';
// Armen portal page. Nothing is sent by a choice alone: photos go after «Загрузить фото», answers after
// «Сохранить ответы». Every result shown is the server's own answer, next to the thing it belongs to.
const ROOT = '/operator/work/armen/';
const actor = document.querySelector('meta[name="actor"]').content;
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const readOnly = actor === 'gev';
const $ = id => document.getElementById(id);
const KEEP = 'kryuk-armen-chosen';
const MAX = 20 * 1024 * 1024;
const TYPES = ['image/jpeg', 'image/png', 'image/webp'];

let state = null;      // the last state the server gave
const saved = {};      // question id -> the answer the server holds for today
const chosen = {};     // question id -> {value, key}: picked here, not saved yet. The key stays with the choice,
                       // so a second tap or a retry repeats the same request and the server stores it once.
const results = {};    // question id -> {ok, text}: what the server said about the last save of that answer
const pending = [];    // photos picked, not sent yet: {file, url, status, text, percent, problem}
let saving = false;
let sending = false;

function note(el, text, kind) { el.textContent = text; el.className = 'note' + (kind ? ' ' + kind : ''); }
function key() { return crypto.randomUUID().replaceAll('-', ''); }
function expired() {
  try { sessionStorage.setItem('kryuk-armen-expired', '1'); } catch (e) {}
  remember();
  location.reload();
}
function remember() {
  // Picked answers survive a reload (the login form after the session ends) in this tab only.
  try {
    if (Object.keys(chosen).length && state) sessionStorage.setItem(KEEP, JSON.stringify({ day: state.day, chosen }));
    else sessionStorage.removeItem(KEEP);
  } catch (e) {}
}
function recall() {
  try {
    const kept = JSON.parse(sessionStorage.getItem(KEEP) || 'null');
    if (!kept || kept.day !== state.day) return;
    for (const q of state.questions) {
      const c = kept.chosen[q.id];
      if (c && q.options.some(o => o[0] === c.value) && /^[a-f0-9]{32}$/.test(c.key) && c.value !== saved[q.id]) chosen[q.id] = { value: c.value, key: c.key };
    }
  } catch (e) {}
}
async function api(path, options = {}) {
  const r = await fetch(ROOT + path, { credentials: 'same-origin', ...options });
  let data = {};
  try { data = await r.json(); } catch (e) {}
  if (r.status === 401) { expired(); throw new Error('Время входа истекло. Войдите снова.'); }
  if (r.status === 429) throw new Error('Слишком часто. Подождите минуту и повторите.');
  if (!r.ok) throw new Error(data.error || 'Не сохранилось');
  return data;
}

// ---- answers: pick first, save with one button
function renderQuestions() {
  $('question-heading').textContent = 'Сегодня · ' + state.day;
  const area = $('questions');
  area.replaceChildren();
  for (const q of state.questions) {
    const card = document.createElement('div'); card.className = 'question';
    const head = document.createElement('div'); head.className = 'qhead';
    const title = document.createElement('h3'); title.textContent = q.title; head.append(title);
    const mark = document.createElement('span'); head.append(mark); card.append(head);
    const choices = document.createElement('div'); choices.className = 'choices';
    const current = chosen[q.id] ? chosen[q.id].value : saved[q.id];
    for (const [value, label] of q.options) {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
      b.setAttribute('aria-pressed', String(current === value));
      b.disabled = readOnly || saving;
      b.onclick = () => {
        if (value === saved[q.id]) delete chosen[q.id];
        else if (!chosen[q.id] || chosen[q.id].value !== value) chosen[q.id] = { value, key: key() };
        delete results[q.id];
        note($('save-status'), '');
        remember(); renderQuestions();
      };
      choices.append(b);
    }
    card.append(choices);
    // The state of each answer sits in its own heading line; only a refusal takes a line of its own, with the reason.
    if (results[q.id] && !results[q.id].ok) {
      note(mark, 'Не сохранено', 'error');
      const line = document.createElement('p'); note(line, results[q.id].text, 'error'); card.append(line);
    } else if (chosen[q.id]) note(mark, 'Не сохранено', 'warn');
    else if (saved[q.id] !== undefined) note(mark, 'Сохранено', 'ok');
    else note(mark, '');
    area.append(card);
  }
  const count = Object.keys(chosen).length;
  $('save').textContent = count ? 'Сохранить ответы (' + count + ')' : 'Сохранить ответы';
  $('save').disabled = readOnly || saving || !count;
  $('savebar').classList.toggle('waiting', count > 0);  // with unsaved choices the button stays at the bottom of the screen
}
async function saveAnswers() {
  if (saving || readOnly) return;
  const ids = Object.keys(chosen);
  if (!ids.length) return;
  saving = true; note($('save-status'), 'Сохраняем…'); renderQuestions();
  const failed = [];
  for (const id of ids) {
    const pick = chosen[id];
    try {
      await api('api/answer', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': pick.key },
        body: JSON.stringify({ question: id, answer: pick.value, day: state.day }) });
      saved[id] = pick.value; delete chosen[id]; results[id] = { ok: true, text: 'Сохранено' };
    } catch (e) {
      results[id] = { ok: false, text: e.message };
      failed.push('«' + state.questions.find(q => q.id === id).title + '»');
    }
  }
  saving = false; remember(); renderQuestions();
  if (!failed.length) note($('save-status'), 'Сохранено: ' + ids.length + ' из ' + ids.length, 'ok');
  else note($('save-status'), 'Сохранено ' + (ids.length - failed.length) + ' из ' + ids.length + '. Не сохранились: ' + failed.join(', ') + '. Ваш выбор на месте, нажмите «Сохранить ответы» еще раз.', 'error');
}

// ---- photos: pick, look, remove, then send
function addPhotos(input) {
  for (const file of Array.from(input.files || [])) {
    if (pending.some(p => p.status !== 'saved' && p.file.name === file.name && p.file.size === file.size && p.file.lastModified === file.lastModified)) continue;
    let problem = '';
    if (!TYPES.includes(file.type)) problem = 'Нужен JPEG, PNG или WebP';
    else if (file.size > MAX) problem = 'Больше 20 МБ';
    pending.push({ file, url: problem ? '' : URL.createObjectURL(file), status: problem ? 'refused' : 'chosen', text: problem, percent: 0 });
  }
  input.value = '';
  for (let i = pending.length - 1; i >= 0; i--) if (pending[i].status === 'saved') drop(i);  // shown once, then gone
  note($('upload-status'), '');
  renderPending();
}
function drop(i) { if (pending[i].url) URL.revokeObjectURL(pending[i].url); pending.splice(i, 1); }
function waiting() { return pending.filter(p => p.status === 'chosen' || p.status === 'failed'); }
function renderPending() {
  const list = $('pending');
  list.replaceChildren();
  pending.forEach((p, i) => {
    const li = document.createElement('li');
    const im = document.createElement('img'); im.alt = ''; if (p.url) im.src = p.url; li.append(im);
    const box = document.createElement('div');
    const name = document.createElement('p'); name.className = 'name'; name.textContent = p.file.name; box.append(name);
    const st = document.createElement('p');
    const size = p.file.size < 1048576 ? Math.max(1, Math.round(p.file.size / 1024)) + ' КБ' : (p.file.size / 1048576).toFixed(1).replace('.', ',') + ' МБ';
    const words = { chosen: [size + ' · выбрано, еще не загружено', ''], uploading: ['Загружаем… ' + p.percent + '%', ''], saved: [p.text, 'ok'], failed: ['Не загружено: ' + p.text, 'error'], refused: [p.text, 'error'] }[p.status];
    st.className = 'state' + (words[1] ? ' ' + words[1] : ''); st.textContent = words[0]; box.append(st); p.line = st;
    li.append(box);
    if (p.status !== 'uploading' && p.status !== 'saved') {
      const x = document.createElement('button'); x.type = 'button'; x.className = 'quiet'; x.textContent = 'Убрать';
      x.setAttribute('aria-label', 'Убрать фото ' + p.file.name); x.disabled = sending;
      x.onclick = () => { drop(i); note($('upload-status'), ''); renderPending(); };
      li.append(x);
    }
    list.append(li);
  });
  const count = waiting().length;
  $('send').hidden = !count && !sending;
  $('send').disabled = sending || !count;
  $('send').textContent = count ? 'Загрузить фото (' + count + ')' : 'Загрузить фото';
  for (const id of ['gallery', 'camera', 'purpose']) $(id).disabled = sending;
}
function sendOne(p, purpose) {
  return new Promise(resolve => {
    const x = new XMLHttpRequest();
    x.open('POST', ROOT + 'api/photo');
    x.setRequestHeader('Content-Type', p.file.type);
    x.setRequestHeader('X-CSRF-Token', csrf);
    x.setRequestHeader('X-Photo-Purpose', purpose);
    x.upload.onprogress = e => { if (e.lengthComputable) { p.percent = Math.round(e.loaded / e.total * 100); $('progress').value = p.percent; if (p.line) p.line.textContent = 'Загружаем… ' + p.percent + '%'; } };
    x.onerror = () => resolve({ status: 0, data: {} });
    x.onload = () => { let data = {}; try { data = JSON.parse(x.responseText); } catch (e) {} resolve({ status: x.status, data }); };
    x.send(p.file);
  });
}
async function sendPhotos() {
  if (sending || readOnly) return;
  const queue = waiting();
  if (!queue.length) return;
  sending = true; const purpose = $('purpose').value; let done = 0;
  $('progress').hidden = false;
  for (const p of queue) {
    p.status = 'uploading'; p.percent = 0; $('progress').value = 0;
    note($('upload-status'), 'Загружаем ' + (done + 1) + ' из ' + queue.length + '…'); renderPending();
    const r = await sendOne(p, purpose);
    if (r.status === 401) { expired(); return; }
    if (r.status === 201 && r.data.saved) { p.status = 'saved'; p.text = r.data.duplicate ? 'Уже было загружено раньше' : 'Сохранено на сервере'; done++; }
    else { p.status = 'failed'; p.text = r.status === 0 ? 'нет связи' : r.status === 429 ? 'сервер занят, повторите через минуту' : r.status === 413 ? 'файл слишком большой' : (r.data.error || 'ошибка ' + r.status); }
  }
  sending = false; $('progress').hidden = true; renderPending();
  const bad = queue.length - done;
  note($('upload-status'), bad ? 'Сохранено ' + done + ' из ' + queue.length + '. Не загружено: ' + bad + '. Они остались в списке, нажмите «Загрузить фото» еще раз.' : 'Сохранено: ' + done + ' из ' + queue.length, bad ? 'error' : 'ok');
  if (done) try { state.photos = (await api('api/state')).photos; renderPhotos(); } catch (e) { note($('status'), 'Список фото не обновился. Обновите страницу.', 'error'); }
}
function renderPhotos() {
  const photos = $('photos');
  photos.replaceChildren();
  for (const p of state.photos) {
    const card = document.createElement('div'); card.className = 'photo';
    const im = document.createElement('img'); im.src = ROOT + 'preview/' + p.id; im.alt = 'Загруженное фото'; im.loading = 'lazy'; card.append(im);
    const date = document.createElement('p'); date.textContent = p.created.slice(0, 10); card.append(date);
    photos.append(card);
  }
  if (!state.photos.length) { const none = document.createElement('p'); none.className = 'hint empty'; none.textContent = 'Пока нет фото.'; photos.append(none); }
}

async function load() {
  state = await api('api/state');
  for (const a of state.answers) if (a.actor === 'armen') saved[a.question] = a.answer;
  recall();
  renderQuestions(); renderPhotos(); renderPending();
}
if (readOnly) {
  $('greeting').textContent = 'Фото и ответы Армена';
  $('upload').hidden = true; $('save').hidden = true;
  $('question-hint').textContent = 'Ответы Армена. Только просмотр.';
}
for (const id of ['gallery', 'camera']) $(id).onchange = e => addPhotos(e.target);
$('send').onclick = sendPhotos;
$('save').onclick = saveAnswers;
$('logout').onclick = async () => {
  try { await api('api/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrf } }); try { sessionStorage.removeItem(KEEP); } catch (e) {} location.reload(); }
  catch (e) { note($('status'), e.message, 'error'); }
};
load().catch(() => note($('status'), 'Не удалось загрузить. Обновите страницу и проверьте вход.', 'error'));
