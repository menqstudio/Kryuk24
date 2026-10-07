"""Build a 1080x1920 story frame from one of the owner's real photos.

The photo keeps its own aspect ratio in the centre; the rest of the frame is a
blurred, darkened zoom of the same photo, so nothing is invented and nothing is
letterboxed with black bars.
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photo" / "01_real_polished"
OUT = ROOT / "photo" / "02_stories"

W, H = 1080, 1920


def build(src_name, dst_name):
    im = Image.open(SRC / src_name).convert("RGB")

    # Background: cover the whole frame, blurred and dimmed.
    scale = max(W / im.width, H / im.height)
    bg = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    bg = bg.filter(ImageFilter.GaussianBlur(42))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)

    # Foreground: the photo itself, full width, vertically centred.
    fw = W
    fh = round(im.height * (W / im.width))
    fg = im.resize((fw, fh), Image.LANCZOS)
    bg.paste(fg, (0, (H - fh) // 2))

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / dst_name
    bg.save(dst, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"{dst_name}  {bg.size[0]}x{bg.size[1]}  {round(dst.stat().st_size/1024)}KB")


SLIDES = [
    # Порядок = порядок показа. Первый кадр — обложка истории.
    ("evakuator-mercedes-cla-moskva-avariyka.jpg", "story-1-moskva-mercedes.jpg"),
    ("evakuator-pogruzka-po-apparelyam-znak-avariynoy.jpg", "story-2-pogruzka.jpg"),
    ("evakuator-avtomobil-posle-dtp-bokovoy-udar.jpg", "story-3-posle-dtp.jpg"),
    ("evakuator-perevozka-bmw-x6-krossover.jpg", "story-4-krossover.jpg"),
    ("evakuator-perevozka-mikroavtobusa-osen.jpg", "story-5-mikroavtobus.jpg"),
]


if __name__ == "__main__":
    for src, dst in SLIDES:
        build(src, dst)
    sys.exit(0)
