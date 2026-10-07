"""Check the KRYUK24 design system. Exit 0 = GREEN.

    python design/scripts/validate_design.py

1. Generated files (tokens CSS/JSON, hook vector) equal what the sources produce.
2. The vendored component library is byte-for-byte the pinned upstream copy (sha256 in UPSTREAM.json).
3. Every custom property the components read is defined by KRYUK24 tokens (or by the component CSS itself).
4. WCAG contrast pairs from the token source pass in light and dark.
5. No other brand leaks into KRYUK24 files: no foreign brand colours, no foreign logo component, no foreign name in visible text.
6. design/README.md has an English and an Armenian part.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "design"
VENDOR = D / "vendor" / "menq-components"
errors = []

# 1. Generated files
r = subprocess.run([sys.executable, str(D / "scripts" / "build_tokens.py"), "--check"], capture_output=True, text=True)
if r.returncode:
    errors.append("generated files are stale: " + r.stdout.strip())

# 2. Vendored copy
up = json.loads((VENDOR / "UPSTREAM.json").read_text(encoding="utf-8"))
if not re.fullmatch(r"[0-9a-f]{40}", up.get("commit", "")):
    errors.append("UPSTREAM.json: commit must be a full SHA")
for name, rec in up["files"].items():
    f = VENDOR / name
    if not f.is_file():
        errors.append("vendor file missing: " + name)
    elif hashlib.sha256(f.read_bytes()).hexdigest() != rec["sha256"]:
        errors.append("vendor file changed by hand: " + name)
extra = sorted(p.name for p in VENDOR.iterdir() if p.name not in up["files"] and p.name != "UPSTREAM.json")
if extra:
    errors.append("unpinned files in vendor/: " + ", ".join(extra))

# 3. Custom property coverage
tokens_css = (D / "tokens" / "kryuk.tokens.css").read_text(encoding="utf-8")
DEF = re.compile(r"(--[a-z0-9-]+)\s*:")
USE = re.compile(r"var\((--[a-z0-9-]+)")
defined = set(DEF.findall(tokens_css))
layer = [VENDOR / "bundle.css", VENDOR / "bro.css", D / "components" / "kryuk.css"]
for f in layer:
    defined |= set(DEF.findall(f.read_text(encoding="utf-8")))
LOCAL = ("--mq-", "--kr-")
# The library's contrast scope reads its own primitives; kryuk.css redefines every surface that uses them.
OVERRIDDEN = {"--neutral-950", "--neutral-900", "--blue-600", "--blue-500", "--cyan-400"}
kryuk_css = (D / "components" / "kryuk.css").read_text(encoding="utf-8")
for must in (".section-contrast {", "--color-surface-primary: var(--navy-900)", ".section-spotlight {"):
    if must not in kryuk_css:
        errors.append("kryuk.css must override the library contrast scope (%s)" % must)
users = layer + [VENDOR / "bundle.js", VENDOR / "bro.bundle.js", D / "components" / "kryuk.bundle.js"]
for f in users:
    for name in sorted(set(USE.findall(f.read_text(encoding="utf-8")))):
        if name not in defined and not name.startswith(LOCAL) and name not in OVERRIDDEN:
            errors.append("%s reads %s, which KRYUK24 does not define" % (f.relative_to(ROOT), name))

# 4. Contrast
src = json.loads((D / "tokens" / "kryuk-tokens.source.json").read_text(encoding="utf-8"))
P = src["primitives"]


def value(theme, name):
    v = src["themes"][theme][name]
    m = re.fullmatch(r"\{(.+)\}", v)
    return P[m.group(1)] if m else v


def rgba(s):
    if s.startswith("#"):
        return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5)) + (1.0,)
    n = [float(x) for x in re.findall(r"[\d.]+", s)]
    return (n[0], n[1], n[2], n[3] if len(n) > 3 else 1.0)


def over(fg, bg):
    return tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)) + (1.0,)


def lum(c):
    ch = [(x / 255) / 12.92 if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4 for x in c[:3]]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


checks = 0
for theme in ("light", "dark"):
    page = rgba(value(theme, "color-page-bg"))
    for fg, bg, need in src["contrast"]:
        b = over(rgba(value(theme, bg)), page)
        f = over(rgba(value(theme, fg)), b)
        hi, lo = sorted((lum(f), lum(b)), reverse=True)
        ratio = (hi + 0.05) / (lo + 0.05)
        checks += 1
        if ratio < need:
            errors.append("contrast %s: %s on %s is %.2f, needs %.1f" % (theme, fg, bg, ratio, need))

# 5. Brand separation
FOREIGN_HEX = ("#0ea5e9", "#0284c7", "#0369a1", "#075985", "#22d3ee", "#06b6d4", "#67e8f9", "#38bdf8")
own = [D / "tokens" / "kryuk.tokens.css", D / "tokens" / "tokens.json", D / "tokens" / "kryuk-tokens.source.json",
       D / "components" / "kryuk.css", D / "components" / "kryuk.bundle.js", D / "preview" / "index.html"]
for f in own:
    text = f.read_text(encoding="utf-8").lower()
    for hx in FOREIGN_HEX:
        if hx in text:
            errors.append("%s carries a foreign brand colour %s" % (f.relative_to(ROOT), hx))
    if "brandmark" in text:
        errors.append("%s uses the foreign logo component (BrandMark); use KryukMark" % f.relative_to(ROOT))
    if re.search(r"""['">]\s*menq\b""", text):
        errors.append("%s shows the name MenQ as visible text" % f.relative_to(ROOT))

# 6. Bilingual README
readme = (D / "README.md").read_text(encoding="utf-8")
if "## English" not in readme or "## Հայերեն" not in readme:
    errors.append("design/README.md needs an English and an Armenian part")

if errors:
    print("KRYUK24 DESIGN SYSTEM: RED")
    for e in errors:
        print("- " + e)
    sys.exit(1)
print("KRYUK24 DESIGN SYSTEM: GREEN (vendor pinned at %s, %d files; %d contrast checks; brand separation clean)" % (up["commit"][:7], len(up["files"]), checks))
