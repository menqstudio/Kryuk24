const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const {Node,fixture}=require('./test_real_markup_contacts.cjs');
const source=fs.readFileSync(__dirname+'/whatsapp-handoff.js','utf8');
const MAX_AGE=24*60*60*1000;
function page(storage,{now=100000,kind='CALCULATOR',mode='LOCAL_PREVIEW',brokenStorage=false,offline=false,from='ТЕСТ Երևան — А',sourceDomain='yandex.ru',message='ТЕСТ 😀',channel='wa'}={}){
 const doc=new Node(fixture),requests=[],opens=[];doc.createElement=tag=>new Node({tag,attrs:{},children:[]});
 const main=doc.querySelector('[data-request]'),booking=doc.querySelector('[data-booking-form]');main.querySelector('[data-from]').value=from;main.querySelector('[data-to]').value='ТЕСТ Москва Б';
 for(const f of [main,booking])f.querySelector('input[value=car]').checked=true;
 booking.querySelector('[data-booking-when]').value='2026-10-08T12:00';booking.querySelector('[data-booking-when]').min='2026-10-07T00:00';
 const form=kind==='CALCULATOR'?main:booking,prefix=kind==='CALCULATOR'?'request':'booking';
 const link=form.querySelector('[data-'+prefix+'-'+channel+']');const u=new URL(link.href);u.searchParams.set('text',message);link.href=u.href;
 const ctx={TextEncoder,Date:{now:()=>now},document:doc,window:{KRYUK_HANDOFF_CONFIG:{mode,endpoint:'/capture'},KRYUK_CONTACT_METADATA:(a,ch)=>({channel:ch,page:'/',position:'form',button:'form-'+ch+'-0',device:'desktop',referrer_domain:sourceDomain,utm:{},yclid:''}),open:(...a)=>opens.push(a)},crypto:crypto.webcrypto,URL,Event:class{},sessionStorage:{getItem:k=>{if(brokenStorage)throw Error('blocked');return storage.get(k)||null;},setItem:(k,v)=>{if(brokenStorage)throw Error('blocked');storage.set(k,v);},removeItem:k=>{if(brokenStorage)throw Error('blocked');storage.delete(k);}},location:{origin:'https://runtime.example'},fetch:(url,o)=>{requests.push(JSON.parse(o.body));return offline?Promise.reject(Error('offline')):Promise.resolve({ok:true,json:async()=>({})});}};
 vm.runInNewContext(source,ctx);
 const event=()=>({preventDefault(){},stopImmediatePropagation(){}});
 return {requests,opens,async click(){link.handlers.find(h=>h.type==='click').fn(event());await new Promise(r=>setImmediate(r));},reset(){form.querySelector('[data-new-request='+prefix+']').handlers[0].fn(event());}};
}
(async()=>{
 for(const kind of ['CALCULATOR','PREBOOKING'])for(const channel of ['wa','tg']){
  const store=new Map(),first=page(store,{kind,channel});await first.click();const p=first.requests[0];
  const reloaded=page(store,{kind,channel,now:100001,sourceDomain:'kryuk24.ru'});await reloaded.click();assert.deepEqual(reloaded.requests[0],p,'same ID AND payload across reload');
  const saved=JSON.parse([...store.values()][0]),raw={...p};delete raw.request_id;delete raw.interaction;
  assert.equal(saved.fingerprint,crypto.createHash('sha256').update(JSON.stringify(raw)).digest('hex'));
  for(const value of ['Երևան','Москва','ТЕСТ 😀'])assert.equal([...store.values()].join('').includes(value),false,'raw input must not persist');
 }
 {const store=new Map(),p=page(store);await p.click();const id=p.requests[0].request_id;p.reset();await p.click();assert.notEqual(p.requests[1].request_id,id);}
 {const store=new Map(),p=page(store);await p.click();const changed=page(store,{from:'ТЕСТ новый адрес'});await changed.click();assert.notEqual(changed.requests[0].request_id,p.requests[0].request_id);}
 {const store=new Map(),p=page(store);await p.click();const late=page(store,{now:100000+MAX_AGE});await late.click();assert.notEqual(late.requests[0].request_id,p.requests[0].request_id);}
 {const store=new Map(),p=page(store);await p.click();const live=page(store,{mode:'LIVE'});await live.click();assert.notEqual(live.requests[0].request_id,p.requests[0].request_id);}
 {const store=new Map(),p=page(store,{brokenStorage:true});await p.click();await p.click();assert.equal(p.requests[0].request_id,p.requests[1].request_id);assert.equal(store.size,0);assert.equal(p.opens.length,2);}
 {const store=new Map(),p=page(store,{offline:true});await p.click();const reload=page(store);await reload.click();assert.equal(reload.requests[0].request_id,p.requests[0].request_id);}
 // Compare implementation fingerprint to Node's SHA256 oracle across Unicode and padding boundaries.
 for(const n of [0,1,55,56,63,64,65,127,128,512,4096]){
  const store=new Map(),p=page(store,{message:'😀ՀայերենРусский'+('x'.repeat(n))});await p.click();const raw={...p.requests[0]};delete raw.request_id;delete raw.interaction;
  assert.equal(JSON.parse([...store.values()][0]).fingerprint,crypto.createHash('sha256').update(JSON.stringify(raw)).digest('hex'));
 }
 console.log('10 form persistence scenarios +11 SHA256 oracle cases PASS (actual markup harness, not browser)');
})().catch(e=>{console.error(e);process.exit(1)});
