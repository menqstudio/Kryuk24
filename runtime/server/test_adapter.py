import unittest, tempfile, threading, urllib.request, urllib.error, json, re
from demo_server import server
class AdapterTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=server(self.tmp.name+'/test.sqlite',0);threading.Thread(target=self.s.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.s.server_port)
  html=urllib.request.urlopen(self.base).read().decode();self.nonce=re.search(r'window.KRYUK_TEST_NONCE="([^"]+)"',html)[1]
 def tearDown(self):self.s.shutdown();self.s.server_close();self.tmp.cleanup()
 def post(self,data,key='one',nonce=True):
  headers={'Content-Type':'application/json','Idempotency-Key':key,'Origin':self.base}
  if nonce:headers['X-Test-Nonce']=self.nonce
  return json.load(urllib.request.urlopen(urllib.request.Request(self.base+'/test-intake',data=json.dumps(data).encode(),headers=headers)))
 def test_capture_retry_and_no_send(self):
  data=dict(contact='TEST',pickup='TEST A',destination='TEST B',vehicle='car',estimate_display='от 4000 ₽')
  a=self.post(data);b=self.post(data);self.assertEqual(a['id'],b['id']);self.assertEqual(a['notification_status'],'NOT_SENT')
  r=json.load(urllib.request.urlopen(self.base+'/test-report'));self.assertEqual(len(r['orders']),1);self.assertTrue(r['orders'][0]['data']['test']);self.assertEqual(r['messages'],[])
 def test_untrusted_request_rejected(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post({},nonce=False)
  self.assertEqual(e.exception.code,403)
 def test_missing_fields_and_spoof_rejected(self):
  for d in ({},{'test':False}):
   with self.assertRaises(urllib.error.HTTPError) as e:self.post(d)
   self.assertEqual(e.exception.code,400)
 def test_site_is_injected_without_source_change(self):
  r=urllib.request.urlopen(self.base);self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy']);self.assertIn(b'/test-intake.js',r.read())
 def test_local_dispatch_endpoint(self):
  order=self.post(dict(contact='TEST',pickup='A',destination='B',vehicle='car'))
  req=urllib.request.Request(self.base+'/test-dispatch-decision',data=json.dumps({'order_id':order['id'],'decision':'ACCEPTED'}).encode(),headers={'Content-Type':'application/json','X-Test-Nonce':self.nonce,'Origin':self.base})
  decision=json.load(urllib.request.urlopen(req));self.assertEqual(decision['trust_level'],'TEST_ONLY')
  report=json.load(urllib.request.urlopen(self.base+'/test-report'));self.assertEqual(report['orders'][0]['status'],'NEW');self.assertEqual(report['notifications'][0]['status'],'BLOCKED_NO_CONNECTOR')
 def test_readable_journal(self):
  raw=urllib.request.urlopen(self.base+'/test-orders').read().decode('utf-8');self.assertIn('Тест: принять',raw);self.assertIn('window.KRYUK_TEST_NONCE=',raw)
if __name__=='__main__':unittest.main()
