"""Create a private, non-overwriting SQLite snapshot. No automatic deletion policy."""
import argparse,os,sqlite3,uuid
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--directory',required=True);a=p.parse_args()
source_path=Path(a.db)
if not source_path.is_file():p.error('existing database required')
os.umask(0o077);folder=Path(a.directory);folder.mkdir(parents=True,exist_ok=True)
target=folder/('runtime-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]+'.sqlite')
with target.open('xb'):pass
source=sqlite3.connect(str(source_path));dest=sqlite3.connect(str(target))
try:
 source.backup(dest)
 if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('backup integrity failure')
finally:source.close();dest.close()
print('Backup integrity OK; restoration must be checked separately')
