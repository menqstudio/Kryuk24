"""Polish the owner's real job photos for publication.

Gentle, reversible-looking corrections only — these are real photographs and must
still read as real: modest white balance, contrast and saturation, light sharpening.
Plates and faces are pixelated then blurred, which cannot be undone.

Source: photo/00_real_source/   Output: photo/01_real_polished/
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photo" / "00_real_source"
OUT = ROOT / "photo" / "01_real_polished"

# Per photo: output name, and the boxes to obscure as (x0, y0, x1, y1) fractions
# of width/height. Boxes are deliberately a little generous.
PHOTOS = [
    ("WhatsApp Image 2026-09-30 at 09.28.22.jpeg",
     "evakuator-perevozka-mikroavtobusa-osen.jpg",
     [(0.000, 0.655, 0.058, 0.740)]),
    ("WhatsApp Image 2026-09-30 at 09.28.23 (1).jpeg",
     "evakuator-perevozka-bmw-x6-krossover.jpg",
     [(0.838, 0.338, 0.924, 0.404)]),
    ("WhatsApp Image 2026-09-30 at 09.28.23.jpeg",
     "evakuator-perevozka-gruzovogo-mikroavtobusa.jpg",
     [(0.096, 0.766, 0.198, 0.838)]),
    ("WhatsApp Image 2026-09-30 at 09.28.24 (1).jpeg",
     "evakuator-posle-dtp-lada-vesta-pogruzka.jpg",
     [(0.757, 0.321, 0.948, 0.388)]),
    ("WhatsApp Image 2026-09-30 at 09.28.24.jpeg",
     "evakuator-pogruzka-po-apparelyam-znak-avariynoy.jpg",
     [(0.370, 0.300, 0.505, 0.348), (0.395, 0.433, 0.520, 0.482)]),
    ("WhatsApp Image 2026-09-30 at 09.28.25 (1).jpeg",
     "evakuator-perevozka-audi-a8-biznes-klass.jpg",
     [(0.136, 0.457, 0.260, 0.525),   # Audi plate
      (0.193, 0.710, 0.297, 0.770),   # tow truck plate
      (0.392, 0.178, 0.470, 0.277)]),  # driver's face
    ("WhatsApp Image 2026-09-30 at 09.28.25 (2).jpeg",
     "evakuator-perevozka-volkswagen-golf.jpg",
     [(0.706, 0.498, 0.814, 0.560), (0.866, 0.776, 0.964, 0.838),
      (0.882, 0.436, 0.952, 0.484)]),   # third party truck in the background
    ("WhatsApp Image 2026-09-30 at 09.28.25.jpeg",
     "evakuator-gazel-next-s-avtomobilem.jpg",
     [(0.014, 0.588, 0.096, 0.670)]),
    ("WhatsApp Image 2026-09-30 at 09.28.26.jpeg",
     "evakuator-avtomobil-posle-dtp-bokovoy-udar.jpg",
     [(0.708, 0.422, 0.810, 0.502), (0.754, 0.762, 0.862, 0.828)]),
    # Прислано владельцем 30.09.2026 вечером, добавлено 02.10.2026.
    ("WhatsApp Image 2026-09-30 at 21.51.12.jpeg",
     "evakuator-mercedes-cla-moskva-avariyka.jpg",
     [(0.559, 0.242, 0.647, 0.283),   # Mercedes plate
      (0.592, 0.460, 0.683, 0.512)]),  # tow truck plate
    # Прислано владельцем 02.10.2026 поздно вечером — скриншоты с телефона.
    # Четвёртый элемент — кадр внутри скриншота (доли ширины/высоты): чёрные поля
    # обрезаются до обработки, рамки для размытия считаются уже от обрезанного кадра.
    ("WhatsApp Image 2026-10-02 at 23.41.48.jpeg",
     "evakuator-manipulyator-pogruzka-avtomobilya-posle-dtp.jpg",
     [(0.000, 0.855, 0.072, 0.940),   # our tow truck plate
      (0.950, 0.748, 1.000, 0.825),   # manipulator plate
      (0.618, 0.536, 0.680, 0.610)],  # third-party logo and phone on the door
     (0.0, 0.3150, 1.0, 0.6488)),
    ("WhatsApp Image 2026-10-02 at 23.45.09.jpeg",
     "evakuator-perevozka-spectehniki-mini-pogruzchik.jpg",
     [],
     (0.0, 0.2063, 1.0, 0.6146)),
    ("WhatsApp Image 2026-10-02 at 23.46.50.jpeg",
     "evakuator-perevozka-rolls-royce-wraith-kupe.jpg",
     [(0.040, 0.412, 0.100, 0.488),   # Rolls-Royce plate
      (0.040, 0.790, 0.080, 0.850),   # tow truck rear plate
      (0.945, 0.450, 0.990, 0.490)],  # car in the background
     (0.0, 0.3369, 1.0, 0.6394)),
    ("WhatsApp Image 2026-10-02 at 23.49.12.jpeg",
     "evakuator-perevozka-vilochnogo-pogruzchika.jpg",
     [(0.312, 0.495, 0.372, 0.552)],   # sticker with a phone number on the forklift
     (0.0, 0.2812, 1.0, 0.6956)),
    ("WhatsApp Image 2026-10-02 at 23.49.53.jpeg",
     "evakuator-perevozka-mini-pogruzchika-s-kovshom.jpg",
     [(0.035, 0.71, 0.155, 0.784)],   # tow truck plate
     (0.0, 0.27, 1.0, 0.7069)),
    ("WhatsApp Image 2026-10-02 at 23.52.32.jpeg",
     "evakuator-manipulyator-podem-avtomobilya-iz-kyuveta.jpg",
     [(0.318, 0.583, 0.380, 0.634),   # worker's face
      (0.200, 0.743, 0.300, 0.787),   # left truck plate
      (0.735, 0.749, 0.842, 0.796),   # right truck plate
      (0.835, 0.371, 0.900, 0.409),   # lifted car plate
      (0.070, 0.625, 0.135, 0.666)],  # car in the background
     (0.0, 0.2769, 1.0, 0.7)),
    # Эвакуатор-манипулятор партнёра: название службы и номер закрыты по решению владельца.
    ("WhatsApp Image 2026-10-02 at 23.44.03.jpeg",
     "evakuator-manipulyator-pogruzka-mercedes-gle.jpg",
     [(0.770, 0.604, 0.962, 0.644),   # service name on the cab front
      (0.518, 0.556, 0.612, 0.604),   # service name on the door
      (0.832, 0.708, 0.922, 0.748)]),  # plate
    ("WhatsApp Image 2026-10-03 at 00.04.59.jpeg",
     "evakuator-pogruzka-vilochnogo-pogruzchika-na-platformu.jpg",
     [(0.650, 0.358, 0.712, 0.408),   # worker's face
      (0.050, 0.730, 0.145, 0.782)]),  # tow truck plate
    ("WhatsApp Image 2026-10-03 at 00.05.00.jpeg",
     "evakuator-perevozka-vilochnogo-pogruzchika-5-tonn.jpg",
     [(0.905, 0.530, 0.970, 0.560)]),  # parked cars in the background
    # Прислано 05.10.2026 — вертикальный кадр, обрезан до 4:3 по машине.
    ("WhatsApp Image 2026-10-05 at 12.30.43.jpeg",
     "evakuator-perevozka-kia-carnival-miniven.jpg",
     [(0.675, 0.425, 0.845, 0.505)],   # Kia plate
     (0.0, 0.094, 1.0, 0.656)),
    # Прислано 07.10.2026 — Tank 500: погрузка лебедкой, на платформе сбоку и сзади.
    ("WhatsApp Image 2026-10-07 at 12.48.20.jpeg",
     "evakuator-perevozka-tank-500-vnedorozhnik.jpg",
     [(0.040, 0.390, 0.082, 0.505)]),  # passer-by at the left edge
    ("WhatsApp Image 2026-10-07 at 12.48.21.jpeg",
     "evakuator-tank-500-na-platforme-vid-szadi.jpg",
     [(0.170, 0.352, 0.290, 0.415),   # Tank plate
      (0.262, 0.636, 0.388, 0.698),   # tow truck plate
      (0.168, 0.468, 0.228, 0.506)],  # parked car on the left
     (0.0, 0.15, 1.0, 0.7125)),
    ("WhatsApp Image 2026-10-07 at 12.48.21 (1).jpeg",
     "evakuator-pogruzka-lebedkoy-tank-500.jpg",
     [(0.435, 0.300, 0.525, 0.350),   # Tank plate
      (0.100, 0.182, 0.170, 0.234)],  # parked car on the left
     (0.0, 0.30, 1.0, 0.8625)),
]


def white_balance(im, strength=0.7, max_gain=0.14):
    """Gentle gray-world balance, with the correction capped so skies stay honest."""
    r, g, b = [c.resize((64, 64)).convert("L") for c in im.split()[:3]]
    means = [sum(c.getdata()) / 4096 for c in (r, g, b)]
    target = sum(means) / 3
    out = []
    for ch, m in zip(im.split()[:3], means):
        gain = 1.0 if m < 1 else target / m
        gain = 1 + (gain - 1) * strength
        gain = max(1 - max_gain, min(1 + max_gain, gain))
        out.append(ch.point(lambda v, k=gain: min(255, int(v * k))))
    return Image.merge("RGB", out)


def stretch(im, lo_pct=0.004, hi_pct=0.996, blend=0.75):
    """Percentile contrast stretch, blended back so it never looks processed."""
    out = []
    for ch in im.split():
        h = ch.histogram()
        total = sum(h)
        acc, lo, hi = 0, 0, 255
        for v, n in enumerate(h):
            acc += n
            if acc >= total * lo_pct:
                lo = v
                break
        acc = 0
        for v, n in enumerate(h):
            acc += n
            if acc >= total * hi_pct:
                hi = v
                break
        if hi - lo < 24:
            out.append(ch)
            continue
        scale = 255.0 / (hi - lo)
        out.append(ch.point(lambda v: max(0, min(255, int((v - lo) * scale)))))
    stretched = Image.merge("RGB", out)
    return Image.blend(im, stretched, blend)


def obscure(im, boxes):
    """Pixelate then blur — the original characters cannot be recovered."""
    w, h = im.size
    for x0, y0, x1, y1 in boxes:
        box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        bw, bh = box[2] - box[0], box[3] - box[1]
        if bw < 4 or bh < 4:
            continue
        region = im.crop(box)
        region = region.resize((max(2, bw // 14), max(2, bh // 14)), Image.BILINEAR)
        region = region.resize((bw, bh), Image.NEAREST)
        region = region.filter(ImageFilter.GaussianBlur(max(2, bw // 18)))
        im.paste(region, box)
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name, boxes, *crop in PHOTOS:
        src = SRC / src_name
        if not src.exists():
            print("missing:", src_name)
            continue
        im = Image.open(src).convert("RGB")
        if crop:
            x0, y0, x1, y1 = crop[0]
            im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
        im = white_balance(im)
        im = stretch(im)
        im = ImageEnhance.Color(im).enhance(1.12)
        im = ImageEnhance.Brightness(im).enhance(1.03)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=62, threshold=3))
        im = obscure(im, boxes)
        dst = OUT / dst_name
        im.save(dst, "JPEG", quality=92, optimize=True, progressive=True)
        print(f"{dst_name:52} {im.size[0]}x{im.size[1]}  "
              f"{round(dst.stat().st_size / 1024)}KB  {len(boxes)} obscured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
