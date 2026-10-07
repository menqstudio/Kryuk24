"""Trusted interactive provisioning; no secrets on argv/stdout or in environment."""
import argparse, getpass, hashlib, json, os, re
from pathlib import Path

def write_new(path,data):
 with open(path,'x',encoding='utf-8') as f:
  os.chmod(path,0o600); json.dump(data,f); f.write('\n')

def main():
 p=argparse.ArgumentParser(); p.add_argument('mode',choices=['server','client']); p.add_argument('--output',required=True); p.add_argument('--username',default='bro-win'); p.add_argument('--origin'); a=p.parse_args()
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',a.username):p.error('invalid username')
 pw=getpass.getpass('Dedicated random Bro password (32+ chars): ')
 if len(pw)<32 or ':' in pw or '\n' in pw:p.error('32+ character random password required')
 if a.mode=='server':data={'username':a.username,'password_sha256':hashlib.sha256(pw.encode()).hexdigest()}
 else:
  from bro_pull import Transport
  Transport(a.origin,a.username,pw); data={'origin':a.origin,'username':a.username,'password':pw}
 write_new(Path(a.output),data); print('Created credential file. Restrict OS access before use.')
if __name__=='__main__':main()
