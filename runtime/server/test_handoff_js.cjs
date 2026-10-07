const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
async function scenario(fail,mode){
 const handlers={},opens=[],requests=[],note={style:{},setAttribute(){}};let pickup='A';
 const link={href:'https://wa.me/79858930606?text='+encodeURIComponent('Здравствуйте! Предварительно: от 4 000 ₽'),addEventListener(_,f){handlers.click=f;}};
 const form={append(){},dispatchEvent(){},querySelector(s){if(s==='[data-request-wa]')return link;if(s==='[data-request-tg]')return null;if(s==='[data-from]')return {value:pickup};if(s==='[data-to]')return {value:'B'};if(s==='input[name=vehicle]:checked')return {value:'car'};if(s==='[data-quote]')return {textContent:'от 4 000 ₽'};return null;}};
 const ctx={TextEncoder,document:{querySelector:s=>s==='[data-request]'?form:null,createElement:tag=>tag==='p'?note:{style:{},setAttribute(){},addEventListener(){}}},URL,Event:class{},crypto:require('node:crypto').webcrypto,location:{origin:'http://127.0.0.1:8765'},window:{KRYUK_CONTACT_METADATA:()=>({channel:'wa',page:'/',position:'form',button:'form-wa-0',device:'desktop',utm:{},referrer_domain:'',yclid:''}),KRYUK_TEST_NONCE:'TEST',KRYUK_HANDOFF_CONFIG:mode?{mode,endpoint:'https://runtime.example/capture'}:undefined,open:(...a)=>opens.push(a)},fetch:(url,options)=>{requests.push(JSON.parse(options.body));assert.equal(opens.length,requests.length,'preview must open before saving');return fail?Promise.reject(Error('offline')):Promise.resolve({ok:true,json:async()=>({})});}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/whatsapp-handoff.js','utf8'),ctx);
 const click=()=>handlers.click({preventDefault(){},stopImmediatePropagation(){}});
 click();await new Promise(r=>setImmediate(r));assert.equal(opens.length,1);if(mode){const u=new URL(opens[0][0]);assert.equal(u.hostname,'wa.me');assert.match(u.searchParams.get('text'),/K24-/);assert.equal(u.searchParams.get('text').includes('ТЕСТ'),mode!=='LIVE');}assert.equal(requests[0].interaction.position,'form');assert.match(requests[0].request_id,/^K24-[a-f0-9]{32}$/);assert.equal(link.href.startsWith('https://wa.me/'),true);assert.match(requests[0].message,/4 000/);
 click();await new Promise(r=>setImmediate(r));assert.equal(requests[0].request_id,requests[1].request_id);
 pickup='C';click();await new Promise(r=>setImmediate(r));assert.notEqual(requests[0].request_id,requests[2].request_id);
 if(fail)assert.match(note.textContent,/не подтверждено/);else assert.match(note.textContent,/НЕ подтверждена/);
}
(async()=>{await scenario(false);await scenario(true);await scenario(true,'STAGING');await scenario(false,'LIVE');console.log('4 frontend logic scenarios PASS (mock DOM; not a browser test)');})().catch(e=>{console.error(e);process.exit(1)});
