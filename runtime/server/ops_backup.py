"""Private full operations backup: SQLite snapshot and hash-verified original/prepared media."""
import argparse,hashlib,json,sqlite3,tarfile,tempfile,os,io
from pathlib import Path
from contextlib import closing
from ops_work import Operations

def backup(db,output):
 if not Path(db).is_file():raise ValueError('existing database required')
 output=Path(output)
 if output.exists():raise ValueError('new backup path required')
 ops=Operations(db);media_root=ops.media.root
 with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
  snapshot=Path(temporary)/'runtime.sqlite'
  with closing(sqlite3.connect(snapshot)) as dst:
   with ops.runtime.db() as src:src.backup(dst)
  with closing(sqlite3.connect(snapshot)) as c:
   if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('snapshot integrity failed')
   rows=c.execute('SELECT path,digest FROM ops_originals UNION SELECT path,digest FROM ops_assets').fetchall()
  archive=Path(temporary)/'backup.tar.gz'
  with tarfile.open(archive,'w:gz') as tar:
   tar.add(snapshot,arcname='runtime.sqlite')
   for relative,digest in rows:
    path=media_root/relative
    if path.is_symlink() or not path.is_file():raise ValueError('media missing; backup aborted')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('media modified; backup aborted')
    info=tarfile.TarInfo('media/'+relative);info.size=len(raw);info.mode=0o400;tar.addfile(info,io.BytesIO(raw))
  # New output only. Never overwrite an earlier backup.
  with archive.open('rb') as src,output.open('xb') as dst:
   os.chmod(output,0o600)
   import shutil;shutil.copyfileobj(src,dst)
 return {'archive':str(output),'media_files':len(rows),'integrity':'OK','restore_test':'NOT_PERFORMED','contains_private_data':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(backup(a.db,a.output)))
