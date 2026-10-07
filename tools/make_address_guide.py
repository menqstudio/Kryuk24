"""Видео-шпаргалка для владельца: как снять ролик для подтверждения адреса в Яндекс Бизнесе.

Не само видео для Яндекса (его снимают телефоном на месте, одним дублем), а
пояснение «что и в каком порядке показать». Требования взяты дословно из формы
Яндекса и Справки: yandex.ru/support/business-priority/ru/moderation/moderation-address

Слайды 1080x1920 (вертикаль, под телефон и WhatsApp) рисуются в HTML с нашими же
макетами вывесок из brand/06_signage, затем склеиваются ffmpeg с плавными переходами.

Выход: offers/address_video_guide/
"""
import glob
import os
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

ROOT = B.ROOT
SIG = ROOT / "brand" / "06_signage"
OUT = ROOT / "offers" / "address_video_guide"
W, H, FPS = 1080, 1920, 30
HOLD, FADE = 8.0, 0.6

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;background:#13233A;color:#fff;
 font-family:'Golos Text','Segoe UI',sans-serif;overflow:hidden}
.top,.num,h1,.plate strong,.plate em{font-family:'Roboto Condensed','Arial Narrow',sans-serif}
.s{position:relative;width:1080px;height:1920px;padding:110px 84px 0}
.top{display:flex;align-items:center;gap:22px;font-weight:700;font-size:44px;letter-spacing:1px}
.top svg{height:86px;width:auto}
.top span{color:#EF5B00;font-weight:600;font-size:30px;letter-spacing:3px;margin-left:auto}
.num{margin-top:120px;font-size:250px;font-weight:700;color:#EF5B00;line-height:.9}
.kick{margin-top:130px;font-size:38px;font-weight:600;letter-spacing:5px;color:#EF5B00}
h1{margin-top:26px;font-size:86px;line-height:1.06;font-weight:700}
h1.big{font-size:104px}
p{margin-top:34px;font-size:44px;line-height:1.3;color:#cfcfcf;font-weight:400}
p b{color:#fff;font-weight:600}
ul{margin-top:44px;list-style:none}
li{position:relative;padding-left:58px;margin-top:30px;font-size:46px;line-height:1.25;color:#e6e6e6}
li:before{content:"";position:absolute;left:0;top:18px;width:26px;height:26px;background:#EF5B00}
li.no:before{background:none;border:5px solid #777;width:26px;height:26px}
.art{position:absolute;left:84px;right:84px;bottom:150px}
.art svg{display:block;width:100%;height:auto;border-radius:10px}
.row{display:flex;gap:26px;align-items:flex-end}
.plate{background:#1f4fa8;border:8px solid #fff;border-radius:22px;padding:36px 48px;width:640px}
.plate small{display:block;font-size:34px;letter-spacing:4px;opacity:.85}
.plate strong{display:block;font-size:74px;line-height:1.05;margin-top:6px}
.plate em{position:absolute;right:120px;bottom:40px;font-style:normal;font-size:150px;font-weight:700}
.foot{position:absolute;left:84px;right:84px;bottom:60px;font-size:30px;color:#8a8a8a;letter-spacing:1px}
.warn{margin-top:50px;border-left:10px solid #EF5B00;padding:8px 0 8px 34px;font-size:46px;line-height:1.28}
.link{margin-top:40px;font-size:38px;color:#EF5B00;word-break:break-all;line-height:1.3}
"""

_lg, _lw = B.lockup(0, 0, 44)
LOGO = f'<svg viewBox="0 0 {_lw:.2f} 44.5" xmlns="http://www.w3.org/2000/svg">{_lg}</svg>'


def sign(stem):
    s = (SIG / f"{stem}.svg").read_text(encoding="utf-8")
    # drop the fixed mm size so CSS can scale it
    import re
    return re.sub(r'\swidth="[^"]+"\sheight="[^"]+"', "", s, count=1)


def top(step):
    return f'<div class="top">{LOGO}<span>{step}</span></div>'


def slides():
    return [
        top("ВИДЕО ДЛЯ ЯНДЕКСА") + '''
        <div class="kick">ПОДТВЕРЖДЕНИЕ АДРЕСА</div>
        <h1 class="big">Как снять видео для Яндекса</h1>
        <p>Яндекс хочет увидеть, что по адресу есть настоящее место, куда может прийти клиент.</p>
        <div class="warn">Срок — <b>до 13 октября 2026</b>.<br>Без видео карточка пропадет с Яндекс Карт.</div>
        <div class="foot">4 кадра · один дубль · обычный телефон</div>''',

        top("ГЛАВНОЕ ПРАВИЛО") + '''
        <div class="kick">ПРЕЖДЕ ЧЕМ СНИМАТЬ</div>
        <h1>Один файл, без остановок</h1>
        <ul>
          <li>Нажали «запись» на улице — выключили только внутри.</li>
          <li>Никакого монтажа, склеек, фильтров и музыки.</li>
          <li>Снимать на обычный телефон, идти пешком.</li>
          <li>Длина не важна: 2 минуты или 10 — не проблема.</li>
          <li>Снять в тот же день, когда отправляем.</li>
        </ul>''',

        top("ШАГ 1 ИЗ 4") + '''
        <div class="num">1</div>
        <h1>Дом и табличка с адресом</h1>
        <p>Начните с улицы. Покажите <b>фасад здания</b> и <b>табличку с названием улицы и номером дома</b> — так, чтобы ее можно было прочитать.</p>
        <p>Если таблички на здании нет — покажите путь от ближайшего дома, где она есть.</p>
        <div class="art"><div class="plate"><small>УЛИЦА</small><strong>Бехтерева</strong></div><div class="plate" style="position:absolute;right:0;bottom:0;width:230px;text-align:center;padding:36px 0"><strong style="font-size:84px">41 к1</strong></div></div>''',

        top("ШАГ 2 ИЗ 4") + '''
        <div class="num">2</div>
        <h1>Вывеска КРЮК24</h1>
        <p>Не выключая запись, подойдите к нашей вывеске и задержите на ней камеру на 3–4 секунды.</p>
        <p>Если вход не виден с улицы — по пути покажите <b>указатель со стрелкой</b>.</p>
        <div class="art">''' + sign("01_vyveska_fasad_2000x500mm") + '<div style="height:26px"></div>'
        + '<div style="width:62%">' + sign("03_ukazatel_600x200mm_vpravo") + '</div></div>',

        top("ШАГ 3 ИЗ 4") + '''
        <div class="num">3</div>
        <h1>Вход и табличка на двери</h1>
        <p>Покажите дверь, табличку КРЮК24 рядом с ней и <b>зайдите внутрь</b> — камера все это время снимает.</p>
        <p>Дверь должна открываться свободно: Яндекс проверяет, что клиент может войти.</p>
        <div class="art"><div style="width:74%">''' + sign("02_tablichka_vhod_400x300mm") + '</div></div>',

        top("ШАГ 4 ИЗ 4") + '''
        <div class="num">4</div>
        <h1>Внутри: место приема клиентов</h1>
        <p>Медленно обведите камерой помещение: <b>логотип на стене, стол, табличку на столе, стенд с тарифами</b>.</p>
        <div class="art">''' + sign("04_logo_zona_priema_1200x380mm") + '<div style="height:26px"></div><div class="row">'
        + '<div style="width:60%">' + sign("06_nastolnaya_tablichka_A5_210x148mm") + '</div>'
        + '<div style="width:36%">' + sign("05_stend_tarify_A3_297x420mm") + '</div></div></div>',

        top("ЧТО ПРОВЕРЯЕТ ЯНДЕКС") + '''
        <div class="kick">ЧТОБЫ НЕ ОТКЛОНИЛИ</div>
        <h1>Внутри должно быть «по-рабочему»</h1>
        <ul>
          <li>В помещении <b>нет ремонта</b> и строительного мусора.</li>
          <li>Есть стол и стул — место, где принимают человека.</li>
          <li>Вывески <b>закреплены</b>, а не стоят у стены.</li>
          <li>Лица прохожих и чужие документы в кадр лучше не брать.</li>
        </ul>
        <div class="warn">Яндекс может дополнительно попросить <b>договор аренды</b> или документ на помещение — держите под рукой.</div>''',

        top("ПОСЛЕ СЪЕМКИ") + '''
        <div class="kick">ЧТО ДЕЛАТЬ С ФАЙЛОМ</div>
        <h1>Ничего не обрезать — и прислать</h1>
        <ul>
          <li>Не обрезайте начало и конец, не сжимайте.</li>
          <li>Загрузите файл на <b>Яндекс Диск</b>.</li>
          <li>Нажмите <b>«Поделиться»</b> и скопируйте ссылку.</li>
          <li>Пришлите ссылку Геворгу — заявку в Яндекс отправим сами.</li>
        </ul>
        <p>Проверка занимает до 3 дней, ответ придет на почту.</p>''',

        top("ПРИМЕР ОТ ЯНДЕКСА") + '''
        <div class="kick">КОРОТКО</div>
        <h1>Улица → вывеска → дверь → стол</h1>
        <p>Один дубль, без остановок, до <b>13 октября</b>.</p>
        <p>Яндекс сам показывает пример такого видео — офис Яндекса, раздел «Примеры видео»:</p>
        <div class="link">yandex.ru/support/business-priority/ru/<br>moderation/moderation-address#video-sample</div>
        <div class="foot">КРЮК24 · +7 985 893-06-06 · kryuk24.ru</div>''',
    ]


def chromium():
    base = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
    hits = sorted(glob.glob(str(base / "chromium_headless_shell-*" / "*" / "*headless*shell*.exe")))
    if not hits:
        sys.exit("headless Chromium not found")
    return hits[-1]


def main():
    stills = OUT / "slides"
    stills.mkdir(parents=True, exist_ok=True)
    exe = chromium()
    pngs = []
    for i, body in enumerate(slides(), 1):
        html = OUT / "_tmp.html"
        html.write_text(f'<!doctype html><meta charset="utf-8"><style>{B.font_face_css()}{CSS}</style><div class="s">{body}</div>',
                        encoding="utf-8")
        png = stills / f"{i:02d}.png"
        subprocess.run([exe, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={W},{H}", f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True)
        html.unlink()
        pngs.append(png)

    n = len(pngs)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error"]
    for p in pngs:
        cmd += ["-loop", "1", "-t", f"{HOLD}", "-r", str(FPS), "-i", str(p)]
    chain, last = [], "[0:v]"
    for i in range(1, n):
        out = f"[v{i}]"
        chain.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={i * (HOLD - FADE):.2f}{out}")
        last = out
    chain.append(f"{last}format=yuv420p[v]")
    dst = OUT / "kryuk24_kak_snyat_video_dlya_yandeksa.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[v]", "-c:v", "libx264", "-preset", "slow",
            "-crf", "20", "-movflags", "+faststart", "-r", str(FPS), str(dst)]
    subprocess.run(cmd, check=True)
    total = n * HOLD - (n - 1) * FADE
    print(f"{dst.name}  {n} slides  {total:.1f}s  {round(dst.stat().st_size / 1024)}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
