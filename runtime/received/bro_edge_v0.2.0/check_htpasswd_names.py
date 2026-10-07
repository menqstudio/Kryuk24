"""Run privately on VPS. Outputs identity membership only, never hashes or file lines."""
import argparse,json
from pathlib import Path

def names(path):
 rows=Path(path).read_text(encoding='utf-8').splitlines()
 users=[]
 for row in rows:
  if not row or row.startswith('#'):continue
  user,sep,_=row.partition(':')
  if not sep or not user:raise ValueError()
  users.append(user)
 return users
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--worker-file',required=True);p.add_argument('--owner-file',required=True);a=p.parse_args()
 try:
  workers=names(a.worker_file);owners=names(a.owner_file)
  result={'worker_exactly_one_bro_win':workers==['bro-win'],'owner_excludes_bro_win':'bro-win' not in owners,'owner_contains_gev':'gev' in owners}
  print(json.dumps(result));raise SystemExit(0 if all(result.values()) else 1)
 except (OSError,ValueError):p.exit(2,'Cannot verify password-file membership; contents omitted.\n')
