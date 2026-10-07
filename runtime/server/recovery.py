"""Validate and restore a SQLite snapshot to a NEW path; never replace a running DB."""
import argparse, os, sqlite3
from pathlib import Path

def restore(source, target):
 source, target = Path(source), Path(target)
 if not source.is_file(): raise ValueError('snapshot does not exist')
 if target.exists(): raise ValueError('destination already exists; choose a new path')
 src = sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)
 try:
  if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('snapshot integrity failed')
  tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if not {'orders','events','call_jobs','matches'}.issubset(tables): raise ValueError('not a KRYUK24 snapshot')
  with target.open('xb'): pass
  os.chmod(target, 0o600)
  dst=sqlite3.connect(target)
  try:
   src.backup(dst)
   if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('restored integrity failed')
  finally: dst.close()
 finally: src.close()
 return str(target)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 print(restore(a.snapshot,a.output));print('Validated new copy only. Running service was not changed.')
