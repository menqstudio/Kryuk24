"""Render the operator dashboard (interactive view) from a throwaway test database, to an HTML file.
    python dash_render.py <server code dir> <out.html>
All data is synthetic (test tasks), nothing real."""
import sys
import tempfile
from pathlib import Path

code, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(code))
from ops_work import Operations  # noqa: E402
from runtime import now  # noqa: E402
import ops_views  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    ops = Operations(Path(tmp) / "db")
    ops.plan("2026-10-07")
    tasks = ops.report()["tasks"]
    ids = {t["job"]: t["id"] for t in tasks}
    jobs = list(ids)
    # a realistic mix: some done, one waiting for Gev, one blocked, the rest pending
    for job in jobs[:5]:
        if job == "DAILY_REPORT":
            continue
        ops.claim(ids[job], "worker")
        ops.observe(ids[job], "worker", "TEST", now(), "Թեստային դիտարկում")
    if "AVITO" in ids and ids["AVITO"]:
        try:
            ops.claim(ids["AVITO"], "worker2")
            ops.observe(ids["AVITO"], "worker2", "TEST", now(), "Կապակցիչ չկա", blocked=True)
        except ValueError:
            pass
    tid = ids["DAILY_REPORT"]
    ops.claim(tid, "worker")
    ops.draft(tid, "worker", dict(action="REPORT_DRAFT", account="TEST", destination="Local file", body="Թեստային հաշվետվություն", reason="Review only"))
    out.write_text(ops_views.dashboard(ops.report(), True), encoding="utf-8")
print("written", out)
