#!/usr/bin/env bash
# Install the KRYUK24-colour operator page on the VPS. Run by Gev, after he has seen the screenshots:
#   sudo bash /tmp/dashboard_colours/install.sh            install
#   sudo bash /tmp/dashboard_colours/install.sh rollback   put the previous file back
# It changes one file (/opt/kryuk24/ops_views.py) and restarts one service (kryuk-capture). It reads no secret,
# touches no database and stops at the first unexpected answer.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/kryuk24/ops_views.py
SAVED=/opt/kryuk24/ops_views.py.before-kryuk-colours
OLD_SHA=f5f6e9d8a8d87ae3dadb7a9ccc2a990040e455a5d06394c9d0a810c0a5cf8752
NEW_SHA=989ea769e8fb507422b28382352f107278c788167c0d1d0a147ebf6fd0e1e438

say() { printf '%s\n' "$*"; }
health() { curl -fsS --max-time 5 http://127.0.0.1:8788/health >/dev/null && say "health: OK" || { say "health: FAILED"; return 1; }; }

if [ "${1:-}" = "rollback" ]; then
  [ -f "$SAVED" ] || { say "STOP: no saved copy at $SAVED"; exit 1; }
  [ "$(sha256sum "$SAVED" | cut -d' ' -f1)" = "$OLD_SHA" ] || { say "STOP: saved copy is not the original file"; exit 1; }
  install -o root -g root -m 644 "$SAVED" "$DEST"
  systemctl restart kryuk-capture; sleep 2; health
  say "ROLLED BACK: $(sha256sum "$DEST" | cut -d' ' -f1)"
  exit 0
fi

[ "$(id -u)" = 0 ] || { say "STOP: run with sudo"; exit 1; }
[ "$(sha256sum "$HERE/ops_views.py" | cut -d' ' -f1)" = "$NEW_SHA" ] || { say "STOP: the new file is not the reviewed one"; exit 1; }
CUR="$(sha256sum "$DEST" | cut -d' ' -f1)"
if [ "$CUR" = "$NEW_SHA" ]; then say "ALREADY INSTALLED"; exit 0; fi
[ "$CUR" = "$OLD_SHA" ] || { say "STOP: the installed file is not the one this change was made from ($CUR)"; exit 1; }
health
[ -e "$SAVED" ] && { say "STOP: $SAVED already exists"; exit 1; }
cp -p "$DEST" "$SAVED"
install -o root -g root -m 644 "$HERE/ops_views.py" "$DEST"
python3 -c "import sys; sys.path.insert(0, '/opt/kryuk24'); import ops_views" || { say "import failed, rolling back"; install -o root -g root -m 644 "$SAVED" "$DEST"; exit 1; }
systemctl restart kryuk-capture
sleep 2
health || { say "rolling back"; install -o root -g root -m 644 "$SAVED" "$DEST"; systemctl restart kryuk-capture; exit 1; }
say "INSTALLED: $(sha256sum "$DEST" | cut -d' ' -f1)"
say "saved original: $SAVED"
say "open https://runtime.kryuk24.ru/operator/work in the browser to look"
