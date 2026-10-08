"""Helper of chain_rehearsal.sh. SAMPLE pictures and SAMPLE passwords only; never a real account or a real photo.

make WORK         three different sample pictures (4000 x 3000 JPEG with a striped 'plate' and a GPS block in EXIF),
                  the mask file for that plate and a sample credential file with the accounts armen and test
upload WORK PORT  over HTTP: as armen picture 0, picture 1, picture 0 again and one answer; as test picture 2 and one answer
plan DB MEDIA     plan today's tasks in the temporary runtime database (the existing Operations.plan)
compare A B       two snapshot files (media_rollback.py snapshot): which tables differ
before DB MEDIA F register file F in the temporary inbox the way another source would (not this pipeline), and print its row
"""
import http.client, io, json, re, sys
from pathlib import Path

SAMPLE = 'SAMPLE-password-not-real-123'
ORIGIN = 'https://runtime.kryuk24.ru'
PREFIX = '/operator/work/armen/'
PLATE = [1800, 2200, 2600, 2400]


def make(work):
    import portal
    from PIL import Image, ImageDraw
    for n, colour in enumerate(((70, 90, 110), (110, 90, 70), (60, 110, 60))):
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
        print('sample-%d.jpg: 4000x3000 JPEG, %.1f MiB' % (n, len(out.getvalue()) / 2 ** 20))
    (work / 'masks.json').write_text(json.dumps([{'kind': 'PLATE', 'box': PLATE}]))
    (work / 'users.json').write_text(json.dumps({'armen': portal.credential(SAMPLE), 'test': portal.credential(SAMPLE)}) + '\n')


def call(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    try:
        c.request(method, PREFIX + path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, r.read(), r.getheader('Set-Cookie')
    finally:
        c.close()


def upload(work, port):
    import portal
    for account, pictures in (('armen', ('sample-0.jpg', 'sample-1.jpg', 'sample-0.jpg')), ('test', ('sample-2.jpg',))):
        status, _, cookie = call(port, 'POST', 'api/login', json.dumps({'username': account, 'password': SAMPLE}), {'Content-Type': 'application/json', 'Origin': ORIGIN})
        cookie = cookie.split(';')[0]
        _, page, _ = call(port, 'GET', '', headers={'Cookie': cookie})
        csrf = re.search(b'name="csrf-token" content="([^"]+)"', page)[1].decode()
        base = {'Origin': ORIGIN, 'Cookie': cookie, 'X-CSRF-Token': csrf}
        for name in pictures:
            status, raw, _ = call(port, 'POST', 'api/photo', (work / name).read_bytes(), {**base, 'Content-Type': 'image/jpeg', 'X-Photo-Purpose': 'WORK'})
            print('%s uploads %s: %s %s' % (account, name, status, raw.decode()))
        status, raw, _ = call(port, 'POST', 'api/answer', json.dumps({'question': 'inquiries', 'answer': 'YES', 'day': portal.day()}),
                              {**base, 'Content-Type': 'application/json', 'Idempotency-Key': ('a' if account == 'armen' else 'b') * 32})
        print('%s answers one question: %s' % (account, status))
        state = json.loads(call(port, 'GET', 'api/state', headers={'Cookie': cookie})[1])
        print('%s sees: %d photos, %d answers, test account: %s, trust: %s' % (account, len(state['photos']), len(state['answers']), state['test_account'], state['trust']))


def compare(a, b):
    one, two = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    differ = sorted(t for t in set(one) | set(two) if one.get(t) != two.get(t))
    print('tables in the first: %d, in the second: %d; tables that differ: %s' % (len(one), len(two), differ or 'none'))


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make(Path(sys.argv[2]))
    elif sys.argv[1] == 'upload':
        upload(Path(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == 'compare':
        compare(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'before':
        from ops_work import Operations
        row = Operations(sys.argv[2], sys.argv[3]).media.original(sys.argv[4], 'OPERATOR: SAMPLE, came in another way before the pipeline', 'SAMPLE permission reference')
        print('in the inbox before the pipeline: %s sha256 %s provenance "%s"' % (row['id'][:17], row['digest'][:12], row['provenance']))
    else:
        from ops_work import Operations
        print(json.dumps(Operations(sys.argv[2], sys.argv[3]).plan()))
