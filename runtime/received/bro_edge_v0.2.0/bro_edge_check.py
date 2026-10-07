"""Trusted Windows acceptance helper. No AI, mutation payloads, redirects or secret logs."""
import argparse, base64, getpass, json, ssl
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def make_opener():
 return build_opener(ProxyHandler({}),HTTPSHandler(context=ssl.create_default_context()),NoRedirect())

def probe(opener,origin,user,password,path,method='GET'):
 auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
 # Never send a valid mutation body. Existing servers parse JSON before dispatch.
 data=b'INVALID_JSON' if method=='POST' else None
 req=Request(origin+path,data=data,method=method,headers={'Authorization':auth,'Content-Type':'application/json','Origin':origin})
 try:
  with opener.open(req,timeout=10) as response:return response.status
 except HTTPError as e:
  code=e.code; e.close();return code
 except Exception:return 'TRANSPORT_ERROR'

def checks(opener,origin,bro_user,bro_password,owner_password):
 results=[]
 def run(label,path,expected,user,password,method='GET'):
  code=probe(opener,origin,user,password,path,method)
  results.append({'check':label,'method':method,'path':path,'http':code,'expected':expected,'pass':code==expected})
 run('Bro positive control','/bro/v1/queue',200,bro_user,bro_password)
 run('Owner positive control','/operator/work',200,'gev',owner_password)
 if not all(r['pass'] for r in results):return results
 for path in ('/operator','/operator/work','/operator/work/report','/operator/report'):
  run('Bro denied owner read',path,401,bro_user,bro_password)
 for path in ('/operator/work/plan','/operator/work/approve','/operator/work/claim','/operator/work/observe','/operator/match','/operator/decision','/operator/call'):
  run('Bro denied owner write',path,401,bro_user,bro_password,'POST')
 run('Owner denied worker queue','/bro/v1/queue',401,'gev',owner_password)
 for path in ('/bro/v1/claim','/bro/v1/observe','/bro/v1/draft'):
  run('Owner denied worker write',path,401,'gev',owner_password,'POST')
 for path in ('/bro/v1/nope','/bro/v1/queue?x=1'):
  run('Authenticated Bro denied extra route',path,403,bro_user,bro_password)
 return results

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args()
 try:
  c=json.loads(Path(a.config).read_text(encoding='utf-8'))
  if set(c)!={'origin','username','password'} or any(not isinstance(v,str) or not v for v in c.values()):raise ValueError()
  u=urlsplit(c['origin'])
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment or c['username']!='bro-win':raise ValueError()
  origin=c['origin'].rstrip('/')
 except Exception:p.exit(2,'Invalid trusted-client config; content omitted.\n')
 password=getpass.getpass('Owner gev password (hidden; never saved): ')
 if not password:p.exit(2,'Owner password required for positive control.\n')
 try:result=checks(make_opener(),origin,c['username'],c['password'],password)
 except Exception:p.exit(2,'Check failed; credentials and responses omitted.\n')
 print(json.dumps({'checks':result,'verdict':'PASS' if all(r['pass'] for r in result) else 'NOT_ACCEPTED','response_bodies_read':False,'valid_mutation_payloads_sent':False},ensure_ascii=False,indent=2))
 raise SystemExit(0 if all(r['pass'] for r in result) else 1)
if __name__=='__main__':main()
