import unittest
from unittest.mock import patch
import bro_edge_check as b
class Tests(unittest.TestCase):
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
