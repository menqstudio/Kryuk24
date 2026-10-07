"""Сгенерированные иллюстрации для лендинга: настроение первого экрана и сюжеты «Что случилось?».

Правило (Гев, 03.10.2026): сгенерированное — только как иллюстрация ситуации, никогда
не выдаётся за нашу машину или наш выезд. Без логотипов, без номеров, без подписи
«наши выезды». Доказательства (лента «Наши выезды», парк, карточка Яндекса, Директ) —
только настоящие фото.

Источник — PNG из ChatGPT (03.10.2026), сохраняются в photo/04_generated_mood.
Выход: site/assets/img/hero-*.jpg, situaciya-*.jpg (4:3).
"""
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DL = Path.home() / "Downloads"
KEEP = ROOT / "photo" / "04_generated_mood"
OUT = ROOT / "site" / "assets" / "img"

# (файл из ChatGPT, имя исходника в photo, имя на сайте, ширина на сайте)
ITEMS = [
    ("kryuk_gen_hero_v1.png", "noch-kryuk-i-tros-lebedki-na-platforme.png", "hero-noch-kryuk-lebedki.jpg", 1240),
    ("kryuk_gen_case1_ne_zavoditsya.png", "situaciya-ne-zavoditsya-dvor-vecher.png", "situaciya-ne-zavoditsya.jpg", 1000),
    ("kryuk_gen_case2_dtp.png", "situaciya-posle-dtp-obochina.png", "situaciya-posle-dtp.jpg", 1000),
    ("kryuk_gen_case3_zastryal.png", "situaciya-zastryal-v-kyuvete-zima.png", "situaciya-zastryal-v-kyuvete.jpg", 1000),
    ("kryuk_gen_case4_kolesa.png", "situaciya-koleso-na-podkatnoy-telezhke.png", "situaciya-kolesa-zablokirovany.jpg", 1000),
    ("kryuk_gen_case5_perevezti.png", "situaciya-kolesa-zakrepleny-remnem.png", "situaciya-perevozka-remni.jpg", 1000),
]


def to43(im):
    w, h = im.size
    if w / h > 4 / 3:
        nw = round(h * 4 / 3)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = round(w * 3 / 4)
    return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def main():
    KEEP.mkdir(exist_ok=True)
    for src, keep, dst, width in ITEMS:
        if (DL / src).exists():
            shutil.copy2(DL / src, KEEP / keep)
        im = to43(Image.open(KEEP / keep).convert("RGB"))
        k = min(1.0, width / im.width)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        im.save(OUT / dst, "JPEG", quality=80, optimize=True, progressive=True)
        print(f"{dst:40} {im.size[0]}x{im.size[1]}  {round((OUT / dst).stat().st_size / 1024)}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
