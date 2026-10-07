"""Read-only preservation evidence; optionally consistent SQLite backup."""
import argparse, hashlib, json, re, sqlite3
from pathlib import Path

def snapshot(db,views,backup=None):
 path=Path(db).resolve()
 c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=10)
 try:
  if backup:
   destination=Path(backup)
   with destination.open('xb'):pass
   target=sqlite3.connect(destination)
   try:c.backup(target)
   finally:target.close()
  c.execute('BEGIN'); result={}
  for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
   if name.startswith('bro_') or name.startswith('sqlite_'):continue
   if not re.fullmatch(r'[A-Za-z0-9_]+',name):raise ValueError('unexpected table name')
   rows=c.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall()
   raw=json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()
   result[name]={'count':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}
  return {'tables':result,'ops_views_sha256':hashlib.sha256(Path(views).read_bytes()).hexdigest()}
 finally:c.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--views',required=True);p.add_argument('--backup');a=p.parse_args()
 print(json.dumps(snapshot(a.db,a.views,a.backup),sort_keys=True,indent=2))
