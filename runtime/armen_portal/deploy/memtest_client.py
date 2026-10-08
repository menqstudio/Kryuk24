"""Memory measurement helper for the portal on the server. SAMPLE credentials only, never a real account.

make WORK        test pictures of the largest allowed size and a sample credential file:
                 two different 40 MP JPEG files just under the 20 MiB limit (the largest request bodies) and
                 two 40 MP RGBA PNG files (small files, 160 MiB each once decoded: the largest decode)
run WORK PORT    log in, upload each pair at the same moment over HTTP, read the state and one preview, log out
"""
import http.client, json, os, re, sys, threading, time
from pathlib import Path

SAMPLE = 'SAMPLE-password-not-real-123'
ORIGIN = 'https://runtime.kryuk24.ru'
PREFIX = '/operator/work/armen/'
LIMIT = 20 * 1024 * 1024
PEAK = '/sys/fs/cgroup/system.slice/kryuk-armen-memtest.service/memory.peak'
PAIRS = (('big-%d.jpg', 'image/jpeg'), ('flat-%d.png', 'image/png'))


def make(work):
    sys.path.insert(0, '/opt/kryuk24-armen')
    from PIL import Image, ImageOps
    import portal
    noise = Image.frombytes('RGB', (8000, 5000), os.urandom(8000 * 5000 * 3))
    for n, picture in enumerate((noise, ImageOps.mirror(noise))):
        target = work / ('big-%d.jpg' % n)
        for quality in range(90, 0, -5):
            picture.save(target, 'JPEG', quality=quality)
            if target.stat().st_size <= LIMIT:
                break
        else:
            raise SystemExit('no quality gives a file under the limit')
        print('%s: 8000x5000 noise, quality %d, %.1f MiB' % (target.name, quality, target.stat().st_size / 2 ** 20))
    for n, colour in enumerate(((10, 20, 30, 255), (40, 50, 60, 255))):
        target = work / ('flat-%d.png' % n)
        Image.new('RGBA', (8000, 5000), colour).save(target, 'PNG')
        print('%s: 8000x5000 RGBA, %.2f MiB' % (target.name, target.stat().st_size / 2 ** 20))
    (work / 'users.json').write_text(json.dumps({'armen': portal.credential(SAMPLE)}) + '\n')
    print('sample credential file written')


def call(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    try:
        c.request(method, PREFIX + path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, r.read(), r.getheader('Set-Cookie')
    finally:
        c.close()


def pair(work, port, cookie, csrf, pattern, kind):
    """Both files of one pair sent at the same moment. True when both were saved."""
    raws = [(work / (pattern % n)).read_bytes() for n in (0, 1)]
    gate = threading.Barrier(2)
    results = [None, None]

    def upload(n):
        gate.wait()
        started = time.monotonic()
        status, raw, _ = call(port, 'POST', 'api/photo', raws[n],
                              {'Content-Type': kind, 'Origin': ORIGIN, 'Cookie': cookie,
                               'X-CSRF-Token': csrf, 'X-Photo-Purpose': 'WORK'})
        results[n] = (status, raw.decode()[:120], round(time.monotonic() - started, 2))

    threads = [threading.Thread(target=upload, args=(n,)) for n in (0, 1)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    for n, result in enumerate(results):
        print('upload %s: status %s, %s s, %s' % (pattern % n, result[0], result[2], result[1]))
    try:
        print('peak of the unit so far: %d MiB' % (int(Path(PEAK).read_text()) // 2 ** 20))
    except OSError as e:
        print('peak not readable from here:', e)
    return [r[0] for r in results] == [201, 201]


def run(work, port):
    status, _, cookie = call(port, 'POST', 'api/login', json.dumps({'username': 'armen', 'password': SAMPLE}),
                             {'Content-Type': 'application/json', 'Origin': ORIGIN})
    print('login:', status)
    if status != 200:
        raise SystemExit(1)
    cookie = cookie.split(';')[0]
    status, page, _ = call(port, 'GET', '', headers={'Cookie': cookie})
    csrf = re.search(b'name="csrf-token" content="([^"]+)"', page)[1].decode()
    saved = [pair(work, port, cookie, csrf, pattern, kind) for pattern, kind in PAIRS]
    status, raw, _ = call(port, 'GET', 'api/state', headers={'Cookie': cookie})
    photos = json.loads(raw)['photos']
    print('state:', status, 'photos listed:', len(photos))
    for photo in photos:
        started = time.monotonic()
        status, raw, _ = call(port, 'GET', 'preview/' + photo['id'], headers={'Cookie': cookie})
        print('preview: status %s, %d bytes, starts as JPEG: %s, %.3f s' % (status, len(raw), raw[:3] == b'\xff\xd8\xff', time.monotonic() - started))
    status, _, _ = call(port, 'POST', 'api/logout', headers={'Cookie': cookie, 'Origin': ORIGIN, 'X-CSRF-Token': csrf})
    print('logout:', status)
    status, _, _ = call(port, 'GET', 'api/state', headers={'Cookie': cookie})
    print('state with the cookie after logout:', status)
    if not all(saved):
        raise SystemExit(1)


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make(Path(sys.argv[2]))
    else:
        run(Path(sys.argv[2]), int(sys.argv[3]))
