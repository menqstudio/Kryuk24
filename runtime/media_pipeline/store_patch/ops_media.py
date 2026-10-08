"""Private original/prepared media manifests. Does not edit or publish images."""
import hashlib, os, threading, time, uuid
from pathlib import Path
from runtime import Runtime, now
MAX_BYTES=20*1024*1024
class StoreLock:
 """One writer in the media store at a time, across processes. An OS lock on <media root>/.pipeline.lock; the system
 releases it when a process dies. Re-entrant for the thread that holds it (the pipeline calls the store while it
 holds the lock)."""
 held={};guard=threading.Lock()
 def __init__(self,media_root,wait=30.0):
  self.path=Path(media_root).resolve()/'.pipeline.lock';self.wait=wait;self.key=str(self.path)
 def __enter__(self):
  me=threading.get_ident()
  with StoreLock.guard:
   mine=StoreLock.held.get(self.key)
   if mine and mine[0]==me:mine[1]+=1;return self
  self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  f=open(self.path,'a+b');deadline=time.monotonic()+self.wait
  while True:
   try:
    if os.name=='nt':
     import msvcrt;f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    else:
     import fcntl;fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    break
   except OSError:
    if time.monotonic()>=deadline:
     f.close();raise TimeoutError('another operation holds the media store lock; nothing was changed') from None
    time.sleep(0.05)
  with StoreLock.guard:StoreLock.held[self.key]=[me,1,f]
  return self
 def __exit__(self,*exc):
  with StoreLock.guard:
   mine=StoreLock.held[self.key];mine[1]-=1
   if mine[1]:return False
   del StoreLock.held[self.key]
  f=mine[2]
  try:
   if os.name=='nt':
    import msvcrt;f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:
    import fcntl;fcntl.flock(f.fileno(),fcntl.LOCK_UN)
  finally:f.close()
  return False
class MediaStore:
 LOCKING=1  # original() and prepared() store the file and write the row as one step, under StoreLock
 def __init__(self,db,root):
  self.runtime=Runtime(str(db));self.root=Path(root).resolve()
  with self.runtime.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS ops_originals(id TEXT PRIMARY KEY,digest TEXT UNIQUE,path TEXT,provenance TEXT,permission TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS ops_assets(id TEXT PRIMARY KEY,original_id TEXT,digest TEXT,path TEXT,note TEXT,review_trust TEXT,created TEXT,UNIQUE(original_id,digest));
''')
 def lock(self,wait=30.0):return StoreLock(self.root,wait)
 def read_image(self,source):
  source=Path(source)
  if not source.is_file() or source.is_symlink():raise ValueError('regular image file required')
  with source.open('rb') as f:raw=f.read(MAX_BYTES+1)
  if not raw or len(raw)>MAX_BYTES:raise ValueError('image size1..20MiB required')
  if raw.startswith(b'\x89PNG\r\n\x1a\n'):extension='png'
  elif raw.startswith(b'\xff\xd8\xff'):extension='jpg'
  elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':extension='webp'
  else:raise ValueError('PNG/JPEG/WebP signature required; not a full decode or quality check')
  return raw,extension,hashlib.sha256(raw).hexdigest()
 def store(self,relative,raw,digest):
  target=self.root/relative;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  if target.exists():
   if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('existing media file mismatch')
  else:
   # Whole or not at all: written under a temporary name, then linked to the final name (a link never writes over an
   # existing name), then the temporary name goes. Nobody ever sees a half file under the final name.
   part=target.with_name('.incoming-'+uuid.uuid4().hex)
   try:
    with part.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.chmod(part,0o400)
    try:os.link(part,target)
    except FileExistsError:
     if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('media race/mismatch')
   finally:
    if part.exists():os.chmod(part,0o600);part.unlink()
  return relative
 def original(self,source,provenance,permission):
  if not isinstance(provenance,str) or not provenance.strip() or len(provenance)>1000 or not isinstance(permission,str) or not permission.strip() or len(permission)>1000:raise ValueError('provenance and permission reference required')
  raw,extension,digest=self.read_image(source);relative='originals/'+digest+'.'+extension
  with self.lock():  # the file and its row are one step for everybody who uses this store
   self.store(relative,raw,digest)
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_originals WHERE digest=?',(digest,)).fetchone()
    if old:return dict(old)
    ident='ORIGINAL-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_originals VALUES(?,?,?,?,?,?)',(ident,digest,relative,provenance,permission,now()))
    return dict(c.execute('SELECT * FROM ops_originals WHERE id=?',(ident,)).fetchone())
 def prepared(self,original,source,note,reviewed=False):
  if reviewed is not True or not isinstance(note,str) or not note.strip() or len(note)>2000:raise ValueError('explicit operator masking/scene review and edit note required')
  with self.runtime.db() as c:
   if not c.execute('SELECT id FROM ops_originals WHERE id=?',(original,)).fetchone():raise ValueError('original not found')
  raw,extension,digest=self.read_image(source);relative='prepared/'+original+'/'+digest+'.'+extension
  with self.lock():  # the file and its row are one step for everybody who uses this store
   self.store(relative,raw,digest)
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_assets WHERE original_id=? AND digest=?',(original,digest)).fetchone()
    if old:return dict(old)
    ident='ASSET-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_assets VALUES(?,?,?,?,?,?,?)',(ident,original,digest,relative,note,'OPERATOR_DECLARED_REVIEW',now()))
    return dict(c.execute('SELECT * FROM ops_assets WHERE id=?',(ident,)).fetchone())
 def verify(self,asset,digest=None):
  with self.runtime.db() as c:row=c.execute('SELECT * FROM ops_assets WHERE id=?',(asset,)).fetchone()
  if not row:raise ValueError('prepared asset not found')
  row=dict(row);path=self.root/row['path']
  if digest is not None and digest!=row['digest']:raise ValueError('asset digest not current')
  if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['digest']:raise ValueError('prepared asset modified/missing')
  row['local_path']=str(path);return row
 def report(self):
  with self.runtime.db() as c:return {'originals':[dict(r) for r in c.execute('SELECT * FROM ops_originals ORDER BY created DESC')],'assets':[dict(r) for r in c.execute('SELECT * FROM ops_assets ORDER BY created DESC')],'editing_connected':False,'publishing_enabled':False}
