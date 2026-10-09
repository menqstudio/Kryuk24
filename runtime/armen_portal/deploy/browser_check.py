"""The portal's pages in a real browser (Chromium) at phone widths, against a local portal with SAMPLE data.

    python runtime/armen_portal/deploy/browser_check.py OUT_FOLDER

Needs playwright with Chromium, Pillow and the `openssl` command. Not part of CI.
How it is real: Chromium opens https://runtime.kryuk24.ru/operator/work/armen/ itself; the host name is pointed at
a portal started here (the same portal.py, a temporary database, a SAMPLE password) behind a throwaway certificate.
So cookies, the Origin check, the content security policy and uploads behave as in production. No request is
rewritten, except one answer that is refused on purpose to see a partial failure.
What it is not: not the server, not Nginx, not a phone, not Armen's account.

Checked at 360, 390 and 430 px: no sideways scroll at any step; nothing is sent by picking a photo or an answer;
a refused file type; removing a picked photo; the upload after the button and the server's own result; a second
tap; answers saved by the button; one refused answer does not show as success and the choice stays; saving again
makes no second row; sign-out. Screenshots of every step are written to OUT_FOLDER.
"""
import io
import json
import ssl
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import portal  # noqa: E402

SAMPLE = 'SAMPLE-password-not-real-123'
URL = 'https://runtime.kryuk24.ru/operator/work/armen/'
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
failures = []
sys.stdout.reconfigure(encoding='utf-8')  # the labels hold Russian words; a redirected Windows console would refuse them


def check(label, condition, detail=''):
    print(('ok   ' if condition else 'FAIL ') + label + (' ' + str(detail) if detail and not condition else ''))
    if not condition:
        failures.append(label)


def picture(path, colour, text):
    im = Image.new('RGB', (1600, 1200), colour)
    ImageDraw.Draw(im).text((60, 60), 'SAMPLE ' + text, fill=(255, 255, 255))
    im.save(path, 'JPEG', quality=85)


def run(width, theme, pw, base):
    tmp = tempfile.TemporaryDirectory()
    store = portal.Store(tmp.name + '/db', tmp.name + '/photos')
    http = portal.server(store, {'armen': portal.credential(SAMPLE)}, 'https://runtime.kryuk24.ru', 0)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(base / 'cert.pem', base / 'key.pem')
    http.socket = context.wrap_socket(http.socket, server_side=True)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    tag = '%d-%s' % (width, theme)

    def rows(sql):
        with store.db() as c:
            return c.execute(sql).fetchall()

    browser = pw.chromium.launch(args=['--host-rules=MAP runtime.kryuk24.ru 127.0.0.1:%d' % http.server_port])
    ctx = browser.new_context(viewport={'width': width, 'height': 800}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              ignore_https_errors=True, color_scheme=theme, locale='ru-RU')
    page = ctx.new_page()
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))

    def wait(selector, text):
        # By a selector, not by evaluated script text: the page's content security policy refuses eval, as it should.
        page.locator(selector).filter(has_text=text).first.wait_for(timeout=20000)

    def shot(name):
        wide = page.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
        check('%s %s: no sideways scroll' % (tag, name), wide[0] <= wide[1], wide)
        # the band's content and the page's column keep to the container (960 px, the operator page's), also on a wide screen:
        # on 09.10.2026 the login page was installed stretched over a whole desktop window and no check saw it
        columns = page.evaluate("[...document.querySelectorAll('.top .wrap, main')].map(e => Math.round(e.getBoundingClientRect().width))")
        check('%s %s: the band and the column are not wider than the container' % (tag, name), len(columns) == 2 and max(columns) <= 960, columns)
        page.screenshot(path=str(out / ('%s-%s.png' % (tag, name))), full_page=True)

    page.goto(URL)
    page.wait_for_selector('#login')
    page.evaluate('document.fonts.ready')
    # one family for text and headings, as on the operator page (Golos Text, one variable file for 400 to 700)
    check('%s the page uses the design font, regular and bold, and its heading is set in it' % tag,
          page.evaluate("document.fonts.check('16px \"Golos Text\"', 'Вход') && document.fonts.check('700 16px \"Golos Text\"', 'Вход')")
          and page.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily").strip('\'"').startswith('Golos Text'))
    check('%s the band shows the logo for a dark ground and Bro\'s picture, both loaded' % tag,
          page.evaluate("[...document.querySelectorAll('.top img')].map(i => [i.getAttribute('src'), i.complete && i.naturalWidth > 0])") == [['logo-dark.webp', True], ['bro.webp', True]])
    shot('1-login')
    page.fill('#password', SAMPLE)
    page.click('#login button')
    page.wait_for_selector('#questions .question')
    shot('2-page')

    # photos: picked is not sent
    picture(base / 'a.jpg', (40, 70, 110), 'A')
    picture(base / 'b.jpg', (110, 70, 40), 'B')
    (base / 'notes.txt').write_text('not a picture')
    page.set_input_files('#gallery', [str(base / 'a.jpg'), str(base / 'b.jpg'), str(base / 'notes.txt')])
    page.wait_for_selector('#pending li:nth-child(3)')
    page.wait_for_timeout(600)  # the previews are decoded from the picked files
    check('%s picking photos sends nothing' % tag, rows('SELECT count(*) FROM armen_photos')[0][0] == 0)
    check('%s previews are shown for the two pictures' % tag, page.evaluate("[...document.querySelectorAll('#pending img')].filter(i => i.naturalWidth > 0).length") == 2)
    check('%s the text file is refused with a reason' % tag, 'Нужен JPEG' in page.inner_text('#pending li:nth-child(3)'))
    check('%s the button counts what will be sent' % tag, page.inner_text('#send') == 'Загрузить фото (2)')
    shot('3-photos-picked')
    page.click('#pending li:nth-child(3) button')
    check('%s a picked item can be removed' % tag, page.locator('#pending li').count() == 2)
    # what is on the photos: three chips, one always picked, no drop-down
    check('%s the photo kind is three chips with the first picked, and no drop-down' % tag,
          page.locator('select').count() == 0 and [b.get_attribute('aria-pressed') for b in page.locator('#purpose button').all()] == ['true', 'false', 'false'])
    page.click('#purpose button[data-value=EQUIPMENT]')
    page.click('#purpose button[data-value=EQUIPMENT]')   # a second tap leaves it picked: a photo always has a kind
    check('%s a tap picks another kind and exactly one stays picked' % tag, [b.get_attribute('aria-pressed') for b in page.locator('#purpose button').all()] == ['false', 'true', 'false'])
    page.dblclick('#send')  # a double tap
    wait('#upload-status', 'Сохранено')
    check('%s after the button both are stored once, a double tap adds nothing' % tag, rows('SELECT count(*) FROM armen_photos')[0][0] == 2)
    check('%s the picked kind is the one the server stored' % tag, [r[0] for r in rows('SELECT DISTINCT purpose FROM armen_photos')] == ['EQUIPMENT'])
    check('%s the result is the server\'s, next to the button' % tag, page.inner_text('#upload-status') == 'Сохранено: 2 из 2' and page.locator('#pending .state.ok').count() == 2, page.inner_text('#upload-status'))
    page.locator('#photos img').nth(1).wait_for(timeout=20000)
    shot('4-photos-saved')
    page.set_input_files('#gallery', [str(base / 'a.jpg')])  # the same picture once more
    page.click('#send')
    wait('#pending', 'Уже было загружено')
    check('%s the same picture again makes no second photo and says so' % tag, rows('SELECT count(*) FROM armen_photos')[0][0] == 2 and 'Уже было загружено' in page.inner_text('#pending'))

    # answers: a second tap takes a pick back (Gev, 09.10.2026: there was no way to cancel a pick)
    first = '#questions .question:nth-child(1) .choices button:nth-child(1)'
    page.click(first)
    picked = (page.get_attribute(first, 'aria-pressed'), page.locator('#questions .note.warn').count(), page.is_disabled('#save'))
    page.click(first)
    back = (page.get_attribute(first, 'aria-pressed'), page.locator('#questions .note.warn').count(), page.is_disabled('#save'), page.inner_text('#save'))
    check('%s a second tap on a picked answer takes it back and nothing is left to save' % tag,
          picked == ('true', 1, False) and back == ('false', 0, True, 'Сохранить ответы') and rows('SELECT count(*) FROM armen_answers')[0][0] == 0, (picked, back))
    # answers: picked is not saved; one is refused on purpose
    for q in (1, 2, 3):
        page.click('#questions .question:nth-child(%d) .choices button:nth-child(1)' % q)
    check('%s picking answers saves nothing' % tag, rows('SELECT count(*) FROM armen_answers')[0][0] == 0)
    page.evaluate("document.querySelector('#questions .question').scrollIntoView()")
    box = page.locator('#save').bounding_box()
    check('%s with unsaved choices the save button is on the screen while the first question is at the top' % tag, box and box['y'] >= 0 and box['y'] + box['height'] <= 800, box)
    check('%s every choice is at least 44 px high' % tag, page.evaluate("Math.min(...[...document.querySelectorAll('.choices button')].map(b => b.getBoundingClientRect().height))") >= 44)
    print('     %s height of the questions card: %d px' % (tag, page.evaluate("document.getElementById('questions').parentElement.getBoundingClientRect().height")))
    check('%s each picked answer says it is not saved yet' % tag, page.locator('#questions .note.warn').count() == 3)
    shot('5-answers-picked')
    refused = []

    def refuse(route):
        if json.loads(route.request.post_data)['question'] == 'inquiries' and not refused:
            refused.append(1)
            return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'Не сохранилось. Повторите позже или сообщите Геву.'}))
        route.continue_()

    page.route('**/api/answer', refuse)
    page.click('#save')
    wait('#save-status', 'Сохранено 2 из 3')
    check('%s two saved, one refused: not shown as all saved' % tag, rows('SELECT count(*) FROM armen_answers')[0][0] == 2 and page.locator('#save-status.error').count() == 1)
    check('%s the refused answer keeps its choice and its own message' % tag, page.get_attribute('#questions .question:nth-child(2) .choices button:nth-child(1)', 'aria-pressed') == 'true'
          and 'Не сохранилось' in page.inner_text('#questions .question:nth-child(2) p.note.error') and page.inner_text('#save') == 'Сохранить ответы (1)')
    shot('6-answers-partly-saved')
    page.dblclick('#save')
    wait('#save-status', 'Сохранено: 1 из 1')
    check('%s saved after the second try, a double tap makes no second row' % tag, rows('SELECT count(*) FROM armen_answers')[0][0] == 3 and rows('SELECT count(*) FROM armen_commands')[0][0] == 3)
    check('%s every saved answer says Сохранено beside it' % tag, page.locator('#questions .note.ok').count() == 3)
    shot('7-answers-saved')
    page.reload()
    page.wait_for_selector('#questions .question')
    check('%s after a reload the saved answers are the pressed ones' % tag, page.locator('#questions button[aria-pressed=true]').count() == 3 and page.locator('#photos img').count() == 2)

    page.click('#logout')
    page.wait_for_selector('#login')
    check('%s sign-out returns to the login form and the cookie no longer opens the page' % tag, page.goto(URL + 'api/state').status == 401)
    check('%s no error in the browser console' % tag, [e for e in errors if '503' not in e and '401' not in e] == [], errors)
    browser.close()
    http.shutdown()
    http.server_close()
    tmp.cleanup()


with tempfile.TemporaryDirectory() as folder:
    base = Path(folder)
    # Its own small config: an openssl without a default config file works too, and no argument starts with a slash.
    (base / 'openssl.cnf').write_text('[req]\ndistinguished_name=dn\nprompt=no\nx509_extensions=v3\n[dn]\nCN=runtime.kryuk24.ru\n[v3]\nsubjectAltName=DNS:runtime.kryuk24.ru\n')
    made = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(base / 'key.pem'), '-out', str(base / 'cert.pem'),
                           '-days', '2', '-config', str(base / 'openssl.cnf')], capture_output=True, text=True)
    if made.returncode != 0:
        sys.exit('the throwaway certificate was not made: ' + made.stderr.strip()[-600:])
    with sync_playwright() as pw:
        for width, theme in ((360, 'light'), (390, 'light'), (430, 'light'), (390, 'dark'), (1280, 'light'), (1280, 'dark')):
            run(width, theme, pw, base)
print('FAILED: %d' % len(failures) if failures else 'all browser checks passed')
sys.exit(1 if failures else 0)
