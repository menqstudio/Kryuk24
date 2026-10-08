#!/bin/sh
# Armen portal install, step 2 of 3: one supervised start and checks on the loopback address.
#   sudo sh install_2_start.sh
# Needs step 1 and Armen's password stored by Gev (provision.sh). Does not enable the unit, creates no timer,
# does not touch Nginx. Uses no real password: only the paths without a login and with a wrong one.
set -eu
CODE=/opt/kryuk24-armen
DATA=/var/lib/kryuk24-armen
FILE=/etc/kryuk24-armen/users.json
UNIT=kryuk-armen.service
BASE=http://127.0.0.1:8790
PREFIX=/operator/work/armen/
ORIGIN=https://runtime.kryuk24.ru
stop() { echo "STOP: $1"; exit 1; }
code() { curl -s -o /dev/null -m 20 -w '%{http_code}' "$@"; }
expect() { if [ "$2" = "$3" ]; then echo "ok   $1: $2"; else echo "FAIL $1: got $2, expected $3"; FAILED=1; fi; }
FAILED=0

echo "== time"; date -u +"%FT%TZ"
echo "== preconditions"
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -f "$FILE" ] || stop "no credential file: Gev has not stored Armen's password yet"
[ "$(stat -c '%U:%G %a' "$FILE")" = "root:kryuk-armen 640" ] || stop "credential file owner or mode is not root:kryuk-armen 640"
if systemctl is-active --quiet "$UNIT"; then stop "$UNIT is already running"; fi
if ss -ltnH | awk '{print $4}' | grep -q ':8790$'; then stop "port 8790 is in use"; fi
echo "preconditions: ok"

echo "== one start (not enabled)"
systemctl start "$UNIT"
tries=0
until ss -ltnH | awk '{print $4}' | grep -q '^127.0.0.1:8790$'; do
  tries=$((tries + 1))
  if [ "$tries" -gt 20 ]; then systemctl status "$UNIT" --no-pager -n 15 || true; stop "the portal did not open its port"; fi
  sleep 0.5
done
echo "active: $(systemctl is-active "$UNIT" || true); enabled: $(systemctl is-enabled "$UNIT" || true)"
echo "sockets on 8790: $(ss -ltnH | awk '{print $4}' | grep ':8790$' | tr '\n' ' ')"
systemctl show "$UNIT" -p User -p MemoryMax -p MemoryCurrent -p NRestarts --no-pager | tr '\n' ' '; echo
echo "timers that name the portal: $(systemctl list-timers --all --no-pager | grep -c armen || true)"

echo "== loopback checks, no real password"
expect "login form without a session" "$(code "$BASE$PREFIX")" 200
expect "login form is the Russian form" "$(curl -s -m 20 "$BASE$PREFIX" | grep -c 'КРЮК24 · Вход')" 1
expect "state without a session" "$(code "$BASE${PREFIX}api/state")" 401
expect "a preview without a session" "$(code "$BASE${PREFIX}preview/00000000000000000000000000000000")" 401
expect "another path" "$(code "$BASE/operator/work")" 401
expect "answer without a session" "$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -d '{}' "$BASE${PREFIX}api/answer")" 401
expect "login with a wrong password" "$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -d '{"username":"armen","password":"wrong-SAMPLE-not-a-real-password"}' "$BASE${PREFIX}api/login")" 401
expect "login from another origin" "$(code -X POST -H 'Content-Type: application/json' -H 'Origin: https://example.invalid' -d '{"username":"armen","password":"wrong-SAMPLE-not-a-real-password"}' "$BASE${PREFIX}api/login")" 403
expect "login without an origin" "$(code -X POST -H 'Content-Type: application/json' -d '{"username":"armen","password":"wrong-SAMPLE-not-a-real-password"}' "$BASE${PREFIX}api/login")" 403
expect "a Basic header alone" "$(code -u armen:wrong-SAMPLE-not-a-real-password "$BASE${PREFIX}api/state")" 401

echo "== data folder (owner:group mode name)"
stat -c '%U:%G %a %n' "$DATA" "$DATA"/* 2>&1
echo "== the other services are as before"
for unit in kryuk-capture.service kryuk-bro-api.service nginx.service; do echo "$unit: $(systemctl is-active "$unit" || true)"; done
date -u +"%FT%TZ"
[ "$FAILED" = 0 ] || stop "a check failed; the portal is left running on the loopback address only, Nginx untouched"
echo "== step 2 done"
