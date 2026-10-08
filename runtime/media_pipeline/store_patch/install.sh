#!/usr/bin/env bash
# Install the lock-aware media store on the server: two files of /opt/kryuk24, and one restart.
#   sudo bash install.sh              install
#   sudo bash install.sh rollback     put the two original files back
#   sudo bash install.sh status       say what is installed; changes nothing
# NOT TO BE RUN until Gev says so for this script. It was written on 08.10.2026 for review.
#
# What it changes: /opt/kryuk24/ops_media.py and /opt/kryuk24/ops_work.py (replaced by the files beside this
# script), and one restart of kryuk-capture, the only long-running service that loads them. The timed and one-shot
# units (kryuk-operations, kryuk-api-read, kryuk-backup) load the files when they next start; none may be running
# during the install. kryuk-bro-api does not load these files and is not restarted.
# What it never touches: any database, any media file, any credential, Nginx, the portal, a timer, a unit file.
# It stops at the first unexpected answer. Both files change together or not at all: after any failure past the
# point where a file was replaced, both originals are put back and the service is restarted with them.
#
# Order. The new ops_media.py works with the original ops_work.py; the new ops_work.py does not work with the
# original ops_media.py. So ops_media.py goes in first and comes out last, and each file is put in place by a
# rename: a unit that starts in the middle reads a pair that works, never half a file.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${KRYUK_CODE_DIR:-/opt/kryuk24}"
# A rehearsal: another folder, no services, no ownership. Refused on the real folder.
DRY="${KRYUK_INSTALL_REHEARSAL:-0}"
FILES="ops_media.py ops_work.py"
BACK="ops_work.py ops_media.py"
SERVICE=kryuk-capture.service
ONESHOTS="kryuk-operations.service kryuk-api-read.service kryuk-backup.service"
HEALTH=http://127.0.0.1:8788/health
SUFFIX=.before-store-lock

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
sha() { sha256sum < "$1" | cut -d' ' -f1; }   # from its bytes only: a name with a backslash changes what sha256sum prints
state() {   # of one installed file: original, new, or other
  local now; now="$(sha "$DEST/$1")"
  if [ "$now" = "$(old_sha "$1")" ]; then echo original; elif [ "$now" = "$(new_sha "$1")" ]; then echo new; else echo "other:$now"; fi
}
put() {     # one file into place by a rename, with the owner and mode the code folder uses
  local part="$2.store-lock-part"
  rm -f "$part"
  if [ "$DRY" = 1 ]; then install -m 644 "$1" "$part"; else install -o root -g root -m 644 "$1" "$part"; fi
  mv -f "$part" "$2"
}
health() {
  if [ "$DRY" = 1 ]; then say "health: not asked (rehearsal)"; return 0; fi
  local n=0
  until curl -fsS --max-time 5 "$HEALTH" >/dev/null 2>&1; do
    n=$((n + 1)); [ "$n" -lt 10 ] || { say "health: FAILED ($HEALTH)"; return 1; }; sleep 1
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
quiet() {   # the moment is right: no one-shot unit is running, the service is running and answers
  if [ "$DRY" != 1 ]; then
    for u in $ONESHOTS; do
      if systemctl is-active --quiet "$u"; then stop "$u is running now; wait until it has finished. Nothing was changed"; fi
    done
    say "$SERVICE before: $(systemctl is-active "$SERVICE" || true) / $(systemctl is-enabled "$SERVICE" 2>&1 || true)"
    systemctl is-active --quiet "$SERVICE" || stop "$SERVICE is not running: this script does not start what was stopped. Nothing was changed"
  fi
  health || stop "the service does not answer before anything was changed"
}
selftest() {   # the new files with this server's Python, as the service's own user, in a temporary folder
  if [ "$DRY" = 1 ]; then "${KRYUK_PYTHON:-python3}" -B "$HERE/selftest.py" "$DEST"
  else runuser -u "$RUNAS" -- /usr/bin/python3 -B "$HERE/selftest.py" "$DEST"; fi
}
originals_back() {   # both originals from their kept copies; used by a failed install and by rollback
  for f in $BACK; do
    [ -f "$DEST/$f$SUFFIX" ] || { say "no kept copy of $f"; continue; }
    [ "$(sha "$DEST/$f$SUFFIX")" = "$(old_sha "$f")" ] || { say "STOP: the kept copy of $f is not the original; it was not put back"; return 1; }
    put "$DEST/$f$SUFFIX" "$DEST/$f"
  done
}

if [ "$DRY" = 1 ] && [ "$DEST" = /opt/kryuk24 ]; then stop "a rehearsal is not run on the real code folder"; fi
[ "$DRY" = 1 ] || [ "$(id -u)" = 0 ] || stop "run with sudo"
for f in $FILES; do [ -f "$DEST/$f" ] || stop "$DEST/$f is not there"; done
say "time: $(date -u +%FT%TZ); code folder: $DEST; rehearsal: $DRY"
for f in $FILES; do say "installed $f: $(state "$f")"; done

case "${1:-install}" in
status)
  for f in $FILES; do
    if [ -e "$DEST/$f$SUFFIX" ]; then say "kept copy of $f: $(sha "$DEST/$f$SUFFIX")"; else say "kept copy of $f: none"; fi
  done
  exit 0;;

rollback)
  for f in $FILES; do
    [ -f "$DEST/$f$SUFFIX" ] || stop "no kept copy $DEST/$f$SUFFIX: nothing was changed"
    [ "$(sha "$DEST/$f$SUFFIX")" = "$(old_sha "$f")" ] || stop "the kept copy of $f is not the original: nothing was changed"
  done
  if [ "$DRY" != 1 ]; then
    for u in $ONESHOTS; do
      if systemctl is-active --quiet "$u"; then stop "$u is running now; wait until it has finished. Nothing was changed"; fi
    done
  fi
  originals_back
  for f in $FILES; do [ "$(state "$f")" = original ] || stop "$f is not the original after putting it back"; done
  restart || stop "the originals are back, but the service did not restart"
  health || stop "the originals are back, but the service does not answer"
  for f in $FILES; do rm -f "$DEST/$f$SUFFIX"; done   # the installed files are the originals again: the copies are not needed
  for f in $FILES; do say "installed $f: $(state "$f")"; done
  say "ROLLED BACK at $(date -u +%FT%TZ)"
  exit 0;;

install) ;;
*) stop "unknown argument: $1";;
esac

# ---- install
for f in $FILES; do
  [ -f "$HERE/$f" ] || stop "the new $f is not beside this script"
  [ "$(sha "$HERE/$f")" = "$(new_sha "$f")" ] || stop "the new $f beside this script is not the reviewed one"
done
[ -f "$HERE/selftest.py" ] || stop "selftest.py is not beside this script"
states=""; for f in $FILES; do states="$states $(state "$f")"; done
if [ "$states" = " new new" ]; then say "ALREADY INSTALLED"; exit 0; fi
[ "$states" = " original original" ] || stop "the installed files are not both the originals this change was made from ($states ). Nothing was changed. If one is new and one original, run: rollback"
for f in $FILES; do
  if [ -e "$DEST/$f$SUFFIX" ]; then stop "$DEST/$f$SUFFIX already exists: nothing was changed"; fi
done
if [ "$DRY" != 1 ]; then
  for t in curl runuser systemctl; do command -v "$t" >/dev/null || stop "$t is not on this server"; done
  for f in $FILES; do [ "$(stat -c '%U:%G %a' "$DEST/$f")" = "root:root 644" ] || stop "$f is not root:root 644"; done
  RUNAS="$(systemctl show -p User --value "$SERVICE")"
  if [ -z "$RUNAS" ] || [ "$RUNAS" = root ]; then stop "$SERVICE has no user of its own ($RUNAS): the self-test is not run as root"; fi
  say "the self-test will run as: $RUNAS"
fi
quiet

for f in $FILES; do cp -p "$DEST/$f" "$DEST/$f$SUFFIX"; done
for f in $FILES; do [ "$(sha "$DEST/$f$SUFFIX")" = "$(old_sha "$f")" ] || { for g in $FILES; do rm -f "$DEST/$g$SUFFIX"; done; stop "a kept copy is not the original: nothing was changed"; }; done
failed() {   # from here on: both originals back, the service restarted with them, the copies removed
  say "FAILED: $1. Putting both originals back."
  originals_back || { say "STOP: the originals could not be put back; the kept copies are in $DEST"; exit 1; }
  restart || say "STOP: the originals are back, but the service did not restart"
  health || say "STOP: the originals are back, but the service does not answer"
  for f in $FILES; do
    if [ "$(state "$f")" = original ]; then rm -f "$DEST/$f$SUFFIX"; fi
  done
  for f in $FILES; do say "installed $f: $(state "$f")"; done
  exit 1
}
for f in $FILES; do put "$HERE/$f" "$DEST/$f" || failed "$f could not be put in place"; done
for f in $FILES; do [ "$(state "$f")" = new ] || failed "$f is not the new file after putting it in place"; done
selftest || failed "the new files do not pass their self-test with this server's Python"
restart || failed "the service did not restart with the new files"
health || failed "the service does not answer with the new files"
for f in $FILES; do say "installed $f: $(state "$f") $(sha "$DEST/$f")"; done
for f in $FILES; do say "kept original: $DEST/$f$SUFFIX"; done
say "INSTALLED at $(date -u +%FT%TZ). Way back: sudo bash $0 rollback"
