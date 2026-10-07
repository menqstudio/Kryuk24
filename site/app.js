/* The visitor reviews and sends the composed WhatsApp message. */
(function(){
'use strict';
var doc=document;doc.documentElement.classList.add('js');
var form=doc.querySelector('[data-request]');
if(form){
 const $=s=>form.querySelector(s), text=el=>el.value.replace(/\s+/g,' ').trim();
 const cl=$('[data-class]'),sit=$('[data-situation]'),wheels=$('[data-wheels]'),blocked=$('[data-blocked]'),model=$('[data-model]'),from=$('[data-from]'),to=$('[data-to]'),km=$('[data-km]'),wa=$('[data-request-wa]'),quote=$('[data-quote]'),detail=$('[data-detail]');
 const vehicle=()=>form.querySelector('input[name=vehicle]:checked')?.value||'';
 const route=$('[data-route-preview]'),frame=$('[data-route-frame]'),kmNote=$('#km-note'),retry=$('[data-route-retry]');
 const points=new Map();let routeVersion=0,routeController,routeState='empty';
 const money=n=>n.toLocaleString('ru-RU');
 const routeURL=base=>base+'?rtext='+encodeURIComponent([from,to].map(el=>{const p=points.get(el);return p?p[1]+','+p[0]:text(el);}).join('~'))+'&rtt=auto';
 let mapTimer;
 function refreshMap(immediate=false){
  clearTimeout(mapTimer);
  const render=()=>{
   const inputs=[from,to].filter(el=>text(el).length>=3),ready=inputs.length===2;
   let params='?ll=37.617635%2C55.755814&z=10';
   if(ready)params=routeURL('').slice(0);
   else if(inputs.length===1){const input=inputs[0],point=points.get(input);params=point?'?ll='+encodeURIComponent(point.join(','))+'&z=15&pt='+encodeURIComponent(point.join(',')+',pm2orm'):'?mode=search&text='+encodeURIComponent(text(input));}
   const url='https://yandex.ru/map-widget/v1/'+params;
   if(frame.getAttribute('src')!==url)frame.src=url;
  };
  if(immediate)render();else mapTimer=setTimeout(render,600);
 }
 function invalidate(){routeVersion++;routeController?.abort();km.value='';routeState='empty';retry.hidden=true;kmNote.hidden=false;kmNote.textContent='Выберите оба адреса из подсказок.';refreshMap();update();}
 async function requestJSON(url,controller){const timer=setTimeout(()=>controller.abort(),12000);try{const res=await fetch(url,{signal:controller.signal});if(!res.ok)throw Error('HTTP');return await res.json();}finally{clearTimeout(timer);}}
 async function calculate(){invalidate();if(!points.has(from)||!points.has(to))return;const version=routeVersion;routeController=new AbortController();routeState='loading';kmNote.textContent='Рассчитываем дорожный маршрут…';update();try{const pair=[points.get(from),points.get(to)].map(p=>p.join(',')).join(';');const data=await requestJSON('https://router.project-osrm.org/route/v1/driving/'+pair+'?overview=false',routeController);if(version!==routeVersion)return;const metres=data.routes?.[0]?.distance;if(data.code!=='Ok'||!Number.isFinite(metres)||metres<0)throw Error('route');km.value=String(Math.ceil(metres/1000));routeState='ready';kmNote.textContent='';kmNote.hidden=true;}catch(e){if(version!==routeVersion)return;routeState='error';kmNote.textContent='Не удалось рассчитать маршрут. Расстояние и цену уточним при разговоре.';retry.hidden=false;}update();refreshMap();}
 retry.addEventListener('click',calculate);refreshMap(true);
 // Search results are selected explicitly; never silently guess an address.
 [from,to].forEach((input,index)=>{
  let timer,controller,sequence=0;const box=doc.createElement('div');box.className='address-results';box.id='address-results-'+index;box.hidden=true;input.parentElement.append(box);input.autocomplete='off';input.setAttribute('aria-controls',box.id);input.setAttribute('aria-expanded','false');const note=doc.createElement('small');note.className='field-note';note.setAttribute('aria-live','polite');input.parentElement.append(note);
  const close=()=>{box.hidden=true;input.setAttribute('aria-expanded','false');};
  input.addEventListener('input',()=>{points.delete(input);invalidate();clearTimeout(timer);controller?.abort();const ticket=++sequence;close();note.textContent='';if(text(input).length<3)return;timer=setTimeout(async()=>{controller=new AbortController();note.textContent='Ищем адрес…';try{const data=await requestJSON('https://photon.komoot.io/api/?limit=5&lat=55.75&lon=37.62&q='+encodeURIComponent(text(input)),controller);if(ticket!==sequence)return;box.replaceChildren();(data.features||[]).forEach(feature=>{const coordinates=feature.geometry?.coordinates;if(!coordinates||coordinates.length!==2||!coordinates.every(Number.isFinite))return;const p=feature.properties||{};const title=[p.name,p.street,p.housenumber,p.city||p.town||p.village,p.state,p.country].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).join(', ');const button=doc.createElement('button');button.type='button';button.textContent=title||coordinates.join(', ');button.addEventListener('click',()=>{input.value=button.textContent;points.set(input,coordinates);close();note.textContent='Адрес выбран';input.focus();calculate();refreshMap(true);});box.append(button);});box.hidden=!box.childElementCount;input.setAttribute('aria-expanded',String(!box.hidden));note.textContent=box.hidden?'Адрес не найден. Уточните город, улицу и дом или отправьте ориентир в мессенджере.':'Выберите нужный адрес.';}catch(e){if(ticket===sequence)note.textContent='Подсказки недоступны. Адрес можно отправить текстом — маршрут уточним.';}},500);});
  input.addEventListener('keydown',e=>{if(e.key==='Escape')close();if(e.key==='ArrowDown'&&!box.hidden){e.preventDefault();box.querySelector('button')?.focus();}});
  box.addEventListener('keydown',e=>{const buttons=[...box.querySelectorAll('button')],i=buttons.indexOf(doc.activeElement);if(e.key==='Escape'){close();input.focus();}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}});
  doc.addEventListener('click',e=>{if(!input.parentElement.contains(e.target))close();});
 });
 // Native selects remain as the no-JavaScript fallback. Enhanced choices toggle off.
 const choiceRefresh=[];
 form.querySelectorAll('select').forEach((select,index)=>{
  const wrapper=doc.createElement('div');wrapper.className='choice-select';const trigger=doc.createElement('button');trigger.type='button';trigger.className='choice-trigger';trigger.setAttribute('aria-haspopup','listbox');trigger.setAttribute('aria-expanded','false');const list=doc.createElement('div');list.className='choice-options';list.id='choice-'+index;list.setAttribute('role','listbox');list.setAttribute('aria-label',select.parentElement.firstChild.textContent.trim());list.hidden=true;trigger.setAttribute('aria-controls',list.id);trigger.setAttribute('aria-label',list.getAttribute('aria-label'));select.after(wrapper);wrapper.append(trigger,list);select.hidden=true;select.tabIndex=-1;
  const sync=()=>{trigger.textContent=select.options[select.selectedIndex].text;trigger.disabled=select.disabled;list.querySelectorAll('button').forEach(b=>{b.disabled=select.disabled;b.setAttribute('aria-selected',String(b.dataset.value===select.value));});if(select.disabled){list.hidden=true;trigger.setAttribute('aria-expanded','false');}};choiceRefresh.push(sync);
  const close=()=>{list.hidden=true;trigger.setAttribute('aria-expanded','false');};
  [...select.options].slice(1).forEach(option=>{const b=doc.createElement('button');b.type='button';b.setAttribute('role','option');b.dataset.value=option.value;b.textContent=option.text;b.addEventListener('click',()=>{select.value=select.value===option.value?'':option.value;close();select.dispatchEvent(new Event('change',{bubbles:true}));trigger.focus();});list.append(b);});
  trigger.addEventListener('click',()=>{list.hidden=!list.hidden;trigger.setAttribute('aria-expanded',String(!list.hidden));});
  wrapper.addEventListener('keydown',e=>{if(select.disabled)return;const buttons=[...list.querySelectorAll('button')];let i=buttons.indexOf(doc.activeElement);if(e.key==='Escape'){close();trigger.focus();}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();list.hidden=false;trigger.setAttribute('aria-expanded','true');buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(e.key==='Home'||e.key==='End'){e.preventDefault();buttons[e.key==='Home'?0:buttons.length-1]?.focus();}});
  doc.addEventListener('click',e=>{if(!wrapper.contains(e.target))close();});sync();
 });
 // Pointer and keyboard activation both clear an already-selected vehicle.
 form.querySelectorAll('input[name=vehicle]').forEach(input=>{let selected=false;input.parentElement.addEventListener('pointerdown',()=>selected=input.checked);input.addEventListener('keydown',e=>{if(e.key===' ')selected=input.checked;});input.addEventListener('click',e=>{if(selected){e.preventDefault();setTimeout(()=>{input.checked=false;selected=false;update();},0);}else update();});});
 let lastVehicle='',models={commercial:'',special:''};
 function update(){const v=vehicle();if(v!==lastVehicle){if(lastVehicle==='commercial'||lastVehicle==='special')models[lastVehicle]=model.value;model.value=models[v]||'';lastVehicle=v;}
 const active=(box,input,on)=>{box.hidden=false;input.disabled=!on;box.classList.toggle('field--inactive',!on);};active($('[data-class-box]'),cl,v==='car');active($('[data-model-box]'),model,v==='commercial'||v==='special');active($('[data-wheels-box]'),wheels,!!v);active($('[data-blocked-box]'),blocked,!!v&&wheels.value==='Нет');$('[data-model-label]').textContent=v==='commercial'?'Модель и размер транспорта':v==='special'?'Тип техники и масса':'Модель или тип техники';model.placeholder='Например, ГАЗель NEXT или мини-погрузчик';
 choiceRefresh.forEach(fn=>fn());
 const base=!v||v==='moto'?4000:v==='commercial'||v==='special'?5000:Math.max(Number(cl.value)||4000,sit.value==='Застрял / сложный подъезд'?5000:0);
 const distance=routeState==='ready'?Number(km.value):null;
 const missing=!v||(v==='car'&&!cl.value)||!sit.value||!wheels.value;
 const complex=v==='commercial'||v==='special'||['После ДТП','Застрял / сложный подъезд','Другое / не знаю'].includes(sit.value)||(wheels.value&&wheels.value!=='Да');
 // Dollies: 1 500 each, one per blocked wheel (Armen, 06.10.2026).
 const dolly=v==='car'&&wheels.value==='Нет'?({1:1500,2:3000,3:4500,4:6000})[blocked.value]||0:0;
 const amount=base+dolly+100*(distance??0);
 quote.textContent='от '+money(amount)+' ₽';
 if(!v)detail.textContent='Минимальный тариф. Выберите транспорт и маршрут.';
 else if(v==='commercial')detail.textContent='Минимум для коммерческого транспорта; размер и погрузку уточним.';
 else if(v==='special')detail.textContent='Минимум для спецтехники; стоимость зависит от массы и погрузки.';
 else if(dolly)detail.textContent='В расчет включены подкатные тележки: '+money(dolly)+' ₽.';
 else if(complex)detail.textContent='Дополнительную погрузку и оборудование согласуем отдельно.';
 else if(missing)detail.textContent=v==='car'&&!cl.value?'Укажите класс, ситуацию и состояние колес.':'Укажите ситуацию и состояние колес.';
 else detail.textContent='';
 detail.hidden=!detail.textContent;
 const names={car:cl.value?'Автомобиль, '+cl.options[cl.selectedIndex].text.toLowerCase():'Автомобиль',moto:'Мотоцикл',commercial:'Коммерческий транспорт',special:'Спецтехника'};
 // Only what the visitor actually filled in, and only fields that are active for the chosen transport.
 const lines=['Здравствуйте! Нужен эвакуатор.'];if(v)lines.push('Транспорт: '+names[v]);if(sit.value)lines.push('Ситуация: '+sit.value);if(v&&wheels.value)lines.push('Колеса крутятся: '+wheels.value);if(v&&wheels.value==='Нет'&&blocked.value)lines.push('Заблокировано колес: '+blocked.value);if(dolly)lines.push('Тележки по тарифу: '+money(dolly)+' ₽ (в сумме)');if((v==='commercial'||v==='special')&&text(model))lines.push('Модель / тип: '+text(model));if(text(from))lines.push('Откуда: '+text(from));if(text(to))lines.push('Куда: '+text(to));if(points.has(from)&&points.has(to))lines.push('Карта: '+routeURL('https://yandex.ru/maps/'));if(distance!==null)lines.push('Расстояние по маршруту: '+distance+' км (предварительно)');lines.push('Предварительно: от '+money(amount)+' ₽'+(distance===null?' + от 100 ₽/км.':'.'));lines.push('Подскажите итоговую стоимость и время подачи.');wa.href='https://wa.me/79858930606?text='+encodeURIComponent(lines.join('\n'));doc.querySelector('[data-request-tg]').href='https://t.me/+79858930606?text='+encodeURIComponent(lines.join('\n'));
 }
 wa.addEventListener('click',()=>update());form.addEventListener('input',update);form.addEventListener('change',update);form.addEventListener('submit',e=>e.preventDefault());update();
}
/* All tariff panels remain accessible without JavaScript. */
doc.querySelectorAll('[data-tabs]').forEach(function(tabs){
 var buttons=Array.from(tabs.querySelectorAll('[role=tab]'));
 var select=function(active,focus){buttons.forEach(function(b){var on=b===active;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;doc.getElementById(b.getAttribute('aria-controls')).hidden=!on;});var body=tabs.closest('.pl');if(body)body.scrollTop=0;if(focus)active.focus();};
 select(buttons.find(function(b){return b.getAttribute('aria-selected')==='true';})||buttons[0]);
 tabs.addEventListener('click',function(e){var b=e.target.closest('[role=tab]');if(b)select(b);});
 tabs.addEventListener('keydown',function(e){var i=buttons.indexOf(doc.activeElement);if(i<0)return;var next;if(e.key==='ArrowRight')next=(i+1)%buttons.length;if(e.key==='ArrowLeft')next=(i-1+buttons.length)%buttons.length;if(e.key==='Home')next=0;if(e.key==='End')next=buttons.length-1;if(next!==undefined){e.preventDefault();select(buttons[next],true);}});
});
// Menu link «Тарифы» always opens the tariff tab, not the cities.
doc.querySelectorAll('a[href="#cena"]').forEach(function(a){a.addEventListener('click',function(){var t=doc.getElementById('tab-tarify');if(t&&t.getAttribute('aria-selected')!=='true')t.click();});});
// Keep the expanded tariff level with the adjacent request fields.
const fields=doc.querySelector('.request-fields'),result=doc.querySelector('.request-result'),tariff=doc.querySelector('.tariff-full');
if(fields&&result&&tariff){
 const map=doc.querySelector('.request .route-preview');
 const fitTariff=()=>{const heading=tariff.querySelector('.tariff-heading'),gap=parseFloat(getComputedStyle(tariff.closest('.request')).rowGap)||0;const left=fields.getBoundingClientRect().height+(map?gap+map.getBoundingClientRect().height:0);const available=left-result.getBoundingClientRect().height-gap-heading.getBoundingClientRect().height-2;tariff.style.setProperty('--tariff-height',Math.max(180,available).toFixed(2)+'px');};
 const observer=new ResizeObserver(fitTariff);observer.observe(fields);observer.observe(result);if(map)observer.observe(map);window.addEventListener('resize',fitTariff);doc.fonts.ready.then(fitTariff);fitTariff();
}

// Advance-order dialog. No message is sent automatically.
const booking=doc.querySelector('#booking-dialog');
if(booking){
 const bf=booking.querySelector('[data-booking-form]'),date=booking.querySelector('[data-booking-when]'),situation=booking.querySelector('[data-booking-situation]'),comment=booking.querySelector('[data-booking-comment]'),routeNote=booking.querySelector('[data-booking-route]'),wa=booking.querySelector('[data-booking-wa]'),tg=booking.querySelector('[data-booking-tg]');
 let opener,previousOverflow='',openedBefore=false;
 const moscowNow=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Moscow',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date()).replace(' ','T');
 const value=el=>el?.value.replace(/\s+/g,' ').trim()||'';
 function compose(){
  date.min=moscowNow();const error=date.value&&date.value<date.min?'Выберите будущую дату и время по Москве.':'';date.setCustomValidity(error);date.setAttribute('aria-invalid',String(!!error));const note=booking.querySelector('#booking-when-error');note.textContent=error;note.hidden=!error;
  const selected=bf.querySelector('input[name=booking-vehicle]:checked'),names={car:'Автомобиль',moto:'Мотоцикл',commercial:'Коммерческий транспорт',special:'Спецтехника'};
  const from=value(form?.querySelector('[data-from]')),to=value(form?.querySelector('[data-to]'));
  routeNote.hidden=!from&&!to;routeNote.textContent='Маршрут из расчета: '+(from||'уточнить')+' → '+(to||'уточнить');
  const lines=['Здравствуйте! Хочу заранее заказать перевозку.'];if(selected)lines.push('Транспорт: '+names[selected.value]);if(situation.value)lines.push('Ситуация: '+situation.value);if(date.value&&!error){const [d,t]=date.value.split('T'),[y,m,dd]=d.split('-').map(Number),MG=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];lines.push('Желаемые дата и время: '+dd+' '+MG[m-1]+', '+t+' по Москве');}if(from)lines.push('Откуда: '+from);if(to)lines.push('Куда: '+to);if(value(comment))lines.push('Комментарий: '+comment.value.trim());lines.push('Подтвердите, пожалуйста, дату, время подачи и окончательную стоимость.');
  const message=encodeURIComponent(lines.join('\n'));wa.href='https://wa.me/79858930606?text='+message;tg.href='https://t.me/+79858930606?text='+message;
 }
 doc.querySelectorAll('[data-booking-open]').forEach(button=>button.addEventListener('click',()=>{
  opener=button;if(!openedBefore){const chosen=form?.querySelector('input[name=vehicle]:checked');if(chosen)bf.querySelector('input[value='+chosen.value+']').checked=true;situation.value=form?.querySelector('[data-situation]')?.value||'';openedBefore=true;}closeCal();buildDays();fillTimes();compose();previousOverflow=doc.body.style.overflow;doc.body.style.overflow='hidden';booking.showModal();
 }));
 booking.querySelector('[data-booking-close]').addEventListener('click',()=>booking.close());
 booking.addEventListener('click',e=>{if(e.target===booking){const r=booking.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)booking.close();}});
 booking.addEventListener('close',()=>{doc.body.style.overflow=previousOverflow;opener?.focus({preventScroll:true});});
 bf.querySelectorAll('input[type=radio]').forEach(input=>{let wasChecked=false;input.parentElement.addEventListener('pointerdown',()=>wasChecked=input.checked);input.addEventListener('keydown',e=>{if(e.key===' ')wasChecked=input.checked;});input.addEventListener('click',e=>{if(wasChecked){e.preventDefault();setTimeout(()=>{input.checked=false;wasChecked=false;compose();},0);}});});
 // Day and time in our own style: three quick days + our own month calendar, then 30-minute slots (Moscow time).
 const days=booking.querySelector('[data-when-days]'),trig=booking.querySelector('[data-when-trigger]'),times=booking.querySelector('[data-when-times]');
 const pad=n=>String(n).padStart(2,'0'),WD=['Вс','Пн','Вт','Ср','Чт','Пт','Сб'],MO=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'],
  MF=['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],AHEAD=90;
 let day='',time='',calMonth=null;
 const cal=doc.createElement('div');cal.className='when-cal';cal.id='when-cal';cal.hidden=true;cal.setAttribute('role','group');cal.setAttribute('aria-label','Календарь');days.after(cal);
 const iso=dt=>dt.toISOString().slice(0,10),utc=v=>{const [y,m,d]=v.split('-').map(Number);return new Date(Date.UTC(y,m-1,d));},shift=(v,n)=>{const t=utc(v);t.setUTCDate(t.getUTCDate()+n);return iso(t);};
 const today=()=>moscowNow().slice(0,10),label=v=>{const t=utc(v);return t.getUTCDate()+' '+MO[t.getUTCMonth()];};
 const setWhen=()=>{date.value=day&&time?day+'T'+time:'';bf.dispatchEvent(new Event('input',{bubbles:true}));};
 const fillTimes=()=>{const now=moscowNow();times.innerHTML='';
  for(let m=0;m<24*60;m+=30){const v=pad(Math.floor(m/60))+':'+pad(m%60),b=doc.createElement('button');b.type='button';b.setAttribute('role','option');b.textContent=v;b.dataset.value=v;
   b.disabled=!!day&&day+'T'+v<=now;b.setAttribute('aria-selected',String(v===time));
   b.addEventListener('click',()=>{time=v;trig.textContent=v;closeTimes();setWhen();trig.focus();});times.append(b);}
  if(time&&day&&day+'T'+time<=now){time='';trig.textContent='Выберите время';setWhen();}};
 const closeTimes=()=>{times.hidden=true;trig.setAttribute('aria-expanded','false');};
 const closeCal=()=>{cal.hidden=true;days.querySelector('.when-day--cal')?.setAttribute('aria-expanded','false');};
 const pickDay=v=>{day=v;closeCal();buildDays();fillTimes();setWhen();};
 const buildCal=focusV=>{const t0=today(),last=shift(t0,AHEAD),[y,m]=calMonth,ym=y+'-'+pad(m+1);cal.innerHTML='';
  const head=doc.createElement('div');head.className='when-cal__head';
  const nav=(txt,lbl,dm,off)=>{const b=doc.createElement('button');b.type='button';b.className='when-cal__nav';b.textContent=txt;b.setAttribute('aria-label',lbl);b.disabled=off;
   b.addEventListener('click',()=>{const d=new Date(Date.UTC(y,m+dm,1));calMonth=[d.getUTCFullYear(),d.getUTCMonth()];buildCal();cal.querySelector('.when-cal__nav:not(:disabled)')?.focus();});return b;};
  const title=doc.createElement('strong');title.textContent=MF[m]+' '+y;title.setAttribute('aria-live','polite');
  head.append(nav('‹','Предыдущий месяц',-1,t0.slice(0,7)===ym),title,nav('›','Следующий месяц',1,last.slice(0,7)===ym));
  const grid=doc.createElement('div');grid.className='when-cal__grid';
  ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].forEach(w=>{const s=doc.createElement('span');s.textContent=w;s.setAttribute('aria-hidden','true');grid.append(s);});
  const start=(new Date(Date.UTC(y,m,1)).getUTCDay()+6)%7,n=new Date(Date.UTC(y,m+1,0)).getUTCDate();
  for(let i=0;i<start;i++)grid.append(doc.createElement('i'));
  for(let d=1;d<=n;d++){const v=ym+'-'+pad(d),b=doc.createElement('button');b.type='button';b.textContent=d;b.dataset.value=v;
   b.disabled=v<t0||v>last;b.setAttribute('aria-pressed',String(v===day));if(v===t0)b.classList.add('is-today');b.setAttribute('aria-label',d+' '+MO[m]);b.tabIndex=-1;
   b.addEventListener('click',()=>{pickDay(v);days.querySelector('.when-day--cal')?.focus();});grid.append(b);}
  const live=[...grid.querySelectorAll('button:not(:disabled)')],f=live.find(b=>b.dataset.value===(focusV||day))||live[0];cal.append(head,grid);if(f){f.tabIndex=0;if(focusV)f.focus();}};
 cal.addEventListener('keydown',e=>{const k={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[e.key],cur=doc.activeElement?.dataset?.value;
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closeCal();days.querySelector('.when-day--cal')?.focus();return;}
  if(!k||!cur)return;e.preventDefault();const v=shift(cur,k);if(v<today()||v>shift(today(),AHEAD))return;
  const t=utc(v);calMonth=[t.getUTCFullYear(),t.getUTCMonth()];buildCal(v);});
 const buildDays=()=>{days.innerHTML='';const t0=today();
  for(let i=0;i<3;i++){const v=shift(t0,i),dt=utc(v),b=doc.createElement('button');
   b.type='button';b.className='when-day';b.setAttribute('role','radio');b.dataset.value=v;b.setAttribute('aria-checked',String(v===day));b.tabIndex=v===day||(!day&&i===0)?0:-1;
   b.innerHTML='<small>'+(i===0?'Сегодня':i===1?'Завтра':WD[dt.getUTCDay()])+'</small><strong>'+label(v)+'</strong>';
   b.addEventListener('click',()=>{if(day===v){day='';closeCal();buildDays();fillTimes();setWhen();}else pickDay(v);days.querySelector('[data-value="'+v+'"]')?.focus();});days.append(b);}
  const far=!!day&&day>shift(t0,2),c=doc.createElement('button');c.type='button';c.className='when-day when-day--cal';c.setAttribute('role','radio');
  c.setAttribute('aria-checked',String(far));c.setAttribute('aria-expanded',String(!cal.hidden));c.setAttribute('aria-controls','when-cal');c.tabIndex=far?0:-1;
  c.innerHTML=far?'<small>'+WD[utc(day).getUTCDay()]+'</small><strong>'+label(day)+'</strong>'
   :'<small>Выбрать</small><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3.5 10h17M8 3v4M16 3v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  c.setAttribute('aria-label','Календарь'+(far?': '+label(day):''));
  c.addEventListener('click',()=>{if(cal.hidden){const t=utc(day||t0);calMonth=[t.getUTCFullYear(),t.getUTCMonth()];buildCal();cal.hidden=false;c.setAttribute('aria-expanded','true');
   cal.scrollIntoView({block:'nearest'});cal.querySelector('.when-cal__grid button[tabindex="0"]')?.focus({preventScroll:true});}else closeCal();});
  days.append(c);};
 days.addEventListener('keydown',e=>{if(e.key==='Escape'&&!cal.hidden){e.preventDefault();e.stopPropagation();closeCal();return;}if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;e.preventDefault();const list=[...days.children],i=list.indexOf(doc.activeElement),n=list[(i+(e.key==='ArrowRight'?1:-1)+list.length)%list.length];n.tabIndex=0;n.focus();n.scrollIntoView({block:'nearest',inline:'nearest'});});
 trig.addEventListener('click',()=>{if(times.hidden){fillTimes();times.hidden=false;trig.setAttribute('aria-expanded','true');(times.querySelector('[aria-selected=true]')||times.querySelector('button:not(:disabled)'))?.scrollIntoView({block:'nearest'});}else closeTimes();});
 times.parentElement.addEventListener('keydown',e=>{const list=[...times.querySelectorAll('button:not(:disabled)')];let i=list.indexOf(doc.activeElement);
  if(e.key==='Escape'&&!times.hidden){e.preventDefault();e.stopPropagation();closeTimes();trig.focus();}
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(times.hidden){fillTimes();times.hidden=false;trig.setAttribute('aria-expanded','true');}list[(i+(e.key==='ArrowDown'?1:-1)+list.length)%list.length]?.focus();}});
 booking.addEventListener('click',e=>{if(!times.parentElement.contains(e.target))closeTimes();if(e.target.isConnected&&!cal.contains(e.target)&&!e.target.closest('.when-day--cal'))closeCal();});
 buildDays();fillTimes();
 bf.addEventListener('input',compose);bf.addEventListener('change',compose);bf.addEventListener('submit',e=>e.preventDefault());
 [wa,tg].forEach(link=>link.addEventListener('click',e=>{compose();const err=booking.querySelector('#booking-when-error');if(!date.value){e.preventDefault();err.textContent='Выберите день и время.';err.hidden=false;days.querySelector('[tabindex="0"]')?.focus();return;}if(!bf.checkValidity()||date.value<date.min){e.preventDefault();bf.reportValidity();}}));
}

var nav=Array.from(doc.querySelectorAll('.nav a')),bar=doc.querySelector('[data-progress]');
var hdr=doc.querySelector('.hdr--over');var onScroll=function(){if(hdr){hdr.classList.toggle('is-scrolled',scrollY>8);doc.documentElement.style.setProperty('--hdr-h',hdr.offsetHeight+'px');}var max=doc.documentElement.scrollHeight-innerHeight;if(bar)bar.style.width=(max>0?Math.min(100,scrollY/max*100):0)+'%';var current=-1;nav.forEach(function(a,i){var s=doc.querySelector(a.getAttribute('href'));if(s&&s.getBoundingClientRect().top<innerHeight*.4)current=i;});nav.forEach(function(a,i){a.classList.toggle('is-on',i===current);});};
window.addEventListener('scroll',onScroll,{passive:true});window.addEventListener('resize',onScroll);onScroll();
})();

(()=>{
 const viewer=document.querySelector('#work-viewer'),openers=[...document.querySelectorAll('[data-work-open]')],items=[...document.querySelector('#work-items').content.querySelectorAll('figure')],image=viewer.querySelector('.work-stage>img'),thumbs=viewer.querySelector('.work-thumbs');let index=0,overflow,swipe,opener=null;
 const render=()=>{const source=items[index].querySelector('img');image.classList.remove('is-swap');void image.offsetWidth;image.classList.add('is-swap');image.src=source.getAttribute('src');image.alt=source.alt;viewer.querySelector('figcaption').textContent=items[index].querySelector('figcaption').textContent;viewer.querySelector('[data-work-count]').textContent=(index+1)+' / '+items.length;[...thumbs.children].forEach((button,i)=>{button.setAttribute('aria-pressed',String(i===index));button.classList.toggle('is-active',i===index);});};
 const step=n=>{index=(index+n+items.length)%items.length;render();};
 items.forEach((item,i)=>{const source=item.querySelector('img'),button=document.createElement('button'),thumb=document.createElement('img');button.type='button';button.setAttribute('aria-label','Фото '+(i+1)+': '+source.alt);thumb.src=source.getAttribute('src');thumb.alt='';thumb.loading='lazy';button.append(thumb);button.addEventListener('click',()=>{index=i;render();});thumbs.append(button);});
 const open=from=>{opener=from;render();overflow=document.body.style.overflow;document.body.style.overflow='hidden';viewer.showModal();};openers.forEach(b=>b.addEventListener('click',()=>{if(b.dataset.frame)index=+b.dataset.frame;open(b);}));viewer.querySelector('.work-close').addEventListener('click',()=>viewer.close());viewer.querySelector('[data-work-prev]').addEventListener('click',()=>step(-1));viewer.querySelector('[data-work-next]').addEventListener('click',()=>step(1));viewer.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();step(-1);}if(e.key==='ArrowRight'){e.preventDefault();step(1);}});
 image.addEventListener('pointerdown',e=>{swipe={x:e.clientX,y:e.clientY};});image.addEventListener('pointerup',e=>{if(!swipe)return;const x=e.clientX-swipe.x,y=e.clientY-swipe.y;swipe=null;if(Math.abs(x)>45&&Math.abs(x)>Math.abs(y)*1.5)step(x<0?1:-1);});image.addEventListener('pointercancel',()=>{swipe=null;});
 viewer.addEventListener('click',e=>{const r=viewer.getBoundingClientRect();if(e.target===viewer&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))viewer.close();});viewer.addEventListener('close',()=>{document.body.style.overflow=overflow||'';opener?.focus({preventScroll:true});});render();
})();

/* v18: каждая строка заголовка растягивается ровно на ширину блока с кнопками */
(function(){
  const box=document.querySelector('[data-fit]');
  if(!box)return;
  const lines=[...box.querySelectorAll('[data-fit-line]')];
  const fit=()=>{
    const w=box.clientWidth;
    if(!w)return;
    lines.forEach(l=>{
      let fs=100;
      for(let i=0;i<3;i++){            /* два-три уточнения: ширина букв растет не строго пропорционально */
        l.style.fontSize=fs+'px';
        const lw=l.getBoundingClientRect().width;
        if(!lw)return;
        fs=Math.min(110,fs*w/lw);
      }
      l.style.fontSize=Math.floor(fs*10)/10+'px';
    });
  };
  fit();
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
  let t=0;window.addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(fit,80);});
})();
