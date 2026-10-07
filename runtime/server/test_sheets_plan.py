import csv,tempfile,unittest
from pathlib import Path
from sheets_plan import plan
HEADERS={'Website':['Request ID / Հայտի ID']+['x']*9,'WhatsApp':['Request ID / Հայտի ID']+['x']*6,'Phone':['Call ID / Գրառման ID']+['x']*7}
class PlanTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
  for n in HEADERS:(self.path/(n+'.csv')).write_text('',encoding='utf-8')
 def tearDown(self):self.tmp.cleanup()
 def write(self,rows):
  with (self.path/'Website.csv').open('w',newline='',encoding='utf-8') as f:csv.writer(f).writerows(rows)
 def test_new_then_unchanged_id(self):
  row=['ID']+['']*9;self.write([row]);a=plan(self.path,HEADERS_TO_ROWS());self.assertEqual(a['counts']['Website'],1)
  snap=HEADERS_TO_ROWS();snap['Website'].append(row);self.assertEqual(plan(self.path,snap)['requests'],[])
 def test_update_same_row_and_preserve_manual_orphan(self):
  row=['ID']+['new']*9;self.write([row]);snap=HEADERS_TO_ROWS();snap['Website']+=[['','manual'],['ID']+['old']*9];a=plan(self.path,snap);self.assertEqual(a['requests'][0]['updateCells']['range']['startRowIndex'],2)
 def test_duplicate_id_fails_closed(self):
  row=['ID']+['']*9;self.write([row,row])
  with self.assertRaises(ValueError):plan(self.path,HEADERS_TO_ROWS())
def HEADERS_TO_ROWS():return {k:[v] for k,v in HEADERS.items()}
if __name__=='__main__':unittest.main()
