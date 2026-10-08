#!/bin/sh
# Marks Gev's own test rows in the real portal as not Armen's (Gev's word of 08.10.2026: the photo of 10:28 UTC and
# the three answers before it were his test under the account "armen").
#   sudo sh exclude_test_rows.sh
# Rows saved up to 10:43 UTC of 08.10.2026, the moment page r2 was installed; exactly 1 photo and 3 answers are
# expected, anything else stops it. A private copy of the database is kept first. Nothing is deleted.
set -eu
CODE=/opt/kryuk24-armen
DATA=/var/lib/kryuk24-armen
KEEP=/root/kryuk24-config-backups
stop() { echo "STOP: $1"; exit 1; }
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -f "$CODE/exclude.py" ] || stop "the installed portal code has no exclude.py; update the code first"
echo "== time"; date -u +"%FT%TZ"
install -d -m 700 "$KEEP"
COPY="$KEEP/portal.sqlite.before-test-marks-$(date -u +%Y%m%dT%H%M%SZ)"
"$CODE/.venv/bin/python" -B -c "import sqlite3,sys;s=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);d=sqlite3.connect(sys.argv[2]);s.backup(d);d.close();s.close()" "$DATA/portal.sqlite" "$COPY"
chmod 600 "$COPY"
echo "private copy of the database: $COPY ($(stat -c '%a %s' "$COPY"))"
run() { (cd "$CODE" && runuser -u kryuk-armen -- "$CODE/.venv/bin/python" -B exclude.py --db "$DATA/portal.sqlite" --photos "$DATA/photos" \
  --before 2026-10-08T10:43:00+00:00 --reason "Gev's own test under the account armen, his word of 08.10.2026" --marked-by GEV --expect-photos 1 --expect-answers 3 "$@"); }
echo "== dry run"; run || true
echo "== apply"; run --apply
echo "== files kept: $(find "$DATA/photos" -type f | wc -l)"
date -u +"%FT%TZ"
echo "== done"
