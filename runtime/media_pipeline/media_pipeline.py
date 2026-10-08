"""Media pipeline: portal uploads -> shared media inbox -> agent work queue -> masked variants -> Gev's review.

Built on what the runtime already has and changes none of it:
  ops_media.MediaStore   the shared inbox: one original for one sha256, prepared assets beside it
  ops_work.Operations    the day's MEDIA_INBOX task, its draft, Gev's approval and the recorded result

This module publishes nothing and sends nothing. An upload is not a publication permission: a prepared
picture reaches a platform only after Gev approved the exact draft that names that platform, and the
publication itself is a recorded result of the existing approval path, not an action of this code.
It invents nothing in a picture: it turns it upright, covers the declared regions, makes it smaller and
drops the metadata. No colour change, no retouching, no generated content.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from ops_work import Operations
from runtime import encode, now

SOURCE = 'ARMEN_PORTAL'
PERMISSION = 'INTERNAL_PROCESSING_ONLY: uploaded by the owner in his portal; an upload is not a publication permission'
TRUST = 'AGENT_DECLARED_MASKS'
# Long edge in pixels. Both are the sizes of the files in use on 08.10.2026: photo/01_real_polished (the card)
# and the site's gallery copies.
VARIANTS = {'FULL': 1600, 'WEB': 747}
# The platform a draft names, and the variant it gets.
PLATFORMS = {'YANDEX_BUSINESS': 'FULL', 'AVITO': 'FULL', 'SITE': 'WEB'}
MASK_KINDS = ('PLATE', 'FACE', 'PERSONAL')
OPEN = ('NEW', 'CLAIMED', 'PREPARED', 'IN_REVIEW', 'APPROVED')
DEFAULT_LIMIT = 5 * 1024 ** 3


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def text(value, label, limit=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(label + ' required')
    return value.strip()


def remove(path):
    """Delete one regular file (also a read-only one) and return its size. A link is never followed."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular file required')
    size = path.stat().st_size
    os.chmod(path, 0o600)
    path.unlink()
    return size


def cover(image, box):
    """Make one region unreadable for good: large blocks, then a blur. The rest of the picture is untouched."""
    region = image.crop(box)
    width, height = region.size
    step = max(12, min(width, height) // 3)  # a plate keeps about three blocks of height: no character survives
    small = region.resize((max(1, width // step), max(1, height // step)), Image.BOX)
    image.paste(small.resize((width, height), Image.NEAREST).filter(ImageFilter.GaussianBlur(step)), box)


class MediaPipeline:
    def __init__(self, db, media_root=None, limit=DEFAULT_LIMIT, clock=None):
        self.ops = Operations(db, media_root)
        self.media = self.ops.media
        self.runtime = self.ops.runtime
        self.root = self.media.root
        self.limit = limit
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        with self.runtime.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS media_work(id TEXT PRIMARY KEY, original_id TEXT UNIQUE NOT NULL, digest TEXT UNIQUE NOT NULL,
 format TEXT, actor TEXT, uploaded TEXT, purpose TEXT, status TEXT NOT NULL, revision INTEGER NOT NULL, worker TEXT,
 lease_until TEXT, attempts INTEGER NOT NULL, platform TEXT, task_id TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS media_work_sources(source TEXT, source_id TEXT, source_file TEXT, actor TEXT, uploaded TEXT,
 purpose TEXT, work_id TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(source, source_id));
CREATE TABLE IF NOT EXISTS media_work_assets(work_id TEXT, variant TEXT, asset_id TEXT NOT NULL, PRIMARY KEY(work_id, variant));
CREATE TABLE IF NOT EXISTS media_work_events(id INTEGER PRIMARY KEY, work_id TEXT, kind TEXT, data TEXT, created TEXT);
''')

    # ---- small helpers
    def event(self, c, work, kind, data):
        c.execute('INSERT INTO media_work_events(work_id,kind,data,created) VALUES(?,?,?,?)', (work, kind, encode(data), now()))

    def row(self, c, work):
        r = c.execute('SELECT * FROM media_work WHERE id=?', (work,)).fetchone()
        if not r:
            raise LookupError('work not found')
        return r

    def leased(self, r):
        return r['status'] == 'CLAIMED' and datetime.fromisoformat(r['lease_until']) > self.clock()

    def owned(self, c, work, worker):
        r = self.row(c, work)
        if not self.leased(r) or r['worker'] != worker:
            raise PermissionError('active owned lease required')
        return r

    def original_path(self, c, r):
        path = self.root / c.execute('SELECT path FROM ops_originals WHERE id=?', (r['original_id'],)).fetchone()['path']
        if path.is_symlink() or not path.is_file() or sha256(path) != r['digest']:
            raise ValueError('original missing or modified')
        return path

    def used(self):
        return sum(f.stat().st_size for f in self.root.rglob('*') if f.is_file() and not f.is_symlink()) if self.root.exists() else 0

    # ---- 1. intake: the portal's photos become originals of the shared inbox and work of the queue
    def intake_portal(self, portal_db, portal_photos):
        """Read the portal's list (read-only) and take in what is new. Run it again as often as wanted:
        a photo already taken in, or the same bytes under another portal id, makes no second original and
        no second work."""
        photos = Path(portal_photos)
        source = sqlite3.connect('file:' + Path(portal_db).as_posix() + '?mode=ro', uri=True, timeout=15)
        source.row_factory = sqlite3.Row
        try:
            rows = source.execute('SELECT id,actor,digest,format,original,purpose,created FROM armen_photos ORDER BY rowid').fetchall()
            # Photos the portal marks as somebody's test (armen_excluded) are not Armen's and never enter the inbox.
            marked = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='armen_excluded'").fetchone()
            excluded = {r['id'] for r in source.execute("SELECT id FROM armen_excluded WHERE kind='photo'")} if marked else set()
        finally:
            source.close()
        result = {'seen': len(rows), 'imported': 0, 'known': 0, 'duplicates': 0, 'mismatched': 0, 'refused_storage': 0, 'excluded': 0}
        for p in rows:
            if p['id'] in excluded:
                result['excluded'] += 1
                continue
            with self.runtime.db() as c:
                if c.execute('SELECT 1 FROM media_work_sources WHERE source=? AND source_id=?', (SOURCE, p['id'])).fetchone():
                    result['known'] += 1
                    continue
            if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)', p['original'] or ''):
                result['mismatched'] += 1
                continue
            path = photos / p['original']
            if path.is_symlink() or not path.is_file() or sha256(path) != p['digest']:
                result['mismatched'] += 1
                continue
            with self.runtime.db() as c:
                known = c.execute('SELECT id FROM media_work WHERE digest=?', (p['digest'],)).fetchone()
            if not known and self.used() + path.stat().st_size > self.limit:
                result['refused_storage'] += 1
                continue
            provenance = '%s photo=%s actor=%s uploaded=%s purpose=%s' % (SOURCE, p['id'], p['actor'], p['created'], p['purpose'])
            original = self.media.original(path, provenance, PERMISSION)  # one original for one sha256
            with self.runtime.db() as c:
                c.execute('BEGIN IMMEDIATE')
                if c.execute('SELECT 1 FROM media_work_sources WHERE source=? AND source_id=?', (SOURCE, p['id'])).fetchone():
                    result['known'] += 1
                    continue
                work = c.execute('SELECT id FROM media_work WHERE original_id=?', (original['id'],)).fetchone()
                if work:
                    work = work['id']
                    result['duplicates'] += 1
                    self.event(c, work, 'DUPLICATE_SOURCE', {'source': SOURCE, 'source_id': p['id'], 'actor': p['actor']})
                else:
                    work = 'MEDIA-' + uuid.uuid4().hex
                    c.execute('INSERT INTO media_work VALUES(?,?,?,?,?,?,?,?,0,NULL,NULL,0,NULL,NULL,?)',
                              (work, original['id'], p['digest'], p['format'], p['actor'], p['created'], p['purpose'], 'NEW', now()))
                    self.event(c, work, 'TAKEN_IN', {'source': SOURCE, 'source_id': p['id'], 'actor': p['actor'], 'purpose': p['purpose']})
                    result['imported'] += 1
                c.execute('INSERT INTO media_work_sources VALUES(?,?,?,?,?,?,?,?)',
                          (SOURCE, p['id'], p['original'], p['actor'], p['created'], p['purpose'], work, now()))
        return result

    # ---- 2. the queue an internal agent sees: fixed fields, no path, no free text
    def view(self, c, r):
        variants = {v['variant']: v['asset_id'] for v in c.execute('SELECT variant,asset_id FROM media_work_assets WHERE work_id=?', (r['id'],))}
        return {'id': r['id'], 'sha256': r['digest'], 'format': r['format'], 'actor': r['actor'], 'uploaded': r['uploaded'],
                'purpose': r['purpose'], 'status': r['status'], 'revision': r['revision'], 'attempts': r['attempts'],
                'platform': r['platform'], 'lease_expired': r['status'] == 'CLAIMED' and not self.leased(r), 'variants': variants}

    def queue(self, status=None):
        with self.runtime.db() as c:
            rows = c.execute('SELECT * FROM media_work ORDER BY rowid').fetchall()
            return [self.view(c, r) for r in rows if status is None or r['status'] == status]

    def get(self, work):
        with self.runtime.db() as c:
            return self.view(c, self.row(c, work))

    def claim(self, work, worker, seconds=900):
        worker = text(worker, 'worker', 100)
        if not isinstance(seconds, int) or not 30 <= seconds <= 3600:
            raise ValueError('lease 30..3600 seconds required')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            r = self.row(c, work)
            expired = r['status'] == 'CLAIMED' and not self.leased(r)
            if r['status'] != 'NEW' and not expired:
                raise ValueError('work not claimable')
            until = (self.clock() + timedelta(seconds=seconds)).isoformat()
            c.execute("UPDATE media_work SET status='CLAIMED',worker=?,lease_until=?,attempts=attempts+1,revision=revision+1 WHERE id=?", (worker, until, work))
            self.event(c, work, 'CLAIMED', {'worker': worker, 'expires': until, 'took_over_an_expired_lease': expired})
        # What an interrupted attempt left behind is not continued: the new attempt starts from the original.
        shutil.rmtree(self.root / 'tmp' / work, ignore_errors=True)
        return self.get(work)

    def original_bytes(self, work, worker):
        """The original, for the worker that holds the lease and for nobody else."""
        with self.runtime.db() as c:
            return self.original_path(c, self.owned(c, work, worker)).read_bytes()

    def release(self, work, worker, reason):
        """A failed or abandoned attempt: back to the queue, its temporary files removed, the original kept."""
        reason = text(reason, 'reason')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            self.owned(c, work, worker)
            c.execute("UPDATE media_work SET status='NEW',worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?", (work,))
            self.event(c, work, 'ATTEMPT_FAILED', {'worker': worker, 'reason': reason})
        shutil.rmtree(self.root / 'tmp' / work, ignore_errors=True)
        return self.get(work)

    def reopen(self, work, reason):
        """A prepared picture that must be done again (a region was missed): back to the queue. Its files stay
        until the new attempt replaces them and the clean-up finds them unused."""
        reason = text(reason, 'reason')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if self.row(c, work)['status'] != 'PREPARED':
                raise ValueError('prepared work required')
            c.execute("UPDATE media_work SET status='NEW',revision=revision+1 WHERE id=?", (work,))
            self.event(c, work, 'REOPENED', {'reason': reason})
        return self.get(work)

    # ---- 3. processing: upright, declared regions covered, two sizes, no metadata
    def prepare(self, work, worker, masks, nothing_to_mask=False):
        """masks: [{'kind': 'PLATE'|'FACE'|'PERSONAL', 'box': [left, top, right, bottom]}] in pixels of the upright
        picture (as a viewer sees it). The worker looked at the picture and declares the regions; without a
        region the worker must say outright that there is nothing to cover. Nothing is detected by this code."""
        if type(masks) is not list or len(masks) > 50 or type(nothing_to_mask) is not bool:
            raise ValueError('mask list and explicit nothing_to_mask boolean required')
        if bool(masks) == nothing_to_mask:
            raise ValueError('either regions to cover or an explicit declaration that there are none')
        with self.runtime.db() as c:
            path = self.original_path(c, self.owned(c, work, worker))
            original_id = self.row(c, work)['original_id']
        tmp = self.root / 'tmp' / work
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, mode=0o700)
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)  # a new picture, upright; the file itself is never rewritten
        if image.mode != 'RGB':
            image = image.convert('RGB')
        for m in masks:
            if type(m) is not dict or set(m) != {'kind', 'box'} or m['kind'] not in MASK_KINDS or type(m['box']) is not list \
                    or len(m['box']) != 4 or any(type(v) is not int for v in m['box']):
                raise ValueError('mask needs a kind and four whole pixel numbers')
            left, top, right, bottom = m['box']
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError('mask outside the picture')
            cover(image, tuple(m['box']))
        made = []
        for variant, edge in VARIANTS.items():
            scale = min(1, edge / max(image.size))  # only ever smaller: a small original is not blown up
            copy = image if scale == 1 else image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
            target = tmp / (variant + '.jpg')
            copy.save(target, 'JPEG', quality=88)  # a fresh file: no EXIF, no GPS, no thumbnail of the uncovered picture
            made.append((variant, target, sha256(target), copy.size))
        note = encode({'masks': masks, 'nothing_to_mask': nothing_to_mask, 'worker': worker, 'upright_size': list(image.size)})
        stored = [(variant, self.media.store('prepared/%s/%s.jpg' % (original_id, digest), target.read_bytes(), digest), digest, size)
                  for variant, target, digest, size in made]
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            self.owned(c, work, worker)
            c.execute('DELETE FROM media_work_assets WHERE work_id=?', (work,))
            for variant, relative, digest, size in stored:
                old = c.execute('SELECT id FROM ops_assets WHERE original_id=? AND digest=?', (original_id, digest)).fetchone()
                asset = old['id'] if old else 'ASSET-' + uuid.uuid4().hex
                if not old:
                    c.execute('INSERT INTO ops_assets VALUES(?,?,?,?,?,?,?)', (asset, original_id, digest, relative, note, TRUST, now()))
                c.execute('INSERT INTO media_work_assets VALUES(?,?,?)', (work, variant, asset))
            c.execute("UPDATE media_work SET status='PREPARED',worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?", (work,))
            self.event(c, work, 'PREPARED', {'worker': worker, 'masks': len(masks), 'nothing_to_mask': nothing_to_mask,
                                             'variants': {v: {'sha256': d, 'size': list(s)} for v, _, d, s in stored}})
        shutil.rmtree(tmp, ignore_errors=True)
        return self.get(work)

    # ---- 4. Gev's review: the day's MEDIA_INBOX task carries the draft, with the platform named
    def submit(self, works, day, worker, platform, account, body, reason):
        """Put prepared pictures before Gev as one draft for one named platform. Nothing is published here:
        the draft waits in READY_REVIEW until Gev approves that exact digest in his dashboard."""
        if platform not in PLATFORMS:
            raise ValueError('a known platform must be named')
        if type(works) is not list or not works or len(set(works)) != len(works):
            raise ValueError('list of distinct works required')
        variant = PLATFORMS[platform]
        assets = []
        with self.runtime.db() as c:
            for work in works:
                if self.row(c, work)['status'] != 'PREPARED':
                    raise ValueError('prepared work required: ' + work)
                a = c.execute('SELECT a.id,a.digest FROM media_work_assets w JOIN ops_assets a ON a.id=w.asset_id WHERE w.work_id=? AND w.variant=?', (work, variant)).fetchone()
                assets.append({'id': a['id'], 'sha256': a['digest']})
            task = c.execute("SELECT id FROM ops_tasks WHERE day=? AND job='MEDIA_INBOX'", (day,)).fetchone()
        if not task:
            raise LookupError('the day has no MEDIA_INBOX task; plan the day first')
        task = task['id']
        self.ops.claim(task, worker)
        self.ops.draft(task, worker, {'action': 'PHOTO_BATCH', 'account': account, 'destination': platform, 'body': body, 'reason': reason, 'assets': assets})
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for work in works:
                c.execute("UPDATE media_work SET status='IN_REVIEW',platform=?,task_id=?,revision=revision+1 WHERE id=?", (platform, task, work))
                self.event(c, work, 'SUBMITTED_FOR_REVIEW', {'task': task, 'platform': platform, 'variant': variant, 'publication_started': False})
        return self.ops.get(task)

    def sync(self):
        """Follow Gev's decision on the drafts: approved, sent back for a change, or the result recorded."""
        changed = []
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for r in c.execute("SELECT * FROM media_work WHERE status IN ('IN_REVIEW','APPROVED')").fetchall():
                task = c.execute('SELECT status,digest FROM ops_tasks WHERE id=?', (r['task_id'],)).fetchone()
                new = {'APPROVED': 'APPROVED', 'DONE': 'PUBLISHED', 'READY_REVIEW': 'IN_REVIEW'}.get(task['status'], 'PREPARED')
                if new == r['status']:
                    continue
                data = {'task': r['task_id'], 'platform': r['platform']}
                if new == 'PUBLISHED':
                    approval = c.execute('SELECT id,actor,reference FROM ops_approvals WHERE task_id=? AND digest=? ORDER BY created DESC', (r['task_id'], task['digest'])).fetchone()
                    if not approval:
                        continue  # a result without Gev's approval of this digest is not a publication
                    data['approval'] = approval['id']
                    data['recorded_result'] = 'ops_observations of the task'
                if new == 'PREPARED':
                    c.execute("UPDATE media_work SET status='PREPARED',platform=NULL,task_id=NULL,revision=revision+1 WHERE id=?", (r['id'],))
                else:
                    c.execute('UPDATE media_work SET status=?,revision=revision+1 WHERE id=?', (new, r['id']))
                self.event(c, r['id'], {'PREPARED': 'SENT_BACK', 'APPROVED': 'APPROVED_BY_GEV', 'PUBLISHED': 'PUBLICATION_RECORDED'}[new], data)
                changed.append({'id': r['id'], 'status': new})
        return changed

    # ---- 5. nothing piles up
    def referenced(self, c):
        ids = set()
        for t in c.execute('SELECT draft FROM ops_tasks WHERE draft IS NOT NULL'):
            ids.update(a['id'] for a in json.loads(t['draft']).get('assets', []))
        return ids

    def cleanup(self, portal_photos=None):
        """Remove what is no longer needed and nothing else. Kept always: every original of the inbox, every
        asset a draft names, every asset of unfinished work. Removed: temporary folders of work nobody holds,
        prepared files of this pipeline that no work and no draft names, and, for work whose publication is
        recorded, the unused variants and the portal's second copy of the original (only when the inbox copy
        is there and both match the recorded sha256)."""
        removed = []
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            works = c.execute('SELECT * FROM media_work').fetchall()
            keep = self.referenced(c)
            active = {r['id'] for r in works if self.leased(r)}
            for r in works:
                if r['status'] != 'PUBLISHED':
                    continue
                for v in c.execute('SELECT variant,asset_id FROM media_work_assets WHERE work_id=?', (r['id'],)).fetchall():
                    if v['asset_id'] not in keep:
                        c.execute('DELETE FROM media_work_assets WHERE work_id=? AND variant=?', (r['id'], v['variant']))
            mapped = {m['asset_id'] for m in c.execute('SELECT asset_id FROM media_work_assets')}
            for a in c.execute('SELECT id,path FROM ops_assets WHERE review_trust=?', (TRUST,)).fetchall():
                if a['id'] in keep or a['id'] in mapped:
                    continue
                target = self.root / a['path']
                if target.is_file() and not target.is_symlink():
                    removed.append({'kind': 'UNUSED_VARIANT', 'file': a['path'], 'bytes': remove(target)})
                c.execute('DELETE FROM ops_assets WHERE id=?', (a['id'],))
            paths = {a['path'] for a in c.execute('SELECT path FROM ops_assets')}
            for r in works:
                folder = self.root / 'prepared' / r['original_id']
                if r['id'] in active or not folder.is_dir():
                    continue
                for f in sorted(folder.iterdir()):
                    relative = 'prepared/%s/%s' % (r['original_id'], f.name)
                    if f.is_file() and not f.is_symlink() and relative not in paths:
                        removed.append({'kind': 'INTERRUPTED_LEFTOVER', 'file': relative, 'bytes': remove(f)})
            if portal_photos is not None:
                for r in works:
                    if r['status'] != 'PUBLISHED':
                        continue
                    try:
                        self.original_path(c, r)
                    except (ValueError, TypeError):
                        continue  # the inbox copy is not provably there: the portal's copy stays
                    for s in c.execute('SELECT source_file FROM media_work_sources WHERE work_id=? AND source=?', (r['id'], SOURCE)).fetchall():
                        copy = Path(portal_photos) / s['source_file']
                        if re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)', s['source_file']) and copy.is_file() and not copy.is_symlink() and sha256(copy) == r['digest']:
                            removed.append({'kind': 'PORTAL_SECOND_COPY', 'file': s['source_file'], 'bytes': remove(copy)})
                            self.event(c, r['id'], 'PORTAL_SECOND_COPY_REMOVED', {'file': s['source_file']})
        tmp = self.root / 'tmp'
        if tmp.is_dir():
            for folder in sorted(tmp.iterdir()):
                if folder.name not in active and folder.is_dir() and not folder.is_symlink():
                    size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
                    shutil.rmtree(folder)
                    removed.append({'kind': 'TEMPORARY', 'file': 'tmp/' + folder.name, 'bytes': size})
        return {'removed': removed, 'bytes': sum(x['bytes'] for x in removed), 'originals_deleted': 0}

    def storage(self, portal_photos=None):
        """Sizes by kind, against the limit. WARN from 80 %, FULL at the limit: intake then takes in nothing new."""
        def size(folder):
            folder = Path(folder)
            files = [f for f in folder.rglob('*') if f.is_file() and not f.is_symlink()] if folder.is_dir() else []
            return {'files': len(files), 'bytes': sum(f.stat().st_size for f in files)}
        parts = {name: size(self.root / name) for name in ('originals', 'prepared', 'tmp')}
        used = self.used()
        with self.runtime.db() as c:
            counts = {s: c.execute('SELECT count(*) FROM media_work WHERE status=?', (s,)).fetchone()[0] for s in OPEN + ('PUBLISHED',)}
        result = {'media_root': parts, 'used_bytes': used, 'limit_bytes': self.limit,
                  'status': 'FULL' if used >= self.limit else 'WARN' if used >= self.limit * 0.8 else 'OK', 'work': counts}
        if portal_photos is not None:
            result['portal_photos'] = size(portal_photos)
        return result
