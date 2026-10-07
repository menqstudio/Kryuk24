#!/bin/sh
# Read-only facts needed before the install. Changes nothing and opens no secret file.
#   sudo sh preinstall_facts.sh > facts-before.txt
# Keep the output: the rollback puts the owner, group and mode of the database folder back from it.
CODE=/opt/kryuk24
DATA=/var/lib/kryuk24
echo "== time"; date -u +"%FT%TZ"
echo "== units that use $CODE (these are stopped for the patch)"
grep -ls "$CODE" /etc/systemd/system/*.service /etc/systemd/system/*.timer 2>/dev/null
echo "== their state now: active / enabled, and User, Group, UMask"
for unit in $(grep -ls "$CODE" /etc/systemd/system/*.service 2>/dev/null | xargs -n1 basename 2>/dev/null); do
  printf '%s: %s / %s; ' "$unit" "$(systemctl is-active "$unit")" "$(systemctl is-enabled "$unit" 2>/dev/null)"
  systemctl show "$unit" -p User -p Group -p SupplementaryGroups -p UMask --no-pager | tr '\n' ' '; echo
done
echo "== timers"; systemctl list-timers --all --no-pager | grep -i 'kryuk\|NEXT'
echo "== database folder and files (owner:group mode name)"
stat -c '%U:%G %a %n' "$DATA" "$DATA"/runtime.sqlite* 2>&1
echo "== everything else in the folder (names and modes only)"
ls -la "$DATA" | awk '{print $1, $3, $4, $9}'
echo "== journal mode"; python3 -c "import sqlite3;print(sqlite3.connect('file:$DATA/runtime.sqlite?mode=ro',uri=True).execute('PRAGMA journal_mode').fetchone()[0])" 2>&1
echo "== code folder: can another user read it"; stat -c '%U:%G %a %n' "$CODE" "$CODE"/ops_work.py 2>&1
echo "== table row counts (the snapshot: run this script again after the install and compare)"
python3 - <<EOF 2>&1
import sqlite3
c = sqlite3.connect("file:$DATA/runtime.sqlite?mode=ro", uri=True)
for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
    print(name, c.execute("SELECT count(*) FROM " + name).fetchone()[0])
print("report draft digests:", c.execute("SELECT day, status, revision, digest FROM ops_tasks WHERE job='DAILY_REPORT' ORDER BY day DESC LIMIT 2").fetchall())
EOF
echo "== credential folders: owner:group mode (no file is opened)"
stat -c '%U:%G %a %n' /etc /etc/kryuk24-bro /etc/kryuk24-api-read 2>&1
echo "== users and groups this install adds (must be absent now)"
for name in kryuk-api-read; do id "$name" 2>&1; done
for name in kryuk-api-read kryuk-db kryuk-readers; do getent group "$name" || echo "group $name: absent"; done
echo "== groups of kryuk-run"; id kryuk-run
echo "== python and sqlite"; python3 -c "import sys,sqlite3;print(sys.version.split()[0], sqlite3.sqlite_version)"
