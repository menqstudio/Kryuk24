#!/usr/bin/env bash
# A trial on the server of the one thing trial_on_server.sh left open: that the hold's drop-in, put where
# install.sh puts it (/etc/systemd/system/<unit>.d/), stops a REAL one-shot unit of this server, and that the unit
# runs again after the drop-in is taken away. It also tries the service's guard on a throwaway unit.
#   sudo bash trial_overlay_on_server.sh
# NOT TO BE RUN without Gev's word for this script: it touches a real unit and runs the real daily backup once.
#
# Part C, on the real kryuk-backup.service (chosen because its job only adds: one private snapshot of the
# database into /var/lib/kryuk24/backups, nothing overwritten, nothing deleted):
#   the hold's drop-in is written for it, systemd reloaded, the unit started: it must NOT run (condition false,
#   no new snapshot). The drop-in is taken away, systemd reloaded, the unit started: it must run (one new
#   snapshot). So the real effect of this trial is one extra snapshot file, and four "systemctl daemon-reload".
# Part D, the guard, on a throwaway unit with its unit file under /etc/systemd/system: with the guard's drop-in
#   it starts while the marker under /run exists and does not start when the marker is gone.
#
# What it never touches: /opt/kryuk24, the database itself, kryuk-capture, any timer, any other unit, a credential.
# Everything it writes is removed at the end, also when a step fails, except the one snapshot.
set -uo pipefail
U=kryuk-backup.service
T=kryuk-backup.timer
NAME=90-kryuk-store-lock-install.conf
DROP="/etc/systemd/system/$U.d"
BACKUPS=/var/lib/kryuk24/backups
TAG="$$"
G="kryuk-guardtrial-$TAG.service"
GM="/run/kryuk-guardtrial-$TAG.marker"
say() { printf '%s\n' "$*"; }
bad=0
check() { if [ "$2" = "$3" ]; then say "  ok    $1: $2"; else say "  WRONG $1: $2 (expected: $3)"; bad=1; fi; }
snapshots() { ls "$BACKUPS" 2>/dev/null | wc -l; }
ran() { systemctl show -p ExecMainStartTimestamp --value "$U"; }
facts() { say "$(systemctl is-active $T)/$(systemctl is-enabled $T) capture=$(systemctl show -p MainPID --value kryuk-capture.service) dropins=[$(systemctl show -p DropInPaths --value $U)]"; }
clean() {
  local code=$?
  trap - EXIT
  rm -f "$DROP/$NAME"; rmdir "$DROP" 2>/dev/null
  systemctl stop "$G" >/dev/null 2>&1; systemctl reset-failed "$G" >/dev/null 2>&1
  rm -f "/etc/systemd/system/$G" "$GM"; rm -rf "/etc/systemd/system/$G.d"
  systemctl daemon-reload
  say "--- after the clean-up"
  check "drop-in of $U on the disk" "$(ls "$DROP/$NAME" 2>/dev/null | wc -l)" "0"
  check "drop-ins of $U loaded" "$(systemctl show -p DropInPaths --value "$U")" ""
  check "throwaway unit" "$(systemctl show -p LoadState --value "$G")" "not-found"
  check "files of the trial left in /etc/systemd/system and /run" "$(ls -d /etc/systemd/system/kryuk-guardtrial-* /run/kryuk-guardtrial-* 2>/dev/null | wc -l)" "0"
  check "timer, capture process, drop-ins as before" "$(facts)" "$before"
  say "snapshots in $BACKUPS: $start at the start, $(snapshots) now"
  say "time: $(date -u +%FT%TZ)"
  if [ "$bad" = 0 ] && [ "$code" = 0 ]; then say "TRIAL OK"; exit 0; fi
  say "TRIAL FAILED"; exit 1
}

[ "$(id -u)" = 0 ] || { say "run with sudo"; exit 1; }
say "time: $(date -u +%FT%TZ); $(systemctl --version | head -1)"
for u in kryuk-capture kryuk-operations kryuk-backup kryuk-api-read kryuk-bro-api kryuk-armen; do
  if [ "$(systemctl show -p NeedDaemonReload --value "$u.service")" = yes ]; then say "STOP: the unit file of $u was changed and not loaded; a reload here would load it. Nothing was done"; exit 1; fi
done
[ "$(systemctl show -p FragmentPath --value "$U")" = "/etc/systemd/system/$U" ] || { say "STOP: the unit file of $U is not in /etc/systemd/system. Nothing was done"; exit 1; }
case "$(systemctl show -p ActiveState --value "$U")" in inactive|failed) ;; *) say "STOP: $U is running. Nothing was done"; exit 1;; esac
[ -z "$(systemctl show -p DropInPaths --value "$U")" ] && [ ! -e "$DROP" ] || { say "STOP: $U already has a drop-in. Nothing was done"; exit 1; }
next="$(systemctl show -p NextElapseUSecRealtime --value "$T")"
left=$(( $(date -u -d "$next" +%s) - $(date -u +%s) ))
[ "$left" -ge 600 ] || { say "STOP: $T fires in $left s. Nothing was done"; exit 1; }
before="$(facts)"; start="$(snapshots)"; ran0="$(ran)"
say "before: $before; next run of the timer in $left s; snapshots: $start; last run of the unit: $ran0"
trap clean EXIT
trap 'exit 130' INT TERM HUP

say "--- C. the hold on the real $U"
mkdir "$DROP"
printf '# Put by store_patch/trial_overlay_on_server.sh for a minute.\n[Unit]\nConditionPathExists=!%s\n' "$DROP/$NAME" > "$DROP/$NAME"
systemctl daemon-reload
case "$(systemctl show -p DropInPaths --value "$U")" in *"$U.d/$NAME"*) shown=yes;; *) shown=no;; esac
check "C1 the drop-in under /etc is loaded for the real unit (what install.sh reads back)" "$shown" "yes"
systemctl start "$U"; check "C2 held: exit code of systemctl start" "$?" "0"
check "C3 held: ConditionResult" "$(systemctl show -p ConditionResult --value "$U")" "no"
check "C4 held: the unit did not run (time of its last run)" "$(ran)" "$ran0"
check "C5 held: no new snapshot" "$(snapshots)" "$start"
rm -f "$DROP/$NAME"; rmdir "$DROP"; systemctl daemon-reload
check "C6 released: no drop-in loaded" "$(systemctl show -p DropInPaths --value "$U")" ""
systemctl start "$U"; check "C7 released: the real backup ran, exit code of systemctl start" "$?" "0"
check "C8 released: ConditionResult" "$(systemctl show -p ConditionResult --value "$U")" "yes"
check "C9 released: result of the run" "$(systemctl show -p Result --value "$U")" "success"
check "C10 released: one new snapshot" "$(snapshots)" "$((start + 1))"
if [ "$(ran)" != "$ran0" ]; then moved=yes; else moved=no; fi
check "C11 released: the time of its last run moved" "$moved" "yes"

say "--- D. the guard of the service, on a throwaway unit of /etc/systemd/system"
printf '[Unit]\nDescription=KRYUK24 throwaway unit of trial_overlay_on_server.sh (safe to delete)\n[Service]\nType=simple\nExecStart=/bin/sleep 120\n' > "/etc/systemd/system/$G"
mkdir "/etc/systemd/system/$G.d"
printf '[Unit]\nConditionPathExists=%s\n' "$GM" > "/etc/systemd/system/$G.d/$NAME"
systemctl daemon-reload
: > "$GM"
systemctl start "$G"; sleep 1
check "D1 guarded, marker there: it starts" "$(systemctl is-active "$G")" "active"
systemctl restart "$G"; sleep 1
check "D2 guarded, marker there: it restarts" "$(systemctl is-active "$G")" "active"
rm -f "$GM"
systemctl restart "$G"; sleep 1
say "  seen  D3 state after that restart: $(systemctl is-active "$G")"
if systemctl is-active --quiet "$G"; then down=no; else down=yes; fi
check "D3 guarded, marker gone (as after a STOP or a restart of the server): a restart leaves it down" "$down" "yes"
systemctl start "$G"; sleep 1
if systemctl is-active --quiet "$G"; then down=no; else down=yes; fi
check "D4 guarded, marker gone: it does not start (down / ConditionResult)" "$down/$(systemctl show -p ConditionResult --value "$G")" "yes/no"
rm -f "/etc/systemd/system/$G.d/$NAME"; rmdir "/etc/systemd/system/$G.d"; systemctl daemon-reload
systemctl start "$G"; sleep 1
check "D5 guard taken away: it starts again" "$(systemctl is-active "$G")" "active"
systemctl stop "$G"
exit 0
