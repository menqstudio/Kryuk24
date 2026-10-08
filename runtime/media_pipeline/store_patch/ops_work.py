"""Durable internal work queue. No external publishing, messaging, payments or browser agent."""
import contextlib, hashlib, html, json, re, uuid
from datetime import date, datetime, timedelta, timezone
from runtime import Runtime, encode, now
from ops_media import MediaStore
from pathlib import Path
YEREVAN=timezone(timedelta(hours=4))
JOBS=[('LOCAL_LEDGER','Մատյանի ամփոփում / Ledger summary','LOCAL_READ'),('RUNTIME_HEALTH','Runtime վիճակ / Runtime health','LOCAL_READ'),('YANDEX_BUSINESS','Քարտ, կարծիքներ, մոդերացիա / Business card','BROWSER_READ'),('YANDEX_DIRECT','Գովազդի վիճակ և ծախս / Direct state and spend','BROWSER_READ'),('METRICA','Նպատակների թվեր / Goal counts','API_READ'),('WEBMASTER','Ինդեքսավորում / Indexing','API_READ'),('AVITO','Հայտարարությունների վիճակ / Listing state','BROWSER_READ'),('HOSTING_DEADLINES','Վճար և ժամկետներ / Balance and deadlines','API_READ'),('MEDIA_INBOX','Նոր իրական նկարներ / New media','PREPARE'),('DAILY_REPORT','Օրվա հաշվետվության պատրաստում / Daily report','PREPARE')]

def text(value,label,limit=4000):
 if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError(label+' required')
 return value.strip()
def timestamp(value):
 parsed=datetime.fromisoformat(value)
 if parsed.tzinfo is None:raise ValueError('timestamp must include timezone')
 return parsed.isoformat()
class Operations:
 def __init__(self,path,media_root=None):
  self.runtime=Runtime(str(path));self.media=MediaStore(path,media_root or Path(path).parent/'media')
  with self.runtime.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS ops_tasks(id TEXT PRIMARY KEY,day TEXT,job TEXT,title TEXT,kind TEXT,owner TEXT,status TEXT,revision INTEGER,worker TEXT,lease_until TEXT,draft TEXT,digest TEXT,created TEXT,UNIQUE(day,job));
CREATE TABLE IF NOT EXISTS ops_observations(id TEXT PRIMARY KEY,task_id TEXT,source TEXT,observed_at TEXT,summary TEXT,trust TEXT,actor TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS ops_approvals(id TEXT PRIMARY KEY,task_id TEXT,digest TEXT,actor TEXT,reference TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS ops_events(id INTEGER PRIMARY KEY,task_id TEXT,kind TEXT,data TEXT,created TEXT);
''')
 def event(self,c,task,kind,data):c.execute('INSERT INTO ops_events(task_id,kind,data,created) VALUES(?,?,?,?)',(task,kind,encode(data),now()))
 def plan(self,day=None):
  day=day or datetime.now(YEREVAN).date().isoformat();date.fromisoformat(day);added=0
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE')
   for job,title,kind in JOBS:
    task='WORK-'+uuid.uuid5(uuid.NAMESPACE_URL,'KRYUK24:'+day+':'+job).hex
    if c.execute('SELECT id FROM ops_tasks WHERE day=? AND job=?',(day,job)).fetchone():continue
    c.execute('INSERT INTO ops_tasks VALUES(?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?)',(task,day,job,title,kind,'GEV','PENDING',now()));self.event(c,task,'PLANNED',{'job':job,'day':day});added+=1
  return {'day':day,'added':added,'external_execution':False}
 def get(self,task):
  with self.runtime.db() as c:
   row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
   if not row:raise LookupError('task not found')
   result=dict(row)
   if result['draft']:result['draft']=json.loads(result['draft'])
   return result
 def claim(self,task,worker,seconds=600):
  worker=text(worker,'worker',100)
  if not isinstance(seconds,int) or not 30<=seconds<=1800:raise ValueError('lease30..1800seconds required')
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
   if not row:raise LookupError('task not found')
   expired=row['status']=='CLAIMED' and datetime.fromisoformat(row['lease_until'])<=datetime.now(timezone.utc)
   if row['status'] not in ('PENDING','BLOCKED') and not expired:raise ValueError('task not claimable')
   until=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
   c.execute("UPDATE ops_tasks SET status='CLAIMED',worker=?,lease_until=?,revision=revision+1 WHERE id=?",(worker,until,task));self.event(c,task,'CLAIMED',{'worker':worker,'expires':until,'expired_read_or_prepare_lease':expired})
  return self.get(task)
 def owned(self,c,task,worker):
  row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
  if not row:raise LookupError('task not found')
  if row['status']!='CLAIMED' or row['worker']!=worker or datetime.fromisoformat(row['lease_until'])<=datetime.now(timezone.utc):raise ValueError('active owned lease required')
  return row
 def observe(self,task,worker,source,observed_at,summary,blocked=False,machine=False):
  source=text(source,'source',500);summary=text(summary,'summary');observed_at=timestamp(observed_at)
  trust='MACHINE_OBSERVED' if machine else 'OPERATOR_REPORTED'
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');row=self.owned(c,task,worker)
   if machine and row['kind'] not in ('LOCAL_READ','API_READ'):raise ValueError('machine evidence only for local and API reads')
   c.execute('INSERT INTO ops_observations VALUES(?,?,?,?,?,?,?,?)',('OBS-'+uuid.uuid4().hex,task,source,observed_at,summary,trust,worker,now()))
   status='BLOCKED' if blocked else 'DONE'
   c.execute('UPDATE ops_tasks SET status=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?',(status,task));self.event(c,task,status,{'source':source,'trust':trust})
  return self.get(task)
 def draft(self,task,worker,data):
  if not isinstance(data,dict) or set(data)-{'action','account','destination','body','assets','reason'}:raise ValueError('invalid draft fields')
  if data.get('action') not in ('REPORT_DRAFT','PHOTO_BATCH','PUBLICATION','MESSAGE','AD_CHANGE'):raise ValueError('draft action required')
  for key in ('account','destination','body','reason'):text(data.get(key),key,10000 if key=='body' else 1000)
  assets=data.get('assets',[])
  if not isinstance(assets,list) or any(not isinstance(a,dict) or set(a)!={'id','sha256'} or not re.fullmatch(r'ASSET-[a-f0-9]{32}',a.get('id','')) or not re.fullmatch(r'[a-f0-9]{64}',a.get('sha256','')) for a in assets):raise ValueError('assets need exact id/sha256')
  normalized={**data,'assets':assets};raw=encode(normalized);digest=hashlib.sha256(raw.encode()).hexdigest()
  # The assets are checked and the draft that names them is written as one step, under the media store's lock: nothing
  # removes an asset between the two. From the moment the draft exists, the clean-up and the rollback keep what it names.
  with (self.media.lock() if assets else contextlib.nullcontext()):
   for asset in assets:self.media.verify(asset['id'],asset['sha256'])
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');self.owned(c,task,worker)
    c.execute("UPDATE ops_tasks SET status='READY_REVIEW',draft=?,digest=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?",(raw,digest,task));self.event(c,task,'DRAFT_READY',{'digest':digest,'external_execution':False})
  return self.get(task)
 def approve(self,task,digest,actor,reference):
  if actor!='GEV':raise ValueError('only GEV can approve')
  reference=text(reference,'explicit approval reference',1000)
  draft=self.get(task)['draft']
  if draft:
   for asset in draft.get('assets',[]):self.media.verify(asset['id'],asset['sha256'])
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
   if not row or row['status']!='READY_REVIEW' or row['digest']!=digest:raise ValueError('current draft digest required')
   c.execute('INSERT INTO ops_approvals VALUES(?,?,?,?,?,?)',('APPROVAL-'+uuid.uuid4().hex,task,digest,actor,reference,now()))
   c.execute("UPDATE ops_tasks SET status='APPROVED',revision=revision+1 WHERE id=?",(task,));self.event(c,task,'APPROVED',{'digest':digest,'actor':actor,'reference':reference,'external_execution':False})
  return self.get(task)
 def revise(self,task,reference):
  reference=text(reference,'revision reason',1000)
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
   if not row or row['status'] not in ('READY_REVIEW','APPROVED'):raise ValueError('review draft required')
   c.execute("UPDATE ops_tasks SET status='PENDING',draft=NULL,digest=NULL,revision=revision+1 WHERE id=?",(task,));self.event(c,task,'REVISION_REQUESTED',{'reason':reference,'previous_digest':row['digest']})
  return self.get(task)
 def finish_approved(self,task,digest,source,summary):
  source=text(source,'result source',500);summary=text(summary,'result evidence')
  draft=self.get(task)['draft']
  if draft:
   for asset in draft.get('assets',[]):self.media.verify(asset['id'],asset['sha256'])
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM ops_tasks WHERE id=?',(task,)).fetchone()
   if not row or row['status']!='APPROVED' or row['digest']!=digest:raise ValueError('matching approved draft required')
   c.execute('INSERT INTO ops_observations VALUES(?,?,?,?,?,?,?,?)',('OBS-'+uuid.uuid4().hex,task,source,now(),summary,'OPERATOR_REPORTED','GEV',now()))
   c.execute("UPDATE ops_tasks SET status='DONE',revision=revision+1 WHERE id=?",(task,));self.event(c,task,'RESULT_RECORDED',{'digest':digest,'source':source,'trust':'OPERATOR_REPORTED','external_execution_by_runtime':False})
  return self.get(task)
 def report(self,day=None):
  with self.runtime.db() as c:
   if day:date.fromisoformat(day);tasks=[dict(r) for r in c.execute('SELECT * FROM ops_tasks WHERE day=? ORDER BY rowid',(day,))]
   else:tasks=[dict(r) for r in c.execute('SELECT * FROM ops_tasks ORDER BY day DESC,rowid')]
   for row in tasks:
    row['draft']=json.loads(row['draft']) if row['draft'] else None
    row['observations']=[dict(o) for o in c.execute('SELECT * FROM ops_observations WHERE task_id=? ORDER BY created',(row['id'],))]
    row['lease_expired']=row['status']=='CLAIMED' and datetime.fromisoformat(row['lease_until'])<=datetime.now(timezone.utc)
  counts={s:sum(t['status']==s for t in tasks) for s in ('PENDING','CLAIMED','BLOCKED','READY_REVIEW','APPROVED','DONE')}
  return {'media':self.media.report(),'tasks':tasks,'counts':counts,'generated':now(),'external_agent_connected':False,'publishing_enabled':False,'messaging_enabled':False}
