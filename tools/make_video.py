"""Build the 17-second card/landing video from the owner's real job photos.

Slow Ken Burns push on each frame plus crossfades, so it reads as a real clip
rather than a slideshow. Output: 1920x1080 master + 1280x720 web copy, no audio.

Frames come from photo/01_real_polished/ — real jobs, plates and faces obscured.
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

W, H = 1920, 1080
FPS = 30
DURATION = 17.0     # hard requirement from Gev
FADE = 0.5          # crossfade length
ZOOM = 1.10         # end scale of the push

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photo" / "01_real_polished"
OUT = ROOT / "photo" / "03_video"

ORDER = [
    "evakuator-perevozka-mikroavtobusa-osen.jpg",        # the truck, autumn, warm
    "evakuator-perevozka-bmw-x6-krossover.jpg",          # premium car, clear day
    "evakuator-gazel-next-s-avtomobilem.jpg",            # the truck itself, close
    "evakuator-avtomobil-posle-dtp-bokovoy-udar.jpg",    # after a collision
    "evakuator-perevozka-audi-a8-biznes-klass.jpg",      # business class
    "evakuator-perevozka-gruzovogo-mikroavtobusa.jpg",   # a big van, roadside
]


def cover(path):
    """Scale-and-crop to exactly WxH so nothing is letterboxed."""
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    left = (im.width - W) // 2
    top = (im.height - H) // 2
    return im.crop((left, top, left + W, top + H))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stills = OUT / "_stills"
    stills.mkdir(exist_ok=True)
    prepared = []
    for i, name in enumerate(ORDER, 1):
        p = SRC / name
        if not p.exists():
            print("missing:", name)
            return 1
        dst = stills / f"{i:02d}.png"
        cover(p).save(dst)
        prepared.append(dst)

    n = len(prepared)
    # n*HOLD - (n-1)*FADE = DURATION
    hold = (DURATION + (n - 1) * FADE) / n
    frames = round(hold * FPS)

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    inputs, filters, labels = [], [], []
    for k, p in enumerate(prepared):
        inputs += ["-loop", "1", "-t", f"{hold:.3f}", "-i", str(p)]
        # alternate push-in / pull-out so consecutive shots do not feel identical
        if k % 2 == 0:
            z = f"1+{ZOOM - 1:.4f}*on/{frames}"
        else:
            z = f"{ZOOM:.4f}-{ZOOM - 1:.4f}*on/{frames}"
        filters.append(
            f"[{k}:v]scale={W * 2}:{H * 2},"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={W}x{H}:fps={FPS},setsar=1[v{k}]"
        )
        labels.append(f"[v{k}]")

    chain = labels[0]
    offset = hold - FADE
    for k in range(1, n):
        out = f"[x{k}]"
        filters.append(
            f"{chain}{labels[k]}xfade=transition=fade:duration={FADE}:offset={offset:.3f}{out}"
        )
        chain = out
        offset += hold - FADE

    master = OUT / "evakuator-24-chasa-moskva-17s-1080p.mp4"
    cmd = [ff, "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", chain, "-t", f"{DURATION}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-crf", "20", "-movflags", "+faststart",
           "-r", str(FPS), str(master)]
    print(f"{n} frames, hold {hold:.3f}s, target {DURATION}s")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(r.stderr[-3000:])
        return r.returncode

    # web copy: 720p, small enough for Yandex upload (10 MB limit) and the landing
    web = OUT / "evakuator-24-chasa-moskva-17s-720p.mp4"
    r = subprocess.run(
        [ff, "-y", "-i", str(master), "-vf", "scale=1280:720", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "26", "-movflags", "+faststart", str(web)],
        capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(r.stderr[-3000:])
        return r.returncode

    for f in (master, web):
        print("wrote", f.name, round(f.stat().st_size / 1024 / 1024, 2), "MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
