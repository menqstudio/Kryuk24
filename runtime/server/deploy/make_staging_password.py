"""Run as root on VPS. Never prints the password/hash or puts it in command arguments."""
import argparse,os,grp,subprocess
from pathlib import Path

def create(env,target):
 # systemd EnvironmentFile subset: KEY=value with optional matching outer quotes.
 values={}
 for line in Path(env).read_text(encoding='utf-8').splitlines():
  line=line.strip()
  if not line or line.startswith('#'):continue
  key,sep,value=line.partition('=')
  if sep:
   value=value.strip()
   if len(value)>=2 and value[0]==value[-1] and value[0] in "\"'":value=value[1:-1]
   values[key.strip()]=value
 password=values.get('KRYUK_OPERATOR_PASSWORD','')
 if len(password)<20 or '\n' in password or '\r' in password:raise ValueError('valid operator password required')
 result=subprocess.run(['openssl','passwd','-6','-stdin'],input=password+'\n',text=True,capture_output=True,check=True)
 digest=result.stdout.strip()
 if not digest.startswith('$6$') or '\n' in digest:raise ValueError('unexpected password hash format')
 group=grp.getgrnam('www-data').gr_gid
 descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640)
 try:
  with os.fdopen(descriptor,'w',encoding='ascii') as f:
   os.fchown(f.fileno(),0,group);os.fchmod(f.fileno(),0o640);f.write('gev:'+digest+'\n')
 except BaseException:
  Path(target).unlink(missing_ok=True)
  raise
 return 'Created staging gate file; verify Nginx while existing IP restriction remains.'
if __name__=='__main__':
 if os.geteuid()!=0:raise SystemExit('root required')
 p=argparse.ArgumentParser();p.add_argument('--env',default='/etc/kryuk24/capture.env');p.add_argument('--output',default='/etc/nginx/kryuk-staging.htpasswd');a=p.parse_args();print(create(a.env,a.output))
