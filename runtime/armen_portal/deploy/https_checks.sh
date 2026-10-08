#!/bin/sh
# Checks of the portal from outside, over real HTTPS and the real Nginx. No real password is used anywhere:
# only the paths without a session and with a wrong SAMPLE password.
#   sh https_checks.sh [SERVER_ADDRESS_FOR_THE_PORT_CHECK]
# Run it from a computer outside the server. It changes nothing; the wrong logins count against the
# login limit of the address it runs from for about a minute.
H=https://runtime.kryuk24.ru
P=$H/operator/work/armen/
ORIGIN=https://runtime.kryuk24.ru
WRONG='{"username":"armen","password":"wrong-SAMPLE-not-a-real-password"}'
FAILED=0
code() { curl -s -o /dev/null -m 30 -w '%{http_code}' "$@"; }
expect() { if [ "$2" = "$3" ]; then echo "ok   $1: $2"; else echo "FAIL $1: got $2, expected $3"; FAILED=1; fi; }
echo "== time"; date -u +"%FT%TZ"
echo "== the login form is open, the rest of the portal needs a session"
expect "login form" "$(code "$P")" 200
expect "login form is the Russian form" "$(curl -s -m 30 "$P" | grep -c 'КРЮК24 · Вход')" 1
expect "address without the last slash" "$(code "$H/operator/work/armen")" 301
expect "login script" "$(code "${P}login.js")" 200
expect "style sheet" "$(code "${P}style.css")" 200
expect "state without a session" "$(code "${P}api/state")" 401
expect "a photo preview without a session" "$(code "${P}preview/00000000000000000000000000000000")" 401
expect "the page script without a session" "$(code "${P}app.js")" 401
expect "an answer without a session" "$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -d '{}' "${P}api/answer")" 401
expect "a photo upload without a session" "$(code -X POST -H 'Content-Type: image/jpeg' -H "Origin: $ORIGIN" --data-binary 'not a picture' "${P}api/photo")" 401
expect "sign-out without a session" "$(code -X POST -H "Origin: $ORIGIN" "${P}api/logout")" 401
echo "== no Basic prompt on the portal, the security headers arrive"
curl -s -m 30 -D - -o /dev/null "$P" | grep -i '^HTTP\|^www-authenticate\|^cache-control\|^content-security-policy\|^x-frame-options\|^x-content-type-options\|^referrer-policy\|^x-robots-tag' | tr -d '\r'
echo "== wrong password, wrong origin"
expect "login with a wrong password" "$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -d "$WRONG" "${P}api/login")" 401
expect "login from another origin" "$(code -X POST -H 'Content-Type: application/json' -H 'Origin: https://example.invalid' -d "$WRONG" "${P}api/login")" 403
expect "a Basic header instead of a session" "$(code -u armen:wrong-SAMPLE-not-a-real-password "${P}api/state")" 401
echo "== body limits: 6 MiB reaches the portal on the photo address, 40 KiB is refused on the login address"
head -c 6291456 /dev/zero > /tmp/armen_check_body.bin
expect "6 MiB to the photo address, no session" "$(code -X POST -H 'Content-Type: image/jpeg' -H "Origin: $ORIGIN" --data-binary @/tmp/armen_check_body.bin "${P}api/photo")" 401
head -c 40960 /dev/zero > /tmp/armen_check_body.bin
expect "40 KiB to the login address" "$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" --data-binary @/tmp/armen_check_body.bin "${P}api/login")" 413
rm -f /tmp/armen_check_body.bin
echo "== the other STAGING addresses still ask for the STAGING password (3 s apart: the operator limit is 20 a minute)"
for path in /operator/work /operator/work/approve /operator/work/armenx /operator/site/ /health /bro/v1/queue /operator/work/armen/../; do
  expect "$path" "$(code --path-as-is "$H$path")" 401
  sleep 3
done
# The catch-all answers 404 by itself before any password is asked (`location / { return 404; }`, a line this
# install did not touch): nothing is served there.
expect "/ (the catch-all, nothing served)" "$(code "$H/")" 404
expect "/anything-else" "$(code "$H/anything-else")" 404
echo "== request budget of the portal's pages: 28 requests as fast as they go (a page with many previews)"
ok=0; limited=0; other=0
for n in $(seq 1 28); do
  c=$(code "${P}preview/0000000000000000000000000000000$((n % 10))")
  case "$c" in 401) ok=$((ok + 1));; 429) limited=$((limited + 1));; *) other=$((other + 1));; esac
done
echo "passed to the portal: $ok, refused with 429: $limited, other: $other"
expect "none of the 28 refused by the limit" "$limited" 0
sleep 8
echo "== the login address keeps the strict limit: 16 wrong logins as fast as they go"
ok=0; limited=0; other=0
for n in $(seq 1 16); do
  c=$(code -X POST -H 'Content-Type: application/json' -H "Origin: $ORIGIN" -d "$WRONG" "${P}api/login")
  case "$c" in 401) ok=$((ok + 1));; 429) limited=$((limited + 1));; *) other=$((other + 1));; esac
done
echo "answered 401 by the portal: $ok, refused with 429: $limited, other: $other"
if [ "$limited" -gt 0 ]; then echo "ok   the login limit holds"; else echo "FAIL the login limit did not refuse anything"; FAILED=1; fi
if [ -n "${1:-}" ]; then
  echo "== the portal's own port from outside"
  expect "port 8790 (000 means no connection)" "$(curl -s -o /dev/null -m 8 -w '%{http_code}' "http://$1:8790/operator/work/armen/")" 000
  expect "plain http is sent to https" "$(code "http://runtime.kryuk24.ru/operator/work/armen/")" 301
fi
date -u +"%FT%TZ"
if [ "$FAILED" = 0 ]; then echo "== all checks passed"; else echo "== SOME CHECKS FAILED"; exit 1; fi
