"""Private Armen input portal. Separate credentials/data; no operator approvals."""
from http.cookies import SimpleCookie,CookieError
import argparse,base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,sys,threading,time,uuid,warnings
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from PIL import Image,ImageOps

PREFIX='/operator/work/armen/'
# Accounts. 'armen' is the owner: only his rows are his accounting. 'gev' reads Armen's rows and writes nothing.
# 'test' is for trying the portal: it uploads and answers like Armen, sees only its own rows, and its rows are never
# Armen's: they are in no state Armen or the reviewer sees, and they never leave the portal (no outbox, no media intake).
ACCOUNTS=('armen','gev','test')
WRITERS=('armen','test')
COOKIE='__Secure-kryuk_armen'
SESSION_TTL=8*60*60

class Sessions:
 def __init__(self,clock=time.monotonic):
  self.clock=clock;self.records={};self.lock=threading.Lock()
 def create(self,actor):
  token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
  with self.lock:
   t=self.clock();self.records={k:v for k,v in self.records.items() if v[2]>t}
   if len(self.records)>=1024:raise ValueError('session capacity')
   self.records[hashlib.sha256(token.encode()).hexdigest()]=(actor,csrf,t+SESSION_TTL)
  return token,csrf
 def resolve(self,header):
  try:
   if len(header)>4096:return None
   jar=SimpleCookie();jar.load(header);token=jar[COOKIE].value
   if not re.fullmatch('[A-Za-z0-9_-]{43}',token):return None
   key=hashlib.sha256(token.encode()).hexdigest()
  except (KeyError,ValueError,CookieError):return None
  with self.lock:
   rec=self.records.get(key)
   if rec and rec[2]>self.clock():return rec
   self.records.pop(key,None);return None
 def revoke(self,header):
  try:
   jar=SimpleCookie();jar.load(header);key=hashlib.sha256(jar[COOKIE].value.encode()).hexdigest()
  except (KeyError,ValueError,CookieError):return
  with self.lock:self.records.pop(key,None)

MAX_LOGIN_BODY=16384
# Files anybody may read, also before login: the look of the page and nothing else. tokens.css is the design
# system's own file (design/tokens/kryuk.tokens.css, copied byte for byte and checked in CI); the logo files are the
# official lockup; the fonts are the site's. Fonts and logo may be kept by the browser for a day.
PUBLIC={'login.js':'text/javascript; charset=utf-8','theme.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8',
 'tokens.css':'text/css; charset=utf-8','fonts.css':'text/css; charset=utf-8','logo-light.webp':'image/webp','logo-dark.webp':'image/webp','bro.webp':'image/webp',
 'font-golos-cyrillic.woff2':'font/woff2','font-golos-latin.woff2':'font/woff2','font-robotocond-700-cyrillic.woff2':'font/woff2','font-robotocond-700-latin.woff2':'font/woff2'}
MAX_IMAGE=20*1024*1024
MAX_TOTAL=1024*1024*1024
QUESTIONS=[
 {'id':'availability','title':'Сейчас можете выехать?','options':[['READY','Да, готов'],['BUSY','На заказе'],['OFFLINE','Не на смене'],['UNKNOWN','Пока не знаю']]},
 {'id':'inquiries','title':'Сегодня были обращения?','options':[['YES','Да'],['NO','Нет'],['UNKNOWN','Не знаю']]},
 {'id':'completed_trips','title':'Сколько перевозок завершили сегодня?','options':[['0','0'],['1','1'],['2','2'],['3','3'],['4','4'],['5_PLUS','5 или больше'],['UNKNOWN','Не знаю']]},
 {'id':'service_area','title':'Где сейчас принимаете заказы?','options':[['MOSCOW','Москва'],['MO','Область'],['BOTH','Москва и область'],['UNKNOWN','Уточню']]},
 {'id':'main_source','title':'Откуда сегодня чаще обращались?','options':[['PHONE','Звонок'],['WHATSAPP','WhatsApp'],['TELEGRAM','Telegram'],['YANDEX','Яндекс'],['AVITO','Авито'],['OTHER','Другое'],['NONE','Не было'],['UNKNOWN','Не знаю']]},
]
MOSCOW=timezone(timedelta(hours=3))
def now():return datetime.now(timezone.utc).isoformat()
def day():return datetime.now(MOSCOW).date().isoformat()
def encode(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def _sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def credential(password):
 # 8 since 08.10.2026, by Gev's decision (it was 16): Armen types it on a phone. The Nginx per-address limit on the
 # login address and the failed-login cap of this process are what stand against guessing.
 if not isinstance(password,str) or not 8<=len(password)<=1024:raise ValueError('password length 8..1024 required')
 salt=secrets.token_bytes(16)
 return {'salt':salt.hex(),'hash':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000).hex()}
def verify(user,password,users):
 """The user name when the password is right, else None. An unknown name costs the same hash calculation."""
 if not isinstance(user,str) or not isinstance(password,str) or not 1<=len(password)<=1024:return None
 rec=users.get(user)
 try:
  salt=bytes.fromhex(rec['salt']) if rec else b'0'*16
  actual=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,600000).hex()
  if rec and hmac.compare_digest(actual,rec['hash']):return user
 except (ValueError,UnicodeError,KeyError,TypeError):pass
 return None
def same(a,b):
 """Constant-time comparison of two header-sized strings. compare_digest refuses non-ASCII str, so compare bytes."""
 return isinstance(a,str) and isinstance(b,str) and hmac.compare_digest(a.encode('utf-8','surrogatepass'),b.encode('utf-8','surrogatepass'))
def authenticate(header,users):
 try:
  if not header.startswith('Basic ') or len(header)>2048:return None
  user,password=base64.b64decode(header[6:],validate=True).decode('utf-8').split(':',1)
  if not 1<=len(password)<=1024:return None
  rec=users.get(user)
  # Unknown usernames receive a same-cost hash calculation too.
  salt=bytes.fromhex(rec['salt']) if rec else b'0'*16
  actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000).hex()
  if rec and hmac.compare_digest(actual,rec['hash']):return user
 except (ValueError,UnicodeError,KeyError):pass
 return None

class Store:
 def __init__(self,db,root,outbox=None):
  self.db_path=str(db);self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.outbox=Path(outbox).resolve() if outbox else None;self.handing=threading.Lock()
  self.decoding=threading.Lock()  # one photo is decoded at a time: a 40 MP picture takes about 160 MiB while it is open
  with self.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS armen_answers(id TEXT PRIMARY KEY, actor TEXT, day TEXT, question TEXT, answer TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS armen_photos(id TEXT PRIMARY KEY, actor TEXT, digest TEXT, format TEXT, original TEXT, preview TEXT, purpose TEXT, created TEXT, UNIQUE(actor,digest));
CREATE TABLE IF NOT EXISTS armen_commands(actor TEXT,key TEXT,digest TEXT,result TEXT,PRIMARY KEY(actor,key));
CREATE TABLE IF NOT EXISTS armen_excluded(kind TEXT,id TEXT,reason TEXT,marked_by TEXT,created TEXT,PRIMARY KEY(kind,id));
''')
 @contextmanager
 def db(self):
  c=sqlite3.connect(self.db_path,timeout=15);c.row_factory=sqlite3.Row
  try:
   with c:yield c
  finally:c.close()
 def answer(self,actor,key,d):
  if set(d)!={'question','answer','day'}:raise ValueError('exact answer fields required')
  q=next((q for q in QUESTIONS if q['id']==d['question']),None)
  if not q or d['answer'] not in {v for v,_ in q['options']} or not isinstance(d['day'],str):raise ValueError('invalid question/answer/day; reload page')
  if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('request key required')
  dg=hashlib.sha256(encode(d).encode()).hexdigest()
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM armen_commands WHERE actor=? AND key=?',(actor,key)).fetchone()
   if old:
    if old['digest']!=dg:raise ValueError('changed request key')
    return json.loads(old['result'])
   # Only a new answer must be for today: the repeat of a saved one gets its saved result after midnight too.
   if d['day']!=day():raise ValueError('invalid question/answer/day; reload page')
   # The test account's answer is never an Armen-reported fact: the stored result says so, so a repeat says so too.
   ident=uuid.uuid4().hex;result={'saved':True,'id':ident,'trust':'TEST_NOT_COUNTED' if actor=='test' else 'ARMEN_REPORTED','day':d['day']}
   c.execute('INSERT INTO armen_answers VALUES(?,?,?,?,?,?)',(ident,actor,d['day'],d['question'],d['answer'],now()))
   c.execute('INSERT INTO armen_commands VALUES(?,?,?,?)',(actor,key,dg,encode(result)))
   return result
 def photo(self,actor,raw,purpose):
  if not raw or len(raw)>MAX_IMAGE or purpose not in ('WORK','EQUIPMENT','OTHER'):raise ValueError('image up to 20 MiB and known purpose required')
  with self.decoding,warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   try:
    with Image.open(io.BytesIO(raw)) as im:
     fmt=im.format
     if fmt not in ('JPEG','PNG','WEBP') or getattr(im,'n_frames',1)!=1 or im.width*im.height>40000000:raise ValueError('single JPEG/PNG/WebP up to 40 megapixels required')
     im.verify()
    with Image.open(io.BytesIO(raw)) as im:
     # Made small first, turned and converted after: the full-size picture is in memory once, never as three copies.
     # The whole file is still decoded, so a broken one is refused.
     im.draft(None,(1200,1200))  # JPEG only: decoded at a smaller scale
     small=im if im.mode in ('RGB','RGBA','L') else im.convert('RGB')  # palette and other modes do not shrink well
     small.thumbnail((600,600));thumb=ImageOps.exif_transpose(small).convert('RGB')
     out=io.BytesIO();thumb.save(out,'JPEG',quality=80)
   except (OSError,Image.DecompressionBombWarning,Image.DecompressionBombError,SyntaxError) as e:
    raise ValueError('cannot decode photo; use JPEG/PNG/WebP') from None
  dg=hashlib.sha256(raw).hexdigest();ext={'JPEG':'jpg','PNG':'png','WEBP':'webp'}[fmt]
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT id FROM armen_photos WHERE actor=? AND digest=?',(actor,dg)).fetchone()
   if old:return {'saved':True,'id':old['id'],'duplicate':True,'publishing_enabled':False}
   total=sum(f.stat().st_size for f in self.root.iterdir() if f.is_file())
   if total+len(raw)+len(out.getvalue())>MAX_TOTAL:raise ValueError('photo storage full; tell Gev')
   ident=uuid.uuid4().hex;original=ident+'.'+ext;preview=ident+'.preview.jpg'
   # Flat, generated filenames only. Orphans on DB failure remain private;
   # never erase an already acknowledged photo automatically.
   for name,data in ((original,raw),(preview,out.getvalue())):
    target=self.root/name
    with target.open('xb') as f:f.write(data)
    os.chmod(target,0o600)
   c.execute('INSERT INTO armen_photos VALUES(?,?,?,?,?,?,?,?)',(ident,actor,dg,fmt,original,preview,purpose,now()))
   result={'saved':True,'id':ident,'duplicate':False,'publishing_enabled':False}
  # After the photo is saved: hand it over. A failure here does not undo the upload; the next hand-over catches up.
  if actor=='armen':
   try:self.hand_over()
   except (OSError,sqlite3.Error) as e:print('hand-over failed, the photo is saved in the portal and NOT handed over: %s: %s'%(type(e).__name__,e),file=sys.stderr,flush=True)
  return result
 def hand_over(self):
  """The only way a photo leaves the portal. For each of Armen's own photos (account 'armen', not marked as a test):
  a hard link to the original and a small metadata file in the outbox folder. Nothing else is put there: no answer,
  no preview, no row of the test account, no database. Safe to run again at any time.
  A hard link, never a copy: one file on the disk under two names, so there is nothing that can be half written.
  When the outbox is on another file system the link is refused and this raises: the photo stays in the portal and
  is not handed over, and that is said, not hidden.
  Every run reads every handed-over file back and compares its sha256 with the one recorded at upload, also a photo
  handed over long ago: when the bytes are no longer the photo, its metadata is taken away and it is reported
  (review of a52d133: an early return had skipped this). The cost is one read of the outbox per run.
  A photo that is no longer Armen's (marked as a test later) gets a record of its own, <id>.withdrawn, written before
  its files are taken out. That record, and nothing else, tells the intake the photo was taken back: the absence of
  a file or of a line in some list is no proof (review of a52d133: a list written after the metadata made a new
  photo look withdrawn when the portal was cut off between the two)."""
  if not self.outbox:return {'handed_over':0,'taken_back':0,'outbox':None,'damaged':[]}
  with self.handing:
   self.outbox.mkdir(parents=True,exist_ok=True,mode=0o750)
   with self.db() as c:
    rows=[dict(r) for r in c.execute("SELECT id,actor,digest,format,original,purpose,created FROM armen_photos WHERE actor='armen' AND id NOT IN (SELECT id FROM armen_excluded WHERE kind='photo') ORDER BY rowid")]
    marked=[dict(r) for r in c.execute("SELECT p.id,p.original,e.created FROM armen_photos p JOIN armen_excluded e ON e.kind='photo' AND e.id=p.id WHERE p.actor='armen' ORDER BY p.rowid")]
   done=0;back=0;damaged=[]
   for m in marked:
    record=self.outbox/(m['id']+'.withdrawn')
    if not record.exists():self._publish(record,{'id':m['id'],'withdrawn':now(),'marked':m['created']})   # the record first
    for name in (m['id']+'.json',m['original']):
     f=self.outbox/name
     if f.is_file() and not f.is_symlink():f.unlink();back+=name.endswith('.json')   # the portal's own copy in the photo folder is untouched
   for r in rows:
    meta=self.outbox/(r['id']+'.json');source=self.root/r['original'];link=self.outbox/r['original']
    if link.exists() and not os.path.samefile(source,link):link.unlink()   # not the photo itself: a leftover under its name
    if not link.exists():os.link(source,link)   # OSError when the outbox is not on the photo folder's file system: no silent copy
    if _sha256(link)!=r['digest']:
     # The file no longer is what was recorded at upload: nothing is, or stays, published for it. Not a take-back:
     # no .withdrawn record is written, and work the intake already made from the whole photo is not touched.
     if meta.exists():meta.unlink()
     link.unlink();damaged.append(r['id']);continue
    if meta.exists():continue
    os.chmod(link,0o640)
    try:os.chown(link,-1,self.outbox.stat().st_gid)   # readable by the outbox folder's group, by nobody else
    except (OSError,AttributeError):pass
    self._publish(meta,{'id':r['id'],'sha256':r['digest'],'format':r['format'],'file':r['original'],'actor':r['actor'],'uploaded':r['created'],'purpose':r['purpose']})
    done+=1
   if damaged:print('hand-over: the stored photo no longer matches its sha256, not handed over: '+', '.join(damaged),file=sys.stderr,flush=True)
   handed=sum(1 for r in rows if (self.outbox/(r['id']+'.json')).exists())
   return {'handed_over':done,'taken_back':back,'outbox':handed,'damaged':damaged}
 def _publish(self,target,data):
  tmp=target.with_name(target.name+'.tmp');tmp.write_text(encode(data),encoding='utf-8')
  os.chmod(tmp,0o640);os.replace(tmp,target)   # appears whole or not at all
 def check_outbox(self):
  """At start: can a photo be handed over at all? A hard link from the photo folder into the outbox is tried with an
  empty probe file. When it fails the portal does not start with that outbox: better no service than photos that
  silently never arrive."""
  if not self.outbox:return
  self.outbox.mkdir(parents=True,exist_ok=True,mode=0o750)
  probe=self.root/('.probe-'+uuid.uuid4().hex);there=self.outbox/probe.name
  try:
   probe.write_bytes(b'');os.link(probe,there)
  except OSError as e:
   raise SystemExit('the outbox must be on the same file system as the photo folder (hard link refused: %s)'%e.strerror) from None
  finally:
   for f in (there,probe):
    if f.exists():f.unlink()
 def exclude(self,kind,ident,reason,marked_by):
  """Mark one answer or photo as not Armen's own (a test by somebody else under his account). The row and the file
  stay; from then on it is in no state, no count and no preview, and the media intake does not take it in."""
  if kind not in ('answer','photo') or not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('kind and id required')
  for value in (reason,marked_by):
   if not isinstance(value,str) or not value.strip() or len(value)>500:raise ValueError('reason and who marked it required')
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not c.execute('SELECT 1 FROM '+('armen_answers' if kind=='answer' else 'armen_photos')+' WHERE id=?',(ident,)).fetchone():raise LookupError('not found')
   c.execute('INSERT OR IGNORE INTO armen_excluded VALUES(?,?,?,?,?)',(kind,ident,reason.strip(),marked_by.strip(),now()))
   mark=dict(c.execute('SELECT * FROM armen_excluded WHERE kind=? AND id=?',(kind,ident)).fetchone())
  if kind=='photo':
   try:self.hand_over()   # a photo marked after it was handed over is taken back out of the outbox
   except (OSError,sqlite3.Error) as e:print('hand-over failed after a mark: %s: %s'%(type(e).__name__,e),file=sys.stderr,flush=True)
  return mark
 def state(self,actor,owner=False):
  today=day()
  with self.db() as c:
   # The reviewer sees Armen's rows and no others; every account sees only its own. Rows marked as a test: nobody.
   args=('armen',) if owner else (actor,)
   where=" WHERE id NOT IN (SELECT id FROM armen_excluded WHERE kind='%s') AND actor=?"
   # In the order they were saved (rowid), not by clock text: two answers may carry the same time, and the id is random.
   answers=[dict(r) for r in c.execute('SELECT * FROM armen_answers'+where%'answer'+' ORDER BY rowid',args)]
   photos=[dict(r) for r in c.execute('SELECT id,actor,purpose,created FROM armen_photos'+where%'photo'+' ORDER BY rowid DESC LIMIT 100',args)]
  # The day is read once for the whole answer: read twice, midnight between the two gave a new day with yesterday's answers.
  latest={}
  for r in answers:
   if r['day']==today:latest[r['actor']+':'+r['question']]=r
  test=actor=='test' and not owner
  return {'day':today,'questions':QUESTIONS,'answers':list(latest.values()),'photos':photos,'test_account':test,
          'trust':'TEST_NOT_COUNTED' if test else 'ARMEN_REPORTED','publishing_enabled':False,'orders_created':False}
 def preview(self,actor,ident,owner=False):
  if not re.fullmatch('[a-f0-9]{32}',ident):raise LookupError('unavailable')
  with self.db() as c:row=c.execute("SELECT * FROM armen_photos WHERE id=? AND id NOT IN (SELECT id FROM armen_excluded WHERE kind='photo')",(ident,)).fetchone()
  if not row or (row['actor']!=actor and not (owner and row['actor']=='armen')):raise LookupError('unavailable')
  p=self.root/row['preview']
  if p.is_symlink():raise LookupError('unavailable')
  return p.read_bytes()

def server(store,users,origin,port=8790):
 if origin!='https://runtime.kryuk24.ru':raise ValueError('explicit runtime HTTPS origin required')
 if not users or set(users)-set(ACCOUNTS) or 'armen' not in users:raise ValueError('armen user required; optional gev reviewer and test account')
 for r in users.values():
  if set(r)!={'salt','hash'} or not re.fullmatch('[a-f0-9]{32}',r['salt']) or not re.fullmatch('[a-f0-9]{64}',r['hash']):raise ValueError('invalid credential record')
 sessions=Sessions();attempts=[];lock=threading.Lock();uploads=threading.BoundedSemaphore(2);logins=threading.BoundedSemaphore(2)
 class H(BaseHTTPRequestHandler):
  def setup(self):super().setup();self.connection.settimeout(30)
  def log_message(self,*args):pass
  def reply(self,status,data,kind='application/json; charset=utf-8',cookie=None,keep=False):
   raw=data if isinstance(data,bytes) else (encode(data) if isinstance(data,dict) else data).encode()
   self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
   for k,v in [('Cache-Control','public, max-age=86400' if keep else 'no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','no-referrer'),('X-Robots-Tag','noindex, nofollow')]:self.send_header(k,v)
   self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; font-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
   if cookie is not None:self.send_header('Set-Cookie',cookie)
   self.end_headers();self.wfile.write(raw)
  def identity(self):
   self.session=sessions.resolve(self.headers.get('Cookie',''))
   return self.session[0] if self.session else None
  def cookie(self,token,age=SESSION_TTL):
   return f'{COOKIE}={token}; Path={PREFIX}; Max-Age={age}; Secure; HttpOnly; SameSite=Strict'
  def login(self):
   if self.headers.get('Origin')!=origin:return self.reply(403,{'error':'origin required'})
   if self.headers.get('Transfer-Encoding'):return self.reply(400,{'error':'invalid login'})
   try:
    # A character outside the basic plane (an emoji) is 12 bytes when JSON escapes it as two \uXXXX: 1024 of them
    # in the password and 64 in the name are 13056 bytes, plus the keys and punctuation.
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=MAX_LOGIN_BODY or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError()
    raw=self.rfile.read(size)
    if len(raw)!=size:raise ValueError()
    d=json.loads(raw)
    if type(d) is not dict or set(d)!={'username','password'} or not all(type(v) is str for v in d.values()):raise ValueError()
    if len(d['username'])>64 or not 1<=len(d['password'])<=1024:raise ValueError()
   except (ValueError,TypeError):return self.reply(400,{'error':'invalid login'})
   with lock:
    t=time.monotonic();attempts[:]=[v for v in attempts if t-v<60]
    if len(attempts)>=30:return self.reply(429,{'error':'Попробуйте через минуту.'})
   if not logins.acquire(blocking=False):return self.reply(429,{'error':'Попробуйте через минуту.'})
   try:
    # Checked directly: wrapped as a Basic header, a long non-ASCII password allowed by provisioning passed the 2048 limit.
    actor=verify(d['username'],d['password'],users)
    if not actor:
     with lock:attempts.append(time.monotonic())
     return self.reply(401,{'error':'Проверьте имя и пароль.'})
    sessions.revoke(self.headers.get('Cookie',''))
    try:token,_=sessions.create(actor)
    except ValueError:return self.reply(503,{'error':'Попробуйте позже.'})
    return self.reply(200,{'logged_in':True},cookie=self.cookie(token))
   finally:logins.release()
  def do_GET(self):
   name=self.path[len(PREFIX):] if self.path.startswith(PREFIX) else None
   if name in PUBLIC:return self.reply(200,(Path(__file__).parent/name).read_bytes(),PUBLIC[name],keep=name.endswith(('.woff2','.webp')))
   actor=self.identity()
   if not actor:
    if self.path==PREFIX:return self.reply(200,(Path(__file__).parent/'login.html').read_bytes(),'text/html; charset=utf-8')
    return self.reply(401,{'error':'login required'})
   if '?' in self.path:return self.reply(404,{'error':'unavailable'})
   if self.path==PREFIX:
    raw=(Path(__file__).parent/'index.html').read_text(encoding='utf-8').replace('__CSRF__',self.session[1]).replace('__ACTOR__',actor)
    return self.reply(200,raw,'text/html; charset=utf-8')
   if self.path==PREFIX+'app.js':return self.reply(200,(Path(__file__).parent/'app.js').read_bytes(),'text/javascript; charset=utf-8')
   if self.path==PREFIX+'api/state':return self.reply(200,store.state(actor,owner=actor=='gev'))
   if self.path.startswith(PREFIX+'preview/'):
    try:return self.reply(200,store.preview(actor,self.path[len(PREFIX+'preview/'):],actor=='gev'),'image/jpeg')
    except (LookupError,OSError):return self.reply(404,{'error':'unavailable'})
   return self.reply(404,{'error':'unavailable'})
  def do_POST(self):
   if self.path==PREFIX+'api/login':return self.login()
   actor=self.identity()
   if not actor:return self.reply(401,{'error':'login required'})
   if self.headers.get('Origin')!=origin or not same(self.headers.get('X-CSRF-Token',''),self.session[1]):return self.reply(403,{'error':'reload page'})
   if self.path==PREFIX+'api/logout':
    sessions.revoke(self.headers.get('Cookie',''));return self.reply(200,{'logged_out':True},cookie=self.cookie('',0))
   if actor not in WRITERS:return self.reply(403,{'error':'read only'})
   try:
    if self.headers.get('Transfer-Encoding'):raise ValueError('chunked upload not supported')
    size=int(self.headers.get('Content-Length','0'));ctype=self.headers.get('Content-Type','').split(';')[0]
    if self.path==PREFIX+'api/answer':
     if not 0<size<=4096 or ctype!='application/json':raise ValueError('JSON answer required')
     raw=self.rfile.read(size)
     if len(raw)!=size:raise ValueError('incomplete body')
     d=json.loads(raw)
     if type(d) is not dict:raise ValueError('object required')
     return self.reply(200,store.answer(actor,self.headers.get('Idempotency-Key'),d))
    if self.path==PREFIX+'api/photo':
     if not 0<size<=MAX_IMAGE or ctype not in ('image/jpeg','image/png','image/webp'):raise ValueError('JPEG/PNG/WebP up to 20 MiB required')
     if not uploads.acquire(blocking=False):return self.reply(429,{'error':'Загрузка занята. Повторите через минуту.'})
     try:
      raw=self.rfile.read(size)
      if len(raw)!=size:raise ValueError('incomplete upload')
      return self.reply(201,store.photo(actor,raw,self.headers.get('X-Photo-Purpose')))
     finally:uploads.release()
    return self.reply(404,{'error':'unavailable'})
   except (ValueError,TypeError,KeyError):return self.reply(400,{'error':'Не сохранилось. Проверьте формат и обновите страницу.'})
   except (OSError,sqlite3.Error):return self.reply(503,{'error':'Не сохранилось. Повторите позже или сообщите Геву.'})
 return ThreadingHTTPServer(('127.0.0.1',port),H)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--photos',required=True);p.add_argument('--credentials',required=True);p.add_argument('--port',type=int,default=8790)
 p.add_argument('--outbox',help='folder the media intake reads; without it no photo leaves the portal');a=p.parse_args()
 os.umask(0o077)
 store=Store(a.db,a.photos,a.outbox);store.check_outbox()
 server(store,json.loads(Path(a.credentials).read_text(encoding='utf-8')),'https://runtime.kryuk24.ru',a.port).serve_forever()
