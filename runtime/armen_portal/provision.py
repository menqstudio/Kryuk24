"""Interactive local provisioning. Never prints passwords or puts them in argv."""
import argparse,getpass,json,os
from pathlib import Path
from portal import credential
p=argparse.ArgumentParser();p.add_argument('--credentials',required=True);p.add_argument('--user',choices=['armen','gev'],required=True);a=p.parse_args()
os.umask(0o077);target=Path(a.credentials)
if target.is_symlink():raise SystemExit('symlink not allowed')
users=json.loads(target.read_text()) if target.exists() else {}
password=getpass.getpass('New password (8+ characters): ')
if password!=getpass.getpass('Repeat password: '):raise SystemExit('Passwords differ')
users[a.user]=credential(password)
tmp=target.with_name(target.name+'.new')
with tmp.open('x') as f:json.dump(users,f);f.write('\n')
os.chmod(tmp,0o600);os.replace(tmp,target)
print('Credential record saved. Restart portal after provisioning or password rotation.')
