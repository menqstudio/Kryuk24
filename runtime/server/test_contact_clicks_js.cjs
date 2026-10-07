const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),crypto=require('node:crypto').webcrypto;
const source=fs.readFileSync(__dirname+'/contact-clicks.js','utf8');
async function run({channel='call',offline=false,beacon=false,throwBeacon=false,storageFails=false,form=false,handled=false,prevented=false,staging=false}={}){
 const requests=[],beacons=[],listeners={},storage=new Map();let t=10000;
 const href=channel==='call'?'tel:+79858930606':channel==='wa'?'https://wa.me/79858930606':'https://t.me/+79858930606';
 const link={href,closest(s){if(s==='a[href]')return this;if(form&&s.includes('[data-request]'))return {};if(s.includes('.hero'))return {};return null;}};
 const location={href:'https://kryuk24.ru/?utm_source=yandex&utm_campaign=tow_moscow&utm_term=a%40example.com&yclid=123456789&phone=PRIVATE',pathname:'/',origin:'https://kryuk24.ru'};
 const ctx={URL,Blob,crypto,location,matchMedia:()=>({matches:true}),queueMicrotask,Date:{now:()=>t},sessionStorage:{getItem:k=>{if(storageFails)throw Error();return storage.get(k)||null;},setItem:(k,v)=>{if(storageFails)throw Error();storage.set(k,v);}},document:{referrer:'https://yandex.ru/search?phone=PRIVATE',querySelectorAll:()=>[link],addEventListener:(name,fn)=>listeners[name]=fn},window:{KRYUK_CONTACT_CONFIG:{mode:'STAGING',endpoint:'/contact-click'}},navigator:{sendBeacon:(url,b)=>{if(throwBeacon)throw Error();beacons.push({url,b});return beacon;}},fetch:(url,options)=>{requests.push({url,body:JSON.parse(options.body),options});return offline?Promise.reject(Error('offline')):Promise.resolve({ok:true});}};
 vm.runInNewContext(source,ctx);
 async function click(){let cancelled=0;const event={target:link,defaultPrevented:prevented,_kryukCapturedForm:handled,_kryukStagingDirect:staging,preventDefault:()=>cancelled++,stopImmediatePropagation:()=>cancelled++};listeners.click(event);await new Promise(r=>setImmediate(r));assert.equal(cancelled,0);assert.equal(link.href,href);}
 await click();
 if(handled||(prevented&&!staging)){assert.equal(requests.length,0);assert.equal(beacons.length,0);return;}
 const bodies=async()=>beacon?Promise.all(beacons.map(async b=>JSON.parse(await b.b.text()))):requests.map(x=>x.body);
 let a=(await bodies())[0];assert.equal(a.metadata.channel,channel);assert.equal(a.metadata.position,form?'form':'hero');assert.equal(a.metadata.referrer_domain,'yandex.ru');assert.equal(a.metadata.device,'mobile');assert.equal(a.metadata.page,'/');assert.equal(a.metadata.utm.utm_term,undefined);
 for(const secret of ['79858930606','PRIVATE','example.com'])assert.equal(JSON.stringify(a).includes(secret),false);
 await click();let data=await bodies();assert.equal(data[0].event_id,data[1].event_id);
 // Reload module within same tab: recent ID still available from sessionStorage.
 if(!storageFails){vm.runInNewContext(source,ctx);await click();data=await bodies();assert.equal(data[0].event_id,data[2].event_id);}
 t+=5001;await click();data=await bodies();assert.notEqual(data[0].event_id,data[data.length-1].event_id);
 if(!beacon)assert.equal(requests[0].options.keepalive,true);
}
(async()=>{
 for(const channel of ['call','wa','tg'])await run({channel});
 await run({offline:true});await run({beacon:true});await run({storageFails:true});await run({throwBeacon:true});
 await run({form:true,handled:true});await run({prevented:true});await run({prevented:true,staging:true});
 console.log('10 contact frontend scenarios PASS (mock DOM, not browser)');
})().catch(e=>{console.error(e);process.exit(1)});
