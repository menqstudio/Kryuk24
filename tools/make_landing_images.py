"""Веб-копии настоящих фото для лендинга: лента «Наши выезды».

Источник — photo/01_real_polished (номера и лица уже закрыты). Здесь только
уменьшение и пережатие, без обработки. Выход: site/assets/img/rabota-*.jpg, hero-*.jpg
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photo" / "01_real_polished"
OUT = ROOT / "site" / "assets" / "img"

# (исходник, имя на сайте) — порядок = порядок в ленте
GALLERY = [
    ("evakuator-mercedes-cla-moskva-avariyka.jpg", "rabota-01-mercedes-cla.jpg"),
    ("evakuator-manipulyator-podem-avtomobilya-iz-kyuveta.jpg", "rabota-02-iz-kyuveta.jpg"),
    ("evakuator-perevozka-bmw-x6-krossover.jpg", "rabota-03-bmw-x6.jpg"),
    ("evakuator-perevozka-spectehniki-mini-pogruzchik.jpg", "rabota-04-mini-pogruzchik.jpg"),
    ("evakuator-perevozka-audi-a8-biznes-klass.jpg", "rabota-05-audi-a8.jpg"),
    ("evakuator-avtomobil-posle-dtp-bokovoy-udar.jpg", "rabota-06-posle-dtp.jpg"),
    ("evakuator-perevozka-gruzovogo-mikroavtobusa.jpg", "rabota-07-mikroavtobus.jpg"),
    ("evakuator-perevozka-rolls-royce-wraith-kupe.jpg", "rabota-08-rolls-royce.jpg"),
    ("evakuator-perevozka-vilochnogo-pogruzchika-5-tonn.jpg", "rabota-09-vilochnyy-pogruzchik.jpg"),
    ("evakuator-perevozka-volkswagen-golf.jpg", "rabota-10-volkswagen-golf.jpg"),
    ("evakuator-manipulyator-pogruzka-mercedes-gle.jpg", "rabota-11-manipulyator.jpg"),
    ("evakuator-posle-dtp-lada-vesta-pogruzka.jpg", "rabota-12-posle-dtp-pogruzka.jpg"),
    ("evakuator-perevozka-mikroavtobusa-osen.jpg", "rabota-13-mikroavtobus-osen.jpg"),
    ("evakuator-manipulyator-pogruzka-avtomobilya-posle-dtp.jpg", "rabota-14-manipulyator-posle-dtp.jpg"),
    ("evakuator-perevozka-mini-pogruzchika-s-kovshom.jpg", "rabota-15-mini-pogruzchik-s-kovshom.jpg"),
    ("evakuator-perevozka-vilochnogo-pogruzchika.jpg", "rabota-16-vilochnyy-pogruzchik.jpg"),
    ("evakuator-pogruzka-po-apparelyam-znak-avariynoy.jpg", "rabota-17-pogruzka-po-apparelyam.jpg"),
    ("evakuator-pogruzka-vilochnogo-pogruzchika-na-platformu.jpg", "rabota-18-pogruzchik-na-platformu.jpg"),
    ("evakuator-perevozka-kia-carnival-miniven.jpg", "rabota-19-miniven-kia.jpg"),
]


def save(src, dst, height=None, width=None, crop43=False, q=78):
    im = Image.open(SRC / src).convert("RGB")
    if crop43:                                  # hero frames share one 4:3 box
        w, h = im.size
        if w / h > 4 / 3:
            nw = round(h * 4 / 3); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = round(w * 3 / 4); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    if height:
        k = min(1.0, height / im.height)
    else:
        k = min(1.0, width / im.width)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    im.save(OUT / dst, "JPEG", quality=q, optimize=True, progressive=True)
    print(f"{dst:40} {im.size[0]}x{im.size[1]}  {round((OUT / dst).stat().st_size / 1024)}KB")
    return im.size


def main():
    for s, d in GALLERY:
        save(s, d, height=560)
    return 0


if __name__ == "__main__":
    sys.exit(main())
