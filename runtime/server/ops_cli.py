"""Local administration. Only internal database/file writes and bounded loopback reads."""
import argparse,json,sys
from pathlib import Path
from ops_work import Operations
from ops_local import run_local
from ops_views import dashboard

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--media-root');sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('plan');a.add_argument('--day')
 a=sub.add_parser('report');a.add_argument('--day');a.add_argument('--html')
 a=sub.add_parser('run-local');a.add_argument('--day',required=True);a.add_argument('--port',type=int,default=8788)
 a=sub.add_parser('claim');a.add_argument('--task',required=True);a.add_argument('--worker',required=True)
 a=sub.add_parser('observe');a.add_argument('--task',required=True);a.add_argument('--worker',required=True);a.add_argument('--source',required=True);a.add_argument('--observed-at',required=True);a.add_argument('--summary-file',required=True);a.add_argument('--blocked',action='store_true')
 a=sub.add_parser('draft');a.add_argument('--task',required=True);a.add_argument('--worker',required=True);a.add_argument('--file',required=True)
 a=sub.add_parser('approve');a.add_argument('--task',required=True);a.add_argument('--digest',required=True);a.add_argument('--reference',required=True)
 a=sub.add_parser('revise');a.add_argument('--task',required=True);a.add_argument('--reason',required=True)
 a=sub.add_parser('result');a.add_argument('--task',required=True);a.add_argument('--digest',required=True);a.add_argument('--source',required=True);a.add_argument('--summary-file',required=True)
 a=sub.add_parser('media-original');a.add_argument('--file',required=True);a.add_argument('--provenance',required=True);a.add_argument('--permission',required=True)
 a=sub.add_parser('media-prepared');a.add_argument('--original',required=True);a.add_argument('--file',required=True);a.add_argument('--note',required=True);a.add_argument('--reviewed',action='store_true')
 args=p.parse_args()
 if not Path(args.db).is_file():p.error('existing runtime database required; do not silently create a new production database')
 ops=Operations(args.db,args.media_root)
 def filetext(path):
  if Path(path).stat().st_size>20000:raise ValueError('input file too large')
  return Path(path).read_text(encoding='utf-8')
 if args.command=='plan':result=ops.plan(args.day)
 elif args.command=='run-local':result=run_local(ops,args.day,args.port)
 elif args.command=='claim':result=ops.claim(args.task,args.worker)
 elif args.command=='observe':result=ops.observe(args.task,args.worker,args.source,args.observed_at,filetext(args.summary_file),args.blocked)
 elif args.command=='draft':result=ops.draft(args.task,args.worker,json.loads(filetext(args.file)))
 elif args.command=='approve':result=ops.approve(args.task,args.digest,'GEV',args.reference)
 elif args.command=='revise':result=ops.revise(args.task,args.reason)
 elif args.command=='result':result=ops.finish_approved(args.task,args.digest,args.source,filetext(args.summary_file))
 elif args.command=='media-original':result=ops.media.original(args.file,args.provenance,args.permission)
 elif args.command=='media-prepared':result=ops.media.prepared(args.original,args.file,args.note,args.reviewed)
 else:
  result=ops.report(args.day)
  if args.html:
   with Path(args.html).open('x',encoding='utf-8') as f:f.write(dashboard(result,interactive=False))
   result={'html':args.html,'sent':False,'external_agent_connected':False}
 sys.stdout.buffer.write((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
if __name__=='__main__':main()
