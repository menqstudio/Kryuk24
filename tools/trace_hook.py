"""Векторизация нового крюка: brand/00_hook_master/kryuk24_hook_transparent.png → SVG-контур.

Крюк — одна заливка без градиентов, поэтому достаточно контура маски:
альфа-канал увеличивается ×4 (бикубически, края становятся гладкими), берется порог,
находятся внешний контур и отверстие кольца, точки прореживаются и через них
проводятся кривые Безье (Catmull-Rom). Результат сравнивается с исходником попиксельно.

Выход: brand/00_hook_master/hook_path.txt  (viewBox + d, читает tools/brand.py)
"""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "brand" / "00_hook_master" / "kryuk24_hook_transparent.png"
OUT = ROOT / "brand" / "00_hook_master" / "hook_path.txt"
K = 4  # upscale factor


def bezier_path(pts):
    """Closed Catmull-Rom spline through pts → SVG cubic Bezier segments."""
    n = len(pts)
    d = [f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return "".join(d) + "Z"


def resample(pts, step=5.0, sigma=1.2):
    """Even spacing along the contour (no bumps from uneven point density),
    light periodic smoothing (removes pixel stair-steps), then one point every `step` px."""
    seg = np.r_[np.hypot(*np.diff(np.vstack([pts, pts[:1]]), axis=0).T)]
    s = np.r_[0, np.cumsum(seg)]
    total = s[-1]
    t = np.arange(0, total, 0.25)
    closed = np.vstack([pts, pts[:1]])
    x = np.interp(t, s, closed[:, 0]); y = np.interp(t, s, closed[:, 1])
    r = int(sigma / 0.25 * 4)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) * 0.25 / sigma) ** 2); k /= k.sum()
    x = np.convolve(np.r_[x[-r:], x, x[:r]], k, "valid"); y = np.convolve(np.r_[y[-r:], y, y[:r]], k, "valid")
    idx = np.round(np.arange(0, len(x), step / 0.25)).astype(int) % len(x)
    return np.c_[x[idx], y[idx]]


def trace():
    a = cv2.imread(str(SRC), cv2.IMREAD_UNCHANGED)[:, :, 3]
    h, w = a.shape
    big = cv2.resize(a, (w * K, h * K), interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.2)
    _, m = cv2.threshold(big, 127, 255, cv2.THRESH_BINARY)
    contours, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in contours:
        if cv2.contourArea(c) < 50 * K * K:
            continue
        parts.append(bezier_path(resample(c[:, 0, :].astype(float) / K)))
    return w, h, "".join(parts)


def check(w, h, d):
    """Render the path back and compare with the source alpha (IoU)."""
    from playwright.sync_api import sync_playwright
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           f'<path fill="#000" fill-rule="evenodd" d="{d}"/></svg>')
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": w, "height": h})
        pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>')
        png = pg.screenshot(clip={"x": 0, "y": 0, "width": w, "height": h}); b.close()
    r = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE) < 128
    a = cv2.imread(str(SRC), cv2.IMREAD_UNCHANGED)[:, :, 3] > 127
    return (r & a).sum() / (r | a).sum()


if __name__ == "__main__":
    w, h, d = trace()
    iou = check(w, h, d)
    OUT.write_text(f"{w} {h}\n{d}\n", encoding="utf-8")
    print(f"viewBox 0 0 {w} {h} · path {len(d)} chars · IoU {iou:.4f}")
