"""Media pipeline: portal uploads -> shared media inbox -> agent work queue -> masked variants -> Gev's review.

Of the portal it reads one folder, the outbox, where the portal itself puts Armen's own photos and their facts.
It has no access to the portal's database, answers, previews or test rows, and needs none.
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
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from media_lock import PipelineLock
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
OPEN = ('NEW', 'CLAIMED', 'PREPARED', 'SUBMITTING', 'IN_REVIEW', 'APPROVED')
WITHDRAWN = '.withdrawn'   # the portal's own record that it took a photo back: <photo id>.withdrawn in the outbox
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
    def __init__(self, db, media_root=None, limit=DEFAULT_LIMIT, clock=None, lock_wait=30.0):
        self.lock_wait = lock_wait
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
 lease_until TEXT, attempts INTEGER NOT NULL, platform TEXT, task_id TEXT, created TEXT NOT NULL,
 owns_original INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS media_work_sources(source TEXT, source_id TEXT, source_file TEXT, actor TEXT, uploaded TEXT,
 purpose TEXT, work_id TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(source, source_id));
CREATE TABLE IF NOT EXISTS media_work_assets(work_id TEXT, variant TEXT, asset_id TEXT NOT NULL, PRIMARY KEY(work_id, variant));
CREATE TABLE IF NOT EXISTS media_work_events(id INTEGER PRIMARY KEY, work_id TEXT, kind TEXT, data TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS media_work_deletions(path TEXT PRIMARY KEY, kind TEXT NOT NULL, created TEXT NOT NULL);
''')

    # ---- one operation at a time, across processes (media_lock.py)
    def lock(self):
        return PipelineLock(self.root, self.lock_wait)

    def intake(self, outbox):
        with self.lock():
            return self._intake(outbox)

    def prepare(self, work, worker, masks, nothing_to_mask=False):
        with self.lock():
            return self._prepare(work, worker, masks, nothing_to_mask)

    def submit(self, works, day, worker, platform, account, body, reason):
        with self.lock():
            return self._submit(works, day, worker, platform, account, body, reason)

    def sync(self):
        with self.lock():
            return self._sync()

    def cleanup(self):
        with self.lock():
            return self._cleanup()

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

    # ---- 1. intake: what the portal handed over becomes originals of the shared inbox and work of the queue
    def _intake(self, outbox):
        """Take in what is new in the portal's outbox. The outbox is all this code ever reads of the portal: for each
        photo one file and one small metadata file (id, sha256, format, file, actor, uploaded, purpose). It never
        opens the portal's database, its photo folder, an answer or a preview. Run it as often as wanted: a photo
        already taken in, or the same bytes under another id, makes no second original and no second work. A run
        cut off at any point is completed by the next one."""
        outbox = Path(outbox)
        # A folder that is not there, cannot be read or is not a folder is refused before anything is looked at or
        # changed: it says nothing about the photos, least of all that they were taken back.
        try:
            if outbox.is_symlink() or not outbox.is_dir():
                raise ValueError('the outbox is not an existing folder; nothing was changed')
            metas = sorted(outbox.glob('*.json'))
            taken_back = self.withdrawals(outbox)
        except OSError as e:
            raise ValueError('the outbox cannot be read (%s); nothing was changed' % type(e).__name__) from None
        result = {'seen': 0, 'imported': 0, 'known': 0, 'duplicates': 0, 'mismatched': 0, 'refused_storage': 0, 'withdrawn': 0, 'repaired': 0,
                  'blocked': 0, 'taken_back_at_the_source': 0}
        # What a run of this intake that was cut off in the middle of a copy left: its own temporary file, never an original.
        incoming = self.root / 'originals'
        if incoming.is_dir():
            for stale in incoming.glob('.incoming-*'):
                remove(stale)
        for meta in metas:
            result['seen'] += 1
            # One damaged entry is counted and skipped; it never stops the photos beside it.
            try:
                p = json.loads(meta.read_text(encoding='utf-8'))
                if type(p) is not dict or set(p) != {'id', 'sha256', 'format', 'file', 'actor', 'uploaded', 'purpose'} or any(type(v) is not str for v in p.values()):
                    raise ValueError
                if meta.name != p['id'] + '.json' or not re.fullmatch(r'[a-f0-9]{32}', p['id']) or not re.fullmatch(r'[a-f0-9]{64}', p['sha256']) \
                        or p['file'] != '%s.%s' % (p['id'], {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}.get(p['format'])) or p['actor'] != 'armen' \
                        or p['purpose'] not in ('WORK', 'EQUIPMENT', 'OTHER') or datetime.fromisoformat(p['uploaded']).tzinfo is None:
                    raise ValueError
            except (ValueError, TypeError, OSError):
                result['mismatched'] += 1
                continue
            if p['id'] in taken_back:
                result['taken_back_at_the_source'] += 1   # the portal says it took this one back: its facts still lying there are not taken in
                continue
            with self.runtime.db() as c:
                if c.execute('SELECT 1 FROM media_work_sources WHERE source=? AND source_id=?', (SOURCE, p['id'])).fetchone():
                    result['known'] += 1
                    continue
            path = outbox / p['file']
            if path.is_symlink() or not path.is_file() or sha256(path) != p['sha256']:
                result['mismatched'] += 1
                continue
            with self.runtime.db() as c:
                known = c.execute('SELECT id FROM media_work WHERE digest=?', (p['sha256'],)).fetchone()
            if not known and self.used() + path.stat().st_size > self.limit:
                result['refused_storage'] += 1
                continue
            provenance = '%s photo=%s actor=%s uploaded=%s purpose=%s' % (SOURCE, p['id'], p['actor'], p['uploaded'], p['purpose'])
            # The file is put under its final name whole or not at all, and nothing under that name is ever deleted
            # (place() below). Only then is it registered: MediaStore finds the right bytes there and adds its row.
            target = self.root / 'originals' / ('%s.%s' % (p['sha256'], p['file'].rsplit('.', 1)[1]))
            try:
                placed = self.place(path, target, p['sha256'])
            except OSError:
                result['blocked'] += 1   # the name is held by somebody right now, or the disk refused: nothing was removed; the next run tries again
                continue
            if placed == 'registered_but_not_these_bytes':
                result['mismatched'] += 1   # an original the inbox names is never written over here: this is for a person to look at
                continue
            if placed == 'replaced':
                result['repaired'] += 1
            original = self.media.original(path, provenance, PERMISSION)  # one original for one sha256; the outbox file is not touched
            # Whose original is it? Ours when the inbox row carries exactly the provenance written here: made now, or by a
            # run of this intake that was cut off. An original the inbox had before, from any other source, is only used.
            owns = 1 if original['provenance'] == provenance else 0
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
                    c.execute('INSERT INTO media_work VALUES(?,?,?,?,?,?,?,?,0,NULL,NULL,0,NULL,NULL,?,?)',
                              (work, original['id'], p['sha256'], p['format'], p['actor'], p['uploaded'], p['purpose'], 'NEW', now(), owns))
                    self.event(c, work, 'TAKEN_IN', {'source': SOURCE, 'source_id': p['id'], 'actor': p['actor'], 'purpose': p['purpose'],
                                                     'original_was_already_in_the_inbox': not owns})
                    result['imported'] += 1
                c.execute('INSERT INTO media_work_sources VALUES(?,?,?,?,?,?,?,?)',
                          (SOURCE, p['id'], p['file'], p['actor'], p['uploaded'], p['purpose'], work, now()))
        # A photo the portal took back (marked as a test after it was handed over) leaves the queue; what Gev already
        # has before him, and anything published, is his to decide and is not touched here. The proof of a take-back
        # is a record the portal writes for that very photo (<id>.withdrawn). The absence of anything (a missing file, a
        # list that does not name the photo yet, an empty or wrong folder) proves nothing and changes no work.
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for r in c.execute("SELECT * FROM media_work WHERE status IN ('NEW','CLAIMED','PREPARED')").fetchall():
                sources = [x['source_id'] for x in c.execute('SELECT source_id FROM media_work_sources WHERE work_id=?', (r['id'],))]
                if sources and all(x in taken_back for x in sources):
                    c.execute("UPDATE media_work SET status='WITHDRAWN',worker=NULL,lease_until=NULL,revision=revision+1 WHERE id=?", (r['id'],))
                    self.event(c, r['id'], 'WITHDRAWN_BY_THE_PORTAL', {'sources': sources})
                    result['withdrawn'] += 1
        return result

    @staticmethod
    def withdrawals(outbox):
        """The photo ids the portal has explicitly taken back: one valid <id>.withdrawn file each. A file that is not a
        whole, well-formed record of that id counts for nothing."""
        ids = set()
        for record in outbox.glob('*' + WITHDRAWN):
            try:
                data = json.loads(record.read_text(encoding='utf-8'))
                ident = record.name[:-len(WITHDRAWN)]
                if type(data) is dict and data.get('id') == ident and re.fullmatch(r'[a-f0-9]{32}', ident) \
                        and type(data.get('withdrawn')) is str and datetime.fromisoformat(data['withdrawn']).tzinfo is not None:
                    ids.add(ident)
            except (OSError, ValueError, TypeError):
                continue
        return ids

    def place(self, source, target, digest):
        """Put the photo under its final name in the inbox, whole or not at all, without ever deleting a file there.
        The inbox's own code (MediaStore, also used by importers outside this pipeline) writes straight under the final
        name before it registers the row, so a file under that name with the wrong bytes may be somebody's write in
        progress. Removing it could leave that importer's row without a file (review of a52d133, finding 1). So:
          - the right bytes are already there: nothing to do;
          - an inbox row names this sha256 and the bytes are not right: left alone, reported;
          - otherwise the photo is copied to a temporary file beside it, checked against its sha256 and moved over the
            name in one step (os.replace). A writer that still holds the old file open writes into a file nobody names
            any more; whoever registers this sha256 afterwards finds the right bytes under the name.
        Returns 'whole', 'placed', 'replaced' or 'registered_but_not_these_bytes'. OSError when the move is refused."""
        if target.is_symlink():
            raise OSError('a link under the name of an original')
        if target.is_file() and sha256(target) == digest:
            return 'whole'
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        incoming = target.with_name('.incoming-' + uuid.uuid4().hex)
        try:
            with open(source, 'rb') as a, open(incoming, 'xb') as b:
                shutil.copyfileobj(a, b)
                b.flush()
                os.fsync(b.fileno())
            if sha256(incoming) != digest:
                raise OSError('the photo changed while it was copied')
            with self.runtime.db() as c:
                c.execute('BEGIN IMMEDIATE')   # nobody registers an original while the name is looked at and moved over
                existed = target.exists()
                if target.is_file() and sha256(target) == digest:
                    return 'whole'             # completed by its writer in the meantime
                if c.execute('SELECT 1 FROM ops_originals WHERE digest=?', (digest,)).fetchone():
                    return 'registered_but_not_these_bytes'
                os.replace(incoming, target)
            os.chmod(target, 0o400)
            return 'replaced' if existed else 'placed'
        finally:
            if incoming.exists():
                remove(incoming)

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
    def _prepare(self, work, worker, masks, nothing_to_mask=False):
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
        # Before a variant file is written under its name, the name goes on the deletion list; it comes off in the same
        # transaction that registers the variant. A processing cut off in between leaves files the list names, and the
        # clean-up removes exactly those. It never guesses from "a file without a row".
        names = ['prepared/%s/%s.jpg' % (original_id, digest) for _, _, digest, _ in made]
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for name in names:
                c.execute('INSERT OR IGNORE INTO media_work_deletions VALUES(?,?,?)', (name, 'INTERRUPTED_LEFTOVER', now()))
        stored = [(variant, self.media.store('prepared/%s/%s.jpg' % (original_id, digest), target.read_bytes(), digest), digest, size)
                  for variant, target, digest, size in made]
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            self.owned(c, work, worker)
            for name in names:
                c.execute('DELETE FROM media_work_deletions WHERE path=?', (name,))
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
    def _submit(self, works, day, worker, platform, account, body, reason):
        """Put prepared pictures before Gev as one draft for one named platform. Nothing is published here:
        the draft waits in READY_REVIEW until Gev approves that exact digest in his dashboard.
        The step has two halves in two stores (the works here, the draft in the task). So that a run cut off between
        them cannot leave a draft before Gev with works that look free, the works are first marked SUBMITTING with
        the task they go to; `sync` finishes or undoes that from what the task really holds."""
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
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for work in works:
                if self.row(c, work)['status'] != 'PREPARED':
                    raise ValueError('prepared work required: ' + work)
                c.execute("UPDATE media_work SET status='SUBMITTING',platform=?,task_id=?,revision=revision+1 WHERE id=?", (platform, task, work))
                self.event(c, work, 'SUBMIT_STARTED', {'task': task, 'platform': platform, 'variant': variant})
        try:
            self.ops.claim(task, worker)
            self.ops.draft(task, worker, {'action': 'PHOTO_BATCH', 'account': account, 'destination': platform, 'body': body, 'reason': reason, 'assets': assets})
        except Exception:
            self._sync()   # refused by the task (not claimable, a bad draft): the works go back to PREPARED, or forward if the draft is there
            raise
        self._sync()       # the draft is in the task: the works become IN_REVIEW from what the task holds
        return self.ops.get(task)

    def _sync(self):
        """Follow what the task really holds: a submit that was cut off is finished or undone, and Gev's decision on a
        draft is taken over (approved, sent back for a change, the result recorded). A work counts as before Gev only
        when the task's draft names its own asset; the work's stored status alone decides nothing."""
        changed = []
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for r in c.execute("SELECT * FROM media_work WHERE status IN ('SUBMITTING','IN_REVIEW','APPROVED')").fetchall():
                task = c.execute('SELECT status,digest,draft FROM ops_tasks WHERE id=?', (r['task_id'],)).fetchone()
                mine = c.execute('SELECT asset_id FROM media_work_assets WHERE work_id=? AND variant=?', (r['id'], PLATFORMS.get(r['platform'], ''))).fetchone()
                named = {a['id'] for a in json.loads(task['draft']).get('assets', [])} if task and task['draft'] else set()
                linked = bool(mine) and mine['asset_id'] in named
                new = {'APPROVED': 'APPROVED', 'DONE': 'PUBLISHED', 'READY_REVIEW': 'IN_REVIEW'}.get(task['status'], 'PREPARED') if linked else 'PREPARED'
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
                kind = {'PREPARED': 'SUBMIT_NOT_COMPLETED' if r['status'] == 'SUBMITTING' else 'SENT_BACK', 'IN_REVIEW': 'SUBMITTED_FOR_REVIEW',
                        'APPROVED': 'APPROVED_BY_GEV', 'PUBLISHED': 'PUBLICATION_RECORDED'}[new]
                if new == 'IN_REVIEW':
                    data.update(variant=PLATFORMS[r['platform']], publication_started=False)
                self.event(c, r['id'], kind, data)
                changed.append({'id': r['id'], 'status': new})
        return changed

    # ---- 5. nothing piles up
    def referenced(self, c):
        ids = set()
        for t in c.execute('SELECT draft FROM ops_tasks WHERE draft IS NOT NULL'):
            ids.update(a['id'] for a in json.loads(t['draft']).get('assets', []))
        return ids

    def _cleanup(self):
        """Remove what is no longer needed and nothing else. Kept always: every original of the inbox, every
        asset a draft names, every asset of unfinished work. Removed: temporary folders of work nobody holds,
        prepared files of this pipeline that no work and no draft names, the files a processing left when it was
        cut off, and, for work whose publication is recorded or which the portal took back, the variants no draft
        names. It removes only what a row or the deletion list says is this pipeline's; a file it knows nothing
        about is left alone. It writes nothing outside the runtime's media folder."""
        # A row is removed in the database first and its file afterwards, through a list that is itself in the database
        # (media_work_deletions): cut off at any point, there is a file nobody names, or a line on the list, never a
        # row whose file is gone. The next run finishes the list.
        removed = []
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            works = c.execute('SELECT * FROM media_work').fetchall()
            keep = self.referenced(c)
            active = {r['id'] for r in works if self.leased(r)}
            for r in works:
                if r['status'] not in ('PUBLISHED', 'WITHDRAWN'):
                    continue
                for v in c.execute('SELECT variant,asset_id FROM media_work_assets WHERE work_id=?', (r['id'],)).fetchall():
                    if v['asset_id'] not in keep:
                        c.execute('DELETE FROM media_work_assets WHERE work_id=? AND variant=?', (r['id'], v['variant']))
            mapped = {m['asset_id'] for m in c.execute('SELECT asset_id FROM media_work_assets')}
            for a in c.execute('SELECT id,path FROM ops_assets WHERE review_trust=?', (TRUST,)).fetchall():
                if a['id'] in keep or a['id'] in mapped:
                    continue
                c.execute('INSERT OR IGNORE INTO media_work_deletions VALUES(?,?,?)', (a['path'], 'UNUSED_VARIANT', now()))
                c.execute('DELETE FROM ops_assets WHERE id=?', (a['id'],))
        removed += self.finish_deletions()
        tmp = self.root / 'tmp'
        if tmp.is_dir():
            for folder in sorted(tmp.iterdir()):
                if folder.name not in active and folder.is_dir() and not folder.is_symlink():
                    size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
                    shutil.rmtree(folder)
                    removed.append({'kind': 'TEMPORARY', 'file': 'tmp/' + folder.name, 'bytes': size})
        return {'removed': removed, 'bytes': sum(x['bytes'] for x in removed), 'originals_deleted': 0}

    def finish_deletions(self):
        """Remove the files on the deletion list, one at a time: the file, then its line. A path some row names again by
        now is taken off the list and its file is kept."""
        done = []
        with self.runtime.db() as c:
            queue = c.execute('SELECT path,kind FROM media_work_deletions ORDER BY rowid').fetchall()
        for q in queue:
            with self.runtime.db() as c:
                c.execute('BEGIN IMMEDIATE')
                named = c.execute('SELECT 1 FROM ops_assets WHERE path=? UNION ALL SELECT 1 FROM ops_originals WHERE path=?', (q['path'], q['path'])).fetchone()
                target = self.root / q['path']
                if not named and target.is_file() and not target.is_symlink():
                    done.append({'kind': q['kind'], 'file': q['path'], 'bytes': remove(target)})
                c.execute('DELETE FROM media_work_deletions WHERE path=?', (q['path'],))
        return done

    def storage(self):
        """Sizes by kind, against the limit. WARN from 80 %, FULL at the limit: intake then takes in nothing new."""
        def size(folder):
            folder = Path(folder)
            files = [f for f in folder.rglob('*') if f.is_file() and not f.is_symlink()] if folder.is_dir() else []
            return {'files': len(files), 'bytes': sum(f.stat().st_size for f in files)}
        parts = {name: size(self.root / name) for name in ('originals', 'prepared', 'tmp')}
        used = self.used()
        with self.runtime.db() as c:
            counts = {s: c.execute('SELECT count(*) FROM media_work WHERE status=?', (s,)).fetchone()[0] for s in OPEN + ('PUBLISHED', 'WITHDRAWN')}
        result = {'media_root': parts, 'used_bytes': used, 'limit_bytes': self.limit,
                  'status': 'FULL' if used >= self.limit else 'WARN' if used >= self.limit * 0.8 else 'OK', 'work': counts}
        return result
