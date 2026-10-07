"""Private original/prepared media manifests. Does not edit or publish images."""
import hashlib, os, uuid
from pathlib import Path
from runtime import Runtime, now
MAX_BYTES=20*1024*1024
class MediaStore:
 def __init__(self,db,root):
  self.runtime=Runtime(str(db));self.root=Path(root).resolve()
  with self.runtime.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS ops_originals(id TEXT PRIMARY KEY,digest TEXT UNIQUE,path TEXT,provenance TEXT,permission TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS ops_assets(id TEXT PRIMARY KEY,original_id TEXT,digest TEXT,path TEXT,note TEXT,review_trust TEXT,created TEXT,UNIQUE(original_id,digest));
''')
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
   try:
    with target.open('xb') as f:f.write(raw)
   except FileExistsError:
    if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('media race/mismatch')
   os.chmod(target,0o400)
  return relative
 def original(self,source,provenance,permission):
  if not isinstance(provenance,str) or not provenance.strip() or len(provenance)>1000 or not isinstance(permission,str) or not permission.strip() or len(permission)>1000:raise ValueError('provenance and permission reference required')
  raw,extension,digest=self.read_image(source);relative='originals/'+digest+'.'+extension;self.store(relative,raw,digest)
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_originals WHERE digest=?',(digest,)).fetchone()
   if old:return dict(old)
   ident='ORIGINAL-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_originals VALUES(?,?,?,?,?,?)',(ident,digest,relative,provenance,permission,now()))
   return dict(c.execute('SELECT * FROM ops_originals WHERE id=?',(ident,)).fetchone())
 def prepared(self,original,source,note,reviewed=False):
  if reviewed is not True or not isinstance(note,str) or not note.strip() or len(note)>2000:raise ValueError('explicit operator masking/scene review and edit note required')
  with self.runtime.db() as c:
   if not c.execute('SELECT id FROM ops_originals WHERE id=?',(original,)).fetchone():raise ValueError('original not found')
  raw,extension,digest=self.read_image(source);relative='prepared/'+original+'/'+digest+'.'+extension;self.store(relative,raw,digest)
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
