import base64,io,json,re,tempfile,threading,unittest,urllib.request,urllib.error,uuid
from pathlib import Path
from PIL import Image
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
  with patch('portal.authenticate',wraps=portal.authenticate) as verify:
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

if __name__=='__main__':unittest.main()
