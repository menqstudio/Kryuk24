#!/bin/sh
# New portal code on the server: stop the portal, replace the code after its tests pass here, start it again.
#   sudo sh update_and_restart.sh /tmp/armen_pkg /tmp/armen_update_code.sh
# When the update is refused (package mismatch, a failing test) the portal is started again with the code it had.
# The unit stays not enabled; no timer; data, credentials and Nginx are not touched. Everybody is signed out
# by the restart (sessions live in memory).
set -eu
SRC=${1:?package folder required}
UPDATE=${2:?path of update_code.sh required}
UNIT=kryuk-armen.service
BASE=http://127.0.0.1:8790/operator/work/armen/
stop() { echo "STOP: $1"; exit 1; }
code() { curl -s -o /dev/null -m 20 -w '%{http_code}' "$@"; }
echo "== time"; date -u +"%FT%TZ"
[ "$(id -u)" = 0 ] || stop "run with sudo"
systemctl is-active --quiet "$UNIT" || stop "the portal is not running; nothing was changed"
echo "data before: $(find /var/lib/kryuk24-armen -type f | wc -l) files; credential file: $(stat -c '%U:%G %a' /etc/kryuk24-armen/users.json)"
systemctl stop "$UNIT"
if sh "$UPDATE" "$SRC"; then UPDATED=yes; else UPDATED=no; fi
systemctl start "$UNIT"
tries=0
until ss -ltnH | awk '{print $4}' | grep -q '^127.0.0.1:8790$'; do
  tries=$((tries + 1)); [ "$tries" -le 20 ] || stop "the portal did not open its port after the start"; sleep 0.5
done
echo "== after the start: active $(systemctl is-active "$UNIT"), enabled $(systemctl is-enabled "$UNIT" || true), code updated: $UPDATED"
echo "data after: $(find /var/lib/kryuk24-armen -type f | wc -l) files; credential file: $(stat -c '%U:%G %a' /etc/kryuk24-armen/users.json)"
echo "login form: $(code "$BASE"); state without a session: $(code "${BASE}api/state"); page script without a session: $(code "${BASE}app.js")"
for name in tokens.css fonts.css style.css theme.js logo-light.webp logo-dark.webp font-golos-cyrillic.woff2; do echo "$name: $(code "$BASE$name")"; done
echo "wrong password: $(code -X POST -H 'Content-Type: application/json' -H 'Origin: https://runtime.kryuk24.ru' -d '{"username":"armen","password":"wrong-SAMPLE-not-a-real-password"}' "${BASE}api/login")"
date -u +"%FT%TZ"
[ "$UPDATED" = yes ] || stop "the code was not updated; the portal runs with the code it had"
echo "== update and restart done"
