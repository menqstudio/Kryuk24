"""Helper of chain_rehearsal.sh. SAMPLE pictures and a SAMPLE password only; never a real account or a real photo.

make WORK         two different sample pictures (4000 x 3000 JPEG with a striped 'plate' and a GPS block in EXIF),
                  the mask file for that plate and a sample credential file for the temporary portal
upload WORK PORT  log in to the temporary portal over HTTP and upload: picture 0, picture 1, picture 0 again
plan DB MEDIA     plan today's tasks in the temporary runtime database (the existing Operations.plan)
"""
import http.client, io, json, os, re, sys
from pathlib import Path

SAMPLE = 'SAMPLE-password-not-real-123'
ORIGIN = 'https://runtime.kryuk24.ru'
PREFIX = '/operator/work/armen/'
PLATE = [1800, 2200, 2600, 2400]


def make(work):
    import portal
    from PIL import Image, ImageDraw
    for n, colour in enumerate(((70, 90, 110), (110, 90, 70))):
        im = Image.effect_noise((4000, 3000), 40).convert('RGB')
        im.paste(colour, [0, 0, 4000, 600])
        d = ImageDraw.Draw(im)
        d.rectangle(PLATE, fill=(255, 255, 255))
        for x in range(PLATE[0], PLATE[2], 40):
            d.rectangle([x, PLATE[1], x + 19, PLATE[3]], fill=(0, 0, 0))
        exif = Image.Exif()
        exif[0x8825] = {1: 'N', 2: (55.0, 45.0, 0.0), 3: 'E', 4: (37.0, 37.0, 0.0)}
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=90, exif=exif)
        (work / ('sample-%d.jpg' % n)).write_bytes(out.getvalue())
        print('sample-%d.jpg: 4000x3000 JPEG, %.1f MiB, GPS block in EXIF: %s' % (n, len(out.getvalue()) / 2 ** 20, bool(Image.open(io.BytesIO(out.getvalue())).getexif().get(0x8825))))
    (work / 'masks.json').write_text(json.dumps([{'kind': 'PLATE', 'box': PLATE}]))
    (work / 'users.json').write_text(json.dumps({'armen': portal.credential(SAMPLE)}) + '\n')


def call(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    try:
        c.request(method, PREFIX + path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, r.read(), r.getheader('Set-Cookie')
    finally:
        c.close()


def upload(work, port):
    status, _, cookie = call(port, 'POST', 'api/login', json.dumps({'username': 'armen', 'password': SAMPLE}),
                             {'Content-Type': 'application/json', 'Origin': ORIGIN})
    print('login:', status)
    cookie = cookie.split(';')[0]
    _, page, _ = call(port, 'GET', '', headers={'Cookie': cookie})
    csrf = re.search(b'name="csrf-token" content="([^"]+)"', page)[1].decode()
    for label, name in (('picture 0', 'sample-0.jpg'), ('picture 1', 'sample-1.jpg'), ('picture 0 again', 'sample-0.jpg')):
        status, raw, _ = call(port, 'POST', 'api/photo', (work / name).read_bytes(),
                              {'Content-Type': 'image/jpeg', 'Origin': ORIGIN, 'Cookie': cookie, 'X-CSRF-Token': csrf, 'X-Photo-Purpose': 'WORK'})
        print('upload of %s: %s %s' % (label, status, raw.decode()))
    status, raw, _ = call(port, 'GET', 'api/state', headers={'Cookie': cookie})
    photos = json.loads(raw)['photos']
    status, raw, _ = call(port, 'GET', 'preview/' + photos[0]['id'], headers={'Cookie': cookie})
    print('portal lists %d photos; preview: %s, %d bytes' % (len(photos), status, len(raw)))


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make(Path(sys.argv[2]))
    elif sys.argv[1] == 'upload':
        upload(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        from ops_work import Operations
        print(json.dumps(Operations(sys.argv[2], sys.argv[3]).plan()))
