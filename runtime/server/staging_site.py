"""Protected full-source preview. Original files remain unchanged; outbound actions disabled."""
import re
from pathlib import Path
from urllib.parse import urlsplit, urljoin
PUBLIC_SUFFIXES={'.html','.css','.js','.svg','.jpg','.jpeg','.png','.webp','.ico','.woff','.woff2','.ttf','.webmanifest'}
INJECTION='''<aside style="position:relative;z-index:9999;background:#ffe4b8;padding:16px;font:16px system-ui">STAGING — только вымышленные данные. Звонки/мессенджеры не открываются. Внешние карты/аналитика отключены; это не проверка их работы. <a href="/operator">Журнал</a><p id="kryuk-staging-action"></p></aside><script>
window.KRYUK_HANDOFF_CONFIG={mode:'LOCAL_PREVIEW',endpoint:'/capture'};
window.KRYUK_CONTACT_CONFIG={mode:'STAGING',endpoint:'/contact-click',pagePrefix:'/operator/site'};
document.addEventListener('click',e=>{const a=e.target.closest?.('a[href]');if(!a)return;try{const u=new URL(a.href,location.href);if(u.origin!==location.origin){e.preventDefault();const ch=u.protocol==='tel:'?'call':u.hostname==='wa.me'||u.hostname==='api.whatsapp.com'?'wa':u.hostname==='t.me'?'tg':null;if(ch)e._kryukStagingDirect=true;document.getElementById('kryuk-staging-action').textContent='STAGING: внешнее действие заблокировано. Это не звонок/сообщение.';}}catch(_){}},false);
</script><script src="/operator/contact-clicks.js" defer></script><script src="/operator/staging-handoff.js" defer></script>'''
def public_file(root,relative):
 p=root/relative
 if any(part.startswith('.') for part in Path(relative).parts) or p.suffix.lower() not in PUBLIC_SUFFIXES:return None
 try:p.resolve().relative_to(root.resolve())
 except ValueError:return None
 return p if p.is_file() and not p.is_symlink() else None

def render_page(path,source):
 base='https://preview.invalid/'+path
 def rewrite(match):
  attr,quote,value=match.groups()
  if value.startswith('#'):return match.group(0)
  u=urlsplit(urljoin(base,value))
  if u.scheme in ('http','https') and u.netloc=='preview.invalid':
   value='/operator/site'+u.path+('?' +u.query if u.query else '')+('#'+u.fragment if u.fragment else '')
  return attr+'='+quote+value+quote
 source=re.sub(r'''\b(src|href)=(['"])(.*?)\2''',rewrite,source,flags=re.IGNORECASE)
 return source.replace('</body>',INJECTION+'</body>')
