"""Промоматериалы КРЮК24 для сбора отзывов на Яндекс Картах (финальный логотип 04.10.2026).

QR ведет на ту же ссылку, что и официальный QR из кабинета Яндекс Бизнеса
(расшифрована из макета 02.10.2026): короткая ссылка ya.cc открывает вкладку
«Отзывы» карточки с виджетом «Оцените это место» и метками utm_source=qr.

Формулировки нейтральные: Яндекс запрещает накрутку, попытку повлиять на
содержание отзыва и агрессивную мотивацию. Мы только просим оценить работу.

Логотип и шрифты — из tools/brand.py (те же, что на сайте).
Выход: offers/qr_promo/
"""
import sys
from pathlib import Path

import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

OUT = B.ROOT / "offers" / "qr_promo"
QR_URL = "https://ya.cc/t/012Zg9wjBBqnXf"
INK, ORANGE, WHITE, GREY = (19, 35, 58), (239, 91, 0), (255, 255, 255), (170, 170, 170)


def qr_plate(px, quiet=4):
    """QR on a white plate. High error correction so a scuffed sticker still scans."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=quiet)
    q.add_data(QR_URL)
    q.make(fit=True)
    img = q.make_image(image_factory=PilImage, fill_color="black", back_color="white")
    return img.convert("RGB").resize((px, px), Image.NEAREST)


def logo(im, x, y, height=None, width=None, vertical=False, centre=False):
    lg = B.lockup_img(height=height, width=width, vertical=vertical)
    if centre:
        x -= lg.width // 2
    im.paste(lg, (round(x), round(y)), lg)
    return lg.size


def T(d, xy, s, size, family="display", weight=700, fill=WHITE, anchor="lt"):
    B.draw_text(d, xy, s, size, family, weight, fill, anchor=anchor)


def card():
    """Визитка 90x50 мм @300dpi — отдается клиенту вместе с документами."""
    W, H = 1063, 591
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    qs, plate = 400, 440
    px, py = W - plate - 40, (H - plate) // 2
    d.rounded_rectangle([px, py, px + plate, py + plate], radius=18, fill=WHITE)
    im.paste(qr_plate(qs), (px + (plate - qs) // 2, py + (plate - qs) // 2))
    logo(im, 56, 52, height=120)
    T(d, (56, 236), "Оцените нашу работу", 48)
    T(d, (56, 294), "на Яндекс Картах", 48)
    T(d, (56, 372), "Наведите камеру телефона на код", 24, "text", 400, GREY)
    d.line([(56, 440), (px - 40, 440)], fill=(60, 60, 60), width=2)
    T(d, (56, 466), B.PHONE, 46, fill=ORANGE)
    T(d, (56, 530), B.SITE, 26, "text", 500, GREY)
    return im, "kryuk24_qr_vizitka_90x50mm_300dpi.png"


def sticker():
    """Наклейка 100x100 мм @300dpi — в кабину и на борт."""
    S = 1181
    im = Image.new("RGB", (S, S), INK)
    d = ImageDraw.Draw(im)
    logo(im, S // 2, 70, height=170, centre=True)
    T(d, (S // 2, 300), "ОЦЕНИТЕ НАШУ РАБОТУ", 50, fill=ORANGE, anchor="mt")
    qs, plate = 540, 600
    px, py = (S - plate) // 2, 400
    d.rounded_rectangle([px, py, px + plate, py + plate], radius=24, fill=WHITE)
    im.paste(qr_plate(qs), (px + (plate - qs) // 2, py + (plate - qs) // 2))
    T(d, (S // 2, 1060), B.PHONE, 60, anchor="mt")
    return im, "kryuk24_qr_nakleyka_100x100mm_300dpi.png"


def phone_screen():
    """1080x1920 — водитель показывает экран, клиент сканирует на месте."""
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    _, lh = logo(im, W // 2, 120, height=470, vertical=True, centre=True)
    y = 120 + lh + 70
    T(d, (W // 2, y), "Оцените нашу работу", 70, anchor="mt")
    T(d, (W // 2, y + 86), "на Яндекс Картах", 70, anchor="mt")
    qs, plate = 640, 720
    px, py = (W - plate) // 2, y + 200
    d.rounded_rectangle([px, py, px + plate, py + plate], radius=32, fill=WHITE)
    im.paste(qr_plate(qs), (px + (plate - qs) // 2, py + (plate - qs) // 2))
    T(d, (W // 2, py + plate + 50), "Наведите камеру телефона на код", 36, "text", 400, GREY, anchor="mt")
    T(d, (W // 2, py + plate + 112), B.PHONE, 58, fill=ORANGE, anchor="mt")
    return im, "kryuk24_qr_ekran_telefona_1080x1920.png"


def story():
    """1080x1920 — история в карточке Яндекса. Верх и низ свободны: там интерфейс
    историй и кнопка, поэтому все содержимое собрано в середине кадра."""
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    _, lh = logo(im, W // 2, 230, height=330, vertical=True, centre=True)
    y = 230 + lh + 60
    T(d, (W // 2, y), "Мы вам помогли?", 76, fill=ORANGE, anchor="mt")
    T(d, (W // 2, y + 96), "Оцените нашу работу", 62, anchor="mt")
    T(d, (W // 2, y + 172), "на Яндекс Картах", 62, anchor="mt")
    qs, plate = 540, 610
    px, py = (W - plate) // 2, y + 280
    d.rounded_rectangle([px, py, px + plate, py + plate], radius=30, fill=WHITE)
    im.paste(qr_plate(qs), (px + (plate - qs) // 2, py + (plate - qs) // 2))
    T(d, (W // 2, py + plate + 44), "Наведите камеру на код", 36, "text", 400, GREY, anchor="mt")
    T(d, (W // 2, py + plate + 94), "или нажмите кнопку ниже", 36, "text", 400, GREY, anchor="mt")
    return im, "kryuk24_qr_story_yandex_1080x1920.png"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for build in (card, sticker, phone_screen, story):
        im, name = build()
        dst = OUT / name
        im.save(dst, "PNG", optimize=True)
        print(f"{name:48} {im.size[0]}x{im.size[1]}  {round(dst.stat().st_size / 1024)}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
