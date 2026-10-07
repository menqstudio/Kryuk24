(()=>{
'use strict';
const cfg=window.KRYUK_CONTACT_CONFIG;if(!cfg||cfg.mode!=='STAGING')return;
const allowedPages=new Set(['/','/index.html','/evakuator-balashikha/','/evakuator-domodedovo/','/evakuator-khimki/','/evakuator-lyubertsy/','/evakuator-podolsk/','/manipulyator/','/perevozka-spetstekhniki/','/operator/staging']);
function channel(a){try{const u=new URL(a.href,location.href);if(u.protocol==='tel:')return 'call';if(u.protocol==='https:'&&['wa.me','api.whatsapp.com'].includes(u.hostname))return 'wa';if(u.protocol==='https:'&&u.hostname==='t.me')return 'tg';}catch(_){}return null;}
function position(a){if(a.closest('[data-request], [data-booking-form]'))return 'form';if(a.closest('.callbar, [data-contact-position="sticky"]'))return 'sticky';if(a.closest('header.hdr, header, [data-contact-position="header"]'))return 'header';if(a.closest('.hero, [data-contact-position="hero"]'))return 'hero';if(a.closest('footer.foot, [data-contact-position="footer"]'))return 'footer';return 'content';}
function metadata(a,ch){
 const pos=position(a),links=Array.from(document.querySelectorAll('a[href]')).filter(x=>channel(x)===ch&&position(x)===pos);
 const ordinal=Math.max(0,links.indexOf(a));if(ordinal>999)return null;
 let domain='';try{domain=new URL(document.referrer).hostname.toLowerCase();if(/^[0-9.]+$/.test(domain)||domain.includes(':')||/[0-9]{7,}/.test(domain))domain='';}catch(_){}
 const page=cfg.pagePrefix&&location.pathname.startsWith(cfg.pagePrefix+'/')?location.pathname.slice(cfg.pagePrefix.length):location.pathname;
 const params=new URL(location.href).searchParams,utm={};for(const key of ['utm_source','utm_medium','utm_campaign','utm_content','utm_term']){const v=params.get(key)||'';if(/^[A-Za-z0-9_-]{1,80}$/.test(v)&&!/[0-9]{7,}/.test(v))utm[key]=v;}
 const y=params.get('yclid')||'';
 return {channel:ch,page:allowedPages.has(page)?page:null,position:pos,button:pos+'-'+ch+'-'+ordinal,referrer_domain:domain,utm,yclid:/^[0-9]{1,32}$/.test(y)?y:'',device:matchMedia('(max-width: 767px)').matches?'mobile':'desktop'};
}
window.KRYUK_CONTACT_METADATA=metadata;
const recent=new Map();
function record(a,ch){
 try{
  const m=metadata(a,ch);if(!m||!m.page||!crypto.randomUUID)return;
  const key='kryuk-click:'+m.page+':'+m.button,now=Date.now();let pending=recent.get(key);
  if(!pending){try{pending=JSON.parse(sessionStorage.getItem(key)||'null');}catch(_){}}
  if(!pending||now-pending.time>=5000||now<pending.time)pending={time:now,payload:{event_id:'CLICK-'+crypto.randomUUID().replaceAll('-',''),metadata:m}};
  recent.set(key,pending);try{sessionStorage.setItem(key,JSON.stringify(pending));}catch(_){}
  const body=JSON.stringify(pending.payload);
  try{if(navigator.sendBeacon&&navigator.sendBeacon(cfg.endpoint,new Blob([body],{type:'application/json'})))return;}catch(_){}
  fetch(cfg.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true,credentials:'omit'}).catch(()=>{});
 }catch(_){} // Tracking never cancels, redirects, waits for, or replaces the contact action.
}
document.addEventListener('click',event=>{
 const a=event.target.closest?.('a[href]');if(!a)return;const ch=channel(a);if(!ch)return;
 // Ownership is established at listener installation. Native listeners may have
 // microtask checkpoints between document capture and the target callback.
 if(window.KRYUK_FORM_CONTACTS?.has(a))return;
 // Document capture sees the event before form handlers. Inspect after their synchronous work.
 queueMicrotask(()=>{if(window.KRYUK_FORM_CONTACTS?.has(a)||event._kryukCapturedForm||(event.defaultPrevented&&!event._kryukStagingDirect))return;record(a,ch);});
},true);
})();
