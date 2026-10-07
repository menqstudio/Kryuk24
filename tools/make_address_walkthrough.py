"""Рисованный пример «прохода с телефоном» для владельца: как выглядит видео одним дублем.

Это иллюстрация, не съемка: нарисованная панорама (улица → вывеска → дверь → помещение),
по которой «камера» идет без склеек, с таймером записи и подписями шагов. Нужна только
чтобы владелец понял маршрут. В Яндекс отправляется настоящее видео с места — на каждом
кадре это написано.

Выход: offers/address_video_guide/kryuk24_primer_prohoda_risunok.mp4
"""
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

ROOT = B.ROOT
SIG = ROOT / "brand" / "06_signage"
OUT = ROOT / "offers" / "address_video_guide"
W, H, FPS = 1080, 1920, 30
PW = 5440                      # panorama width
STYLE = {"Bold": ("display", 700), "SemiBold": ("text", 500), "Regular": ("text", 400)}


def T(d, xy, s, size, weight="Bold", fill=(255, 255, 255, 255), anchor="lt"):
    B.draw_text(d, xy, s, size, *STYLE[weight], fill=fill, anchor=anchor)


def sign(stem, x, y, w):
    s = (SIG / f"{stem}.svg").read_text(encoding="utf-8")
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s)
    vw, vh = float(vb.group(1)), float(vb.group(2))
    inner = s[s.index(">") + 1: s.rindex("</svg>")]
    h = w * vh / vw
    return (f'<svg x="{x}" y="{y}" width="{w}" height="{h:.0f}" viewBox="0 0 {vw} {vh}">{inner}</svg>', h)


def panorama_svg():
    b = []
    # --- outside: sky, wall, pavement
    b.append('<rect x="0" y="0" width="3300" height="1920" fill="#9fb4c6"/>')
    b.append('<rect x="0" y="230" width="3300" height="1290" fill="#c9c2b6"/>')
    for i in range(0, 3300, 220):                      # wall panels
        b.append(f'<rect x="{i}" y="230" width="4" height="1290" fill="#b5ad9f"/>')
    for yy in (560, 900, 1240):
        b.append(f'<rect x="0" y="{yy}" width="3300" height="4" fill="#b5ad9f"/>')
    b.append('<rect x="0" y="1520" width="3300" height="400" fill="#6f7276"/>')
    b.append('<rect x="0" y="1520" width="3300" height="18" fill="#55585c"/>')
    # windows
    for wx in (1180, 1560, 1940):
        b.append(f'<rect x="{wx}" y="880" width="300" height="420" fill="#31404d" stroke="#efece6" stroke-width="14"/>')
        b.append(f'<rect x="{wx + 143}" y="880" width="14" height="420" fill="#efece6"/>')
    # 1. address plates
    b.append('<rect x="150" y="640" width="640" height="210" rx="22" fill="#1f4fa8" stroke="#fff" stroke-width="10"/>')
    b.append('<text x="196" y="716" font-size="38" letter-spacing="5" fill="#dfe8fb" font-weight="600">УЛИЦА</text>')
    b.append('<text x="196" y="806" font-size="84" fill="#fff" font-weight="700">Бехтерева</text>')
    b.append('<rect x="820" y="640" width="210" height="210" rx="22" fill="#1f4fa8" stroke="#fff" stroke-width="10"/>')
    b.append('<text x="925" y="786" font-size="84" fill="#fff" font-weight="700" text-anchor="middle">41 к1</text>')
    # 2. facade sign + pointer
    s, _ = sign("01_vyveska_fasad_2000x500mm", 1200, 470, 1000)
    b.append(s)
    s, _ = sign("03_ukazatel_600x200mm_vpravo", 1400, 1360, 480)
    b.append(s)
    # 3. door + entrance plate
    b.append('<rect x="2700" y="640" width="400" height="880" fill="#3b3f45" stroke="#22252a" stroke-width="16"/>')
    b.append('<rect x="2740" y="690" width="320" height="380" fill="#55606b"/>')
    b.append('<rect x="3040" y="1090" width="18" height="70" rx="8" fill="#d8d8d8"/>')
    s, _ = sign("02_tablichka_vhod_400x300mm", 2300, 760, 360)
    b.append(s)
    # doorway (the cut between outside and inside is one continuous pan through the door)
    b.append('<rect x="3300" y="0" width="120" height="1920" fill="#1b1c1f"/>')
    # --- inside: wall, floor
    b.append(f'<rect x="3420" y="0" width="{PW - 3420}" height="1920" fill="#e9e6df"/>')
    b.append(f'<rect x="3420" y="1480" width="{PW - 3420}" height="440" fill="#8a7a66"/>')
    b.append(f'<rect x="3420" y="1460" width="{PW - 3420}" height="22" fill="#cfcabf"/>')
    # 4. wall logo, desk, desk plate, chair
    s, _ = sign("04_logo_zona_priema_1200x380mm", 3560, 420, 880)
    b.append(s)
    b.append('<rect x="3600" y="1180" width="800" height="40" fill="#5b4a3a"/>')
    b.append('<rect x="3640" y="1220" width="30" height="300" fill="#4a3c2f"/><rect x="4330" y="1220" width="30" height="300" fill="#4a3c2f"/>')
    b.append('<rect x="3640" y="1220" width="720" height="150" fill="#6a5745"/>')
    s, hh = sign("06_nastolnaya_tablichka_A5_210x148mm", 3880, 1180 - 190, 270)
    b.append(s)
    b.append('<rect x="3660" y="1120" width="150" height="60" rx="6" fill="#2b2b2b"/>')          # laptop base
    b.append('<rect x="3668" y="1010" width="134" height="112" rx="6" fill="#1f1f1f"/>')
    b.append('<rect x="4470" y="1040" width="150" height="230" rx="18" fill="#30343a"/><rect x="4450" y="1270" width="190" height="34" rx="10" fill="#30343a"/><rect x="4535" y="1304" width="20" height="180" fill="#30343a"/>')
    # tariff stand
    s, _ = sign("05_stend_tarify_A3_297x420mm", 4740, 520, 400)
    b.append(s)
    b.append('<rect x="4728" y="508" width="424" height="590" fill="none" stroke="#3a3a3a" stroke-width="10"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{H}" viewBox="0 0 {PW} {H}" '
            f'font-family="Roboto Condensed,Arial Narrow,sans-serif"><style>{B.font_face_css()}</style>{"".join(b)}</svg>')


def chromium():
    base = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
    hits = sorted(glob.glob(str(base / "chromium_headless_shell-*" / "*" / "*headless*shell*.exe")))
    if not hits:
        sys.exit("headless Chromium not found")
    return hits[-1]


# (time, camera x). Between keys the camera eases; equal x = hold.
KEYS = [(0, 0), (5, 0), (9, 1160), (14, 1160), (18, 2130), (23, 2130),
        (28, 3460), (34, 3460), (38, 4360), (43, 4360)]
CAPTIONS = [(0, 5.5, "ШАГ 1", "Дом и табличка с адресом"),
            (9, 14.5, "ШАГ 2", "Вывеска КРЮК24"),
            (18, 23.5, "ШАГ 3", "Вход и табличка у двери"),
            (23.5, 28, "НЕ ВЫКЛЮЧАЕМ", "Заходим внутрь — запись идет"),
            (28, 34.5, "ШАГ 4", "Место приема клиентов"),
            (38, 43, "ШАГ 4", "Стенд с тарифами — и только теперь «стоп»")]
END = 43.0


def cam_x(t):
    for (t0, x0), (t1, x1) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            if x0 == x1:
                return x0
            k = (t - t0) / (t1 - t0)
            k = k * k * (3 - 2 * k)           # smoothstep
            return x0 + (x1 - x0) * k
    return KEYS[-1][1]


def overlay(frame, t):
    d = ImageDraw.Draw(frame, "RGBA")
    # phone-camera chrome: REC + running timer = "one take"
    d.rounded_rectangle([40, 50, 330, 124], radius=37, fill=(0, 0, 0, 150))
    if int(t * 2) % 2 == 0:
        d.ellipse([62, 72, 92, 102], fill=(230, 40, 40, 255))
    T(d, (108, 72), f"REC {int(t) // 60:02d}:{int(t) % 60:02d}", 42, "SemiBold")
    d.rounded_rectangle([W - 470, 50, W - 40, 124], radius=37, fill=(239, 91, 0, 235))
    T(d, (W - 255, 87), "ПРИМЕР · РИСУНОК", 36, "Bold", (17, 17, 17, 255), anchor="mm")
    # step caption
    for t0, t1, kick, title in CAPTIONS:
        if t0 <= t < t1:
            d.rectangle([0, H - 400, W, H - 150], fill=(17, 17, 17, 225))
            T(d, (60, H - 364), kick, 40, "SemiBold", (239, 91, 0, 255))
            size = 70
            while B.measure(title, size, "display", 700) > W - 120:
                size -= 2
            T(d, (60, H - 300), title, size, "Bold")
    d.rectangle([0, H - 150, W, H], fill=(17, 17, 17, 255))
    T(d, (W // 2, H - 100), "Образец маршрута. В Яндекс отправляется", 34, "Regular", (190, 190, 190, 255), anchor="mm")
    T(d, (W // 2, H - 54), "только настоящее видео, снятое на месте.", 34, "Regular", (190, 190, 190, 255), anchor="mm")
    return frame


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    html = OUT / "_pano.html"
    html.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}svg{display:block}</style>'
                    + panorama_svg(), encoding="utf-8")
    pano_png = OUT / "_panorama.png"
    subprocess.run([chromium(), "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={PW},{H}", f"--screenshot={pano_png}", html.as_uri()],
                   check=True, capture_output=True)
    html.unlink()
    pano = Image.open(pano_png).convert("RGB")
    assert pano.size == (PW, H), pano.size

    dst = OUT / "kryuk24_primer_prohoda_risunok.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(END * FPS)
    for i in range(n):
        t = i / FPS
        x = int(round(cam_x(t)))
        frame = pano.crop((x, 0, x + W, H))
        p.stdin.write(overlay(frame, t).tobytes())
    p.stdin.close()
    p.wait()
    print(f"{dst.name}  {END:.0f}s  {round(dst.stat().st_size / 1024)}KB")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
