"""Does the lock-aware store work with THIS Python and THESE files? A check in a temporary folder; no real data.

    python -B selftest.py CODE_DIR

CODE_DIR holds ops_media.py and ops_work.py (and the modules they import). Everything it writes is in a temporary
folder that it removes. It is run by install.sh as the service's user, after the files are in place and before any
service is restarted, and again by the tests. Prints one line and exits 0, or says what failed and exits 1.
"""
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import ops_media  # noqa: E402
import ops_work  # noqa: E402

PNG = b'\x89PNG\r\n\x1a\n'  # the store checks the signature of a file, not its picture


def main():
    if getattr(ops_media.MediaStore, 'LOCKING', 0) != 1:
        raise AssertionError('MediaStore.LOCKING is missing: this is not the lock-aware store')
    tmp = tempfile.mkdtemp(prefix='kryuk-store-selftest-')
    try:
        root = Path(tmp)
        ops = ops_work.Operations(root / 'db.sqlite', root / 'media')
        (root / 'a.png').write_bytes(PNG + b'original')
        (root / 'b.png').write_bytes(PNG + b'variant')
        original = ops.media.original(root / 'a.png', 'SELFTEST', 'SELFTEST')
        again = ops.media.original(root / 'a.png', 'SELFTEST again', 'SELFTEST')
        assert again['id'] == original['id'], 'the same bytes made a second original'
        asset = ops.media.prepared(original['id'], root / 'b.png', 'SELFTEST', reviewed=True)
        ops.media.verify(asset['id'], asset['digest'])
        try:
            ops.media.prepared('ORIGINAL-' + '0' * 32, root / 'b.png', 'SELFTEST', reviewed=True)
            raise AssertionError('a variant was stored for an original that does not exist')
        except ValueError:
            pass
        refused = []
        with ops.media.lock(1):
            with ops.media.lock(1):     # the holder may take it again
                pass

            def other():
                try:
                    with ops.media.lock(0.3):
                        refused.append(False)
                except TimeoutError:
                    refused.append(True)
            t = threading.Thread(target=other)
            t.start()
            t.join(10)
        assert refused == [True], 'another thread took the lock while it was held'
        with ops.media.lock(1):         # and it is free again afterwards
            pass
        ops.plan('2026-01-05')
        task = [t for t in ops.report('2026-01-05')['tasks'] if t['job'] == 'MEDIA_INBOX'][0]['id']
        ops.claim(task, 'selftest')
        done = ops.draft(task, 'selftest', {'action': 'PHOTO_BATCH', 'account': 'SELFTEST', 'destination': 'SELFTEST', 'body': 'SELFTEST', 'reason': 'SELFTEST',
                                            'assets': [{'id': asset['id'], 'sha256': asset['digest']}]})
        assert done['status'] == 'READY_REVIEW', done['status']
        left = [f.name for f in (root / 'media').rglob('.incoming-*')]
        assert not left, 'temporary files left: %s' % left
        files = sorted(f.relative_to(root / 'media').as_posix() for f in (root / 'media').rglob('*') if f.is_file())
        assert len(files) == 3 and '.pipeline.lock' in files, files
    finally:
        for f in Path(tmp).rglob('*'):
            if f.is_file():
                os.chmod(f, 0o600)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print('SELFTEST OK: python %s; one original for the same bytes, a variant, a refused variant for a missing original, the lock held and re-entered, a draft with an asset; temporary folder removed: %s'
          % (sys.version.split()[0], not os.path.exists(tmp)))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('SELFTEST FAILED: %s: %s' % (type(e).__name__, e))
        sys.exit(1)
