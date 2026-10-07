"""Набор для WhatsApp владельца: статусы 1080x1920 из настоящих фото + фото профиля.

Статус = фото работы целиком (не обрезаем), сверху логотип, снизу услуга,
цена из действующего тарифа и телефон. Верх и низ кадра свободны — там интерфейс
WhatsApp. Цены — те же, что на kryuk24.ru и в карточке Яндекса.

Логотип и шрифты — из tools/brand.py (финальный логотип 04.10.2026, те же шрифты, что на сайте).
Выход: offers/whatsapp_kit/
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

ROOT = B.ROOT
SRC = ROOT / "photo" / "01_real_polished"
OUT = ROOT / "offers" / "whatsapp_kit"
AVATAR = ROOT / "brand" / "03_avatar" / "png" / "avatar_yandex.png"
QR_STORY = ROOT / "offers" / "qr_promo" / "kryuk24_qr_ekran_telefona_1080x1920.png"  # без «кнопки ниже»: в WhatsApp ее нет

W, H = 1080, 1920
INK, ORANGE, WHITE, GREY = (19, 35, 58), (239, 91, 0), (255, 255, 255), (190, 190, 190)
STYLE = {"Bold": ("display", 700), "SemiBold": ("text", 500), "Regular": ("text", 400)}


def T(d, xy, s, size, weight="Bold", fill=WHITE, anchor="lt"):
    B.draw_text(d, xy, s, size, *STYLE[weight], fill=fill, anchor=anchor)


def fit(text, max_w, size, weight="Bold", floor=40):
    while size > floor and B.measure(text, size, *STYLE[weight]) > max_w:
        size -= 2
    return size


def header(im):
    lg = B.lockup_img(height=130)
    im.paste(lg, (90, 236), lg)


def status(src_name, title, price, dst_name):
    im = Image.open(SRC / src_name).convert("RGB")
    s = max(W / im.width, H / im.height)
    bg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(46))
    bg = ImageEnhance.Brightness(bg).enhance(0.30)

    # the photo itself, whole, never cropped; capped so the text block always fits
    fh_max = 860
    k = min(W / im.width, fh_max / im.height)
    fg = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    py = 440 + (fh_max - fg.height) // 2
    bg.paste(fg, ((W - fg.width) // 2, py))

    d = ImageDraw.Draw(bg)
    header(bg)
    y = 1350
    T(d, (70, y), title, fit(title, W - 140, 76))
    T(d, (70, y + 100), price, fit(price, W - 140, 58, "SemiBold"), "SemiBold", ORANGE)
    d.rectangle([70, y + 186, W - 70, y + 190], fill=(90, 90, 90))
    T(d, (70, y + 222), B.PHONE, 70)
    T(d, (W - 70, y + 236), B.SITE, 36, "SemiBold", GREY, anchor="rt")
    dst = OUT / dst_name
    bg.save(dst, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"{dst_name:46} {bg.size[0]}x{bg.size[1]}  {round(dst.stat().st_size / 1024)}KB")


def save_number():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    lg = B.lockup_img(height=420, vertical=True)
    im.paste(lg, ((W - lg.width) // 2, 300), lg)
    T(d, (W // 2, 870), "Сохраните номер —", 78, anchor="mt")
    T(d, (W // 2, 964), "пригодится на дороге", 78, anchor="mt")
    d.rounded_rectangle([110, 1130, W - 110, 1310], radius=28, fill=ORANGE)
    T(d, (W // 2, 1220), B.PHONE, 96, fill=INK, anchor="mm")
    T(d, (W // 2, 1390), "Москва и область, без выходных", 44, "Regular", GREY, anchor="mt")
    T(d, (W // 2, 1460), "Легковой — от 4 000 ₽ + 100 ₽/км", 44, "Regular", GREY, anchor="mt")
    dst = OUT / "status-7-sohranite-nomer.jpg"
    im.save(dst, "JPEG", quality=92, optimize=True)
    print(f"{dst.name:46} {W}x{H}  {round(dst.stat().st_size / 1024)}KB")


def cover(src_name="evakuator-mercedes-cla-moskva-avariyka.jpg"):
    """Обложка профиля WhatsApp Business, 1600x900. Настоящее фото работы, затемненное слева под текст.

    Нижняя треть свободна: там WhatsApp ставит круглый аватар (в телефоне слева, в Web по центру).
    """
    cw, ch = 1600, 900
    im = Image.open(SRC / src_name).convert("RGB")
    s = max(cw / im.width, ch / im.height)
    bg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    left, top = (bg.width - cw) // 2, (bg.height - ch) // 2
    bg = bg.crop((left, top, left + cw, top + ch))
    bg = ImageEnhance.Brightness(bg).enhance(0.62)
    shade = Image.new("RGB", (cw, ch), INK)
    mask = Image.new("L", (cw, ch), 0)
    md = ImageDraw.Draw(mask)
    for x in range(cw):                                    # плотный слева, прозрачный справа
        md.line([(x, 0), (x, ch)], fill=round(245 * max(0.0, 1 - x / (cw * 0.86)) ** 0.55))
    bg = Image.composite(shade, bg, mask)
    d = ImageDraw.Draw(bg)
    lg = B.lockup_img(height=120)
    bg.paste(lg, (90, 80), lg)
    T(d, (90, 270), "Эвакуатор в Москве", 82)
    T(d, (90, 364), "и области", 82)
    T(d, (90, 478), "Круглосуточно · от 4 000 ₽ + 100 ₽/км", 40, "SemiBold", ORANGE)
    dst = OUT / "oblozhka-profilya-1600x900.jpg"
    bg.save(dst, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"{dst.name:46} {cw}x{ch}  {round(dst.stat().st_size / 1024)}KB")


STATUSES = [
    ("evakuator-mercedes-cla-moskva-avariyka.jpg", "Эвакуатор в Москве и области",
     "Легковой — от 4 000 ₽ + 100 ₽/км", "status-1-legkovoy.jpg"),
    ("evakuator-perevozka-bmw-x6-krossover.jpg", "Кроссоверы и внедорожники",
     "от 4 500 ₽ + 100 ₽/км", "status-2-krossover.jpg"),
    ("evakuator-perevozka-gruzovogo-mikroavtobusa.jpg", "Микроавтобусы и коммерческий",
     "от 5 000 ₽ + 100 ₽/км", "status-3-mikroavtobus.jpg"),
    ("evakuator-avtomobil-posle-dtp-bokovoy-udar.jpg", "Эвакуация после ДТП",
     "от 4 000 ₽ + 100 ₽/км", "status-4-posle-dtp.jpg"),
    ("evakuator-manipulyator-podem-avtomobilya-iz-kyuveta.jpg", "Застряли? Вытащим",
     "от 5 000 ₽", "status-5-zastryal.jpg"),
    ("evakuator-perevozka-spectehniki-mini-pogruzchik.jpg", "Перевозка спецтехники",
     "2 500 ₽ за тонну, от 5 000 ₽ + 100 ₽/км", "status-6-spectehnika.jpg"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for args in STATUSES:
        status(*args)
    save_number()
    Image.open(QR_STORY).convert("RGB").save(OUT / "status-8-otzyv-qr.jpg", "JPEG", quality=92)
    Image.open(AVATAR).convert("RGB").resize((640, 640), Image.LANCZOS).save(OUT / "foto-profilya-640.jpg", "JPEG", quality=94)
    print("status-8-otzyv-qr.jpg, foto-profilya-640.jpg copied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
