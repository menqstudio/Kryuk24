#!/usr/bin/env bash
# A second trial on the server, of what trial_on_server.sh left open: the hold and the guard exactly where
# install.sh puts them, on throwaway units whose unit files are in /etc/systemd/system like the real ones and
# whose drop-ins are in /etc/systemd/system/<unit>.d/. No real unit is started, stopped or given a drop-in, and
# no backup is made (the first form of this trial ran the real kryuk-backup once; GPT's review of ef2c9e4
# advised against that, and it was never run).
#   sudo bash trial_overlay_on_server.sh
# NOT TO BE RUN without Gev's word for this script.
#
# Part C, the hold, on a throwaway one-shot unit: with the drop-in loaded it does not run; with the drop-in taken
#   away it runs.
# Part D, the guard, on a throwaway service with Restart=on-failure like kryuk-capture: without the guard a killed
#   process is restarted by systemd; with the guard (Restart=no and a condition on a marker under /run) a killed
#   process stays down, a start without the marker does nothing, a start with the marker works; with the guard
#   taken away it is restarted again.
#
# What it writes, all removed at the end, also when a step fails:
#   /etc/systemd/system/kryuk-overlaytrial-*.service, kryuk-guardtrial-*.service and their .d folders, two marker
#   files under /run, and "systemctl daemon-reload" six times.
# What it never touches: /opt/kryuk24, /var/lib/kryuk24, any real unit or timer, a credential. Before and after it
# reads the state, the drop-ins and the main process of every kryuk unit and compares them.
set -uo pipefail
NAME=90-kryuk-store-lock-install.conf
ETC=/etc/systemd/system
TAG="$$"
O="kryuk-overlaytrial-$TAG.service"
G="kryuk-guardtrial-$TAG.service"
OM="/run/kryuk-overlaytrial-$TAG.ran"
GM="/run/kryuk-guardtrial-$TAG.marker"
REAL="kryuk-capture.service kryuk-operations.service kryuk-backup.service kryuk-api-read.service kryuk-bro-api.service kryuk-armen.service kryuk-operations.timer kryuk-backup.timer"
say() { printf '%s\n' "$*"; }
bad=0
check() { if [ "$2" = "$3" ]; then say "  ok    $1: $2"; else say "  WRONG $1: $2 (expected: $3)"; bad=1; fi; }
seen() { say "  seen  $1: $2"; }
up() { if systemctl is-active --quiet "$1"; then echo yes; else echo no; fi; }
facts() { local u; for u in $REAL; do printf '%s=%s/%s/pid%s/dropins[%s] ' "$u" "$(systemctl show -p ActiveState --value "$u")" "$(systemctl show -p SubState --value "$u")" "$(systemctl show -p MainPID --value "$u")" "$(systemctl show -p DropInPaths --value "$u")"; done; }
clean() {
  local code=$?
  trap - EXIT
  systemctl stop "$O" "$G" >/dev/null 2>&1
  systemctl reset-failed "$O" "$G" >/dev/null 2>&1
  rm -f "$ETC/$O" "$ETC/$G" "$OM" "$GM"
  rm -rf "$ETC/$O.d" "$ETC/$G.d"
  systemctl daemon-reload
  say "--- after the clean-up"
  check "throwaway one-shot unit" "$(systemctl show -p LoadState --value "$O")" "not-found"
  check "throwaway service" "$(systemctl show -p LoadState --value "$G")" "not-found"
  check "files of the trial left in /etc/systemd/system and /run" "$(ls -d $ETC/kryuk-overlaytrial-* $ETC/kryuk-guardtrial-* /run/kryuk-overlaytrial-* /run/kryuk-guardtrial-* 2>/dev/null | wc -l)" "0"
  after="$(facts)"
  if [ "$after" = "$before" ]; then same=yes; else same=NO; fi
  check "every real unit and timer: state, main process and drop-ins as before" "$same" "yes"
  if [ "$same" != yes ]; then say "  before: $before"; say "  after:  $after"; fi
  say "time: $(date -u +%FT%TZ)"
  if [ "$bad" = 0 ] && [ "$code" = 0 ]; then say "TRIAL OK"; exit 0; fi
  say "TRIAL FAILED"; exit 1
}

[ "$(id -u)" = 0 ] || { say "run with sudo"; exit 1; }
say "time: $(date -u +%FT%TZ); $(systemctl --version | head -1)"
for u in kryuk-capture kryuk-operations kryuk-backup kryuk-api-read kryuk-bro-api kryuk-armen; do
  if [ "$(systemctl show -p NeedDaemonReload --value "$u.service")" = yes ]; then say "STOP: the unit file of $u was changed and not loaded; a reload here would load it. Nothing was done"; exit 1; fi
done
for u in kryuk-operations.service kryuk-backup.service kryuk-api-read.service; do
  case "$(systemctl show -p ActiveState --value "$u")" in inactive|failed) ;; *) say "STOP: $u is running; a reload is not done beside it. Nothing was done"; exit 1;; esac
done
before="$(facts)"
say "before: $before"
trap clean EXIT
trap 'exit 130' INT TERM HUP

say "--- C. the hold, on a throwaway one-shot unit of $ETC"
printf '[Unit]\nDescription=KRYUK24 throwaway unit of trial_overlay_on_server.sh (safe to delete)\n[Service]\nType=oneshot\nExecStart=/usr/bin/touch %s\n' "$OM" > "$ETC/$O"
mkdir "$ETC/$O.d"
printf '[Unit]\nConditionPathExists=!%s\n' "$ETC/$O.d/$NAME" > "$ETC/$O.d/$NAME"
systemctl daemon-reload
check "C1 unit file under /etc" "$(systemctl show -p FragmentPath --value "$O")" "$ETC/$O"
case "$(systemctl show -p DropInPaths --value "$O")" in *"$ETC/$O.d/$NAME"*) shown=yes;; *) shown=no;; esac
check "C2 the drop-in under /etc is loaded (what install.sh reads back)" "$shown" "yes"
systemctl start "$O"; check "C3 held: exit code of systemctl start" "$?" "0"
check "C4 held: ConditionResult" "$(systemctl show -p ConditionResult --value "$O")" "no"
check "C5 held: its command did not run" "$(ls "$OM" 2>/dev/null | wc -l)" "0"
seen "C6 held: state" "$(systemctl show -p ActiveState --value "$O")/$(systemctl show -p SubState --value "$O")"
rm -f "$ETC/$O.d/$NAME"; rmdir "$ETC/$O.d"; systemctl daemon-reload
check "C7 released: no drop-in loaded" "$(systemctl show -p DropInPaths --value "$O")" ""
systemctl start "$O"; check "C8 released: exit code of systemctl start" "$?" "0"
check "C9 released: its command ran" "$(ls "$OM" 2>/dev/null | wc -l)" "1"
seen "C10 released: ConditionResult / Result" "$(systemctl show -p ConditionResult --value "$O") / $(systemctl show -p Result --value "$O")"

say "--- D. the guard, on a throwaway service of $ETC with Restart=on-failure"
printf '[Unit]\nDescription=KRYUK24 throwaway service of trial_overlay_on_server.sh (safe to delete)\n[Service]\nType=simple\nExecStart=/bin/sleep 300\nRestart=on-failure\nRestartSec=1\n' > "$ETC/$G"
systemctl daemon-reload
systemctl start "$G"; sleep 1
check "D1 no guard: it runs" "$(up "$G")" "yes"
p1="$(systemctl show -p MainPID --value "$G")"; kill -9 "$p1"; sleep 4
p2="$(systemctl show -p MainPID --value "$G")"
if [ "$(up "$G")" = yes ] && [ "$p2" != "$p1" ] && [ "$p2" != 0 ]; then back=yes; else back=no; fi
check "D2 no guard: a killed process is restarted by systemd" "$back" "yes"
mkdir "$ETC/$G.d"
printf '[Unit]\nConditionPathExists=%s\n[Service]\nRestart=no\n' "$GM" > "$ETC/$G.d/$NAME"
systemctl daemon-reload
check "D3 the guard is loaded for the running service" "$(systemctl show -p Restart --value "$G")" "no"
check "D4 the guard does not stop a service that is running" "$(up "$G")/$(systemctl show -p MainPID --value "$G")" "yes/$p2"
kill -9 "$p2"; sleep 4
check "D5 guarded: a killed process is NOT restarted" "$(up "$G")" "no"
seen "D6 guarded: state after the kill" "$(systemctl show -p ActiveState --value "$G")/$(systemctl show -p Result --value "$G")"
systemctl start "$G"; sleep 1
check "D7 guarded, no marker: a start does nothing (up / ConditionResult)" "$(up "$G")/$(systemctl show -p ConditionResult --value "$G")" "no/no"
: > "$GM"; systemctl restart "$G"; code=$?; sleep 1; rm -f "$GM"
check "D8 guarded, marker made for the restart: it starts" "$code/$(up "$G")" "0/yes"
p3="$(systemctl show -p MainPID --value "$G")"; kill -9 "$p3"; sleep 4
check "D9 guarded, marker removed again: a killed process stays down" "$(up "$G")" "no"
rm -f "$ETC/$G.d/$NAME"; rmdir "$ETC/$G.d"; systemctl daemon-reload
systemctl reset-failed "$G" >/dev/null 2>&1
systemctl start "$G"; sleep 1
check "D10 guard taken away: it starts" "$(up "$G")" "yes"
p4="$(systemctl show -p MainPID --value "$G")"; kill -9 "$p4"; sleep 4
check "D11 guard taken away: a killed process is restarted again" "$(up "$G")" "yes"
systemctl stop "$G"
exit 0
