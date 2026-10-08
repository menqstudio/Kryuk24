"""Tests of the media pipeline on temporary folders. The portal side is the real portal Store; no network."""
import io
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

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


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.portal_db, self.portal_photos = base / 'portal.sqlite', base / 'portal-photos'
        self.portal = Store(self.portal_db, self.portal_photos)
        self.time = [datetime.now(timezone.utc)]
        self.media_root = base / 'media'
        self.pipe = MediaPipeline(base / 'runtime.sqlite', self.media_root, clock=lambda: self.time[0])
        self.day = datetime.now(YEREVAN).date().isoformat()
        self.pipe.ops.plan(self.day)

    def tearDown(self):
        for f in Path(self.tmp.name).rglob('*'):
            if f.is_file():
                f.chmod(0o600)  # stored media is read-only; Windows refuses to delete it otherwise
        self.tmp.cleanup()

    def upload(self, raw=None, actor='armen', purpose='WORK'):
        return self.portal.photo(actor, raw or photo(plate=PLATE), purpose)['id']

    def take_in(self):
        return self.pipe.intake_portal(self.portal_db, self.portal_photos)

    def one(self):
        self.upload()
        self.take_in()
        return self.pipe.queue()[0]['id']

    def prepared(self, masks=None):
        work = self.one()
        self.pipe.claim(work, 'agent')
        return self.pipe.prepare(work, 'agent', masks if masks is not None else [{'kind': 'PLATE', 'box': PLATE}])

    def rows(self, sql, args=()):
        c = sqlite3.connect(self.pipe.runtime.path)  # closed by hand: on Windows an open file cannot be deleted
        try:
            return c.execute(sql, args).fetchall()
        finally:
            c.close()

    def files(self, folder):
        return sorted(f.relative_to(self.media_root).as_posix() for f in (self.media_root / folder).rglob('*') if f.is_file()) if (self.media_root / folder).is_dir() else []

    def submit(self, works, platform='YANDEX_BUSINESS'):
        return self.pipe.submit(works, self.day, 'agent', platform, 'KRYUK24', 'SAMPLE batch', 'SAMPLE reason')

    # ---- intake
    def test_upload_becomes_one_original_and_one_work_with_its_facts(self):
        raw = photo(plate=PLATE)
        ident = self.upload(raw, purpose='EQUIPMENT')
        self.assertEqual(self.take_in(), {'seen': 1, 'imported': 1, 'known': 0, 'duplicates': 0, 'mismatched': 0, 'refused_storage': 0, 'excluded': 0})
        (work,) = self.pipe.queue()
        self.assertEqual((work['status'], work['actor'], work['purpose'], work['format'], work['attempts']), ('NEW', 'armen', 'EQUIPMENT', 'JPEG', 0))
        self.assertEqual(work['sha256'], __import__('hashlib').sha256(raw).hexdigest())
        self.assertTrue(datetime.fromisoformat(work['uploaded']).tzinfo)
        self.assertNotIn('path', json.dumps(work))
        source = self.rows('SELECT source,source_id,work_id FROM media_work_sources')
        (original,) = self.rows('SELECT provenance,permission FROM ops_originals')
        self.assertEqual(source, [('ARMEN_PORTAL', ident, work['id'])])
        self.assertIn('photo=' + ident, original[0])
        self.assertIn('not a publication permission', original[1])
        self.assertEqual((self.media_root / self.files('originals')[0]).read_bytes(), raw, 'the original is kept byte for byte')

    def test_repeat_makes_no_second_original_and_no_second_work(self):
        raw = photo(plate=PLATE)
        self.upload(raw)
        self.take_in()
        self.assertEqual(self.take_in()['known'], 1)
        self.assertTrue(self.portal.photo('armen', raw, 'WORK')['duplicate'], 'the portal itself stores the same bytes once')
        self.upload(raw, actor='second-account')  # the same bytes under another portal id
        result = self.take_in()
        self.assertEqual((result['imported'], result['duplicates'], result['known']), (0, 1, 1))
        self.assertEqual(len(self.pipe.queue()), 1)
        self.assertEqual(len(self.files('originals')), 1)
        self.assertEqual(self.take_in()['known'], 2)

    def test_a_photo_marked_as_a_test_in_the_portal_never_enters_the_inbox(self):
        test = self.upload(photo(colour=(9, 9, 9)))
        real = self.upload(photo(plate=PLATE))
        self.portal.exclude('photo', test, 'SAMPLE: a test under the account', 'GEV')
        result = self.take_in()
        self.assertEqual((result['seen'], result['imported'], result['excluded']), (2, 1, 1))
        self.assertEqual(len(self.pipe.queue()), 1)
        self.assertEqual(self.rows('SELECT source_id FROM media_work_sources'), [(real,)])
        self.assertEqual(len(self.files('originals')), 1)

    def test_a_portal_file_that_is_not_what_was_recorded_is_not_taken_in(self):
        self.upload()
        (file,) = [f for f in self.portal_photos.iterdir() if 'preview' not in f.name]
        file.chmod(0o600)
        file.write_bytes(photo(colour=(1, 2, 3)))
        self.assertEqual(self.take_in()['mismatched'], 1)
        self.assertEqual(self.pipe.queue(), [])
        self.assertEqual(self.files('originals'), [])

    def test_intake_stops_at_the_storage_limit_and_reports_it(self):
        self.pipe.limit = 1000
        self.upload()
        self.assertEqual(self.take_in()['refused_storage'], 1)
        self.assertEqual(self.pipe.queue(), [])
        self.pipe.limit = 10 ** 9
        self.assertEqual(self.take_in()['imported'], 1)
        self.pipe.limit = self.pipe.used()
        self.assertEqual(self.pipe.storage(self.portal_photos)['status'], 'FULL')
        self.pipe.limit = int(self.pipe.used() / 0.9)
        report = self.pipe.storage(self.portal_photos)
        self.assertEqual((report['status'], report['work']['NEW'], report['media_root']['originals']['files'], report['portal_photos']['files']), ('WARN', 1, 1, 2))

    # ---- the agent's limited access
    def test_only_the_worker_holding_the_lease_reads_the_original(self):
        work = self.one()
        with self.assertRaises(PermissionError):
            self.pipe.original_bytes(work, 'agent')
        self.pipe.claim(work, 'agent')
        self.assertEqual(__import__('hashlib').sha256(self.pipe.original_bytes(work, 'agent')).hexdigest(), self.pipe.get(work)['sha256'])
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
        # Upright the picture is 3000 x 2000 and the stripes lie where a viewer sees them.
        upright_plate = [1700, 1400, 2100, 1500]
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
        report = self.pipe.ops.report(self.day)
        self.assertFalse(report['publishing_enabled'])
        with self.assertRaises(ValueError):
            self.pipe.ops.approve(task['id'], task['digest'], 'AGENT', 'SAMPLE')
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.assertEqual(self.pipe.sync(), [{'id': new, 'status': 'APPROVED'}])
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE: placed by hand, link recorded')
        self.assertEqual(self.pipe.sync(), [{'id': new, 'status': 'PUBLISHED'}])
        kinds = [k for (k,) in self.rows('SELECT kind FROM media_work_events WHERE work_id=? ORDER BY id', (new,))]
        self.assertEqual(kinds, ['TAKEN_IN', 'CLAIMED', 'PREPARED', 'SUBMITTED_FOR_REVIEW', 'APPROVED_BY_GEV', 'PUBLICATION_RECORDED'])

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

    # ---- interruption and failure
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
    def test_nothing_of_unfinished_work_is_removed(self):
        work = self.prepared()['id']
        self.submit([work])
        before = (self.files('originals'), self.files('prepared'), sorted(f.name for f in self.portal_photos.iterdir()))
        result = self.pipe.cleanup(self.portal_photos)
        self.assertEqual((result['removed'], result['originals_deleted']), ([], 0))
        self.assertEqual((self.files('originals'), self.files('prepared'), sorted(f.name for f in self.portal_photos.iterdir())), before)

    def test_after_the_recorded_publication_one_original_the_final_variant_and_the_record_stay(self):
        work = self.prepared()['id']
        task = self.submit([work], platform='YANDEX_BUSINESS')
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE result')
        self.pipe.sync()
        digest = self.pipe.get(work)['sha256']
        result = self.pipe.cleanup(self.portal_photos)
        self.assertEqual(sorted(x['kind'] for x in result['removed']), ['PORTAL_SECOND_COPY', 'UNUSED_VARIANT'])
        (original,) = self.files('originals')
        self.assertEqual(sha256(self.media_root / original), digest, 'the one original is the inbox copy, intact')
        self.assertEqual([f.name for f in self.portal_photos.iterdir() if 'preview' not in f.name], [], "the portal's second copy is gone")
        self.assertEqual(len([f for f in self.portal_photos.iterdir() if 'preview' in f.name]), 1, "the portal's preview stays")
        self.assertEqual(list(self.pipe.get(work)['variants']), ['FULL'])
        self.pipe.media.verify(task['draft']['assets'][0]['id'], task['draft']['assets'][0]['sha256'])
        self.assertEqual(len(self.files('prepared')), 1)
        self.assertEqual(self.rows('SELECT count(*) FROM ops_approvals'), [(1,)])
        self.assertEqual(self.rows("SELECT count(*) FROM ops_observations WHERE summary='SAMPLE result'"), [(1,)])
        self.assertEqual(self.pipe.cleanup(self.portal_photos)['removed'], [], 'a second run finds nothing more')
        self.assertTrue(self.portal.photo('armen', photo(plate=PLATE), 'WORK')['duplicate'], 'the portal still knows the picture')
        self.assertEqual(self.take_in()['imported'], 0)

    def test_the_portal_copy_stays_when_the_inbox_original_is_not_provably_there(self):
        work = self.prepared()['id']
        task = self.submit([work])
        self.pipe.ops.approve(task['id'], task['digest'], 'GEV', 'SAMPLE approval reference')
        self.pipe.ops.finish_approved(task['id'], task['digest'], 'SAMPLE result source', 'SAMPLE result')
        self.pipe.sync()
        original = self.media_root / self.files('originals')[0]
        original.chmod(0o600)
        original.write_bytes(b'damaged')
        kinds = [x['kind'] for x in self.pipe.cleanup(self.portal_photos)['removed']]
        self.assertNotIn('PORTAL_SECOND_COPY', kinds)
        self.assertEqual(len([f for f in self.portal_photos.iterdir() if 'preview' not in f.name]), 1)


if __name__ == '__main__':
    unittest.main()
