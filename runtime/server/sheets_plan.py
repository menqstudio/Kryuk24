"""Build an ID-based connector sync plan; no embedded Google credentials or network calls."""
import argparse,csv,json
from pathlib import Path
CONFIG=json.loads((Path(__file__).parent/'GOOGLE_SHEET.json').read_text(encoding='utf-8'))
WIDTHS={'Website':10,'WhatsApp':7,'Phone':8}

def plan(export_dir,snapshot):
 requests=[];counts={}
 for name,width in WIDTHS.items():
  live=snapshot.get(name)
  if not isinstance(live,list) or not live:raise ValueError('fresh header+rows snapshot required: '+name)
  # Snapshot must be collected from the exact known tab through connector reads.
  expected={'Website':'Request ID / Հայտի ID','WhatsApp':'Request ID / Հայտի ID','Phone':'Call ID / Գրառման ID'}[name]
  if not live[0] or live[0][0]!=expected or len(live[0])!=width:raise ValueError('unexpected headers: '+name)
  existing={};free=[]
  for index in range(1,1000):
   row=live[index] if index<len(live) else []
   if row and row[0]:
    if row[0] in existing:raise ValueError('duplicate existing ID: '+row[0])
    existing[row[0]]=index
   elif not any(row):free.append(index)
   # Never use a row which has manual data but no ID.
  with (Path(export_dir)/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:incoming=list(csv.reader(f))
  seen=set();updates=0
  for row in incoming:
   if len(row)!=width or not row[0] or row[0] in seen:raise ValueError('malformed or duplicate incoming row')
   seen.add(row[0]);idx=existing.get(row[0])
   if idx is None:
    if not free:raise ValueError('table capacity reached: '+name)
    idx=free.pop(0)
   old=(live[idx] if idx<len(live) else [])
   if row==old:continue
   # Exported/synchronized columns are Runtime-owned. Unknown/extra columns are not written.
   requests.append({'updateCells':{'range':{'sheetId':CONFIG['tabs'][name],'startRowIndex':idx,'endRowIndex':idx+1,'startColumnIndex':0,'endColumnIndex':width},'rows':[{'values':[{'userEnteredValue':{'stringValue':v}} for v in row]}],'fields':'userEnteredValue'}});updates+=1
  counts[name]=updates
 return {'spreadsheet_id':CONFIG['spreadsheet_id'],'requests':requests,'counts':counts,'execution':'CONNECTED_SESSION_ONLY','snapshot_required':'Re-read current target cells immediately before applying; do not reuse stale plans.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--export',required=True);p.add_argument('--snapshot',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 result=plan(a.export,json.loads(Path(a.snapshot).read_text(encoding='utf-8')))
 with Path(a.output).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps(result['counts']))
