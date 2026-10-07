"""Make the KRYUK24-colour version of the operator dashboard (ops_views.py) from the installed one.

    python runtime/wip/dashboard_colours/make_patch.py            write ops_views.py next to this script
    python runtime/wip/dashboard_colours/make_patch.py --check    exit 1 when the written file is not what the source gives

Source: runtime/server/ops_views.py, the record of the file installed on the server (Gev's design, protected).
Only colours change: the azure / cyan palette becomes KRYUK24's navy / orange from design/tokens (Gev's yes,
07.10.2026 22:58 UTC). Layout, sizes, radii, texts, icons, logos, behaviour and every line of Python stay as they are.
Every replacement is an exact string that must occur the stated number of times, so a changed source stops the
script instead of producing a half-coloured file.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "runtime" / "server" / "ops_views.py"
OUT = Path(__file__).resolve().parent / "ops_views.py"
SRC_SHA = "f5f6e9d8"  # first 8 hex of the installed file's sha256 (docs/CURRENT_STATE.md 3.2)

# (old, new, expected count)
R = [
    # primitives: KRYUK24 navy / grey scale under the same names, orange instead of azure / cyan
    ("--neutral-0:#ffffff;--neutral-50:#f8fafc;--neutral-100:#f1f5f9;--neutral-200:#e2e8f0;--neutral-300:#cbd5e1;--neutral-400:#94a3b8;--neutral-500:#64748b;--neutral-700:#334155;--neutral-800:#1e293b;--neutral-900:#0f172a;--neutral-950:#020617;\n--blue-400:#38bdf8;--blue-500:#0ea5e9;--blue-600:#0284c7;--cyan-400:#22d3ee;--cyan-500:#06b6d4;",
     "--neutral-0:#ffffff;--neutral-50:#f4f6f8;--neutral-100:#eef1f4;--neutral-200:#dde3ea;--neutral-300:#c5cdd7;--neutral-400:#9aa6b6;--neutral-500:#5a6676;--neutral-700:#3e4a5a;--neutral-800:#1c3150;--neutral-900:#13233a;--neutral-950:#0b1524;\n--orange-300:#f18a4b;--orange-350:#ff8a4c;--orange-400:#ff7424;--orange-500:#ef5b00;--orange-700:#a33d00;", 1),
    # light semantic
    ("--text:var(--neutral-950);--text2:var(--neutral-700);--muted:var(--neutral-500);--inverse:var(--neutral-0);",
     "--text:var(--neutral-900);--text2:var(--neutral-700);--muted:var(--neutral-500);--inverse:var(--neutral-0);--on-action:var(--neutral-900);", 1),
    ("--action:var(--blue-600);--action-strong:#0369a1;--accent:var(--cyan-500);--accent-soft:rgba(6,182,212,.14);--focus:var(--blue-500);",
     "--action:var(--orange-500);--action-strong:var(--orange-700);--accent:var(--orange-300);--accent-soft:rgba(239,91,0,.10);--focus:var(--orange-500);", 1),
    ("--ok:#15803d;--okbg:rgba(34,197,94,.12);--okfill:#22c55e;", "--ok:#166534;--okbg:rgba(22,163,74,.12);--okfill:#16a34a;", 1),
    ("--review:#b45309;--reviewbg:rgba(245,158,11,.14);--reviewfill:#f59e0b;", "--review:#92400e;--reviewbg:rgba(245,158,11,.14);--reviewfill:#f59e0b;", 1),
    ("--work:#0369a1;--workbg:rgba(2,132,199,.10);", "--work:#2a4466;--workbg:rgba(19,35,58,.08);", 1),
    ("--hover:rgba(2,132,199,.08);--selected:rgba(2,132,199,.12);--overlay:rgba(2,6,23,.52);",
     "--hover:rgba(19,35,58,.06);--selected:rgba(239,91,0,.12);--overlay:rgba(11,21,36,.56);", 1),
    ("--grad:linear-gradient(135deg,var(--action),var(--accent));", "--grad:linear-gradient(var(--action),var(--action));", 1),
    ("--shadow-sm:0 1px 2px rgba(15,23,42,.08);--shadow:0 12px 30px rgba(15,23,42,.10);--shadow-lg:0 24px 70px rgba(15,23,42,.16);",
     "--shadow-sm:0 1px 2px rgba(19,35,58,.08);--shadow:0 12px 30px rgba(19,35,58,.10);--shadow-lg:0 24px 70px rgba(19,35,58,.16);", 1),
    ("--glow:0 0 40px rgba(6,182,212,.24);--shadow-hover:0 30px 84px rgba(6,182,212,.18);",
     "--glow:0 0 0 3px rgba(239,91,0,.18);--shadow-hover:0 18px 44px rgba(19,35,58,.14);", 1),
    # dark semantic
    ("--line:rgba(255,255,255,.12);--line2:rgba(34,211,238,.32);", "--line:rgba(255,255,255,.10);--line2:rgba(241,138,75,.32);", 1),
    ("--action:var(--blue-500);--action-strong:var(--blue-400);--accent:var(--cyan-400);--accent-soft:rgba(34,211,238,.16);--focus:var(--cyan-400);",
     "--action:var(--orange-500);--action-strong:var(--orange-350);--accent:var(--orange-300);--accent-soft:rgba(241,138,75,.14);--focus:var(--orange-300);", 1),
    ("--work:var(--blue-400);--workbg:rgba(14,165,233,.16);", "--work:var(--neutral-300);--workbg:rgba(255,255,255,.06);", 1),
    ("--hover:rgba(14,165,233,.12);--selected:rgba(14,165,233,.18);--overlay:rgba(2,6,23,.72);",
     "--hover:rgba(255,255,255,.06);--selected:rgba(241,138,75,.16);--overlay:rgba(3,8,16,.72);", 1),
    ("--glow:0 0 40px rgba(34,211,238,.24);--shadow-hover:0 30px 84px rgba(34,211,238,.18);",
     "--glow:0 0 0 3px rgba(241,138,75,.24);--shadow-hover:0 18px 44px rgba(0,0,0,.45);", 1),
    # the navy band: orange spotlight instead of azure / cyan
    ("radial-gradient(90% 140% at 100% 0%,rgba(14,165,233,.28) 0%,transparent 55%),radial-gradient(70% 120% at 0% 100%,rgba(34,211,238,.16) 0%,transparent 55%)",
     "radial-gradient(90% 140% at 100% 0%,rgba(239,91,0,.20) 0%,transparent 55%),radial-gradient(70% 120% at 0% 100%,rgba(241,138,75,.10) 0%,transparent 55%)", 1),
    ("/* top: dark navy contrast band in both themes, grid + azure/cyan spotlight */", "/* top: dark navy contrast band in both themes, grid + soft orange spotlight (KRYUK24 colours) */", 1),
    # elements that named azure / cyan directly
    (".logo{width:52px;height:52px;border-radius:var(--r-pill);background:linear-gradient(135deg,var(--blue-500),var(--cyan-400));color:var(--neutral-950);display:grid;place-items:center;box-shadow:0 0 40px rgba(34,211,238,.35)}",
     ".logo{width:52px;height:52px;border-radius:var(--r-pill);background:var(--orange-500);color:var(--neutral-900);display:grid;place-items:center}", 1),
    ("border:1px solid rgba(34,211,238,.32);background:rgba(34,211,238,.10);color:var(--cyan-400);",
     "border:1px solid rgba(241,138,75,.40);background:rgba(239,91,0,.14);color:var(--orange-300);", 1),
    ("padding:2px;background:linear-gradient(135deg,var(--blue-500),var(--cyan-400));box-shadow:0 0 32px rgba(34,211,238,.35)}",
     "padding:2px;background:var(--orange-500)}", 1),
    ("color:var(--neutral-950);background:linear-gradient(135deg,var(--blue-500),var(--cyan-400));border-radius:var(--r-pill);padding:1px 7px;box-shadow:0 0 12px rgba(34,211,238,.45)}",
     "color:var(--neutral-900);background:var(--orange-500);border-radius:var(--r-pill);padding:1px 7px}", 1),
    (".clock .sun{color:var(--cyan-400)}.clock .moon{color:var(--blue-400)}", ".clock .sun{color:var(--orange-300)}.clock .moon{color:var(--neutral-300)}", 1),
    ("filter:drop-shadow(0 0 6px rgba(6,182,212,.35))", "filter:none", 1),
    ("background:var(--grad);color:var(--inverse);box-shadow:var(--glow)}", "background:var(--grad);color:var(--on-action)}", 1),
    ("padding:2px;background:linear-gradient(135deg,var(--blue-500),var(--cyan-400));box-shadow:var(--glow)}", "padding:2px;background:var(--orange-500)}", 1),
    # buttons: orange with navy text (white on orange fails 4.5:1)
    ("border-radius:var(--r-pill);border:0;background:var(--grad);color:var(--inverse);font-weight:600;font-size:16px;",
     "border-radius:var(--r-pill);border:0;background:var(--grad);color:var(--on-action);font-weight:600;font-size:16px;", 1),
    ("button:hover{transform:translateY(-2px);box-shadow:var(--glow)}", "button:hover{transform:translateY(-2px);box-shadow:var(--glow);background:var(--orange-400)}", 1),
    ("button.second{background:var(--soft);", "button.second,button.second:hover{background:var(--soft);", 1),
    # the progress ring gradient lives in the Python markup
    ('<stop offset="0" stop-color="#0284c7"/><stop offset="1" stop-color="#22d3ee"/>', '<stop offset="0" stop-color="#ef5b00"/><stop offset="1" stop-color="#f18a4b"/>', 1),
]
FOREIGN = ("#0284c7", "#22d3ee", "#0ea5e9", "#38bdf8", "#06b6d4", "#0369a1", "rgba(34,211,238", "rgba(6,182,212", "rgba(14,165,233", "rgba(2,132,199", "--blue-", "--cyan-")


def build():
    src = SRC.read_text(encoding="utf-8")
    if not hashlib.sha256(src.encode("utf-8")).hexdigest().startswith(SRC_SHA):
        raise SystemExit("runtime/server/ops_views.py is not the installed file this patch was made for (sha256 " + SRC_SHA + "…)")
    out = src
    for old, new, n in R:
        if out.count(old) != n:
            raise SystemExit("expected %d× %r, found %d" % (n, old[:80], out.count(old)))
        out = out.replace(old, new)
    left = [f for f in FOREIGN if f in out]
    if left:
        raise SystemExit("azure / cyan left in the result: " + ", ".join(left))
    return out


def main():
    out = build()
    if "--check" in sys.argv[1:]:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == out
        print("DASHBOARD COLOURS: " + ("up to date" if ok else "STALE"))
        return 0 if ok else 1
    OUT.write_text(out, encoding="utf-8", newline="")
    print("written %s, sha256 %s" % (OUT.relative_to(ROOT), hashlib.sha256(out.encode("utf-8")).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
