"""Вывески и таблички КРЮК24 для помещения — комплект под печать (финальный логотип 04.10.2026).

Зачем: Яндекс Бизнес подтверждает адрес по видео, на котором видны вывеска,
вход с табличкой и место приема клиентов с фирменным оформлением.
Источник требований: yandex.ru/support/business-priority/ru/moderation/moderation-address

Логотип, крюк, цвета и шрифты — из tools/brand.py (те же, что на сайте).
Тарифы на стенде читаются прямо из site/index.html — стенд и сайт всегда совпадают.
Единица viewBox = 1 мм, размер 1:1.

Выход: brand/06_signage/  (svg + pdf для типографии + png для просмотра)
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

OUT = B.ROOT / "brand" / "06_signage"
GREY = B.GREY
T = B.text


def site_tariff():
    """[(section title, [(name, price), …]), …] from the tariff panels of the live page source."""
    s = (B.ROOT / "site" / "index.html").read_text(encoding="utf-8")
    a = s.index('id="cena-tarify"'); s = s[a:s.index('id="cena-goroda"')]
    out = []
    for panel in re.findall(r'<div class="pl__panel".*?</ul>', s, re.S):
        title = html.unescape(re.search(r'<h3 class="sub">(.*?)</h3>', panel).group(1))
        rows = []
        for li in re.findall(r'<li class="pl__c">(.*?)</li>', panel, re.S):
            name = html.unescape(re.sub(r"<[^>]+>", "", re.search(r'class="pl__n">(.*?)</span>', li).group(1)))
            price = html.unescape(re.search(r'class="pl__p">(.*?)</strong>', li).group(1))
            km = re.search(r'class="pl__km">(.*?)</span>', li)
            rows.append((name, price + (" " + html.unescape(km.group(1)) if km else "")))
        out.append((title, rows))
    assert sum(len(r) for _, r in out) == 19, "tariff on the site changed — check the stand layout"
    return out


def facade():
    """Фасадная вывеска 2000x500 мм. Пропорция 4:1 — типография масштабирует под проем."""
    W, H = 2000, 500
    h = 300
    g, lw = B.lockup(90, (H - h) / 2, h)
    dx = 90 + lw + 80
    rx = dx + 6 + 80
    rw = W - 90 - rx
    ph = B.fit(B.PHONE, rw, "display", 700)
    b = [g, B.rect(dx, 110, 6, 280, B.ORANGE),
         T(rx, 262, B.PHONE, ph, "display", 700, B.WHITE),
         T(rx, 262 + 110, B.SITE, 80, "text", 500, B.ORANGE_SOFT, ls=3)]
    return W, H, B.svg_doc(W, H, b, label="КРЮК24 — фасадная вывеска"), "01_vyveska_fasad_2000x500mm"


def entrance():
    """Табличка у входа / на дверь 400x300 мм."""
    W, H = 400, 300
    M = 32
    g, _ = B.lockup(M, 28, 76)
    kr = B.fit("КРУГЛОСУТОЧНО", W - 2 * M, "display", 700, 0.02)
    b = [g, B.rect(M, 124, W - 2 * M, 2.5, B.ORANGE),
         T(M, 152, "ЗАЯВКИ ПРИНИМАЕМ", 16, "text", 500, GREY, ls=1.6),
         T(M, 152 + 12 + kr * 0.72, "КРУГЛОСУТОЧНО", kr, "display", 700, B.WHITE, ls=kr * 0.02),
         T(M, 252, B.PHONE, 40, "display", 700, B.ORANGE),
         T(M, 278, B.SITE, 16, "text", 500, GREY, ls=0.6),
         T(W - M, 278, B.ADDRESS, 16, "text", 500, GREY, anchor="end")]
    return W, H, B.svg_doc(W, H, b, label="КРЮК24 — табличка у входа"), "02_tablichka_vhod_400x300mm"


def pointer(direction):
    """Указатель 600x200 мм со стрелкой и словом «ВХОД» — на путь от адресной таблички до входа."""
    W, H = 600, 200
    aw, M = 150, 36
    right = direction == "right"
    zone = (W - M - aw, W - M) if right else (M, M + aw)
    tip = zone[1] if right else zone[0]
    tail = zone[0] if right else zone[1]
    sgn = 1 if right else -1
    cy = 128
    head = 54
    shaft_end = tip - sgn * head
    pts = [(tail, cy - 12), (shaft_end, cy - 12), (shaft_end, cy - 40), (tip, cy), (shaft_end, cy + 40),
           (shaft_end, cy + 12), (tail, cy + 12)]
    b = ['<polygon points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f'" fill="{B.ORANGE}"/>',
         T((zone[0] + zone[1]) / 2, 74, "ВХОД", B.fit("ВХОД", aw - 10, "display", 700, 0.04), "display", 700, B.WHITE,
           anchor="middle", ls=2)]
    lx0 = M if right else M + aw + 30
    avail = W - 2 * M - aw - 30
    h = 110
    while B.lockup_size(h)[0] > avail:
        h -= 2
    g, _ = B.lockup(lx0, (H - h) / 2, h)
    b.append(g)
    return W, H, B.svg_doc(W, H, b, label="КРЮК24 — указатель ко входу"), f"03_ukazatel_600x200mm_{'vpravo' if right else 'vlevo'}"


def interior():
    """Логотип на стену в зоне приема клиентов 1200x380 мм."""
    W, H = 1200, 380
    h = 240
    lw, _ = B.lockup_size(h)
    g, _ = B.lockup((W - lw) / 2, (H - h) / 2, h)
    return W, H, B.svg_doc(W, H, [g], label="КРЮК24 — логотип в зону приема"), "04_logo_zona_priema_1200x380mm"


def tariffs():
    """Информационный стенд «Тарифы», A3 (297x420 мм), светлый — читается в помещении."""
    W, H = 297, 420
    M = 22
    g, _ = B.lockup(M, 13, 36)
    b = [B.rect(0, 0, W, 62, B.INK), g,
         T(W - M, 34, "ТАРИФЫ", 18, "display", 700, B.WHITE, anchor="end", ls=0.6),
         T(W - M, 46, "погрузка и выгрузка + цена километра", 5.6, "text", 400, GREY, anchor="end")]
    y = 64
    for title, rows in site_tariff():
        y += 12.5
        b.append(T(M, y, title, 9, "display", 700, B.ORANGE))
        y += 2.5
        for label, price in rows:
            y += 10.1
            room = W - 2 * M - B.measure(price, 6.9, "text", 700) - 6
            lines, cur = [], ""
            for word in label.split():           # long names wrap instead of shrinking the type
                test = (cur + " " + word).strip()
                if B.measure(test, 6.9, "text", 500) > room and cur:
                    lines.append(cur); cur = word
                else:
                    cur = test
            lines.append(cur)
            b.append(T(W - M, y, price, 6.9, "text", 700, B.INK, anchor="end"))
            for i, ln in enumerate(lines):
                b.append(T(M, y + i * 8.0, ln, 6.9, "text", 500, B.INK))
            y += (len(lines) - 1) * 8.0
            b.append(B.rect(M, y + 3.5, W - 2 * M, 0.3, "#D1D7DC"))
    assert y < H - 46 - 6, y
    b += [B.rect(0, H - 40, W, 40, B.INK),
          T(M, H - 14, B.PHONE, 21, "display", 700, B.ORANGE),
          T(W - M, H - 15, B.SITE, 11, "text", 500, B.WHITE, anchor="end")]
    return W, H, B.svg_doc(W, H, b, bg=B.WHITE, label="КРЮК24 — тарифы"), "05_stend_tarify_A3_297x420mm"


def desk():
    """Настольная табличка A5 (210x148 мм) — обозначает место приема заявок и оплаты."""
    W, H = 210, 148
    M = 16
    g, _ = B.lockup(M, 13, 38)
    t = B.fit("ПРИЕМ ЗАЯВОК И ОПЛАТА", W - 2 * M, "display", 700, 0.02)
    b = [g, B.rect(M, 60, W - 2 * M, 1.6, B.ORANGE),
         T(M, 60 + 12 + t * 0.72, "ПРИЕМ ЗАЯВОК И ОПЛАТА", t, "display", 700, B.WHITE, ls=t * 0.02),
         T(M, 108, "Оплата: наличными или банковским переводом", 7.4, "text", 400, GREY),
         T(M, 133, B.PHONE, 16, "display", 700, B.ORANGE),
         T(W - M, 133, B.SITE, 8.6, "text", 500, GREY, anchor="end")]
    return W, H, B.svg_doc(W, H, b, label="КРЮК24 — настольная табличка"), "06_nastolnaya_tablichka_A5_210x148mm"


def main():
    (OUT / "png").mkdir(parents=True, exist_ok=True)
    for build in (facade, entrance, lambda: pointer("right"), lambda: pointer("left"), interior, tariffs, desk):
        w, h, s, stem = build()
        (OUT / f"{stem}.svg").write_text(s, encoding="utf-8")
        pw = round(1600 * w / max(w, h))
        B.render(s, png_path=OUT / "png" / f"{stem}.png", pdf_path=OUT / f"{stem}.pdf", png_width=pw)
        print(f"{stem:44} {w}x{h} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
