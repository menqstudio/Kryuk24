(()=>{
'use strict';
const config=window.KRYUK_HANDOFF_CONFIG||{mode:'LOCAL_PREVIEW',endpoint:'/test-intake'};
if(!['LOCAL_PREVIEW','STAGING','LIVE'].includes(config.mode))return;
// Register actual managed nodes before any click, not during event propagation.
const owned=window.KRYUK_FORM_CONTACTS||(window.KRYUK_FORM_CONTACTS=new WeakSet());
const main=document.querySelector('[data-request]');if(!main)return;
// SHA-256 identity only: browser storage contains no raw form/contact/address text.
function fingerprint(text){
 const k=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 const bytes=new TextEncoder().encode(text),padded=new Uint8Array(Math.ceil((bytes.length+9)/64)*64);padded.set(bytes);padded[bytes.length]=128;
 const view=new DataView(padded.buffer);view.setUint32(padded.length-8,Math.floor(bytes.length/0x20000000));view.setUint32(padded.length-4,bytes.length*8);
 const h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],r=(x,n)=>(x>>>n)|(x<<(32-n)),w=new Int32Array(64);
 for(let offset=0;offset<padded.length;offset+=64){
  for(let i=0;i<16;i++)w[i]=view.getInt32(offset+i*4);
  for(let i=16;i<64;i++){const x=w[i-15],y=w[i-2],s0=r(x,7)^r(x,18)^(x>>>3),s1=r(y,17)^r(y,19)^(y>>>10);w[i]=(w[i-16]+s0+w[i-7]+s1)|0;}
  let [a,b,c,d,e,f,g,z]=h;
  for(let i=0;i<64;i++){const s1=r(e,6)^r(e,11)^r(e,25),ch=(e&f)^(~e&g),t1=(z+s1+ch+k[i]+w[i])|0,s0=r(a,2)^r(a,13)^r(a,22),maj=(a&b)^(a&c)^(b&c),t2=(s0+maj)|0;z=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
  [a,b,c,d,e,f,g,z].forEach((v,i)=>h[i]=(h[i]+v)>>>0);
 }
 return h.map(x=>x.toString(16).padStart(8,'0')).join('');
}
for(const form of [main,document.querySelector('[data-booking-form]')].filter(Boolean)){
 const booking=form!==main,prefix=booking?'booking':'request';
 const note=document.createElement('p');note.style.cssText='grid-column:1/-1;padding:12px;border:1px solid #d6dfeb';note.setAttribute('role','status');note.textContent=config.mode==='LOCAL_PREVIEW'?'Локальный тест: вместо мессенджера — предпросмотр. Ничего не отправится; копия формы сохраняется отдельно.':'Откроется чат с готовым текстом — отправляете вы. Данные формы сохраняются отдельно для обработки обращения.';form.append(note);
 const storageKey='kryuk-form-v1:'+config.mode+':'+config.endpoint+':'+prefix,ttl=24*60*60*1000;
 let current=null;
 try{const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(saved&&/^K24-[a-f0-9]{32}$/.test(saved.id)&&/^[a-f0-9]{64}$/.test(saved.fingerprint)&&Number.isFinite(saved.savedAt)&&Date.now()>=saved.savedAt&&Date.now()-saved.savedAt<ttl)current=saved;else sessionStorage.removeItem(storageKey);}catch(_){}
 const reset=document.createElement('button');reset.type='button';reset.className='btn btn--ghost';reset.textContent='Новая заявка';reset.setAttribute('data-new-request',prefix);reset.addEventListener('click',e=>{e.preventDefault();current=null;try{sessionStorage.removeItem(storageKey);}catch(_){}note.textContent='Следующее нажатие создаст новую заявку. Данные формы сохранены.';});form.append(reset);
 const value=(f,s)=>f.querySelector(s)?.value?.trim()||'';
 for(const channel of ['wa','tg']){
  const link=form.querySelector('[data-'+prefix+'-'+channel+']');if(!link)continue;
  link.addEventListener('click',event=>{
   if(typeof crypto==='undefined'||typeof crypto.randomUUID!=='function'||typeof TextEncoder!=='function'){note.textContent='Копия не сохранится: браузер не поддерживает ID. Обычный мессенджер остается доступен.';return;}
   event.preventDefault();event.stopImmediatePropagation();form.dispatchEvent(new Event('change',{bubbles:true}));
   if(booking){const date=form.querySelector('[data-booking-when]');if(!form.checkValidity()||!date.value||date.value<date.min){note.textContent='Выберите транспорт, день и время.';form.reportValidity();return;}}
   const original=new URL(link.href),message=original.searchParams.get('text')||'';
   const data={contact:'NOT_PROVIDED',pickup:value(main,'[data-from]')||'NOT_PROVIDED',destination:value(main,'[data-to]')||'NOT_PROVIDED',vehicle:value(form,booking?'input[name=booking-vehicle]:checked':'input[name=vehicle]:checked')||'NOT_PROVIDED',message,estimate_display:booking?'NOT_QUOTED':main.querySelector('[data-quote]').textContent,channel,form_kind:booking?'PREBOOKING':'CALCULATOR'};
   const digest=fingerprint(JSON.stringify(data)),timestamp=Date.now();
   if(!current||current.fingerprint!==digest||timestamp-current.savedAt>=ttl||timestamp<current.savedAt){
    current={fingerprint:digest,id:'K24-'+crypto.randomUUID().replaceAll('-',''),savedAt:timestamp};
    if(window.KRYUK_CONTACT_METADATA){const meta=window.KRYUK_CONTACT_METADATA(link,channel);if(meta?.page)current.interaction=meta;}
   }
   try{sessionStorage.setItem(storageKey,JSON.stringify(current));}catch(_){}
   const id=current.id;data.request_id=id;
   if(current.interaction)data.interaction=current.interaction;
   event._kryukCapturedForm=true;
   original.searchParams.set('text',(config.mode==='LIVE'?'':'ТЕСТ — НЕ ВЫЕЗЖАТЬ\n')+'Заявка: '+id+'\n'+message);
   const preview=new URL('/handoff-preview',location.origin);preview.searchParams.set('id',id);
   // Synchronous opening happens before the independent capture request.
   window.open(config.mode==='LOCAL_PREVIEW'?preview.href:original.href,'_blank','noopener,noreferrer');
   fetch(config.endpoint,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':id,...(config.mode==='LOCAL_PREVIEW'?{'X-Test-Nonce':window.KRYUK_TEST_NONCE}:{})},body:JSON.stringify(data),keepalive:true})
    .then(async r=>{if(!r.ok)throw Error('HTTP '+r.status);await r.json();note.textContent='Копия '+id+' сохранена. Отправка сообщения клиентом НЕ подтверждена.';})
    .catch(()=>{note.textContent='Сохранение '+id+' не подтверждено. Переход в мессенджер/предпросмотр выполнен независимо. Повторите с теми же данными для сохранения с тем же ID.';});
  },true);
  owned.add(link);
 }
}
})();
