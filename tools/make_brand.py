"""Основные файлы фирменного стиля КРЮК24 (финальный логотип 04.10.2026).

Выход:
  brand/01_mark/      знак-крюк: orange/ink, ink на белом, белый, прозрачный — SVG + PNG 1024
  brand/02_lockups/   логотип «крюк + КРЮК24 / ЭВАКУАТОР+»: горизонтальный (темный, светлый, прозрачный), вертикальный — SVG + PNG
  brand/03_avatar/    аватары 1024: круг, скругленный квадрат, Яндекс Бизнес (крюк крупно, без скругления)
  brand/04_livery/    панель на дверь эвакуатора (черная и белая кабина) — SVG + PDF + PNG
  brand/05_favicon/   копия иконок сайта (они уже с новым крюком) + превью
Все из tools/brand.py — тот же крюк и те же шрифты, что на сайте.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

ROOT = B.ROOT
BR = ROOT / "brand"


def out(folder, stem, svg, png_w=1024, pdf=False, transparent=False):
    d = BR / folder
    (d / "png").mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.svg").write_text(svg, encoding="utf-8")
    B.render(svg, png_path=d / "png" / f"{stem}.png", pdf_path=(d / f"{stem}.pdf") if pdf else None,
             png_width=png_w, transparent=transparent)
    print(f"{folder}/{stem}")


def marks():
    # square 240 canvas, hook 180 high, centred
    S, H = 240, 180
    w = B.HOOK_W * H / B.HOOK_H
    x, y = (S - w) / 2, (S - H) / 2
    for stem, bg, col in (("mark_orange_on_ink", B.INK, B.ORANGE), ("mark_orange_transparent", None, B.ORANGE),
                          ("mark_ink_on_white", B.WHITE, B.INK), ("mark_ink_transparent", None, B.INK),
                          ("mark_white_on_ink", B.INK, B.WHITE)):
        g, _ = B.hook(x, y, H, col)
        out("01_mark", stem, B.svg_doc(S, S, [g], bg=bg, unit="px", label="КРЮК24 — знак"), transparent=bg is None)


def lockups():
    h = 120
    lw, lh = B.lockup_size(h)
    pad = 40
    W, H = round(lw + 2 * pad), round(lh + 2 * pad)
    for stem, bg, on in (("lockup_horizontal_on_ink", B.INK, "dark"), ("lockup_horizontal_on_white", B.WHITE, "light"),
                         ("lockup_horizontal_transparent_dark", None, "dark"), ("lockup_horizontal_transparent_light", None, "light")):
        g, _ = B.lockup(pad, pad, h, on)
        out("02_lockups", stem, B.svg_doc(W, H, [g], bg=bg, unit="px", label="КРЮК24 — эвакуатор"), png_w=1600, transparent=bg is None)
    S = 420
    for stem, bg, on in (("lockup_vertical_on_ink", B.INK, "dark"), ("lockup_vertical_transparent_dark", None, "dark"),
                         ("lockup_vertical_transparent_light", None, "light")):
        g, gh = B.lockup_vertical(S / 2, 0, 250, on)
        out("02_lockups", stem, B.svg_doc(S, S, [f'<g transform="translate(0,{(S - gh) / 2:.2f})">{g}</g>'], bg=bg, unit="px",
                                          label="КРЮК24 — эвакуатор"), png_w=1600, transparent=bg is None)


def avatars():
    S = 240
    def centred(h, col=B.ORANGE):
        w = B.HOOK_W * h / B.HOOK_H
        return B.hook((S - w) / 2, (S - h) / 2, h, col)[0]
    out("03_avatar", "avatar_round", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}px" height="{S}px">'
        f'<circle cx="120" cy="120" r="120" fill="{B.INK}"/>{centred(150)}</svg>', transparent=True)
    out("03_avatar", "avatar_square", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}px" height="{S}px">'
        f'<rect width="{S}" height="{S}" rx="54" fill="{B.INK}"/>{centred(160)}</svg>', transparent=True)
    # Яндекс Бизнес сам кладет круглую маску и показывает мелко: крюк 72 % высоты, без скругления
    out("03_avatar", "avatar_yandex", B.svg_doc(S, S, [centred(S * 0.72)], unit="px", label="КРЮК24"))


def livery():
    W, H = 900, 600
    for stem, bg, on, main in (("door_panel_black_truck", B.INK, "dark", B.WHITE), ("door_panel_white_truck", B.WHITE, "light", B.INK)):
        h = 190
        lw, _ = B.lockup_size(h)
        x0 = (W - lw) / 2
        g, _ = B.lockup(x0, 110, h, on)
        ph = B.fit(B.PHONE, lw, "display", 700)
        body = [g, B.rect(x0, 110 + h + 42, lw, 6, B.ORANGE),
                B.text(x0, 110 + h + 42 + 34 + ph * 0.74, B.PHONE, ph, "display", 700, main),
                B.text(W / 2, H - 46, "24/7 · " + B.SITE.upper(), 30, "text", 500, B.ORANGE, anchor="middle", ls=4)]
        out("04_livery", stem, B.svg_doc(W, H, body, bg=bg, unit="px", label="КРЮК24 — наклейка на дверь эвакуатора"), png_w=1600, pdf=True)


def favicon():
    d = BR / "05_favicon"; d.mkdir(parents=True, exist_ok=True)
    site = ROOT / "site"
    for f in ("favicon.ico", "favicon-16.png", "favicon-32.png", "favicon-48.png", "favicon-96.png",
              "apple-touch-icon-180.png", "icon-192.png", "icon-512.png", "site.webmanifest"):
        shutil.copy2(site / f, d / f)
    shutil.copy2(site / "assets" / "favicon.svg", d / "favicon.svg")
    print("05_favicon: copied from site")


if __name__ == "__main__":
    marks(); lockups(); avatars(); livery(); favicon()
