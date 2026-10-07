// Actual site/index.html parsed by stdlib; event harness explicitly flushes microtasks
// between separate native-listener callbacks. This is NOT a browser/complete app.js test.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const parsed=cp.spawnSync(process.env.KRYUK_TEST_PYTHON||'python3',['-X','utf8',__dirname+'/html_dom_fixture.py'],{encoding:'utf8',maxBuffer:8*1024*1024,env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'}});
if(parsed.error||parsed.status!==0)throw Error('Fixture subprocess failed: '+JSON.stringify({command:process.env.KRYUK_TEST_PYTHON||'python3',status:parsed.status,signal:parsed.signal,error:parsed.error?.message,stderr:parsed.stderr}));
const fixture=JSON.parse(parsed.stdout);
function matches(node,selector){
 if(!node.tag)return false;
 for(const sel of selector.split(',').map(s=>s.trim())){
  const tag=sel.match(/^[a-z]+/);if(tag&&tag[0]!==node.tag)continue;
  const cls=sel.match(/\.([\w-]+)/);if(cls&&!(node.attrs.class||'').split(/\s+/).includes(cls[1]))continue;
  let good=true;for(const m of sel.matchAll(/\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]/g)){if(!(m[1] in node.attrs)||(m[2]!==undefined&&node.attrs[m[1]]!==m[2]))good=false;}
  if(sel.includes(':checked')&&!node.checked)good=false;
  if(good)return true;
 }return false;
}
class Node{
 constructor(raw,parent=null){this.tag=raw.tag;this.attrs={...(raw.attrs||{})};this.parent=parent;this.children=(raw.children||[]).map(x=>new Node(x,this));this.rawText=raw.text||'';this.value=this.attrs.value||'';this.checked='checked' in this.attrs;this.min=this.attrs.min||'';this.style={};this.handlers=[];}
 get textContent(){return this.rawText+this.children.map(x=>x.textContent).join('');}set textContent(v){this.rawText=v;this.children=[];}
 get href(){return new URL(this.attrs.href||'', 'https://runtime.example/operator/site/').href;}
 set href(v){this.attrs.href=v;}
 closest(sel){for(let n=this;n;n=n.parent)if(matches(n,sel))return n;return null;}
 querySelectorAll(sel){const out=[];for(const c of this.children){if(matches(c,sel))out.push(c);out.push(...c.querySelectorAll(sel));}return out;}
 querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
 setAttribute(k,v){this.attrs[k]=v;}append(n){this.children.push(n);n.parent=this;}
 addEventListener(type,fn,capture){this.handlers.push({type,fn,capture});}
 dispatchEvent(){}checkValidity(){return true;}reportValidity(){}
}
async function scenario(kind,channel,{invalid=false,offline=false}={}){
 const doc=new Node(fixture),requests=[],opens=[],tasks=[],storage=new Map(),ownedEvents=[];
 doc.createElement=tag=>new Node({tag,attrs:{},children:[]});doc.referrer='';const main=doc.querySelector('[data-request]'),booking=doc.querySelector('[data-booking-form]');assert.ok(main&&booking,'actual source must have both forms');
 main.querySelector('[data-from]').value='ТЕСТ А';main.querySelector('[data-to]').value='ТЕСТ Б';
 for(const f of [main,booking])f.querySelector('input[value=car]').checked=true;
 const date=booking.querySelector('[data-booking-when]');date.value=invalid?'':'2026-10-08T12:00';date.min='2026-10-07T00:00';
 const form=kind==='CALCULATOR'?main:booking,prefix=kind==='CALCULATOR'?'request':'booking',link=form.querySelector('[data-'+prefix+'-'+channel+']');
 assert.equal(link.tag,'a');assert.equal(link.attrs.target,'_blank');assert.ok(link.querySelector('svg'),'nested real button markup required');
 const window={KRYUK_CONTACT_CONFIG:{mode:'STAGING',endpoint:'/contact-click',pagePrefix:'/operator/site'},KRYUK_HANDOFF_CONFIG:{mode:'LOCAL_PREVIEW',endpoint:'/capture'},open:(...a)=>opens.push(a)};
 const ctx={TextEncoder,document:doc,window,URL,Blob,WeakSet,crypto:require('node:crypto').webcrypto,location:{href:'https://runtime.example/operator/site/',pathname:'/operator/site/',origin:'https://runtime.example'},matchMedia:()=>({matches:false}),navigator:{sendBeacon:()=>false},sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},queueMicrotask:fn=>tasks.push(fn),Event:class{},fetch:(url,options)=>{requests.push({url,data:JSON.parse(options.body)});return offline?Promise.reject(Error('offline')):Promise.resolve({ok:true,json:async()=>({})});}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/contact-clicks.js','utf8'),ctx);
 const handoff=process.env.KRYUK_HANDOFF_JS||__dirname+'/whatsapp-handoff.js';
 vm.runInNewContext(fs.readFileSync(handoff,'utf8'),ctx);
 async function checkpoint(){while(tasks.length)tasks.shift()();await Promise.resolve();}
 async function click(){const event={target:link.querySelector('svg'),defaultPrevented:false,stop:false,preventDefault(){this.defaultPrevented=true;},stopImmediatePropagation(){this.stop=true;}};
  for(const h of doc.handlers.filter(h=>h.type==='click'&&h.capture)){h.fn(event);await checkpoint();}
  for(const h of link.handlers.filter(h=>h.type==='click'&&h.capture)){h.fn(event);await checkpoint();if(event.stop)break;}
  ownedEvents.push(event._kryukCapturedForm);await new Promise(r=>setImmediate(r));
 }
 await click();await click();
 assert.equal(requests.filter(x=>x.url==='/contact-click').length,0,kind+' '+channel+': independent click must NOT precede form owner');
 const captures=requests.filter(x=>x.url==='/capture');
 if(invalid){assert.equal(captures.length,0);assert.equal(opens.length,0);return;}
 assert.equal(captures.length,2);assert.equal(captures[0].data.request_id,captures[1].data.request_id);assert.equal(captures[0].data.interaction.channel,channel);assert.equal(captures[0].data.interaction.position,'form');assert.equal(captures[0].data.form_kind,kind);assert.equal(opens.length,2);assert.ok(ownedEvents.every(Boolean));
}
module.exports={Node,fixture};
if(require.main===module)(async()=>{for(const kind of ['CALCULATOR','PREBOOKING'])for(const channel of ['wa','tg'])await scenario(kind,channel);await scenario('PREBOOKING','wa',{invalid:true});await scenario('CALCULATOR','wa',{offline:true});console.log('6 actual-source-markup event scenarios PASS (listener-checkpoint harness; not browser)');})().catch(e=>{console.error(e);process.exit(1)});
