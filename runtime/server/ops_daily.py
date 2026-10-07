"""Daily planner plus actual local checks. No autonomous external browser executor."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from ops_work import Operations
from ops_local import run_local
from ops_views import dashboard

def run(db,directory,day=None,backup_directory=None):
 if not Path(db).is_file():raise ValueError('existing runtime DB required')
 ops=Operations(db);plan=ops.plan(day);checks=run_local(ops,plan['day'])
 folder=Path(directory);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
 path=folder/('operations-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.html')
 with path.open('x',encoding='utf-8') as f:f.write(dashboard(ops.report(plan['day']),False))
 path.chmod(0o600)
 full_backup=None
 if backup_directory:
  from ops_backup import backup
  folder_backup=Path(backup_directory);folder_backup.mkdir(parents=True,exist_ok=True,mode=0o700)
  full_backup=backup(db,folder_backup/('operations-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.tar.gz'))
 return {'full_backup':full_backup,'day':plan['day'],'added':plan['added'],'checks':checks,'report':str(path),'report_sent':False,'external_agent_connected':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--reports',required=True);p.add_argument('--backup-directory');a=p.parse_args()
 sys.stdout.buffer.write((json.dumps(run(a.db,a.reports,backup_directory=a.backup_directory),ensure_ascii=False)+'\n').encode('utf-8'))
