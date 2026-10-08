"""Tests of the media pipeline on temporary folders. The portal side is the real portal Store with its outbox; no network."""
import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import media_rollback
import portal as portal_module
from media_pipeline import MediaPipeline, PLATFORMS, VARIANTS, sha256
from portal import Store

YEREVAN = timezone(timedelta(hours=4))
PLATE = [900, 1400, 1300, 1500]  # in the upright picture


def photo(size=(3000, 2000), colour=(70, 90, 110), orientation=None, gps=False, plate=None, fmt='JPEG'):
    """A sample picture: a flat field, optionally a striped 'plate' and EXIF with an orientation and a GPS block."""
    im = Image.new('RGB', size, colour)
    if plate:
        d = ImageDraw.Draw(im)
        d.rectangle(plate, fill=(255, 255, 255))
        for x in range(plate[0], plate[2], 20):
            d.rectangle([x, plate[1], x + 9, plate[3]], fill=(0, 0, 0))
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    if gps:
        exif[0x8825] = {1: 'N', 2: (55.0, 45.0, 0.0), 3: 'E', 4: (37.0, 37.0, 0.0)}
    out = io.BytesIO()
    im.save(out, fmt, **({'exif': exif, 'quality': 92} if fmt == 'JPEG' else {}))
    return out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = base = Path(self.tmp.name)
        self.portal_db, self.portal_photos, self.outbox = base / 'portal.sqlite', base / 'portal-photos', base / 'outbox'
        self.portal = Store(self.portal_db, self.portal_photos, self.outbox)
        self.time = [datetime.now(timezone.utc)]
        self.db, self.media_root = base / 'runtime.sqlite', base / 'media'
        self.pipe = MediaPipeline(self.db, self.media_root, clock=lambda: self.time[0])
        self.day = datetime.now(YEREVAN).date().isoformat()
        self.pipe.ops.plan(self.day)

    def tearDown(self):
        for f in Path(self.tmp.name).rglob('*'):
            if f.is_file():
                f.chmod(0o600)  # stored media is read-only; Windows refuses to delete it otherwise
        self.tmp.cleanup()

    def rows(self, sql, args=()):
        c = sqlite3.connect(self.db)  # closed by hand: on Windows an open file cannot be deleted
        try:
            found = c.execute(sql, args).fetchall()
            c.commit()
            return found
        finally:
            c.close()

    def upload(self, raw=None, actor='armen', purpose='WORK'):
        return self.portal.photo(actor, raw or photo(plate=PLATE), purpose)['id']

    def take_in(self):
        return self.pipe.intake(self.outbox)

    def one(self):
        self.upload()
        self.take_in()
        return self.pipe.queue()[0]['id']

    def prepared(self, masks=None):
        work = self.one()
        self.pipe.claim(work, 'agent')
        return self.pipe.prepare(work, 'agent', masks if masks is not None else [{'kind': 'PLATE', 'box': PLATE}])

    def files(self, folder):
        return sorted(f.relative_to(self.media_root).as_posix() for f in (self.media_root / folder).rglob('*') if f.is_file()) if (self.media_root / folder).is_dir() else []

    def names(self, folder):
        return sorted(f.name for f in folder.iterdir())

    def submit(self, works, platform='YANDEX_BUSINESS'):
        return self.pipe.submit(works, self.day, 'agent', platform, 'KRYUK24', 'SAMPLE batch', 'SAMPLE reason')

    def publish(self, works):
        task = self.submit(works)
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE result')
        self.pipe.sync()
        return task


class Tests(Base):
    # ---- intake
    def test_upload_becomes_one_original_and_one_work_with_its_facts(self):
        raw = photo(plate=PLATE)
        ident = self.upload(raw, purpose='EQUIPMENT')
        self.assertEqual(self.take_in(), {'seen': 1, 'imported': 1, 'known': 0, 'duplicates': 0, 'mismatched': 0, 'refused_storage': 0, 'withdrawn': 0, 'repaired': 0, 'withdrawal_checked': True})
        (work,) = self.pipe.queue()
        self.assertEqual((work['status'], work['actor'], work['purpose'], work['format'], work['attempts']), ('NEW', 'armen', 'EQUIPMENT', 'JPEG', 0))
        self.assertEqual(work['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(datetime.fromisoformat(work['uploaded']).tzinfo)
        self.assertNotIn('path', json.dumps(work))
        self.assertEqual(self.rows('SELECT source,source_id,work_id FROM media_work_sources'), [('ARMEN_PORTAL', ident, work['id'])])
        ((provenance, permission),) = self.rows('SELECT provenance,permission FROM ops_originals')
        self.assertIn('photo=' + ident, provenance)
        self.assertIn('not a publication permission', permission)
        self.assertEqual((self.media_root / self.files('originals')[0]).read_bytes(), raw, 'the original is kept byte for byte')

    def test_the_pipeline_reads_the_outbox_and_nothing_else_of_the_portal(self):
        # The proof is by removal: with the portal's database and photo folder gone, the intake works the same.
        raw = photo(plate=PLATE)
        self.upload(raw)
        self.portal.answer('armen', '0' * 32, dict(question='inquiries', answer='YES', day=portal_module.day()))
        self.portal.photo('test', photo(colour=(1, 1, 1)), 'WORK')  # the test account: never handed over
        alone = self.base / 'outbox-alone'
        shutil.copytree(self.outbox, alone)
        self.portal_db.unlink()
        shutil.rmtree(self.portal_photos)
        self.assertEqual(sorted(f.name.split('.', 1)[1] if f.name != 'INDEX.json' else f.name for f in alone.iterdir()), ['INDEX.json', 'jpg', 'json'],
                         'one photo, its facts and the index: no answer, no preview, no test row, no database')
        self.assertEqual(self.pipe.intake(alone)['imported'], 1)
        self.assertEqual((self.media_root / self.files('originals')[0]).read_bytes(), raw)
        source = Path(__file__).with_name('media_pipeline.py').read_text(encoding='utf-8')
        for word in ('armen_answers', 'armen_photos', 'armen_commands', 'sqlite3'):
            self.assertNotIn(word, source, 'the pipeline has no code that opens the portal database')

    def test_repeat_makes_no_second_original_and_no_second_work(self):
        raw = photo(plate=PLATE)
        ident = self.upload(raw)
        self.take_in()
        self.assertEqual(self.take_in()['known'], 1)
        self.assertTrue(self.portal.photo('armen', raw, 'WORK')['duplicate'], 'the portal itself stores the same bytes once')
        other = 'f' * 32   # the same bytes handed over under another id
        shutil.copyfile(self.outbox / (ident + '.jpg'), self.outbox / (other + '.jpg'))
        meta = json.loads((self.outbox / (ident + '.json')).read_text(encoding='utf-8'))
        (self.outbox / (other + '.json')).write_text(json.dumps({**meta, 'id': other, 'file': other + '.jpg'}), encoding='utf-8')
        result = self.take_in()
        self.assertEqual((result['imported'], result['duplicates'], result['known']), (0, 1, 1))
        self.assertEqual(len(self.pipe.queue()), 1)
        self.assertEqual(len(self.files('originals')), 1)
        self.assertEqual(self.take_in()['known'], 2)

    def test_a_handed_over_file_that_is_not_what_its_facts_say_is_not_taken_in(self):
        ident = self.upload()
        target = self.outbox / (ident + '.jpg')
        target.chmod(0o600)
        target.write_bytes(photo(colour=(1, 2, 3)))
        self.assertEqual(self.take_in()['mismatched'], 1)
        (self.outbox / 'not-an-id.json').write_text('{}')
        (self.outbox / ('e' * 32 + '.json')).write_text(json.dumps({'id': 'e' * 32, 'sha256': '0' * 64, 'format': 'JPEG', 'file': '../x.jpg', 'actor': 'armen', 'uploaded': 'x', 'purpose': 'WORK'}))
        self.assertEqual(self.take_in()['mismatched'], 3)
        self.assertEqual((self.pipe.queue(), self.files('originals')), ([], []))

    def test_intake_stops_at_the_storage_limit_and_reports_it(self):
        self.pipe.limit = 1000
        self.upload()
        self.assertEqual(self.take_in()['refused_storage'], 1)
        self.assertEqual(self.pipe.queue(), [])
        self.pipe.limit = 10 ** 9
        self.assertEqual(self.take_in()['imported'], 1)
        self.pipe.limit = self.pipe.used()
        self.assertEqual(self.pipe.storage()['status'], 'FULL')
        self.pipe.limit = int(self.pipe.used() / 0.9)
        report = self.pipe.storage()
        self.assertEqual((report['status'], report['work']['NEW'], report['media_root']['originals']['files']), ('WARN', 1, 1))

    def test_the_test_account_and_marked_photos_never_enter_and_a_later_mark_withdraws(self):
        self.portal.photo('test', photo(colour=(9, 9, 9)), 'WORK')
        marked = self.upload(photo(colour=(8, 8, 8)))
        self.portal.exclude('photo', marked, 'SAMPLE: somebody tried the account', 'GEV')
        real = self.upload(photo(plate=PLATE))
        result = self.take_in()
        self.assertEqual((result['seen'], result['imported']), (1, 1), "only Armen's own unmarked photo is in the outbox at all")
        self.assertEqual(self.rows('SELECT source_id FROM media_work_sources'), [(real,)])
        work = self.pipe.queue()[0]['id']
        self.pipe.claim(work, 'agent')
        self.pipe.prepare(work, 'agent', [{'kind': 'PLATE', 'box': PLATE}])
        self.portal.exclude('photo', real, 'SAMPLE: marked after it was handed over', 'GEV')
        self.assertEqual(self.take_in()['withdrawn'], 1)
        self.assertEqual(self.pipe.get(work)['status'], 'WITHDRAWN')
        with self.assertRaises(ValueError):
            self.submit([work])
        with self.assertRaises(ValueError):
            self.pipe.claim(work, 'agent')
        self.assertEqual(sorted(x['kind'] for x in self.pipe.cleanup()['removed']), ['UNUSED_VARIANT', 'UNUSED_VARIANT'])
        self.assertEqual(len(self.files('originals')), 1, 'the original stays: this code never deletes one')

    # ---- interrupted intake
    def test_intake_cut_off_after_the_copy_is_completed_by_the_next_run(self):
        ident = self.upload()
        self.pipe.media.original(self.outbox / (ident + '.jpg'), 'ARMEN_PORTAL photo=%s (the run died right after this)' % ident, 'SAMPLE')
        self.assertEqual((len(self.files('originals')), self.pipe.queue()), (1, []))
        result = self.take_in()
        self.assertEqual((result['imported'], result['duplicates']), (1, 0))
        self.assertEqual((len(self.files('originals')), len(self.pipe.queue()), self.rows('SELECT count(*) FROM ops_originals')), (1, 1, [(1,)]))
        self.assertEqual(self.take_in()['known'], 1)

    def test_intake_cut_off_in_the_middle_of_the_copy_is_repaired_and_a_named_original_is_never_touched(self):
        raw = photo(plate=PLATE)
        self.upload(raw)
        half = self.media_root / 'originals' / (hashlib.sha256(raw).hexdigest() + '.jpg')
        half.parent.mkdir(parents=True)
        half.write_bytes(raw[:1000])                      # what a killed copy leaves: the right name, part of the bytes
        result = self.take_in()
        self.assertEqual((result['imported'], result['repaired'], result['mismatched']), (1, 1, 0))
        self.assertEqual(half.read_bytes(), raw)
        # An original an inbox row names, damaged later: nothing is written over it and nothing is imported twice.
        self.rows('DELETE FROM media_work_sources')
        half.chmod(0o600)
        half.write_bytes(b'damaged later')
        result = self.take_in()
        self.assertEqual((result['repaired'], result['mismatched'], result['imported']), (0, 1, 0))
        self.assertEqual(half.read_bytes(), b'damaged later')

    def test_a_file_that_is_whole_or_registered_by_now_is_never_removed_by_the_repair(self):
        # Review of 08.10.2026, finding 3: between "this is a half file nobody registered" and its removal another
        # importer registered it, and the row was left without its file. The two orders in which that can happen:
        raw = photo(plate=PLATE)
        self.upload(raw)
        target = self.media_root / 'originals' / (hashlib.sha256(raw).hexdigest() + '.jpg')
        real = self.pipe.media.original
        # (a) somebody completed the file in the meantime, nobody registered it yet: it is whole, so it stays and is used
        target.parent.mkdir(parents=True)
        target.write_bytes(raw)
        with patch.object(self.pipe.media, 'original', side_effect=[ValueError('existing media file mismatch'), None]) as fake:
            fake.side_effect = lambda *a: (_ for _ in ()).throw(ValueError('existing media file mismatch')) if fake.call_count == 1 else real(*a)
            result = self.take_in()
        self.assertEqual((result['imported'], result['repaired'], result['mismatched'], target.read_bytes() == raw), (1, 0, 0, True))
        # (b) another importer registered it right after this one saw the mismatch: the row is found, the file is left alone
        self.rows('DELETE FROM media_work_sources')
        self.rows('DELETE FROM media_work')
        with patch.object(self.pipe.media, 'original', side_effect=ValueError('existing media file mismatch')):
            result = self.take_in()
        self.assertEqual((result['repaired'], result['mismatched']), (0, 1))
        self.assertEqual((target.read_bytes() == raw, self.rows('SELECT count(*) FROM ops_originals')), (True, [(1,)]), 'the row and its file are both there')

    def test_one_operation_at_a_time_across_processes(self):
        # Findings 2 and 3: a second intake, a clean-up, a sync or a rollback does not run beside another operation.
        self.upload()
        other = MediaPipeline(self.db, self.media_root, lock_wait=0.2)
        with self.pipe.lock():
            for name, call in (('intake', lambda: other.intake(self.outbox)), ('cleanup', other.cleanup), ('sync', other.sync),
                               ('processing', lambda: other.prepare('MEDIA-' + '0' * 32, 'agent', [], True)),
                               ('submit', lambda: other.submit(['MEDIA-' + '0' * 32], self.day, 'agent', 'SITE', 'KRYUK24', 'SAMPLE', 'SAMPLE')),
                               ('rollback', lambda: media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json', lock_wait=0.2))):
                with self.assertRaises(TimeoutError, msg=name):
                    call()
        self.assertEqual((self.pipe.queue(), (self.base / 'history.json').exists(), self.files('originals')), ([], False, []), 'the refused operations changed nothing')
        self.assertEqual(other.intake(self.outbox)['imported'], 1, 'and the lock is free again afterwards')

    def test_a_missing_wrong_or_empty_outbox_is_refused_or_ignored_and_withdraws_nothing(self):
        # Finding 4: a folder that does not exist turned existing NEW work into WITHDRAWN.
        work = self.one()
        for bad in (self.base / 'no-such-folder', self.portal_db):   # absent; a file, not a folder
            with self.assertRaises(ValueError):
                self.pipe.intake(bad)
        self.assertEqual(self.pipe.get(work)['status'], 'NEW')
        empty = self.base / 'empty'
        empty.mkdir()
        result = self.pipe.intake(empty)
        self.assertEqual((result['withdrawn'], result['withdrawal_checked'], self.pipe.get(work)['status']), (0, False, 'NEW'), 'an empty folder proves nothing')
        for index in ('not json', json.dumps({'outbox': 'SOMETHING_ELSE', 'generated': datetime.now(timezone.utc).isoformat(), 'ids': []}), json.dumps({'outbox': 'ARMEN_PORTAL', 'ids': []})):
            (empty / 'INDEX.json').write_text(index)
            result = self.pipe.intake(empty)
            self.assertEqual((result['withdrawal_checked'], self.pipe.get(work)['status']), (False, 'NEW'), index[:20])
        # the real outbox with the photo's files gone but the portal's index still naming it: not a take-back
        for f in self.outbox.iterdir():
            if f.name != 'INDEX.json':
                f.chmod(0o600)
                f.unlink()
        result = self.take_in()
        self.assertEqual((result['withdrawn'], result['withdrawal_checked'], self.pipe.get(work)['status']), (0, True, 'NEW'))

    # ---- the agent's limited access
    def test_only_the_worker_holding_the_lease_reads_the_original(self):
        work = self.one()
        with self.assertRaises(PermissionError):
            self.pipe.original_bytes(work, 'agent')
        self.pipe.claim(work, 'agent')
        self.assertEqual(hashlib.sha256(self.pipe.original_bytes(work, 'agent')).hexdigest(), self.pipe.get(work)['sha256'])
        with self.assertRaises(PermissionError):
            self.pipe.original_bytes(work, 'another')
        with self.assertRaises(ValueError):
            self.pipe.claim(work, 'another')
        self.time[0] += timedelta(seconds=901)
        with self.assertRaises(PermissionError):
            self.pipe.original_bytes(work, 'agent')

    # ---- processing
    def test_region_is_covered_sizes_are_made_and_metadata_is_gone(self):
        raw = photo(size=(2000, 3000), orientation=6, gps=True, plate=[1400, 900, 1500, 1300])  # stored on its side
        self.upload(raw)
        self.take_in()
        work = self.pipe.queue()[0]['id']
        self.pipe.claim(work, 'agent')
        with Image.open(io.BytesIO(raw)) as im:
            self.assertTrue(im.getexif().get(0x8825), 'the sample original carries a GPS block')
        upright_plate = [1700, 1400, 2100, 1500]  # upright the picture is 3000 x 2000 and the stripes lie where a viewer sees them
        done = self.pipe.prepare(work, 'agent', [{'kind': 'PLATE', 'box': upright_plate}])
        self.assertEqual((done['status'], sorted(done['variants'])), ('PREPARED', sorted(VARIANTS)))
        for variant, edge in VARIANTS.items():
            asset = self.pipe.media.verify(done['variants'][variant])
            with Image.open(asset['local_path']) as im:
                self.assertEqual((im.format, im.size), ('JPEG', (edge, round(edge * 2 / 3))))
                self.assertEqual(len(im.getexif()), 0, 'no EXIF, so no GPS and no orientation tag')
                k = edge / 3000
                left, top, right, bottom = [round(v * k) for v in upright_plate]
                low, high = im.crop((left + 3, top + 3, right - 3, bottom - 3)).convert('L').getextrema()
                self.assertLess(high - low, 60, 'the black and white stripes are gone: %d' % (high - low))
                self.assertEqual(max(abs(a - b) for a, b in zip(im.getpixel((10, 10)), (70, 90, 110))) <= 4, True, 'the rest keeps its colour')
        trust, note = self.rows('SELECT review_trust,note FROM ops_assets LIMIT 1')[0]
        self.assertEqual(trust, 'AGENT_DECLARED_MASKS')
        self.assertEqual(json.loads(note)['masks'], [{'kind': 'PLATE', 'box': upright_plate}])
        self.assertEqual(self.files('tmp'), [])
        self.assertEqual((self.media_root / self.files('originals')[0]).read_bytes(), raw, 'the original is untouched')

    def test_without_the_cover_the_stripes_stay_so_the_check_above_means_something(self):
        done = self.prepared(masks=[{'kind': 'FACE', 'box': [0, 0, 100, 100]}])
        with Image.open(self.pipe.media.verify(done['variants']['FULL'])['local_path']) as im:
            k = 1600 / 3000
            low, high = im.crop([round(v * k) for v in PLATE]).convert('L').getextrema()
        self.assertGreater(high - low, 200)

    def test_a_small_original_is_not_blown_up_and_png_is_accepted(self):
        self.upload(photo(size=(640, 480), fmt='PNG'))
        self.take_in()
        work = self.pipe.queue()[0]['id']
        self.pipe.claim(work, 'agent')
        done = self.pipe.prepare(work, 'agent', [], nothing_to_mask=True)
        sizes = set()
        for asset in done['variants'].values():
            with Image.open(self.pipe.media.verify(asset)['local_path']) as im:
                sizes.add(im.size)
        self.assertEqual(sizes, {(640, 480)})

    def test_no_variant_without_regions_or_an_outright_declaration(self):
        work = self.one()
        self.pipe.claim(work, 'agent')
        for masks, nothing in (([], False), ([{'kind': 'PLATE', 'box': PLATE}], True), ([{'kind': 'LOGO', 'box': PLATE}], False),
                               ([{'kind': 'PLATE', 'box': [0, 0, 4000, 10]}], False), ([{'kind': 'PLATE', 'box': [5, 5, 5, 9]}], False),
                               ([{'kind': 'PLATE', 'box': [0.5, 0, 10, 10]}], False)):
            with self.assertRaises(ValueError):
                self.pipe.prepare(work, 'agent', masks, nothing)
        self.assertEqual(self.pipe.get(work)['variants'], {})
        self.assertEqual(self.files('prepared'), [])

    # ---- review
    def test_draft_names_the_platform_waits_for_gev_and_an_upload_alone_gets_nowhere(self):
        new = self.one()
        with self.assertRaises(ValueError):
            self.submit([new])
        self.pipe.claim(new, 'agent')
        done = self.pipe.prepare(new, 'agent', [{'kind': 'PLATE', 'box': PLATE}])
        with self.assertRaises(ValueError):
            self.submit([new], platform='SOMEWHERE')
        task = self.submit([new], platform='SITE')
        self.assertEqual((task['status'], task['draft']['destination'], task['draft']['action']), ('READY_REVIEW', 'SITE', 'PHOTO_BATCH'))
        self.assertEqual([a['id'] for a in task['draft']['assets']], [done['variants'][PLATFORMS['SITE']]])
        self.assertEqual(self.pipe.sync(), [])
        self.assertEqual((self.pipe.get(new)['status'], self.pipe.get(new)['platform']), ('IN_REVIEW', 'SITE'))
        self.assertFalse(self.pipe.ops.report(self.day)['publishing_enabled'])
        with self.assertRaises(ValueError):
            self.pipe.ops.approve(task['id'], task['digest'], 'AGENT', 'SAMPLE')
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.assertEqual(self.pipe.sync(), [{'id': new, 'status': 'APPROVED'}])
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE: placed by hand, link recorded')
        self.assertEqual(self.pipe.sync(), [{'id': new, 'status': 'PUBLISHED'}])
        kinds = [k for (k,) in self.rows('SELECT kind FROM media_work_events WHERE work_id=? ORDER BY id', (new,))]
        self.assertEqual(kinds, ['TAKEN_IN', 'CLAIMED', 'PREPARED', 'SUBMIT_STARTED', 'SUBMITTED_FOR_REVIEW', 'APPROVED_BY_GEV', 'PUBLICATION_RECORDED'])

    def test_a_submit_cut_off_is_finished_or_undone_from_what_the_task_holds(self):
        # Finding 6: the draft was already READY_REVIEW while the work still said PREPARED, and the rollback went ahead.
        work = self.prepared()['id']
        with patch.object(self.pipe, '_sync', side_effect=RuntimeError('the process died right after the draft was written')):
            with self.assertRaises(RuntimeError):
                self.submit([work])
        task = self.rows("SELECT id,status FROM ops_tasks WHERE job='MEDIA_INBOX'")
        self.assertEqual((self.pipe.get(work)['status'], task[0][1]), ('SUBMITTING', 'READY_REVIEW'))
        with self.assertRaises(ValueError):
            media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        # even with a work status that says nothing, the rollback reads the task itself and refuses
        self.rows("UPDATE media_work SET status='PREPARED'")
        with self.assertRaises(ValueError):
            media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        self.assertFalse((self.base / 'history.json').exists())
        self.rows("UPDATE media_work SET status='SUBMITTING'")
        self.assertEqual(self.pipe.sync(), [{'id': work, 'status': 'IN_REVIEW'}], 'finished from what the task holds')
        self.assertEqual(self.pipe.sync(), [])
        # cut off, or refused, BEFORE the draft: the work goes back to PREPARED and can be submitted again
        self.pipe.ops.revise(task[0][0], 'SAMPLE: sent back')
        self.assertEqual(self.pipe.sync(), [{'id': work, 'status': 'PREPARED'}])
        with patch.object(self.pipe.ops, 'draft', side_effect=ValueError('SAMPLE: the draft was refused')):
            with self.assertRaises(ValueError):
                self.submit([work])
        self.assertEqual((self.pipe.get(work)['status'], self.pipe.get(work)['platform']), ('PREPARED', None))
        kinds = [k for (k,) in self.rows('SELECT kind FROM media_work_events WHERE work_id=? ORDER BY id', (work,))]
        self.assertEqual(kinds[-5:], ['SUBMIT_STARTED', 'SUBMITTED_FOR_REVIEW', 'SENT_BACK', 'SUBMIT_STARTED', 'SUBMIT_NOT_COMPLETED'])

    def test_sent_back_by_gev_returns_to_prepared_and_can_be_redone(self):
        work = self.prepared()['id']
        task = self.submit([work])
        self.pipe.ops.revise(task['id'], 'SAMPLE: one more plate in the background')
        self.assertEqual(self.pipe.sync(), [{'id': work, 'status': 'PREPARED'}])
        self.assertIsNone(self.pipe.get(work)['platform'])
        first = self.pipe.get(work)['variants']
        self.pipe.reopen(work, 'SAMPLE: cover the second plate')
        self.pipe.claim(work, 'agent')
        again = self.pipe.prepare(work, 'agent', [{'kind': 'PLATE', 'box': PLATE}, {'kind': 'PLATE', 'box': [800, 1300, 1400, 1600]}])
        self.assertNotEqual(again['variants'], first)
        self.assertEqual(len(self.files('prepared')), 4)
        self.assertEqual(sorted(x['kind'] for x in self.pipe.cleanup()['removed']), ['UNUSED_VARIANT', 'UNUSED_VARIANT'])
        self.assertEqual(len(self.files('prepared')), 2)

    # ---- interruption and failure of processing
    def test_interrupted_processing_is_taken_over_and_its_leftovers_go(self):
        work = self.one()
        self.pipe.claim(work, 'agent-1')
        original_id = self.files('originals')[0]
        half = self.media_root / 'tmp' / work
        half.mkdir(parents=True)
        (half / 'FULL.jpg').write_bytes(b'half written')
        ((oid,),) = self.rows('SELECT original_id FROM media_work')
        stray = self.media_root / 'prepared' / oid
        stray.mkdir(parents=True)
        (stray / ('0' * 64 + '.jpg')).write_bytes(b'stored but never registered')
        self.assertEqual(self.pipe.cleanup()['removed'], [], 'work somebody holds is left alone')
        with self.assertRaises(ValueError):
            self.pipe.claim(work, 'agent-2')
        self.time[0] += timedelta(seconds=901)  # agent-1 never came back
        taken = self.pipe.claim(work, 'agent-2')
        self.assertEqual((taken['attempts'], self.files('tmp')), (2, []))
        with self.assertRaises(PermissionError):
            self.pipe.prepare(work, 'agent-1', [{'kind': 'PLATE', 'box': PLATE}])
        self.pipe.prepare(work, 'agent-2', [{'kind': 'PLATE', 'box': PLATE}])
        self.assertEqual([x['kind'] for x in self.pipe.cleanup()['removed']], ['INTERRUPTED_LEFTOVER'])
        self.assertEqual((len(self.files('prepared')), self.files('originals')), (2, [original_id]))

    def test_failed_attempt_goes_back_to_the_queue_with_its_reason(self):
        work = self.one()
        self.pipe.claim(work, 'agent')
        (self.media_root / 'tmp' / work).mkdir(parents=True)
        back = self.pipe.release(work, 'agent', 'SAMPLE: the picture is too dark to judge')
        self.assertEqual((back['status'], back['attempts'], self.files('tmp')), ('NEW', 1, []))
        self.assertEqual(len(self.files('originals')), 1)

    # ---- clean-up
    def test_clean_up_removes_nothing_of_unfinished_work_and_never_touches_the_portal(self):
        work = self.prepared()['id']
        self.submit([work])
        before = (self.files('originals'), self.files('prepared'), self.names(self.portal_photos), self.names(self.outbox))
        result = self.pipe.cleanup()
        self.assertEqual((result['removed'], result['originals_deleted']), ([], 0))
        self.assertEqual((self.files('originals'), self.files('prepared'), self.names(self.portal_photos), self.names(self.outbox)), before)

    def test_after_the_recorded_publication_the_original_the_final_variant_and_the_record_stay(self):
        work = self.prepared()['id']
        task = self.publish([work])
        digest = self.pipe.get(work)['sha256']
        portal_before = self.names(self.portal_photos)
        self.assertEqual([x['kind'] for x in self.pipe.cleanup()['removed']], ['UNUSED_VARIANT'])
        (original,) = self.files('originals')
        self.assertEqual(sha256(self.media_root / original), digest)
        self.assertEqual(list(self.pipe.get(work)['variants']), ['FULL'])
        self.pipe.media.verify(task['draft']['assets'][0]['id'], task['draft']['assets'][0]['sha256'])
        self.assertEqual(len(self.files('prepared')), 1)
        self.assertEqual((self.rows('SELECT count(*) FROM ops_approvals'), self.rows("SELECT count(*) FROM ops_observations WHERE summary='SAMPLE result'")), ([(1,)], [(1,)]))
        self.assertEqual(self.pipe.cleanup()['removed'], [], 'a second run finds nothing more')
        self.assertEqual(self.names(self.portal_photos), portal_before, 'the portal keeps its own copy: this code cannot write there')
        self.assertEqual(self.take_in()['imported'], 0)


class BackupAndRollback(Base):
    """The way back, tried: what is kept, what goes, what a second run and a restore do."""

    def test_backup_is_a_whole_checked_copy_and_restoring_it_gives_the_state_before(self):
        before = media_rollback.snapshot(self.db)
        made = media_rollback.backup(self.db, self.base / 'before.sqlite')
        self.assertEqual((made['integrity'], made['tables']), ('ok', before))
        with self.assertRaises(OSError):
            media_rollback.backup(self.db, self.base / 'before.sqlite')   # never over an existing copy
        work = self.prepared()['id']
        self.submit([work])
        self.assertNotEqual(media_rollback.snapshot(self.db), before)
        self.assertEqual(media_rollback.snapshot(self.base / 'before.sqlite'), before, 'the copy did not move with the source')
        restored = self.base / 'restored.sqlite'
        shutil.copyfile(self.base / 'before.sqlite', restored)
        self.assertEqual(media_rollback.snapshot(restored), before)
        self.assertEqual(hashlib.sha256(restored.read_bytes()).hexdigest(), made['sha256'])

    def test_rollback_keeps_the_history_and_leaves_the_other_tables_as_they_were(self):
        untouched = ('ops_tasks', 'ops_observations', 'ops_approvals', 'ops_events', 'orders', 'events')
        before = media_rollback.snapshot(self.db)
        raws = [photo(plate=PLATE), photo(colour=(20, 30, 40))]
        for raw in raws:
            self.upload(raw)
        self.take_in()
        first = self.pipe.queue()[0]['id']
        self.pipe.claim(first, 'agent')
        self.pipe.prepare(first, 'agent', [{'kind': 'PLATE', 'box': PLATE}])
        history = self.rows('SELECT work_id,kind FROM media_work_events ORDER BY id')
        result = media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        self.assertEqual((result['done'], len(result['originals_removed']), result['originals_kept_only_copy'], result['variants_removed']), (True, 2, [], 2))
        archive = json.loads((self.base / 'history.json').read_text(encoding='utf-8'))
        self.assertEqual([(e['work_id'], e['kind']) for e in archive['media_work_events']], history, 'every accepted work and what happened to it is in the archive')
        self.assertEqual((len(archive['media_work']), len(archive['media_work_sources']), len(archive['ops_originals']), len(archive['ops_assets'])), (2, 2, 2, 2))
        after = media_rollback.snapshot(self.db)
        self.assertEqual(sorted(after), sorted(set(before) - set(media_rollback.TABLES)), 'the four pipeline tables are gone, no other table appeared or went')
        self.assertEqual({t: after[t] for t in untouched}, {t: before[t] for t in untouched})
        self.assertEqual((after['ops_originals'], after['ops_assets']), (before['ops_originals'], before['ops_assets']))
        self.assertEqual((self.files('originals'), self.files('prepared'), self.files('tmp')), ([], [], []))
        for raw in raws:   # the photos are whole where they came from
            self.assertIn(hashlib.sha256(raw).hexdigest(), {sha256(f) for f in self.outbox.glob('*.jpg')})
        # a second run finds nothing and does not write over the archive
        self.assertEqual(media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')['done'], False)
        # and the pipeline can be put in again: the same photos come back once each
        again = MediaPipeline(self.db, self.media_root)
        self.assertEqual(again.intake(self.outbox)['imported'], 2)
        self.assertEqual(again.intake(self.outbox)['known'], 2)

    def test_rollback_never_removes_an_original_the_inbox_had_before_the_pipeline(self):
        # Finding 1: the same picture came in from another source first; the rollback deleted that row and its file,
        # and the row was not even in the archive.
        raw = photo(plate=PLATE)
        elsewhere = self.base / 'from-elsewhere.jpg'
        elsewhere.write_bytes(raw)
        first = self.pipe.media.original(elsewhere, 'OPERATOR: sent by WhatsApp on 01.10.2026', 'SAMPLE permission reference')
        self.upload(raw)
        self.assertEqual(self.take_in()['imported'], 1)
        work = self.pipe.queue()[0]['id']
        self.assertEqual(self.rows('SELECT original_id,owns_original FROM media_work'), [(first['id'], 0)], 'the work uses the original; it did not make it')
        self.pipe.claim(work, 'agent')
        self.pipe.prepare(work, 'agent', [{'kind': 'PLATE', 'box': PLATE}])
        stranger = self.media_root / 'prepared' / first['id'] / 'in-progress-of-somebody-else.jpg'
        stranger.write_bytes(b'not registered yet')
        self.assertEqual(self.pipe.cleanup()['removed'], [], 'beside an original it did not make the clean-up sweeps no unnamed file')
        result = media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual((result['originals_removed'], result['originals_kept_not_made_by_the_pipeline'], result['variants_removed']), ([], [digest], 2))
        self.assertEqual(self.rows('SELECT id,provenance FROM ops_originals'), [(first['id'], 'OPERATOR: sent by WhatsApp on 01.10.2026')])
        self.assertEqual((self.media_root / first['path']).read_bytes(), raw)
        self.assertTrue(stranger.exists())
        archive = json.loads((self.base / 'history.json').read_text(encoding='utf-8'))
        self.assertEqual([o['id'] for o in archive['ops_originals']], [first['id']], 'what the work used is in the archive too')

    def test_rollback_never_removes_an_original_that_is_the_only_copy(self):
        raw = photo(plate=PLATE)
        ident = self.upload(raw)
        self.take_in()
        for f in self.outbox.iterdir():   # the portal no longer holds it in the outbox
            f.chmod(0o600)
            f.unlink()
        result = media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        self.assertEqual((result['originals_removed'], result['originals_kept_only_copy']), ([], [hashlib.sha256(raw).hexdigest()]))
        (original,) = self.files('originals')
        self.assertEqual((self.media_root / original).read_bytes(), raw)
        self.assertEqual(self.rows('SELECT count(*) FROM ops_originals'), [(1,)], 'its inbox row stays with it')
        self.assertIn(ident, json.dumps(json.loads((self.base / 'history.json').read_text(encoding='utf-8'))['media_work_sources']))

    def test_rollback_keeps_published_work_whole_and_waits_for_gev_on_an_open_draft(self):
        work = self.prepared()['id']
        task = self.submit([work])
        with self.assertRaises(ValueError):
            media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        self.assertFalse((self.base / 'history.json').exists())
        self.assertEqual(len(self.pipe.queue()), 1, 'nothing was changed by the refused run')
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE result')
        self.pipe.sync()
        result = media_rollback.rollback(self.db, self.media_root, self.outbox, self.base / 'history.json')
        self.assertEqual((result['kept_published'], result['originals_removed']), ([work], []))
        self.assertEqual(len(self.files('originals')), 1)
        self.pipe.media.verify(task['draft']['assets'][0]['id'], task['draft']['assets'][0]['sha256'])
        self.assertEqual((self.rows('SELECT count(*) FROM ops_approvals'), self.rows("SELECT status FROM ops_tasks WHERE job='MEDIA_INBOX'")), ([(1,)], [('DONE',)]))


if __name__ == '__main__':
    unittest.main()
