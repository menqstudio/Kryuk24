#!/usr/bin/env bash
# A trial on the server of the two things install.sh rests on and its tests only stand in for. Installs nothing.
#   sudo bash trial_on_server.sh
#
# Part A, the hold, with the real systemd and a throwaway unit (unit file and drop-in both under
# /run/systemd/system, which is memory, so nothing is written to the disk of the server): a running one-shot unit
# is "activating" and is-active does not say so; with the drop-in loaded the unit does not start; with the drop-in
# deleted it starts again. It does not show that a drop-in under /run applies to a unit file under /etc: that is
# how systemd reads drop-ins, and install.sh checks it on the real units each time (DropInPaths) before it goes on.
# Part B, the service, with the real Python and the service's own user: a copy of the code folder with the two
# new files, an empty database of its own, another port (18788), started as a transient unit with the same
# protections as kryuk-capture, asked for /health, restarted, asked again, stopped.
#
# What it touches on the server, all of it removed at the end, also when a step fails:
#   /run/systemd/system/kryuk-holdtrial-*.service and its .d folder, four "systemctl daemon-reload",
#   a transient unit kryuk-capture-trial-*, a folder under /tmp, port 127.0.0.1:18788.
# What it never touches: /opt/kryuk24, /var/lib/kryuk24, any real unit, timer, credential or database.
# It reads no credential: the trial service gets a random password of its own that is never printed.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REAL=/opt/kryuk24
PORT=18788
TAG="$$"
HT="kryuk-holdtrial-$TAG.service"
CT="kryuk-capture-trial-$TAG"
W=""
say() { printf '%s\n' "$*"; }
sha() { sha256sum 2>/dev/null < "$1" | cut -d' ' -f1; }
bad=0
check() {   # check "what" "measured" "expected"
  if [ "$2" = "$3" ]; then say "  ok    $1: $2"; else say "  WRONG $1: $2 (expected: $3)"; bad=1; fi
}
real_facts() { say "$(sha $REAL/ops_media.py) $(sha $REAL/ops_work.py) pid=$(systemctl show -p MainPID --value kryuk-capture.service) since=$(systemctl show -p ActiveEnterTimestamp --value kryuk-capture.service) state=$(systemctl is-active kryuk-capture.service)"; }
clean() {
  local code=$?
  trap - EXIT
  systemctl stop "$HT" >/dev/null 2>&1
  systemctl stop "$CT.service" >/dev/null 2>&1
  systemctl reset-failed "$HT" "$CT.service" >/dev/null 2>&1
  rm -f "/run/systemd/system/$HT" "/run/kryuk-holdtrial-$TAG.marker"
  rm -rf "/run/systemd/system/$HT.d"
  systemctl daemon-reload
  if [ -n "$W" ]; then rm -rf "$W"; fi
  say "--- after the clean-up"
  check "throwaway unit" "$(systemctl show -p LoadState --value "$HT")" "not-found"
  check "trial service" "$(systemctl show -p LoadState --value "$CT.service")" "not-found"
  check "files left in /etc/systemd/system, /run, /tmp" "$(ls -d /etc/systemd/system/kryuk-holdtrial-* /run/systemd/system/kryuk-holdtrial-* /run/kryuk-holdtrial-* /tmp/store-lock-trial.* 2>/dev/null | wc -l)" "0"
  check "port $PORT listening" "$(ss -ltn 2>/dev/null | grep -c ":$PORT ")" "0"
  check "the real files and the real service" "$(real_facts)" "$before"
  say "time: $(date -u +%FT%TZ)"
  if [ "$bad" = 0 ] && [ "$code" = 0 ]; then say "TRIAL OK"; exit 0; fi
  say "TRIAL FAILED"; exit 1
}

[ "$(id -u)" = 0 ] || { say "run with sudo"; exit 1; }
say "time: $(date -u +%FT%TZ); $(systemctl --version | head -1); $(/usr/bin/python3 --version 2>&1)"
for u in kryuk-capture kryuk-operations kryuk-backup kryuk-api-read kryuk-bro-api kryuk-armen; do
  if [ "$(systemctl show -p NeedDaemonReload --value "$u.service")" = yes ]; then say "STOP: the unit file of $u was changed and not loaded; a reload here would load it. Nothing was done"; exit 1; fi
done
if [ "$(ss -ltn 2>/dev/null | grep -c ":$PORT ")" != 0 ]; then say "STOP: port $PORT is in use. Nothing was done"; exit 1; fi
RUNAS="$(systemctl show -p User --value kryuk-capture.service)"
before="$(real_facts)"
say "the real files and the real service before: $before"
trap clean EXIT
trap 'exit 130' INT TERM HUP

say "--- A. the hold, with the real systemd"
cat > "/run/systemd/system/$HT" <<EOF
[Unit]
Description=KRYUK24 throwaway unit of trial_on_server.sh (safe to delete)
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'touch /run/kryuk-holdtrial-$TAG.marker; sleep 30'
EOF
systemctl daemon-reload
check "A1 the throwaway unit is loaded" "$(systemctl show -p LoadState --value "$HT")" "loaded"
systemctl start --no-block "$HT"; sleep 2
check "A2 a running one-shot unit, ActiveState" "$(systemctl show -p ActiveState --value "$HT")" "activating"
check "A3 the same moment, is-active" "$(systemctl is-active "$HT")" "activating"
systemctl is-active --quiet "$HT"; check "A4 the same moment, exit code of is-active --quiet (0 would mean active)" "$?" "3"
check "A5 it really ran" "$(ls /run/kryuk-holdtrial-$TAG.marker 2>/dev/null | wc -l)" "1"
systemctl stop "$HT"; rm -f "/run/kryuk-holdtrial-$TAG.marker"
check "A6 stopped" "$(systemctl show -p ActiveState --value "$HT")" "inactive"
mkdir -p "/run/systemd/system/$HT.d"
printf '[Unit]\nConditionPathExists=!%s\n' "/run/systemd/system/$HT.d/90-kryuk-store-lock-install.conf" > "/run/systemd/system/$HT.d/90-kryuk-store-lock-install.conf"
systemctl daemon-reload
case "$(systemctl show -p DropInPaths --value "$HT")" in *"$HT.d/90-kryuk-store-lock-install.conf"*) shown=yes;; *) shown=no;; esac
check "A7 the drop-in is loaded (DropInPaths)" "$shown" "yes"
systemctl start "$HT"; started=$?; sleep 1
check "A8 held: exit code of systemctl start" "$started" "0"
check "A9 held: ConditionResult" "$(systemctl show -p ConditionResult --value "$HT")" "no"
check "A10 held: ActiveState" "$(systemctl show -p ActiveState --value "$HT")" "inactive"
check "A11 held: its command did not run" "$(ls /run/kryuk-holdtrial-$TAG.marker 2>/dev/null | wc -l)" "0"
rm -f "/run/systemd/system/$HT.d/90-kryuk-store-lock-install.conf"
systemctl start --no-block "$HT"; sleep 2
check "A12 drop-in deleted, before any reload: it starts (a failed reload cannot keep a unit held)" "$(ls /run/kryuk-holdtrial-$TAG.marker 2>/dev/null | wc -l)" "1"
systemctl stop "$HT"; rm -f "/run/kryuk-holdtrial-$TAG.marker"
rmdir "/run/systemd/system/$HT.d"; systemctl daemon-reload
check "A13 after the release, DropInPaths" "$(systemctl show -p DropInPaths --value "$HT")" ""
systemctl start --no-block "$HT"; sleep 2
check "A14 after the release it starts" "$(systemctl show -p ActiveState --value "$HT")/$(ls /run/kryuk-holdtrial-$TAG.marker 2>/dev/null | wc -l)" "activating/1"
systemctl stop "$HT"

say "--- B. the service with the new files, in a temporary place"
W="$(mktemp -d /tmp/store-lock-trial.XXXXXX)"
mkdir "$W/code" "$W/data"
cp $REAL/*.py "$W/code/"
cp "$HERE/ops_media.py" "$HERE/ops_work.py" "$W/code/"
check "B1 the copy holds the new ops_media.py" "$(sha "$W/code/ops_media.py")" "0f877f7703279ec984da924f5f34965b99ac0d9488b428facae6d9fa1c897df4"
check "B2 the copy holds the new ops_work.py" "$(sha "$W/code/ops_work.py")" "69aa0809da3b8dd5c894b1abe2c2e9feb735785184bf8bc79fe979a3495da251"
check "B3 the rest of the copy is the installed code" "$(cd "$W/code" && for f in *.py; do case $f in ops_media.py|ops_work.py) ;; *) cmp -s "$f" "$REAL/$f" || echo "$f";; esac; done | wc -l)" "0"
( umask 077; printf 'KRYUK_OPERATOR_PASSWORD=%s\nKRYUK_ALLOWED_ORIGINS=https://trial.invalid\n' "$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')" > "$W/env" )
chown -R "$RUNAS:$RUNAS" "$W/code" "$W/data"; chmod 755 "$W"
systemd-run --quiet --unit="$CT" --uid="$RUNAS" --gid="$RUNAS" \
  -p WorkingDirectory="$W/code" -p EnvironmentFile="$W/env" -p UMask=0077 -p NoNewPrivileges=yes \
  -p ProtectSystem=strict -p ProtectHome=yes -p ReadWritePaths="$W/data" \
  /usr/bin/python3 "$W/code/secure_server.py" --db "$W/data/runtime.sqlite" --port "$PORT"
check "B4 systemd-run" "$?" "0"
ask() { local n=0; until curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" 2>/dev/null; do n=$((n + 1)); [ "$n" -lt 10 ] || { echo "no answer"; return; }; sleep 1; done; }
check "B5 /health with the new files" "$(ask)" '{"mode":"STAGING","ok":true,"sending_enabled":false}'
pid1="$(systemctl show -p MainPID --value "$CT.service")"
check "B6 it runs as" "$(ps -o user= -p "$pid1" | tr -d ' ')" "$RUNAS"
check "B7 it runs the copy" "$(tr '\0' ' ' < "/proc/$pid1/cmdline" | cut -d' ' -f2)" "$W/code/secure_server.py"
check "B8 its database is its own" "$(ls "$W/data" | grep -c runtime.sqlite)" "1"
check "B9 the new store answers in that Python (LOCKING)" "$(runuser -u "$RUNAS" -- /usr/bin/python3 -B -c "import sys; sys.path.insert(0, '$W/code'); import ops_media; print(ops_media.MediaStore.LOCKING)" 2>&1)" "1"
systemctl restart "$CT.service"; check "B10 restart" "$?" "0"; sleep 2
check "B11 active after the restart" "$(systemctl is-active "$CT.service")" "active"
check "B12 /health after the restart" "$(ask)" '{"mode":"STAGING","ok":true,"sending_enabled":false}'
pid2="$(systemctl show -p MainPID --value "$CT.service")"
if [ "$pid1" != "$pid2" ] && [ "$pid2" != 0 ]; then newpid=yes; else newpid=no; fi
check "B13 a new process after the restart" "$newpid" "yes"
check "B14 nothing in its journal that looks like an error" "$(journalctl -u "$CT.service" --no-pager 2>/dev/null | grep -ci 'traceback\|error')" "0"
check "B15 the real service still answers on its own port" "$(curl -fsS --max-time 5 http://127.0.0.1:8788/health 2>/dev/null)" '{"mode":"STAGING","ok":true,"sending_enabled":false}'
systemctl stop "$CT.service"
exit 0
