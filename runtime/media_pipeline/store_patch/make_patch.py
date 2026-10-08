"""Make the lock-aware version of the shared media store (ops_media.py) from the installed one.

    python runtime/media_pipeline/store_patch/make_patch.py                 write ops_media.py next to this script
    python runtime/media_pipeline/store_patch/make_patch.py --check         exit 1 when the written file is not what the source gives
    python runtime/media_pipeline/store_patch/make_patch.py --server-tests  run the server's own suites with the patched file in place

Source: runtime/server/ops_media.py, the record of the file installed on the server (protected: changed only by a
script like this one, by exact replacements; a different source stops it).

Why (GPT's reviews of 08.10.2026, heads a52d133 and 85ad816): the store wrote a file under its final name and
registered its row afterwards, in two steps nobody else could see as one. The media pipeline removes files (unused
variants, an original on rollback). Between "the file is there" and "its row is written" a removal could take the
file from under an importer, leaving a registered row without a file. A lock inside the pipeline alone cannot help:
the importer does not take it.

What changes, and nothing else:
  1. StoreLock: one lock of the operating system on <media root>/.pipeline.lock, across processes, released by the
     system when a process dies, re-entrant for the thread that holds it.
  2. MediaStore.original() and MediaStore.prepared() take that lock around "store the file" + "write the row": for
     every user of the store the two are one step. In prepared() the check that the original exists is inside the
     lock too (review of c957f87): a precondition checked outside it could be gone by the time the lock is taken.
     MediaStore.LOCKING = 1 says so; the pipeline refuses a store without it.
  4. ops_work.py, Operations.draft(): the check of the assets a draft names and the writing of the draft are one step
     under the same lock (only for a draft that names assets).
  3. MediaStore.store() writes a new file whole or not at all: to a temporary name beside it, then a hard link to the
     final name (which fails when the name exists, so nothing is ever written over), then the temporary name goes.
The pipeline takes the same lock for intake, processing, submit, sync, clean-up and rollback. So writing,
registering and deleting in this store are serialised for everybody who uses the store's own code.
What it cannot cover: a program that writes into the media folder and the database without this code.
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "runtime" / "server" / "ops_media.py"
OUT = Path(__file__).resolve().parent / "ops_media.py"
SRC_SHA = "5ca3e4dea8b0b11040a4a85ff0985c4c881ac80348abfaf7c8058cca2dbbda4c"

LOCK = '''class StoreLock:
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
'''

# (old, new, expected count)
R = [
    ("import hashlib, os, uuid\n", "import hashlib, os, threading, time, uuid\n", 1),
    ("MAX_BYTES=20*1024*1024\nclass MediaStore:\n", "MAX_BYTES=20*1024*1024\n" + LOCK + "class MediaStore:\n LOCKING=1  # original() and prepared() store the file and write the row as one step, under StoreLock\n", 1),
    (""" def read_image(self,source):""", """ def lock(self,wait=30.0):return StoreLock(self.root,wait)
 def read_image(self,source):""", 1),
    ("""  else:
   try:
    with target.open('xb') as f:f.write(raw)
   except FileExistsError:
    if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('media race/mismatch')
   os.chmod(target,0o400)
  return relative""", """  else:
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
  return relative""", 1),
    ("""  raw,extension,digest=self.read_image(source);relative='originals/'+digest+'.'+extension;self.store(relative,raw,digest)
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_originals WHERE digest=?',(digest,)).fetchone()
   if old:return dict(old)
   ident='ORIGINAL-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_originals VALUES(?,?,?,?,?,?)',(ident,digest,relative,provenance,permission,now()))
   return dict(c.execute('SELECT * FROM ops_originals WHERE id=?',(ident,)).fetchone())""",
     """  raw,extension,digest=self.read_image(source);relative='originals/'+digest+'.'+extension
  with self.lock():  # the file and its row are one step for everybody who uses this store
   self.store(relative,raw,digest)
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_originals WHERE digest=?',(digest,)).fetchone()
    if old:return dict(old)
    ident='ORIGINAL-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_originals VALUES(?,?,?,?,?,?)',(ident,digest,relative,provenance,permission,now()))
    return dict(c.execute('SELECT * FROM ops_originals WHERE id=?',(ident,)).fetchone())""", 1),
    # prepared(): the check that the original exists moves INSIDE the lock (review of c957f87). Outside it, a rollback
    # could take the lock between the check and the write, remove the original, and leave this method to store a
    # variant and a row for an original that is gone.
    ("""  with self.runtime.db() as c:
   if not c.execute('SELECT id FROM ops_originals WHERE id=?',(original,)).fetchone():raise ValueError('original not found')
  raw,extension,digest=self.read_image(source);relative='prepared/'+original+'/'+digest+'.'+extension;self.store(relative,raw,digest)
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_assets WHERE original_id=? AND digest=?',(original,digest)).fetchone()
   if old:return dict(old)
   ident='ASSET-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_assets VALUES(?,?,?,?,?,?,?)',(ident,original,digest,relative,note,'OPERATOR_DECLARED_REVIEW',now()))
   return dict(c.execute('SELECT * FROM ops_assets WHERE id=?',(ident,)).fetchone())""",
     """  raw,extension,digest=self.read_image(source);relative='prepared/'+original+'/'+digest+'.'+extension
  with self.lock():  # the check of the original, the file and its row are one step for everybody who uses this store
   with self.runtime.db() as c:
    if not c.execute('SELECT id FROM ops_originals WHERE id=?',(original,)).fetchone():raise ValueError('original not found')
   self.store(relative,raw,digest)
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM ops_assets WHERE original_id=? AND digest=?',(original,digest)).fetchone()
    if old:return dict(old)
    ident='ASSET-'+uuid.uuid4().hex;c.execute('INSERT INTO ops_assets VALUES(?,?,?,?,?,?,?)',(ident,original,digest,relative,note,'OPERATOR_DECLARED_REVIEW',now()))
    return dict(c.execute('SELECT * FROM ops_assets WHERE id=?',(ident,)).fetchone())""", 1),
]

# The second file: ops_work.py. One method, draft(): it checked the assets a draft names and wrote the draft afterwards,
# as two steps. A clean-up or a rollback between the two could remove an asset no draft named yet, and the draft would
# then name an asset that is gone (the same kind of gap, found while fixing prepared(); not in the review). Now the
# check and the write are one step under the store's lock. A draft without assets (a report) takes no lock.
WORK_SRC = ROOT / "runtime" / "server" / "ops_work.py"
WORK_OUT = Path(__file__).resolve().parent / "ops_work.py"
WORK_SHA = "d1e6a2dfa653f40ddbf886c170e8c0d143b1750ad59c1703c647313f7e8818d6"
RW = [
    ("import hashlib, html, json, re, uuid\n", "import contextlib, hashlib, html, json, re, uuid\n", 1),
    ("""  for asset in assets:self.media.verify(asset['id'],asset['sha256'])
  normalized={**data,'assets':assets};raw=encode(normalized);digest=hashlib.sha256(raw.encode()).hexdigest()
  with self.runtime.db() as c:
   c.execute('BEGIN IMMEDIATE');self.owned(c,task,worker)
   c.execute("UPDATE ops_tasks SET status='READY_REVIEW',draft=?,digest=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?",(raw,digest,task));self.event(c,task,'DRAFT_READY',{'digest':digest,'external_execution':False})
  return self.get(task)""",
     """  normalized={**data,'assets':assets};raw=encode(normalized);digest=hashlib.sha256(raw.encode()).hexdigest()
  # The assets are checked and the draft that names them is written as one step, under the media store's lock: nothing
  # removes an asset between the two. From the moment the draft exists, the clean-up and the rollback keep what it names.
  with (self.media.lock() if assets else contextlib.nullcontext()):
   for asset in assets:self.media.verify(asset['id'],asset['sha256'])
   with self.runtime.db() as c:
    c.execute('BEGIN IMMEDIATE');self.owned(c,task,worker)
    c.execute("UPDATE ops_tasks SET status='READY_REVIEW',draft=?,digest=?,worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?",(raw,digest,task));self.event(c,task,'DRAFT_READY',{'digest':digest,'external_execution':False})
  return self.get(task)""", 1),
]


FILES = ((SRC, OUT, SRC_SHA, R), (WORK_SRC, WORK_OUT, WORK_SHA, RW))


def build(source, sha, replacements):
    if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
        raise SystemExit("%s is not the installed file this patch was made for (sha256 %s…)" % (source.relative_to(ROOT).as_posix(), sha[:8]))
    out = source.read_text(encoding="utf-8")
    for old, new, n in replacements:
        if out.count(old) != n:
            raise SystemExit("%s: expected %d× %r, found %d" % (source.name, n, old[:80], out.count(old)))
        out = out.replace(old, new)
    return out


def server_tests(made):
    """The server's own suites, in a copy of runtime/server with the patched files in place of the installed ones."""
    with tempfile.TemporaryDirectory() as tmp:
        code = Path(tmp) / "server"
        shutil.copytree(SRC.parent, code, ignore=shutil.ignore_patterns("__pycache__"))
        for target, out in made:
            (code / target.name).write_text(out, encoding="utf-8", newline="")
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-p", "test_*.py"], cwd=code, capture_output=True, text=True)
        tail = done.stderr.strip().splitlines()
        print("server suites with the patched %s: %s | %s" % (" and ".join(t.name for t, _ in made), tail[-3] if len(tail) > 2 else "", tail[-1] if tail else ""))
        return done.returncode


def main():
    made = [(target, build(source, sha, replacements)) for source, target, sha, replacements in FILES]
    if "--check" in sys.argv[1:]:
        ok = all(target.exists() and target.read_text(encoding="utf-8") == out for target, out in made)
        print("MEDIA STORE PATCH: " + ("up to date" if ok else "STALE"))
        return 0 if ok else 1
    if "--server-tests" in sys.argv[1:]:
        return server_tests(made)
    for target, out in made:
        target.write_text(out, encoding="utf-8", newline="")
        print("written %s, sha256 %s" % (target.relative_to(ROOT), hashlib.sha256(out.encode("utf-8")).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
