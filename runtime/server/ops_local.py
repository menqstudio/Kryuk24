"""Actual loopback/SQLite reads only. Never signs into or edits external accounts."""
import json, urllib.request, urllib.error
from datetime import date, datetime, timedelta
from runtime import Runtime, now

def run_local(ops,day,health_port=8788):
 if not isinstance(health_port,int) or not 1<=health_port<=65535:raise ValueError('port required')
 results=[]
 for task in ops.report(day)['tasks']:
  if task['kind']!='LOCAL_READ' or task['status'] not in ('PENDING','BLOCKED'):continue
  worker='LOCAL_READ_WORKER';ops.claim(task['id'],worker,30)
  try:
   if task['job']=='RUNTIME_HEALTH':
    source='loopback /health'
    with urllib.request.urlopen('http://127.0.0.1:'+str(health_port)+'/health',timeout=5) as response:
     raw=response.read(2049)
     if len(raw)>2048:raise ValueError('health response too large')
     data=json.loads(raw)
     if not isinstance(data,dict):raise ValueError('health object required')
     if data.get('ok') is not True or data.get('sending_enabled') is not False:raise ValueError('unexpected health response')
     summary=json.dumps({'http_status':response.status,'mode':data.get('mode'),'sending_enabled':data['sending_enabled'],'scope':'Process endpoint only; not public HTTPS, database writability or message delivery'},ensure_ascii=False)
   else:
    source='local SQLite / recorded ledger';target=(date.fromisoformat(day)-timedelta(days=1)).isoformat();report=ops.runtime.report()
    from contact_metrics import MOSCOW,daily_summary
    contacts=[x for x in report['contact_interactions'] if x['data'].get('test') is not True]
    orders=[x for x in report['orders'] if x['data'].get('test') is not True and datetime.fromisoformat(x['created']).astimezone(MOSCOW).date().isoformat()==target]
    counts=next((x for x in daily_summary(contacts) if x['date']==target),{'date':target,'call':0,'wa':0,'tg':0})
    calls=[x for x in report['call_jobs'] if x['data'].get('test') is not True and x['data']['date']==target]
    summary=json.dumps({'period':target,'timezone':'Europe/Moscow','recorded_contact_clicks':counts,'recorded_forms':len(orders),'operator_reported_phone_records':len(calls),'test_excluded':True,'meaning':'Recorded rows only; click is not a call/message. Tracking not live: zero is not zero actual demand. Revenue/profit UNKNOWN.'},ensure_ascii=False)
   ops.observe(task['id'],worker,source,now(),summary,machine=True);results.append({'id':task['id'],'status':'DONE'})
  except (ValueError,OSError,urllib.error.URLError) as error:
   ops.observe(task['id'],worker,'local read attempt',now(),type(error).__name__+': '+str(error),blocked=True,machine=True);results.append({'id':task['id'],'status':'BLOCKED'})
 return {'results':results,'browser_jobs_executed':False,'external_agent_connected':False}
