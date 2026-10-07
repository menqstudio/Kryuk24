import base64,json,tempfile,threading,unittest,urllib.request,urllib.error
from secure_server import server
class SecureTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.origins=set(['https://kryuk24.ru']);self.s=server(self.tmp.name+'/db','T'*32,self.origins,0);self.base='http://127.0.0.1:'+str(self.s.server_port);self.origins.add(self.base);threading.Thread(target=self.s.serve_forever,daemon=True).start();self.data=dict(request_id='K24-'+'a'*32,contact='NOT_PROVIDED',pickup='A',destination='B',vehicle='car',message='TEST',estimate_display='от 4000 ₽',channel='wa',form_kind='CALCULATOR')
 def tearDown(self):self.s.shutdown();self.s.server_close();self.tmp.cleanup()
 def request(self,path,data=None,auth=False,origin=None):
  headers={'Origin':origin or self.base,'Content-Type':'application/json','Idempotency-Key':self.data['request_id']}
  if auth:headers['Authorization']='Basic '+base64.b64encode(b'gev:'+b'T'*32).decode()
  return urllib.request.urlopen(urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers=headers))
 def test_private_journal_and_report(self):
  for path in ('/operator','/operator/report'):
   with self.assertRaises(urllib.error.HTTPError) as e:self.request(path)
   self.assertEqual(e.exception.code,401)
  self.assertIn('Тестовый журнал',self.request('/operator',auth=True).read().decode())
 def test_capture_is_test_and_has_no_receipt(self):
  a=json.load(self.request('/capture',self.data));b=json.load(self.request('/capture',self.data));self.assertEqual(a,b);self.assertTrue(a['test']);self.assertEqual(a['message_receipt'],'UNVERIFIED');r=json.load(self.request('/operator/report',auth=True));self.assertEqual(len(r['orders']),1);self.assertEqual(r['notifications'],[])
 def test_untrusted_origin_rejected(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/capture',self.data,origin='https://evil.example')
  self.assertEqual(e.exception.code,403)
 def test_client_cannot_spoof_live(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/capture',dict(self.data,test=False))
  self.assertEqual(e.exception.code,400)
 def test_match_requires_operator(self):
  self.request('/capture',self.data).close();d=dict(order_id=self.data['request_id'],external_ref='TEST-reference',evidence='Observed '+self.data['request_id'])
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/operator/match',d)
  self.assertEqual(e.exception.code,401);self.assertEqual(json.load(self.request('/operator/match',d,auth=True))['order_id'],self.data['request_id'])
 def test_staging_pages_require_auth_and_use_capture(self):
  for path in ('/operator/staging','/operator/staging-preview','/operator/staging-handoff.js'):
   with self.assertRaises(urllib.error.HTTPError) as e:self.request(path)
   self.assertEqual(e.exception.code,401)
   self.assertEqual(self.request(path,auth=True).status,200)
  page=self.request('/operator/staging',auth=True).read().decode()
  self.assertIn("endpoint:'/capture'",page);self.assertIn("mode:'LOCAL_PREVIEW'",page)
  script=self.request('/operator/staging-handoff.js',auth=True).read().decode()
  self.assertIn('/operator/staging-preview',script)
 def test_staging_preview_query_keeps_auth_and_returns_html(self):
  self.request('/capture',self.data).close()
  path='/operator/staging-preview?id='+self.data['request_id']
  with self.assertRaises(urllib.error.HTTPError) as e:self.request(path)
  self.assertEqual(e.exception.code,401)
  with self.request(path,auth=True) as response:
   self.assertEqual(response.status,200)
   self.assertIn('text/html',response.headers['Content-Type'])
   content=response.read().decode('utf-8')
  self.assertIn('/operator/report',content)
  self.assertIn("searchParams.get('id')",content)
  report=json.load(self.request('/operator/report',auth=True))
  self.assertEqual(len(report['orders']),1)
  self.assertEqual(report['orders'][0]['id'],self.data['request_id'])
 def test_contact_endpoint_beacon_shape_and_guards(self):
  from test_contact_metrics import metadata
  body={'event_id':'CLICK-'+'d'*32,'metadata':metadata()}
  for origin,extra in [('https://evil.example',False),(self.base,True)]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.request('/contact-click',dict(body,phone='PRIVATE') if extra else body,origin=origin)
   self.assertEqual(e.exception.code,400 if extra else 403)
  with self.request('/contact-click',body) as response:self.assertEqual(response.status,201)
  with self.request('/contact-click',body) as response:self.assertEqual(response.status,200)
  report=json.load(self.request('/operator/report',auth=True));self.assertEqual(len(report['contact_interactions']),1);self.assertEqual(report['orders'],[])
 def test_contact_options_and_size_limit(self):
  req=urllib.request.Request(self.base+'/contact-click',method='OPTIONS',headers={'Origin':self.base})
  with urllib.request.urlopen(req) as response:self.assertEqual(response.status,204)
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/contact-click',{'padding':'x'*9000})
  self.assertEqual(e.exception.code,400)
 def test_contact_rate_limit_is_shared_with_capture(self):
  from test_contact_metrics import metadata
  body={'event_id':'CLICK-'+'e'*32,'metadata':metadata()}
  for _ in range(120):self.request('/contact-click',body).close()
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/capture',self.data)
  self.assertEqual(e.exception.code,429)
 def test_full_site_preview_authenticated_and_no_external_network(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/operator/site/')
  self.assertEqual(e.exception.code,401)
  for page in ('','evakuator-balashikha/','evakuator-domodedovo/','evakuator-khimki/','evakuator-lyubertsy/','evakuator-podolsk/','manipulyator/','perevozka-spetstekhniki/'):
   with self.request('/operator/site/'+page,auth=True) as response:
    self.assertEqual(response.status,200);content=response.read().decode()
    self.assertIn("mode:'STAGING'",content);self.assertIn('/operator/contact-clicks.js',content)
    self.assertIn("connect-src 'self'",response.headers['Content-Security-Policy'])
  with self.request('/operator/site/assets/mark-orange.svg?v=18',auth=True) as response:self.assertEqual(response.status,200)
  for path in ('../runtime.py','.htaccess','README.md','%2e%2e/runtime.py'):
   with self.assertRaises(urllib.error.HTTPError) as e:self.request('/operator/site/'+path,auth=True)
   self.assertEqual(e.exception.code,404)
 def test_public_report_not_exposed(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/test-report')
  self.assertEqual(e.exception.code,404)
if __name__=='__main__':unittest.main()
