import json, os, subprocess, sys, unittest
from pathlib import Path
class FixtureEncodingTests(unittest.TestCase):
 def test_fixture_emits_utf8_even_with_cp1252_stdout_setting(self):
  script=Path(__file__).parent/'html_dom_fixture.py'
  result=subprocess.run([sys.executable,str(script)],env={**os.environ,'PYTHONIOENCODING':'cp1252'},capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
  text=result.stdout.decode('utf-8');self.assertEqual(json.loads(text)['tag'],'document');self.assertIn('Заберем',text)
