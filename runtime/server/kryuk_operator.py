"""Local operator commands. No outbound communication."""
import argparse,json,sqlite3,csv
from pathlib import Path
from runtime import Runtime
p=argparse.ArgumentParser();p.add_argument('--db',required=True);sub=p.add_subparsers(dest='command',required=True)
a=sub.add_parser('match');a.add_argument('--id',required=True);a.add_argument('--reference',required=True);a.add_argument('--evidence',required=True);a.add_argument('--actor',required=True)
a=sub.add_parser('call');a.add_argument('--date',required=True);a.add_argument('--outcome',required=True);a.add_argument('--amount',type=float);a.add_argument('--evidence',required=True);a.add_argument('--actor',required=True);a.add_argument('--key',required=True)
a=sub.add_parser('backup');a.add_argument('--output',required=True)
a=sub.add_parser('summary')
a=sub.add_parser('sheets-export');a.add_argument('--output',required=True)
args=p.parse_args()
if not Path(args.db).is_file():p.error('existing database required')
r=Runtime(args.db)
if args.command=='match':result=r.match_whatsapp(args.id,args.reference,args.evidence,args.actor)
elif args.command=='call':result=r.record_call(dict(date=args.date,outcome=args.outcome,amount=args.amount,evidence=args.evidence,actor=args.actor,source='PHONE'),args.key)
elif args.command=='backup':
 target=Path(args.output)
 if target.exists():p.error('backup output already exists; choose a new path')
 # Reserve a new file, then use SQLite backup API so WAL contents are included.
 with target.open('xb'):pass
 source=sqlite3.connect(args.db);dest=sqlite3.connect(str(target))
 try:
  source.backup(dest)
  if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('backup integrity failed')
 finally:source.close();dest.close()
 result={'backup':str(target),'integrity':'ok','restore_test':'NOT_PERFORMED'}
elif args.command=='sheets-export':
 target=Path(args.output)
 if target.exists():p.error('choose a new export directory')
 target.mkdir(parents=True);report=r.report();by_id={o['id']:o for o in report['orders']};matched={m['order_id'] for m in report['whatsapp_matches']}
 names={'car':'Автомобиль','moto':'Мотоцикл','commercial':'Коммерческий транспорт','special':'Спецтехника'}
 website=[[o['id'],o['created'],o['data'].get('form_kind',''),o['data'].get('channel',''),o['data']['pickup'],o['data']['destination'],names.get(o['data']['vehicle'],o['data']['vehicle']),o['data'].get('estimate_display',''),'TRUE' if o['data'].get('test') is True else 'FALSE','OPERATOR_OBSERVED' if o['id'] in matched else 'UNVERIFIED'] for o in report['orders']]
 matches=[[m['order_id'],m['external_ref'],m['evidence'],m['actor'],m['created'],'TEST_ONLY' if by_id[m['order_id']]['data'].get('test') is True else 'OPERATOR_OBSERVED','TRUE' if by_id[m['order_id']]['data'].get('test') is True else 'FALSE'] for m in report['whatsapp_matches']]
 calls=[[c['id'],c['data']['date'],c['data']['outcome'],c['data'].get('amount') if c['data'].get('amount') is not None else '',c['data']['evidence'],c['data']['actor'],'OPERATOR_REPORTED','TRUE' if c['data'].get('test') is True else 'FALSE'] for c in report['call_jobs']]
 for name,rows in [('Website',website),('WhatsApp',matches),('Phone',calls)]:
  with (target/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.writer(f)
   for row in rows:writer.writerow([("'"+v if v.lstrip().startswith(('=','+','-','@')) else v) if isinstance(v,str) else v for v in row])
 result={'export_directory':str(target),'website_rows':len(website),'match_rows':len(matches),'phone_rows':len(calls),'automated_sync':False,'instructions':'Snapshot CSVs without headers: update corresponding Sheet from A2; do NOT repeatedly append snapshots. Preserve manual-only data separately.'}
else:
 report=r.report();website=[x for x in report['orders'] if x['data'].get('test') is not True];calls=[x for x in report['call_jobs'] if x['data'].get('test') is not True];ids={x['id'] for x in website}
 result={'website_captured_forms':len(website),'website_message_observations':sum(x['order_id'] in ids for x in report['whatsapp_matches']),'phone_records':len(calls),'phone_completed_reported':sum(x['data']['outcome']=='COMPLETED' for x in calls),'test_records_excluded':True,'orders_profit':'UNKNOWN','note':'Captured forms are not received messages; phone outcomes are operator-reported. No website attribution for phone records.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
