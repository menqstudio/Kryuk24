(()=>{
'use strict';
const form=document.querySelector('[data-request]');if(!form)return;
const box=document.createElement('fieldset');box.style.cssText='border:2px solid #d69c00;padding:16px;grid-column:1/-1;min-width:0';
box.innerHTML='<legend>Только локальный тест</legend><p>Заявка сохранится в тестовом журнале. Армену ничего не отправится; машина не назначается.</p><label>Тестовый контакт <input data-test-contact maxlength="100" placeholder="Например, TEST-GEV"></label><button type="button" data-test-save>Зарегистрировать тестовую заявку</button><p role="status" aria-live="polite" data-test-status></p><a href="/test-orders">Посмотреть тестовые заявки</a>';
form.append(box);let pending=null,confirmed=false;
const status=box.querySelector('[data-test-status]'),button=box.querySelector('button');
button.addEventListener('click',async()=>{
 const value=s=>form.querySelector(s)?.value?.trim()||'';
 const data={contact:value('[data-test-contact]'),pickup:value('[data-from]'),destination:value('[data-to]'),vehicle:value('input[name=vehicle]:checked'),message:new URL(form.querySelector('[data-request-wa]').href).searchParams.get('text')||'',estimate_display:form.querySelector('[data-quote]').textContent};
 if(!data.contact||!data.pickup||!data.destination||!data.vehicle){status.textContent='Заполните тестовый контакт, транспорт и оба адреса.';return;}
 const raw=JSON.stringify(data);
 if(!pending||pending.raw!==raw)pending={raw,key:crypto.randomUUID()};
 else if(confirmed){status.textContent='Эта тестовая заявка уже зарегистрирована. Измените данные для новой.';return;}
 confirmed=false;button.disabled=true;status.textContent='Сохраняем тест…';
 try{const r=await fetch('/test-intake',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':pending.key,'X-Test-Nonce':window.KRYUK_TEST_NONCE},body:pending.raw});const d=await r.json();if(!r.ok)throw Error(d.error);confirmed=true;status.textContent='Тестовая заявка '+d.id+' сохранена. Статус NEW. Армен НЕ уведомлен.';}
 catch(e){status.textContent='Не удалось сохранить. Можно повторить с теми же данными. '+e.message;}
 finally{button.disabled=false;}
});
})();
