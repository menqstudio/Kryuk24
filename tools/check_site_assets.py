"""Static check of the site folder: every local file a page or a stylesheet points to exists.

    python tools/check_site_assets.py            exit 0 = nothing is missing

No browser and no network: this is the part of the site checks that runs anywhere (CI, a fresh checkout).
The full checks with a browser are tools/tests/run_checks.py.
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parents[1] / "site"
ATTR = re.compile(r"""(?:href|src|poster|content)\s*=\s*["']([^"']+)["']""", re.I)
SRCSET = re.compile(r"""srcset\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.I)
FILE_LIKE = re.compile(r"\.(css|js|png|jpe?g|webp|svg|ico|woff2?|json|webmanifest|xml|txt|html|mp4|pdf)$", re.I)


def local_target(page, ref):
    """The file a reference names, or None when it is not a local file (other site, anchor, data, phone, mail)."""
    ref = ref.strip()
    parts = urlsplit(ref)
    if parts.scheme or parts.netloc or ref.startswith(("#", "data:", "tel:", "mailto:", "//")) or not parts.path:
        return None
    path = unquote(parts.path)
    target = SITE / path.lstrip("/") if path.startswith("/") else page.parent / path
    if path.endswith("/"):
        target = target / "index.html"
    elif not FILE_LIKE.search(path):
        return None                                        # a route or a word in a content attribute, not a file
    return target


def main():
    missing, checked = [], 0
    for page in sorted(SITE.rglob("*")):
        if page.suffix.lower() not in (".html", ".css") or not page.is_file():
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        refs = CSS_URL.findall(text)
        if page.suffix.lower() == ".html":
            refs += ATTR.findall(text)
            for group in SRCSET.findall(text):
                refs += [item.strip().split(" ")[0] for item in group.split(",")]
        for ref in refs:
            target = local_target(page, ref)
            if target is None:
                continue
            checked += 1
            if not target.is_file():
                missing.append("%s -> %s" % (page.relative_to(SITE).as_posix(), ref))
    print("site files: %d, local references checked: %d, missing: %d" % (sum(1 for p in SITE.rglob("*") if p.is_file()), checked, len(set(missing))))
    for line in sorted(set(missing)):
        print("  MISSING", line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
