import unittest
from unittest.mock import patch
import bro_edge_check as b
class Tests(unittest.TestCase):
 def test_bro_only_no_owner_control(self):
  with patch.object(b,'probe',side_effect=[200]+[401]*11+[403]*2) as m:
   r=b.checks(None,'https://example.invalid','bro-win','secret',bro_only=True)
  self.assertEqual(len(r),14);self.assertTrue(all(x['pass'] for x in r))
  self.assertTrue(all(call.args[2]=='bro-win' for call in m.call_args_list))
 def test_pacing_applied_to_every_request(self):
  pauses=[]
  with patch.object(b,'probe',side_effect=[200]+[401]*11+[403]*2):
   b.checks(None,'https://example.invalid','bro-win','secret',bro_only=True,pace=lambda:pauses.append(1))
  self.assertEqual(len(pauses),14)
 def test_bro_wrong_password_stops(self):
  with patch.object(b,'probe',return_value=401):
   r=b.checks(None,'https://example.invalid','bro-win','wrong',bro_only=True)
  self.assertEqual(len(r),1);self.assertFalse(r[0]['pass'])
 def test_cli_bro_only_never_prompts(self):
  import tempfile,json,sys
  from pathlib import Path
  with tempfile.TemporaryDirectory() as root:
   c=Path(root)/'config.json';c.write_text(json.dumps({'origin':'https://example.invalid','username':'bro-win','password':'test-only'}))
   with patch.object(sys,'argv',['script','--config',str(c),'--bro-only']),patch.object(b.getpass,'getpass',side_effect=AssertionError('must not prompt')),patch.object(b,'make_opener'),patch.object(b,'checks',return_value=[{'pass':True}]),patch('builtins.print'):
    with self.assertRaises(SystemExit) as e:b.main()
    self.assertEqual(e.exception.code,0)
 def test_pass_matrix(self):
  codes=[200,200]+[401]*15+[403]*2
  with patch.object(b,'probe',side_effect=codes):r=b.checks(None,'https://example.invalid','bro-win','secret','owner')
  self.assertEqual(len(r),19);self.assertTrue(all(x['pass'] for x in r))
 def test_wrong_owner_stops_after_controls(self):
  with patch.object(b,'probe',side_effect=[200,401]):r=b.checks(None,'https://example.invalid','bro-win','secret','wrong')
  self.assertEqual(len(r),2);self.assertFalse(all(x['pass'] for x in r))
 def test_403_is_not_auth_isolation_proof(self):
  with patch.object(b,'probe',side_effect=[200,200]+[403]*17):r=b.checks(None,'https://example.invalid','bro-win','secret','owner')
  self.assertFalse(all(x['pass'] for x in r))
 def test_no_valid_json_mutation(self):
  class Response:
   status=401
   def __enter__(self):return self
   def __exit__(self,*a):pass
  class Opener:
   def open(self,req,timeout):
    self.req=req;return Response()
  o=Opener();b.probe(o,'https://example.invalid','bro','secret','/operator/work/plan','POST')
  self.assertEqual(o.req.data,b'INVALID_JSON')
if __name__=='__main__':unittest.main()
