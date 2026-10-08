#!/usr/bin/env bash
# Install the lock-aware media store on the server: two files of /opt/kryuk24, and one restart.
#   sudo bash install.sh              install
#   sudo bash install.sh rollback     put the two original files back
#   sudo bash install.sh status       say what is installed and what is held; changes nothing
#   sudo bash install.sh release      let the one-shot units start again, after a STOP that left them held
# NOT TO BE RUN until Gev says so for this script. It was written on 08.10.2026 for review.
#
# What it changes: /opt/kryuk24/ops_media.py and /opt/kryuk24/ops_work.py (replaced by the files beside this
# script), and one restart of kryuk-capture, the only long-running service that loads them (kryuk-bro-api does not).
# While it works it holds the one-shot units that run code of this folder (kryuk-operations, kryuk-api-read,
# kryuk-backup): a drop-in under /run/systemd/system with a condition that is false while the drop-in exists, so
# no timer and no hand can start them, and it takes the hold away when it has finished. It changes no timer and
# no unit file; a restart of the server removes /run by itself.
# What it never touches: any database, any media file, any credential, Nginx, the portal.
#
# Why the hold. A process that has loaded the original files writes into the store without the lock. If one
# started after the check and was still running beside the restarted service, the two could meet in the store.
# So for the whole time between the first check and the end, nothing that loads these files can start.
#
# Order. The new ops_media.py works with the original ops_work.py; the new ops_work.py does not work with the
# original ops_media.py. So ops_media.py goes in first and comes out last, each by a rename.
#
# Exit codes. 0: done. 1: stopped or failed, and the installed files are the originals (or were never touched).
# 2: it needs a person: the two files or the service are in a state it could not bring back by itself. The kept
# copies stay, the service was not restarted on a pair it could not confirm, the one-shot units stay held.
# The script does not rely on "set -e" where a file is put in place: every such step is checked by name.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${KRYUK_CODE_DIR:-/opt/kryuk24}"
# A rehearsal: another folder, no services, no ownership, no hold. Refused on the real folder.
DRY="${KRYUK_INSTALL_REHEARSAL:-0}"
FILES="ops_media.py ops_work.py"
BACK="ops_work.py ops_media.py"
SERVICE=kryuk-capture.service
ONESHOTS="kryuk-operations.service kryuk-api-read.service kryuk-backup.service"
# units whose processes may be running from the code folder during the install
MAY_RUN="kryuk-capture.service kryuk-bro-api.service"
HEALTH=http://127.0.0.1:8788/health
SUFFIX=.before-store-lock
HOLD_DIR="${KRYUK_HOLD_DIR:-/run/systemd/system}"
HOLD_NAME=90-kryuk-store-lock-install.conf
TIMER_MARGIN=600   # seconds: not started when a timer of a held unit fires sooner than this
HELD=0   # 1 while this run holds the one-shot units
KEEP=0   # 1 while the files and the service are in a state this run has not confirmed

old_sha() { case "$1" in
  ops_media.py) echo 5ca3e4dea8b0b11040a4a85ff0985c4c881ac80348abfaf7c8058cca2dbbda4c;;
  ops_work.py)  echo d1e6a2dfa653f40ddbf886c170e8c0d143b1750ad59c1703c647313f7e8818d6;;
esac; }
new_sha() { case "$1" in
  ops_media.py) echo 0f877f7703279ec984da924f5f34965b99ac0d9488b428facae6d9fa1c897df4;;
  ops_work.py)  echo 69aa0809da3b8dd5c894b1abe2c2e9feb735785184bf8bc79fe979a3495da251;;
esac; }
say() { printf '%s\n' "$*"; }
stop() { say "STOP: $*"; exit 1; }
sha() { sha256sum 2>/dev/null < "$1" | cut -d' ' -f1; }   # from the bytes only; empty when the file cannot be read
state() {   # of one installed file: original, new, or other
  local now; now="$(sha "$DEST/$1")"
  if [ -z "$now" ]; then echo "other:unreadable"
  elif [ "$now" = "$(old_sha "$1")" ]; then echo original
  elif [ "$now" = "$(new_sha "$1")" ]; then echo new
  else echo "other:$now"; fi
}
states() { local f; for f in $FILES; do say "installed $f: $(state "$f")"; done; }
put() {     # one file into place by a rename, with the owner and mode the code folder uses; 1 when any step fails
  local part="$2.store-lock-part"
  rm -f "$part" || return 1
  if [ "$DRY" = 1 ]; then install -m 644 "$1" "$part" || { rm -f "$part"; return 1; }
  else install -o root -g root -m 644 "$1" "$part" || { rm -f "$part"; return 1; }; fi
  mv -f "$part" "$2" || { rm -f "$part"; return 1; }
}
health() {
  if [ "$DRY" = 1 ]; then say "health: not asked (rehearsal)"; return 0; fi
  local n=0
  until curl -fsS --max-time 5 "$HEALTH" >/dev/null 2>&1; do
    n=$((n + 1)); if [ "$n" -ge 10 ]; then say "health: FAILED ($HEALTH)"; return 1; fi; sleep 1
  done
  say "health: OK $(curl -fsS --max-time 5 "$HEALTH" 2>/dev/null || true)"
}
restart() {
  if [ "$DRY" = 1 ]; then say "restart: not done (rehearsal)"; return 0; fi
  systemctl restart "$SERVICE" || { say "$SERVICE: the restart command failed"; return 1; }
  sleep 2
  say "$SERVICE: $(systemctl is-active "$SERVICE" || true)"
  systemctl is-active --quiet "$SERVICE"
}
selftest() {   # the new files with this server's Python, as the service's own user, in a temporary folder
  if [ "$DRY" = 1 ]; then "${KRYUK_PYTHON:-python3}" -B "$HERE/selftest.py" "$DEST"
  else runuser -u "$RUNAS" -- /usr/bin/python3 -B "$HERE/selftest.py" "$DEST"; fi
}

# ---- the hold on the one-shot units
hold_file() { printf '%s' "$HOLD_DIR/$1.d/$HOLD_NAME"; }
hold_loaded() { case "$(systemctl show -p DropInPaths --value "$1" 2>/dev/null)" in *"$1.d/$HOLD_NAME"*) return 0;; *) return 1;; esac; }
hold() {      # no one-shot unit can start from here on; 1 when that could not be confirmed
  if [ "$DRY" = 1 ]; then say "hold: not done (rehearsal)"; return 0; fi
  local u
  HELD=1
  for u in $ONESHOTS; do
    mkdir -p "$HOLD_DIR/$u.d" || return 1
    printf '# Put by store_patch/install.sh for the minutes of an install. While this file exists the unit does not start.\n# To let it start again: sudo bash install.sh release (or delete this file and run systemctl daemon-reload).\n[Unit]\nConditionPathExists=!%s\n' "$(hold_file "$u")" > "$(hold_file "$u")" || return 1
  done
  systemctl daemon-reload || { say "systemctl daemon-reload failed"; return 1; }
  for u in $ONESHOTS; do
    hold_loaded "$u" || { say "the hold is not loaded for $u"; return 1; }
  done
  say "held (cannot start until this script has finished): $ONESHOTS"
}
release() {   # the one-shot units can start again; 1 when that could not be confirmed
  if [ "$DRY" = 1 ]; then return 0; fi
  local u bad=0
  for u in $ONESHOTS; do
    rm -f "$(hold_file "$u")" || bad=1
    rmdir "$HOLD_DIR/$u.d" 2>/dev/null || true
    if [ -e "$(hold_file "$u")" ]; then bad=1; fi
  done
  systemctl daemon-reload || bad=1
  for u in $ONESHOTS; do
    if hold_loaded "$u"; then bad=1; fi
  done
  if [ "$bad" = 0 ]; then HELD=0; say "released (can start again): $ONESHOTS"; return 0; fi
  say "STOP: the hold could not be taken away completely. Look at $HOLD_DIR/*.d/$HOLD_NAME, then: sudo bash $0 release"
  return 1
}
finish() {    # every way out of the script passes here
  local code=$?
  trap - EXIT
  if [ "$HELD" = 1 ]; then
    if [ "$KEEP" = 1 ]; then
      say "The one-shot units STAY HELD ($ONESHOTS): they must not start while the files and the service are in this state."
      say "When the state is put right: sudo bash $0 release"
      [ "$code" -ge 2 ] || code=2
    else
      release || code=2
    fi
  fi
  exit "$code"
}
needs_a_person() {   # a state this script does not repair by guessing
  say "STOP: $1"
  states
  local f
  for f in $FILES; do
    if [ -f "$DEST/$f$SUFFIX" ]; then say "kept copy of $f: $DEST/$f$SUFFIX ($(sha "$DEST/$f$SUFFIX"))"; else say "kept copy of $f: none"; fi
  done
  say "$2"
  KEEP=1
  exit 2
}

# ---- what must be true before anything is changed
timers_not_near() {   # a held unit whose timer fires during the hold would lose that run
  local u t next at now
  now="$(date -u +%s)"
  for u in $ONESHOTS; do
    for t in $(systemctl show -p TriggeredBy --value "$u" 2>/dev/null); do
      next="$(systemctl show -p NextElapseUSecRealtime --value "$t" 2>/dev/null)"
      [ -n "$next" ] || continue
      at="$(date -u -d "$next" +%s 2>/dev/null)" || stop "the next run of $t could not be read ($next). Nothing was changed"
      if [ $((at - now)) -lt "$TIMER_MARGIN" ]; then stop "$t fires in $((at - now)) s, sooner than $TIMER_MARGIN s. Run this after it. Nothing was changed"; fi
      say "$t: next run in $((at - now)) s"
    done
  done
}
units_not_stale() {   # this script reloads systemd: it must not be the one to load somebody's unfinished edit
  local u
  for u in $ONESHOTS $MAY_RUN; do
    if [ "$(systemctl show -p NeedDaemonReload --value "$u" 2>/dev/null)" = yes ]; then stop "the unit file of $u was changed and not loaded; this script's reload would load it. Nothing was changed"; fi
  done
}
oneshots_idle() {     # a running one-shot unit is "activating", not "active": the state is read, not is-active
  local u s
  for u in $ONESHOTS; do
    s="$(systemctl show -p ActiveState --value "$u" 2>/dev/null)"
    case "$s" in
      inactive|failed) ;;
      *) say "$u is running now (state: ${s:-unknown}); wait until it has finished"; return 1;;
    esac
  done
}
nothing_else_runs() { # no process runs code of this folder except the services that are meant to
  local pid unit ok u found=0
  for pid in $(pgrep -f -- "$DEST/" 2>/dev/null); do
    unit="$(ps -o unit= -p "$pid" 2>/dev/null | tr -d ' ')"
    [ -n "$unit" ] || continue   # it ended while we looked
    ok=0; for u in $MAY_RUN; do if [ "$unit" = "$u" ]; then ok=1; fi; done
    if [ "$ok" = 0 ]; then say "process $pid runs code of $DEST outside $MAY_RUN (unit: $unit): $(ps -o args= -p "$pid" 2>/dev/null | cut -c1-80)"; found=1; fi
  done
  return "$found"
}
restore() {   # 0 only when both installed files are the originals; stops at the first step that fails
  local f s
  for f in $FILES; do
    if [ ! -f "$DEST/$f$SUFFIX" ]; then say "restore: there is no kept copy of $f"; return 1; fi
    if [ "$(sha "$DEST/$f$SUFFIX")" != "$(old_sha "$f")" ]; then say "restore: the kept copy of $f is not the original"; return 1; fi
    s="$(state "$f")"
    case "$s" in original|new) ;; *) say "restore: the installed $f is neither the original nor the new file ($s)"; return 1;; esac
  done
  for f in $BACK; do
    if [ "$(state "$f")" = original ]; then continue; fi
    if ! put "$DEST/$f$SUFFIX" "$DEST/$f"; then say "restore: $f could not be put back; the next file was not touched"; return 1; fi
    if [ "$(state "$f")" != original ]; then say "restore: $f is not the original after putting it back; the next file was not touched"; return 1; fi
  done
  for f in $FILES; do
    if [ "$(state "$f")" != original ]; then say "restore: $f is not the original"; return 1; fi
  done
  say "restore: both installed files are the originals"
}
real_checks() {       # the server's side of the preconditions; not in a rehearsal
  local t u
  for t in curl runuser systemctl pgrep ps date; do command -v "$t" >/dev/null || stop "$t is not on this server"; done
  units_not_stale
  timers_not_near
}

trap finish EXIT
trap 'exit 130' INT TERM HUP
if [ "$DRY" = 1 ] && [ "$DEST" = /opt/kryuk24 ]; then stop "a rehearsal is not run on the real code folder"; fi
if [ "$DRY" != 1 ] && [ "$(id -u)" != 0 ]; then stop "run with sudo"; fi
for f in $FILES; do [ -f "$DEST/$f" ] || stop "$DEST/$f is not there"; done
say "time: $(date -u +%FT%TZ); code folder: $DEST; rehearsal: $DRY"
states

case "${1:-install}" in
status)
  for f in $FILES; do
    if [ -e "$DEST/$f$SUFFIX" ]; then say "kept copy of $f: $(sha "$DEST/$f$SUFFIX")"; else say "kept copy of $f: none"; fi
  done
  if [ "$DRY" != 1 ]; then
    for u in $ONESHOTS; do
      if [ -e "$(hold_file "$u")" ] || hold_loaded "$u"; then h=HELD; else h="not held"; fi
      say "$u: $(systemctl show -p ActiveState --value "$u" 2>/dev/null), $h"
    done
    say "$SERVICE: $(systemctl is-active "$SERVICE" || true)"
  fi
  exit 0;;

release)
  if [ "$DRY" = 1 ]; then stop "a rehearsal holds nothing"; fi
  HELD=1
  exit 0;;   # finish() takes the hold away and says so

rollback)
  for f in $FILES; do
    [ -f "$DEST/$f$SUFFIX" ] || stop "no kept copy $DEST/$f$SUFFIX: nothing was changed"
    [ "$(sha "$DEST/$f$SUFFIX")" = "$(old_sha "$f")" ] || stop "the kept copy of $f is not the original: nothing was changed"
    case "$(state "$f")" in original|new) ;; *) stop "the installed $f is neither the original nor the new file: nothing was changed";; esac
  done
  if [ "$DRY" != 1 ]; then real_checks; fi
  hold || stop "the one-shot units could not be held. Nothing was changed"
  if [ "$DRY" != 1 ]; then
    oneshots_idle || stop "a one-shot unit is running. Nothing was changed"
    nothing_else_runs || stop "something else runs code of this folder. Nothing was changed"
    was="$(systemctl is-active "$SERVICE" || true)"
  else
    was=active
  fi
  KEEP=1
  restore || needs_a_person "the originals could not be put back" "$SERVICE was NOT restarted: it still runs what it had loaded."
  if [ "$was" = active ]; then
    restart || needs_a_person "the originals are back, but the service did not restart" "Look at: systemctl status $SERVICE"
    health || needs_a_person "the originals are back and the service restarted, but it does not answer" "Look at: journalctl -u $SERVICE"
  else
    say "$SERVICE was not running ($was): this script does not start what was stopped"
  fi
  for f in $FILES; do rm -f "$DEST/$f$SUFFIX"; done   # the installed files are the originals again and the service runs them
  KEEP=0
  states
  say "ROLLED BACK at $(date -u +%FT%TZ)"
  exit 0;;

install) ;;
*) stop "unknown argument: $1";;
esac

# ---- install: checks that need nothing held
for f in $FILES; do
  [ -f "$HERE/$f" ] || stop "the new $f is not beside this script"
  [ "$(sha "$HERE/$f")" = "$(new_sha "$f")" ] || stop "the new $f beside this script is not the reviewed one"
done
[ -f "$HERE/selftest.py" ] || stop "selftest.py is not beside this script"
both=""; for f in $FILES; do both="$both $(state "$f")"; done
if [ "$both" = " new new" ]; then say "ALREADY INSTALLED"; exit 0; fi
[ "$both" = " original original" ] || stop "the installed files are not both the originals this change was made from ($both ). Nothing was changed. If one is new and one original, run: rollback"
for f in $FILES; do
  if [ -e "$DEST/$f$SUFFIX" ]; then stop "$DEST/$f$SUFFIX already exists: nothing was changed"; fi
done
if [ "$DRY" != 1 ]; then
  for f in $FILES; do [ "$(stat -c '%U:%G %a' "$DEST/$f")" = "root:root 644" ] || stop "$f is not root:root 644"; done
  RUNAS="$(systemctl show -p User --value "$SERVICE")"
  if [ -z "$RUNAS" ] || [ "$RUNAS" = root ]; then stop "$SERVICE has no user of its own ($RUNAS): the self-test is not run as root"; fi
  say "the self-test will run as: $RUNAS"
  real_checks
fi

# ---- from here nothing that loads these files can start
hold || stop "the one-shot units could not be held. Nothing was changed"
if [ "$DRY" != 1 ]; then
  oneshots_idle || stop "a one-shot unit is running. Nothing was changed"
  nothing_else_runs || stop "something else runs code of this folder. Nothing was changed"
  say "$SERVICE before: $(systemctl is-active "$SERVICE" || true) / $(systemctl is-enabled "$SERVICE" 2>&1 || true)"
  systemctl is-active --quiet "$SERVICE" || stop "$SERVICE is not running: this script does not start what was stopped. Nothing was changed"
fi
health || stop "the service does not answer before anything was changed"

for f in $FILES; do
  cp -p "$DEST/$f" "$DEST/$f$SUFFIX" || { for g in $FILES; do rm -f "$DEST/$g$SUFFIX"; done; stop "$f could not be copied beside itself: nothing was changed"; }
done
for f in $FILES; do
  [ "$(sha "$DEST/$f$SUFFIX")" = "$(old_sha "$f")" ] || { for g in $FILES; do rm -f "$DEST/$g$SUFFIX"; done; stop "a kept copy is not the original: nothing was changed"; }
done

failed() {   # both originals back and confirmed, the service restarted with them and answering; anything less needs a person
  say "FAILED: $1. Putting both originals back."
  restore || needs_a_person "the originals could not be put back" "$SERVICE was NOT restarted: it still runs what it had loaded."
  restart || needs_a_person "the originals are back, but the service did not restart" "Look at: systemctl status $SERVICE"
  health || needs_a_person "the originals are back and the service restarted, but it does not answer" "Look at: journalctl -u $SERVICE"
  for f in $FILES; do rm -f "$DEST/$f$SUFFIX"; done
  KEEP=0
  states
  exit 1
}
KEEP=1
for f in $FILES; do
  put "$HERE/$f" "$DEST/$f" || failed "$f could not be put in place"
  [ "$(state "$f")" = new ] || failed "$f is not the new file after putting it in place"
done
selftest || failed "the new files do not pass their self-test with this server's Python"
if [ "$DRY" != 1 ]; then
  oneshots_idle || failed "a one-shot unit is running although it was held"
  nothing_else_runs || failed "something started that runs code of this folder"
fi
restart || failed "the service did not restart with the new files"
health || failed "the service does not answer with the new files"
KEEP=0
for f in $FILES; do say "installed $f: $(state "$f") $(sha "$DEST/$f")"; done
for f in $FILES; do say "kept original: $DEST/$f$SUFFIX"; done
say "INSTALLED at $(date -u +%FT%TZ). Way back: sudo bash $0 rollback"
