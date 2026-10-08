import base64,io,json,re,subprocess,sys,tempfile,threading,unittest,urllib.request,urllib.error,uuid
from pathlib import Path
from PIL import Image
import portal
from portal import Store,server,credential,day,PREFIX,Sessions,SESSION_TTL,COOKIE
from unittest.mock import patch

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.password='SAMPLE-password-not-real-123'
  cls.creds={'armen':credential(cls.password),'gev':credential(cls.password)}
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name+'/db',self.tmp.name+'/media')
  self.http=server(self.store,self.creds,'https://runtime.kryuk24.ru',0)
  self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
  self.base='http://127.0.0.1:'+str(self.http.server_port)
  self.cookies={}
 def tearDown(self):
  self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path=PREFIX,user='armen',body=None,headers=None):
  h={}
  if user is not None:
   if user not in self.cookies:
    status,raw,hs=self.login(user)
    if status!=200:return status,raw,hs
    self.cookies[user]=hs['Set-Cookie'].split(';')[0]
   h['Cookie']=self.cookies[user]
  h.update(headers or {})
  req=urllib.request.Request(self.base+path,data=body,headers=h)
  try:
   with urllib.request.urlopen(req) as r:return r.status,r.read(),r.headers
  except urllib.error.HTTPError as e:
   with e:return e.code,e.read(),e.headers
 def login(self,user='armen',headers=None,password=None):
  h={'Content-Type':'application/json','Origin':'https://runtime.kryuk24.ru'};h.update(headers or {})
  return self.request(PREFIX+'api/login',None,json.dumps({'username':user,'password':password or self.password}).encode(),h)
 def csrf(self,user='armen'):
  _,raw,_=self.request(user=user)
  return re.search(b'name="csrf-token" content="([^"]+)"',raw)[1].decode()
 def answer(self,headers=None,user='armen'):
  d=dict(question='availability',answer='READY',day=day())
  h={'Content-Type':'application/json','Origin':'https://runtime.kryuk24.ru','X-CSRF-Token':self.csrf(user),'Idempotency-Key':uuid.uuid4().hex}
  h.update(headers or {})
  return self.request(PREFIX+'api/answer',user,json.dumps(d).encode(),h)
 def png(self):
  out=io.BytesIO();Image.new('RGB',(20,20),'navy').save(out,'PNG');return out.getvalue()
 def test_login_and_no_owner_routes(self):
  self.assertEqual(self.request(user='unknown')[0],401)
  self.assertEqual(self.request('/operator/work')[0],404)
  self.assertEqual(self.request('/operator/work/approve',body=b'{}')[0],403)
  status,raw,h=self.request();self.assertEqual(status,200)
  self.assertNotIn(self.password.encode(),raw);self.assertEqual(h['X-Frame-Options'],'DENY')
 def test_one_click_save_and_csrf_origin_denials(self):
  self.assertEqual(self.answer()[0],200)
  self.assertEqual(self.answer({'Origin':'https://evil.example'})[0],403)
  self.assertEqual(self.answer({'X-CSRF-Token':'wrong'})[0],403)
  state=json.loads(self.request(PREFIX+'api/state')[1])
  self.assertEqual(state['answers'][0]['answer'],'READY')
  self.assertFalse(state['orders_created'])
 def test_owner_read_only_and_armen_identity_not_body(self):
  self.assertEqual(self.answer(user='gev')[0],403)
  d=dict(question='availability',answer='READY',day=day(),actor='gev')
  with self.assertRaises(ValueError):self.store.answer('armen',uuid.uuid4().hex,d)
 def test_answer_idempotency_and_history(self):
  key=uuid.uuid4().hex;d=dict(question='inquiries',answer='YES',day=day())
  first=self.store.answer('armen',key,d);self.assertEqual(first,self.store.answer('armen',key,d))
  with self.assertRaises(ValueError):self.store.answer('armen',key,{**d,'answer':'NO'})
  self.store.answer('armen',uuid.uuid4().hex,{**d,'answer':'NO'})
  with self.store.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM armen_answers').fetchone()[0],2)
 def test_photo_original_private_thumbnail_and_duplicate(self):
  raw=self.png();r=self.store.photo('armen',raw,'WORK');r2=self.store.photo('armen',raw,'WORK')
  self.assertEqual(r['id'],r2['id']);self.assertTrue(r2['duplicate'])
  with self.store.db() as c:row=c.execute('SELECT * FROM armen_photos').fetchone()
  self.assertEqual((self.store.root/row['original']).read_bytes(),raw)
  im=Image.open(io.BytesIO(self.store.preview('armen',r['id'])));self.assertEqual(im.format,'JPEG');im.close()
  with self.assertRaises(LookupError):self.store.preview('other',r['id'])
  self.assertEqual(self.request(PREFIX+'preview/../../credentials')[0],404)
 def test_image_full_decode_and_size_and_format(self):
  for raw in (b'\xff\xd8\xffFAKE',b'<svg/>',b''):
   with self.assertRaises(ValueError):self.store.photo('armen',raw,'WORK')
  with self.assertRaises(ValueError):self.store.photo('armen',self.png(),'PUBLICATION_APPROVED')
 def test_http_upload_and_no_publication(self):
  headers={'Content-Type':'image/png','Origin':'https://runtime.kryuk24.ru','X-CSRF-Token':self.csrf(),'X-Photo-Purpose':'WORK'}
  status,raw,_=self.request(PREFIX+'api/photo',body=self.png(),headers=headers)
  self.assertEqual(status,201);self.assertFalse(json.loads(raw)['publishing_enabled'])
  self.assertEqual(self.request(PREFIX+'api/photo',body=self.png(),headers={**headers,'Origin':'null'})[0],403)
 def test_questions_unknown_option_and_invalid_answer(self):
  d=dict(question='completed_trips',answer='UNKNOWN',day=day());self.store.answer('armen',uuid.uuid4().hex,d)
  with self.assertRaises(ValueError):self.store.answer('armen',uuid.uuid4().hex,{**d,'answer':5})
  with self.assertRaises(ValueError):self.store.answer('armen',uuid.uuid4().hex,{**d,'day':'2000-01-01'})

 def test_session_cookie_and_no_repeated_password_hash(self):
  import portal
  # Counts the hash itself, whichever function asks for it: one for the login, none for the ten requests after it.
  with patch('portal.hashlib.pbkdf2_hmac',wraps=portal.hashlib.pbkdf2_hmac) as verify:
   status,raw,h=self.request();self.assertEqual(status,200)
   for _ in range(10):self.assertEqual(self.request(PREFIX+'api/state')[0],200)
   self.assertEqual(verify.call_count,1)
  _,_,h=self.login();cookie=h['Set-Cookie']
  for flag in ('Secure','HttpOnly','SameSite=Strict','Path='+PREFIX,'Max-Age=28800'):self.assertIn(flag,cookie)
  self.assertNotIn('WWW-Authenticate',h)
 def test_login_requires_origin_and_auth_header_is_not_session(self):
  self.assertEqual(self.login(headers={'Origin':'https://evil.example'})[0],403)
  self.assertEqual(self.login(password='wrong')[0],401)
  auth='Basic '+base64.b64encode(('armen:'+self.password).encode()).decode()
  self.assertEqual(self.request(PREFIX+'api/state',None,headers={'Authorization':auth})[0],401)
  self.assertEqual(self.request(PREFIX+'api/state',None,headers={'Cookie':COOKIE+'=forged'})[0],401)
 def test_logout_revokes_and_csrf_is_session_specific(self):
  token=self.csrf();cookie=self.cookies['armen']
  _,_,h=self.login();other=h['Set-Cookie'].split(';')[0]
  self.assertEqual(self.answer({'Cookie':other,'X-CSRF-Token':token})[0],403)
  headers={'Origin':'https://runtime.kryuk24.ru','X-CSRF-Token':token,'Cookie':cookie}
  status,_,h=self.request(PREFIX+'api/logout',body=b'',headers=headers)
  self.assertEqual(status,200);self.assertIn('Max-Age=0',h['Set-Cookie'])
  self.assertEqual(self.request(PREFIX+'api/state',None,headers={'Cookie':cookie})[0],401)
 def test_session_expiry_restart_and_token_rotation(self):
  clock=[0];sessions=Sessions(lambda:clock[0]);token,csrf=sessions.create('armen')
  header=COOKIE+'='+token
  self.assertEqual(sessions.resolve(header)[0],'armen')
  self.assertIsNone(Sessions().resolve(header))
  clock[0]=SESSION_TTL;self.assertIsNone(sessions.resolve(header))
  token2,csrf2=sessions.create('armen');self.assertNotEqual(token,token2);self.assertNotEqual(csrf,csrf2)
  sessions.revoke(COOKIE+'='+token2);self.assertIsNone(sessions.resolve(COOKIE+'='+token2))
 def test_successful_relogin_revokes_presented_session(self):
  self.csrf();old=self.cookies['armen']
  status,_,h=self.login(headers={'Cookie':old});self.assertEqual(status,200)
  self.assertNotEqual(h['Set-Cookie'].split(';')[0],old)
  self.assertEqual(self.request(PREFIX+'api/state',None,headers={'Cookie':old})[0],401)

 def test_long_non_ascii_password_allowed_by_provisioning_logs_in(self):
  # 800 Armenian letters: provisioning accepts it; wrapped as a Basic header it passed 2048 bytes and login refused it.
  password='ա'*800;tmp=tempfile.TemporaryDirectory()
  http=server(Store(tmp.name+'/db',tmp.name+'/media'),{'armen':credential(password)},'https://runtime.kryuk24.ru',0)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   def post(pw):
    req=urllib.request.Request('http://127.0.0.1:%d%sapi/login'%(http.server_port,PREFIX),data=json.dumps({'username':'armen','password':pw}).encode(),
                               headers={'Content-Type':'application/json','Origin':'https://runtime.kryuk24.ru'})
    try:
     with urllib.request.urlopen(req) as r:return r.status
    except urllib.error.HTTPError as e:
     with e:return e.code
   self.assertEqual(post(password),200)
   self.assertEqual(post(password[:-1]),401)
  finally:
   http.shutdown();http.server_close();thread.join();tmp.cleanup()
 def test_longest_allowed_emoji_password_logs_in_escaped_or_not(self):
  # 1024 characters outside the basic plane: 4 bytes each as UTF-8, 12 bytes each when JSON escapes them (two \uXXXX).
  password='\U0001F600'*1024;name='armen';tmp=tempfile.TemporaryDirectory()
  http=server(Store(tmp.name+'/db',tmp.name+'/media'),{name:credential(password)},'https://runtime.kryuk24.ru',0)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   def post(body):
    req=urllib.request.Request('http://127.0.0.1:%d%sapi/login'%(http.server_port,PREFIX),data=body,
                               headers={'Content-Type':'application/json','Origin':'https://runtime.kryuk24.ru'})
    try:
     with urllib.request.urlopen(req) as r:return r.status
    except urllib.error.HTTPError as e:
     with e:return e.code
   d={'username':name,'password':password}
   plain=json.dumps(d,ensure_ascii=False).encode('utf-8');escaped=json.dumps(d,ensure_ascii=True).encode('ascii')
   self.assertEqual((len(plain)>4096,len(escaped)>12288),(True,True),'the escaped form is the long one')
   self.assertEqual(post(plain),200);self.assertEqual(post(escaped),200,'the same name and password, escaped: %d bytes'%len(escaped))
   wrong=json.dumps({'username':name,'password':password[:-1]+'\U0001F601'},ensure_ascii=True).encode('ascii')
   self.assertEqual(post(wrong),401)
   # The largest body the rules allow: 64 and 1024 such characters, every one escaped.
   largest=json.dumps({'username':'\U0001F600'*64,'password':password},ensure_ascii=True).encode('ascii')
   self.assertLessEqual(len(largest),portal.MAX_LOGIN_BODY);self.assertEqual(post(largest),401,'read and checked, not refused for its size')
   self.assertEqual(post(escaped+b' '*(portal.MAX_LOGIN_BODY+1-len(escaped))),400,'one byte over the limit')
  finally:
   http.shutdown();http.server_close();thread.join();tmp.cleanup()
 def test_state_reads_the_day_once_so_midnight_cannot_split_an_answer(self):
  d=dict(question='inquiries',answer='YES',day=day());self.store.answer('armen',uuid.uuid4().hex,d)
  # Simulation of midnight inside one request: the first reading of the day is today, every later one is tomorrow.
  with patch('portal.day',side_effect=[d['day']]+['2999-01-01']*20) as clock:
   state=self.store.state('armen')
  self.assertEqual(clock.call_count,1)
  self.assertEqual((state['day'],[a['day'] for a in state['answers']]),(d['day'],[d['day']]),'one day for the heading and for the answers under it')
 def test_malformed_csrf_header_is_refused_not_a_crash(self):
  for bad in ('é','é'*40,''):
   status,raw,_=self.answer({'X-CSRF-Token':bad})
   self.assertEqual((status,json.loads(raw)['error']),(403,'reload page'),repr(bad))
  self.assertEqual(self.answer()[0],200,'the server still answers and the right token still works')
 def test_repeat_of_a_saved_answer_after_midnight_returns_the_saved_result(self):
  key=uuid.uuid4().hex;d=dict(question='inquiries',answer='YES',day=day())
  first=self.store.answer('armen',key,d)
  with patch('portal.day',return_value='2999-01-01'):
   self.assertEqual(self.store.answer('armen',key,d),first,'the same key and body: the saved result, whatever the date is now')
   with self.assertRaises(ValueError):self.store.answer('armen',key,{**d,'answer':'NO'})
   with self.assertRaises(ValueError):self.store.answer('armen',uuid.uuid4().hex,d)  # a new answer for a day that is over
   with self.assertRaises(ValueError):self.store.answer('armen',key,{**d,'day':5})
  with self.store.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM armen_answers').fetchone()[0],1)
 def test_latest_answer_is_the_last_saved_when_times_are_equal(self):
  # Simulation of equal timestamps: the clock text is fixed. The id is random, so the old order (created, id) was a coin toss per pair.
  with patch('portal.now',return_value='2026-10-08T00:00:00+00:00'):
   for i in range(40):
    want='YES' if i%2 else 'NO'
    self.store.answer('armen',uuid.uuid4().hex,dict(question='inquiries',answer=want,day=day()))
    shown=[a['answer'] for a in self.store.state('armen')['answers'] if a['question']=='inquiries']
    self.assertEqual(shown,[want],'after save %d'%(i+1))
   for colour in ('red','green','blue'):
    out=io.BytesIO();Image.new('RGB',(20,20),colour).save(out,'PNG');last=self.store.photo('armen',out.getvalue(),'WORK')['id']
    self.assertEqual(self.store.state('armen')['photos'][0]['id'],last)
 def test_preview_follows_the_orientation_and_other_modes_decode(self):
  out=io.BytesIO();exif=Image.Exif();exif[0x0112]=6;Image.new('RGB',(1600,800),'navy').save(out,'JPEG',exif=exif)
  with Image.open(io.BytesIO(self.store.preview('armen',self.store.photo('armen',out.getvalue(),'WORK')['id']))) as im:
   self.assertEqual(im.size,(300,600),'turned as the camera recorded it, then fitted into 600')
  for mode in ('P','L','RGBA','LA','1'):
   out=io.BytesIO();Image.new(mode,(900,300)).save(out,'PNG')
   with Image.open(io.BytesIO(self.store.preview('armen',self.store.photo('armen',out.getvalue(),'OTHER')['id']))) as im:
    self.assertEqual((im.mode,im.size),('RGB',(600,200)),mode)
  out=io.BytesIO();Image.new('RGB',(3000,2000),'navy').save(out,'JPEG');cut=out.getvalue()[:len(out.getvalue())//2]
  with self.assertRaises(ValueError):self.store.photo('armen',cut,'WORK')
 def test_two_40_megapixel_uploads_at_once_stay_under_the_service_memory_limit(self):
  # A real measurement in a separate process: two pictures of the largest allowed size are saved by two threads at
  # the same moment and the process reports its own peak memory. The unit file allows 768 MiB (MemoryMax).
  child=r'''
import io,sys,tempfile,threading
from PIL import Image
import portal
def peak():
 if sys.platform=='win32':
  import ctypes
  from ctypes import wintypes
  class M(ctypes.Structure):_fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in 'abcdefgh']
  m=M();m.cb=ctypes.sizeof(m);k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=wintypes.HANDLE
  p=ctypes.WinDLL('psapi');p.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
  if not p.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(m),m.cb):raise OSError('no memory figure')
  return m.a/2**20  # PeakWorkingSetSize
 import resource
 return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(2**20 if sys.platform=='darwin' else 1024)
raws=[open(n,'rb').read() for n in sys.argv[2:4]];tmp=tempfile.TemporaryDirectory();store=portal.Store(tmp.name+'/db',tmp.name+'/media');saved=[]
ts=[threading.Thread(target=lambda r=r:saved.append(store.photo('armen',r,'WORK')['duplicate'])) for r in raws]
[t.start() for t in ts];[t.join() for t in ts]
print(len(saved),round(peak()))
'''
  folder=Path(self.tmp.name)
  for fmt,mode in (('PNG','RGBA'),('PNG','RGB'),('JPEG','RGB')):
   names=[]
   for n,colour in enumerate(((10,20,30,255),(40,50,60,255))):
    name=folder/('big-%s-%s-%d'%(fmt,mode,n));Image.new(mode,(8000,5000),colour[:len(mode)]).save(name,fmt);names.append(str(name))
   got=subprocess.run([sys.executable,'-c',child,'x']+names,capture_output=True,text=True,cwd=str(Path(__file__).parent),timeout=300)
   self.assertEqual(got.returncode,0,got.stderr[-600:])
   saved,peak=map(int,got.stdout.split())
   self.assertEqual(saved,2,'both pictures were saved')
   self.assertLess(peak,512,'%s %s: peak %d MiB; the service is allowed 768'%(fmt,mode,peak))
   print('\n  two 40 MP %s %s at once: peak %d MiB'%(fmt,mode,peak),file=sys.stderr)
 def test_password_of_eight_characters_is_the_shortest_accepted(self):
  # Gev's decision of 08.10.2026: 8, not 16. Seven are refused when the password is set; eight are stored and log in.
  with self.assertRaises(ValueError):credential('SAMPLE7')
  short='SAMPLE-8';tmp=tempfile.TemporaryDirectory()
  http=server(Store(tmp.name+'/db',tmp.name+'/media'),{'armen':credential(short)},'https://runtime.kryuk24.ru',0)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   req=urllib.request.Request('http://127.0.0.1:%d%sapi/login'%(http.server_port,PREFIX),data=json.dumps({'username':'armen','password':short}).encode(),
    headers={'Content-Type':'application/json','Origin':'https://runtime.kryuk24.ru'})
   with urllib.request.urlopen(req) as r:self.assertEqual(r.status,200)
  finally:http.shutdown();http.server_close();thread.join();tmp.cleanup()
 def test_design_files_are_public_and_the_page_script_is_not(self):
  # The look of the page is readable before login (tokens, fonts, logo, theme); app.js and the data are not.
  for name,kind in portal.PUBLIC.items():
   status,raw,headers=self.request(PREFIX+name,user=None)
   self.assertEqual((status,headers['Content-Type'],len(raw)>0),(200,kind,True),name)
   self.assertEqual(headers['Cache-Control'],'public, max-age=86400' if name.endswith(('.woff2','.webp')) else 'no-store',name)
  self.assertEqual(self.request(PREFIX+'app.js',user=None)[0],401)
  self.assertEqual(self.request(PREFIX+'portal.py',user=None)[0],401)
  self.assertEqual(self.request(PREFIX+'app.js')[0],200)
  status,raw,headers=self.request(user=None)
  self.assertIn("font-src 'self'",headers['Content-Security-Policy'])
  for name in (b'tokens.css',b'fonts.css',b'style.css',b'theme.js',b'logo-light.webp',b'logo-dark.webp'):self.assertIn(name,raw)
  page=self.request()[1]
  for part in (b'id="send"',b'id="save"',b'id="pending"',b'tokens.css'):self.assertIn(part,page)
 def test_rows_marked_as_a_test_are_out_of_every_state_and_preview(self):
  # Gev tried the portal under Armen's account; his rows are marked and must not count as Armen's.
  photo=self.store.photo('armen',self.png(),'WORK')['id']
  answer=self.store.answer('armen',uuid.uuid4().hex,dict(question='inquiries',answer='YES',day=day()))['id']
  for owner in (False,True):
   s=self.store.state('armen',owner);self.assertEqual((len(s['answers']),len(s['photos'])),(1,1))
  self.assertEqual(self.store.exclude('photo',photo,'SAMPLE test','GEV')['marked_by'],'GEV')
  self.store.exclude('answer',answer,'SAMPLE test','GEV');self.store.exclude('answer',answer,'SAMPLE test again','GEV')
  for owner in (False,True):
   s=self.store.state('armen',owner);self.assertEqual((s['answers'],s['photos']),([],[]))
  with self.assertRaises(LookupError):self.store.preview('armen',photo)
  with self.assertRaises(LookupError):self.store.preview('gev',photo,True)
  with self.assertRaises(LookupError):self.store.exclude('photo',uuid.uuid4().hex,'SAMPLE','GEV')
  with self.assertRaises(ValueError):self.store.exclude('photo',photo,'','GEV')
  with self.store.db() as c:self.assertEqual([r[0] for r in c.execute('SELECT count(*) FROM armen_photos UNION ALL SELECT count(*) FROM armen_answers UNION ALL SELECT count(*) FROM armen_excluded')],[1,1,2])
  # A new answer to the same question is Armen's own and is the one shown.
  self.store.answer('armen',uuid.uuid4().hex,dict(question='inquiries',answer='NO',day=day()))
  self.assertEqual([a['answer'] for a in self.store.state('armen')['answers']],['NO'])
 def test_the_test_account_writes_but_its_rows_are_never_armens(self):
  # Kept apart by the system, not by a mark made afterwards: the account 'test' answers and uploads like Armen,
  # sees only its own rows, and none of them reaches Armen's state, the reviewer's state or the outbox.
  import tempfile as t
  folder=t.TemporaryDirectory();store=Store(folder.name+'/db',folder.name+'/media',folder.name+'/outbox')
  users={'armen':credential(self.password),'gev':credential(self.password),'test':credential(self.password)}
  http=server(store,users,'https://runtime.kryuk24.ru',0);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  def call(path,cookie=None,body=None,headers=None):
   h={'Origin':'https://runtime.kryuk24.ru'};h.update(headers or {})
   if cookie:h['Cookie']=cookie
   req=urllib.request.Request('http://127.0.0.1:%d%s'%(http.server_port,PREFIX+path),data=body,headers=h)
   try:
    with urllib.request.urlopen(req) as r:return r.status,r.read(),r.headers
   except urllib.error.HTTPError as e:
    with e:return e.code,e.read(),e.headers
  def enter(user):
   s,_,hs=call('api/login',body=json.dumps({'username':user,'password':self.password}).encode(),headers={'Content-Type':'application/json'})
   self.assertEqual(s,200);cookie=hs['Set-Cookie'].split(';')[0]
   return cookie,re.search(b'name="csrf-token" content="([^"]+)"',call('',cookie)[1])[1].decode()
  try:
   cookie,csrf=enter('test')
   s,raw,_=call('api/photo',cookie,self.png(),{'Content-Type':'image/png','X-CSRF-Token':csrf,'X-Photo-Purpose':'WORK'});self.assertEqual(s,201)
   s,_,_=call('api/answer',cookie,json.dumps(dict(question='inquiries',answer='YES',day=day())).encode(),{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':uuid.uuid4().hex});self.assertEqual(s,200)
   mine=json.loads(call('api/state',cookie)[1])
   self.assertEqual((len(mine['photos']),len(mine['answers']),mine['test_account'],mine['trust']),(1,1,True,'TEST_NOT_COUNTED'))
   self.assertEqual(call('preview/'+mine['photos'][0]['id'],cookie)[0],200)
   for user in ('armen','gev'):
    other,_=enter(user);seen=json.loads(call('api/state',other)[1])
    self.assertEqual((seen['photos'],seen['answers'],seen['test_account']),([],[],False),user)
    self.assertEqual(call('preview/'+mine['photos'][0]['id'],other)[0],404,user)
   self.assertEqual(store.hand_over()['outbox'],0)
   self.assertEqual([f.name for f in Path(folder.name+'/outbox').iterdir()],[],'nothing of the test account is handed over')
   # Armen's own photo and answer are his, with the test rows beside them in the same database.
   cookie,csrf=enter('armen')
   s,_,_=call('api/photo',cookie,self.png(),{'Content-Type':'image/png','X-CSRF-Token':csrf,'X-Photo-Purpose':'WORK'});self.assertEqual(s,201)
   state=json.loads(call('api/state',cookie)[1]);self.assertEqual((len(state['photos']),state['answers'],state['trust']),(1,[],'ARMEN_REPORTED'))
   self.assertEqual(sorted(f.suffix for f in Path(folder.name+'/outbox').iterdir()),['.json','.png'],'the facts and the photo')
  finally:
   http.shutdown();http.server_close();thread.join();folder.cleanup()
 def test_the_outbox_holds_photos_and_their_facts_only_and_follows_marks(self):
  import tempfile as t
  folder=t.TemporaryDirectory();outbox=Path(folder.name+'/outbox');store=Store(folder.name+'/db',folder.name+'/media',outbox)
  try:
   raw=self.png();ident=store.photo('armen',raw,'EQUIPMENT')['id']
   store.answer('armen',uuid.uuid4().hex,dict(question='inquiries',answer='YES',day=day()))
   names=sorted(f.name for f in outbox.iterdir());self.assertEqual(names,[ident+'.json',ident+'.png'])
   meta=json.loads((outbox/(ident+'.json')).read_text(encoding='utf-8'))
   self.assertEqual(set(meta),{'id','sha256','format','file','actor','uploaded','purpose'})
   self.assertEqual((meta['actor'],meta['purpose'],meta['file'],(outbox/meta['file']).read_bytes()==raw),('armen','EQUIPMENT',ident+'.png',True))
   self.assertEqual(store.hand_over(),{'handed_over':0,'taken_back':0,'outbox':1,'damaged':[]},'a second run adds nothing')
   # an interrupted hand-over: the link is there, the metadata file is not; the next run completes it
   (outbox/(ident+'.json')).unlink();self.assertEqual(store.hand_over()['handed_over'],1)
   # marked as a test afterwards: taken back out, the portal's own file stays
   store.exclude('photo',ident,'SAMPLE','GEV');self.assertEqual([f.name for f in outbox.iterdir()],[ident+'.withdrawn'],'a record of its own says it was taken back')
   record=json.loads((outbox/(ident+'.withdrawn')).read_text(encoding='utf-8'));self.assertEqual(record['id'],ident)
   self.assertEqual(store.hand_over(),{'handed_over':0,'taken_back':0,'outbox':0,'damaged':[]},'and the record stays, run after run')
   self.assertTrue((Path(folder.name+'/media')/(ident+'.png')).is_file())
   self.assertEqual(Store(folder.name+'/db2',folder.name+'/media2').hand_over()['outbox'],None,'without an outbox nothing leaves the portal')
  finally:folder.cleanup()
 def test_hand_over_is_a_hard_link_checked_before_its_facts_appear_and_never_a_silent_copy(self):
  # Review of 08.10.2026: a copy cut off at 1000 bytes got its facts published on the next run, with a hash that
  # could not match. Now there is no copy: a link or an error. And the facts wait for the file to be read back.
  import tempfile as t,os as o,contextlib as cl
  folder=t.TemporaryDirectory();outbox=Path(folder.name+'/outbox');store=Store(folder.name+'/db',folder.name+'/media')
  try:
   raw=self.png();ident=store.photo('armen',raw,'WORK')['id'];source=Path(folder.name+'/media')/(ident+'.png')
   outbox.mkdir();(outbox/(ident+'.png')).write_bytes(raw[:10])        # what a cut-off copy of an older version left
   store.outbox=outbox.resolve()
   self.assertEqual(store.hand_over(),{'handed_over':1,'taken_back':0,'outbox':1,'damaged':[]})
   self.assertTrue(o.path.samefile(source,outbox/(ident+'.png')),'one file under two names')
   meta=json.loads((outbox/(ident+'.json')).read_text(encoding='utf-8'))
   self.assertEqual((outbox/meta['file']).read_bytes(),raw);self.assertEqual(meta['sha256'],__import__('hashlib').sha256(raw).hexdigest())
   # the outbox on another file system: the link is refused; nothing is copied and nothing is published for the photo
   with patch('portal.os.link',side_effect=OSError(18,'Invalid cross-device link')):
    err=io.StringIO()
    with cl.redirect_stderr(err):saved=store.photo('armen',self.png2(),'WORK')
    self.assertEqual(saved['saved'],True,'the upload itself is kept')
    self.assertIn('NOT handed over',err.getvalue())
    with self.assertRaises(OSError):store.hand_over()
    with self.assertRaises(SystemExit):store.check_outbox()
   self.assertEqual(sorted(f.name for f in outbox.iterdir()),sorted([ident+'.json',ident+'.png']),'no file and no facts for the photo that could not be linked')
   store.check_outbox();self.assertEqual(store.hand_over()['handed_over'],1,'with the link possible again the next run hands it over')
   # the portal's own original damaged after upload: its facts are withdrawn, never published over wrong bytes
   third=store.photo('armen',self.png3(),'WORK')['id'];damaged=Path(folder.name+'/media')/(third+'.png')
   (outbox/(third+'.json')).unlink();o.chmod(damaged,0o600);damaged.write_bytes(b'not the photo')
   result=store.hand_over();self.assertEqual(result['damaged'],[third])
   self.assertFalse((outbox/(third+'.json')).exists());self.assertFalse((outbox/(third+'.png')).exists())
   self.assertFalse((outbox/(third+'.withdrawn')).exists(),'damaged is not taken back: no such record')
   # Review of a52d133, finding 4: a photo handed over EARLIER whose bytes change later. The run found the facts and
   # the same file and returned early, without reading it: damaged was [] and the facts stayed.
   o.chmod(source,0o600);source.write_bytes(b'changed after it was handed over')
   result=store.hand_over()
   self.assertIn(ident,result['damaged'])
   self.assertFalse((outbox/(ident+'.json')).exists(),'its facts are taken away');self.assertFalse((outbox/(ident+'.png')).exists())
   self.assertEqual(store.hand_over()['outbox'],1,'only the photo that is still whole is handed over')
  finally:folder.cleanup()
 def png2(self):
  out=io.BytesIO();Image.new('RGB',(21,20),'maroon').save(out,'PNG');return out.getvalue()
 def png3(self):
  out=io.BytesIO();Image.new('RGB',(22,20),'olive').save(out,'PNG');return out.getvalue()
 def test_the_test_accounts_answer_is_never_reported_as_armens_also_when_repeated(self):
  key=uuid.uuid4().hex;d=dict(question='inquiries',answer='YES',day=day())
  first=self.store.answer('test',key,d);self.assertEqual(first['trust'],'TEST_NOT_COUNTED')
  self.assertEqual(self.store.answer('test',key,d),first,'the repeat of the same request gives the same classification')
  self.assertEqual(self.store.answer('armen',uuid.uuid4().hex,d)['trust'],'ARMEN_REPORTED')
  self.assertEqual(self.store.state('test')['trust'],'TEST_NOT_COUNTED')
if __name__=='__main__':unittest.main()
