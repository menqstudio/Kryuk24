"""Чистка многослойного styles.css без изменения вида страницы.

Что делает:
1. Разбирает CSS (правила, @media, @keyframes, @supports), убирает комментарии.
2. Раскладывает группы «a,b{…}» на отдельные селекторы — порядок и специфичность те же.
3. Удаляет правила, чьи селекторы не встречаются ни на одной странице сайта
   (список совпадений собирает браузер: tools/css_clean_probe.py → matches.json).
4. Удаляет объявление, если ниже то же свойство для того же селектора задано снова
   в том же медиа-контексте или безусловно (с учётом !important и шорткатов) —
   такое объявление никогда не побеждает.
5. Удаляет пустые правила и неиспользуемые @keyframes, склеивает соседние правила
   с одинаковым телом обратно в группы.

Проверка результата — сравнение вычисленных стилей до/после (css_clean_probe.py --compare).
"""
import json
import re
import sys
from pathlib import Path

SHORTHANDS = {
    "padding": ["padding-top", "padding-right", "padding-bottom", "padding-left", "padding-block", "padding-inline",
                "padding-block-start", "padding-block-end", "padding-inline-start", "padding-inline-end"],
    "padding-block": ["padding-top", "padding-bottom", "padding-block-start", "padding-block-end"],
    "padding-inline": ["padding-left", "padding-right", "padding-inline-start", "padding-inline-end"],
    "margin": ["margin-top", "margin-right", "margin-bottom", "margin-left", "margin-block", "margin-inline",
               "margin-block-start", "margin-block-end", "margin-inline-start", "margin-inline-end"],
    "margin-block": ["margin-top", "margin-bottom", "margin-block-start", "margin-block-end"],
    "margin-inline": ["margin-left", "margin-right", "margin-inline-start", "margin-inline-end"],
    "inset": ["top", "right", "bottom", "left"],
    "border-radius": ["border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius", "border-bottom-right-radius"],
    "gap": ["row-gap", "column-gap"],
    "overflow": ["overflow-x", "overflow-y"],
    "flex": ["flex-grow", "flex-shrink", "flex-basis"],
    "outline": ["outline-color", "outline-style", "outline-width"],
    "transition": ["transition-property", "transition-duration", "transition-timing-function", "transition-delay"],
    "animation": ["animation-name", "animation-duration", "animation-timing-function", "animation-delay",
                  "animation-iteration-count", "animation-direction", "animation-fill-mode", "animation-play-state"],
    "font": ["font-family", "font-size", "font-weight", "font-style", "line-height", "font-variant", "font-stretch"],
    "background": ["background-color", "background-image", "background-repeat", "background-position", "background-size",
                   "background-attachment", "background-origin", "background-clip"],
    "list-style": ["list-style-type", "list-style-position", "list-style-image"],
    "text-decoration": ["text-decoration-line", "text-decoration-color", "text-decoration-style", "text-decoration-thickness"],
    "grid-template": ["grid-template-columns", "grid-template-rows", "grid-template-areas"],
    "grid-column": ["grid-column-start", "grid-column-end"],
    "grid-row": ["grid-row-start", "grid-row-end"],
    "place-items": ["align-items", "justify-items"],
    "place-content": ["align-content", "justify-content"],
    "border": ["border-width", "border-style", "border-color", "border-top", "border-right", "border-bottom", "border-left",
               "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
               "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
               "border-top-color", "border-right-color", "border-bottom-color", "border-left-color"],
}


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_block(css, i=0):
    """Returns list of nodes: ('rule', selector, decls) | ('at', prelude, children|raw)."""
    nodes = []
    n = len(css)
    while i < n:
        while i < n and css[i] in " \t\r\n;":
            i += 1
        if i >= n or css[i] == "}":
            return nodes, i + 1
        j = i
        depth = 0
        while j < n and css[j] != "{":
            if css[j] == ";" and css[i] == "@":
                break
            j += 1
        if j >= n:
            break
        if css[j] == ";":  # @import / @charset
            nodes.append(("raw", css[i:j + 1].strip(), None))
            i = j + 1
            continue
        prelude = css[i:j].strip()
        if prelude.startswith("@media") or prelude.startswith("@supports") or prelude.startswith("@layer"):
            children, k = parse_block(css, j + 1)
            nodes.append(("at", prelude, children))
            i = k
        elif prelude.startswith("@"):  # keyframes, font-face: keep raw
            depth = 0
            k = j
            while k < n:
                if css[k] == "{":
                    depth += 1
                elif css[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            nodes.append(("raw", css[i:k + 1].strip(), prelude))
            i = k + 1
        else:
            k = css.index("}", j)
            nodes.append(("rule", prelude, parse_decls(css[j + 1:k])))
            i = k + 1
    return nodes, i


def parse_decls(body):
    out = []
    buf, depth = "", 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    decls = []
    for d in out:
        if ":" not in d:
            continue
        prop, val = d.split(":", 1)
        prop = prop.strip().lower()
        val = val.strip()
        imp = bool(re.search(r"!\s*important\s*$", val))
        decls.append([prop, val, imp])
    return decls


def split_selectors(sel):
    parts, buf, depth = [], "", 0
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return [re.sub(r"\s+", " ", p) for p in parts]


def flatten(nodes, media=""):
    """Linear list of items in cascade order: dict(kind, media, sel, decls | raw)."""
    out = []
    for kind, a, b in nodes:
        if kind == "rule":
            for s in split_selectors(a):
                out.append({"kind": "rule", "media": media, "sel": s, "decls": [list(d) for d in b]})
        elif kind == "at":
            m = re.sub(r"\s+", " ", a)
            out.extend(flatten(b, (media + " && " if media else "") + m))
        else:
            out.append({"kind": "raw", "media": media, "raw": a, "name": b})
    return out


def covers(later, earlier):
    return later == earlier or later == ""


def dedupe(items):
    rules = [it for it in items if it["kind"] == "rule"]
    removed = 0
    for i, it in enumerate(rules):
        for d in it["decls"]:
            if d is None:
                continue
            prop, _, imp = d
            for later in rules[i + 1:]:
                if later["sel"] != it["sel"] or not covers(later["media"], it["media"]):
                    continue
                hit = False
                for ld in later["decls"]:
                    if ld is None:
                        continue
                    lp, _, limp = ld
                    if imp and not limp:
                        continue
                    if lp == prop or prop in SHORTHANDS.get(lp, []):
                        if prop.startswith("--") or lp.startswith("--") or lp == prop or not prop.startswith("--"):
                            hit = True
                            break
                if hit:
                    idx = it["decls"].index(d)
                    it["decls"][idx] = None
                    removed += 1
                    break
    for it in rules:
        it["decls"] = [d for d in it["decls"] if d is not None]
    return removed


def keep_selector(sel, matched, keep_tokens):
    # state classes appear only after user actions (scroll, click, JS) — the probe may not see them
    if any(t in sel for t in keep_tokens):
        return True
    if sel in matched:
        return matched[sel]
    return True  # unknown to the probe → keep (safe)


def build(items):
    """Re-group adjacent rules with identical media+body, re-nest media."""
    out, i = [], 0
    while i < len(items):
        it = items[i]
        if it["kind"] == "rule":
            body = ";".join(f"{p}:{v}" for p, v, _ in it["decls"])
            sels = [it["sel"]]
            j = i + 1
            while j < len(items) and items[j]["kind"] == "rule" and items[j]["media"] == it["media"] and \
                    ";".join(f"{p}:{v}" for p, v, _ in items[j]["decls"]) == body:
                sels.append(items[j]["sel"])
                j += 1
            out.append({"media": it["media"], "text": ",".join(sels) + "{" + body + "}"})
            i = j
        else:
            out.append({"media": it["media"], "text": it["raw"]})
            i += 1
    # nest by media, merging consecutive blocks with the same media
    css, cur, buf = [], None, []

    def flush():
        if not buf:
            return
        if cur:
            levels = cur.split(" && ")
            inner = "\n".join("  " + x for x in buf)
            block = inner
            for lv in reversed(levels):
                block = f"{lv}{{\n{block}\n}}"
            css.append(block)
        else:
            css.extend(buf)

    for o in out:
        if o["media"] != cur:
            flush()
            cur, buf = o["media"], []
        buf.append(o["text"])
    flush()
    return "\n".join(css) + "\n"


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    matches = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) > 3 else {}
    css = strip_comments(src.read_text(encoding="utf-8"))
    nodes, _ = parse_block(css)
    items = flatten(nodes)
    n_rules = sum(1 for it in items if it["kind"] == "rule")
    n_decl = sum(len(it["decls"]) for it in items if it["kind"] == "rule")
    keep_tokens = [":not(.js)", "no-js", "is-", "field--inactive", "choice-", "address-results", "[open]", "[hidden]", "::backdrop", "print"]
    unused = 0
    if matches:
        kept = []
        for it in items:
            if it["kind"] == "rule" and not keep_selector(it["sel"], matches, keep_tokens):
                unused += 1
                continue
            kept.append(it)
        items = kept
    removed = dedupe(items)
    items = [it for it in items if it["kind"] != "rule" or it["decls"]]
    body = " ".join(";".join(f"{p}:{v}" for p, v, _ in it["decls"]) for it in items if it["kind"] == "rule")
    final = []
    for it in items:
        if it["kind"] == "raw" and it["name"] and it["name"].startswith("@keyframes"):
            name = it["name"].split()[1]
            if not re.search(r"\b" + re.escape(name) + r"\b", body):
                continue
        final.append(it)
    out = build(final)
    dst.write_text(out, encoding="utf-8", newline="\n")
    print(json.dumps({"rules_in": n_rules, "decls_in": n_decl, "unused_selectors_removed": unused,
                      "overridden_decls_removed": removed, "bytes_in": src.stat().st_size, "bytes_out": dst.stat().st_size}))


if __name__ == "__main__":
    main()
