#!/bin/sh
# Armen portal install, step 3 of 3: the portal's subtree in the installed Nginx file, then a reload.
#   sudo sh install_3_nginx.sh /tmp/armen_nginx EXPECTED_SHA256_OF_THE_INSTALLED_FILE
# The folder holds nginx_insert.py and nginx-location.conf.example. Approved by Gev on 08.10.2026 for
# /operator/work/armen/ only. A private copy of the file is kept first; `nginx -t` comes before the reload;
# when the test fails the old file is put back and nothing is reloaded. No other address is changed.
set -eu
SRC=${1:?folder required}
EXPECT=${2:?sha256 of the installed file as it was read}
FILE=/etc/nginx/conf.d/kryuk24.conf
stop() { echo "STOP: $1"; exit 1; }
echo "== time"; date -u +"%FT%TZ"
[ "$(id -u)" = 0 ] || stop "run with sudo"
systemctl is-active --quiet kryuk-armen.service || stop "the portal is not running; step 2 first"
ss -ltnH | awk '{print $4}' | grep -q '^127.0.0.1:8790$' || stop "the portal does not listen on 127.0.0.1:8790"
echo "== insert, test"
python3 "$SRC/nginx_insert.py" insert "$SRC/nginx-location.conf.example" --expect "$EXPECT" || stop "the Nginx file was not changed, or was put back; no reload"
echo "== reload (the test passed)"
systemctl reload nginx
sleep 3
echo "nginx: $(systemctl is-active nginx)"
echo "== what the installed file says about access now (every auth, limit and location line)"
grep -n 'auth_basic\|limit_req \|location \|client_max_body_size' "$FILE"
echo "== private copies"; ls -l /root/kryuk24-config-backups | awk 'NR>1 {print $1, $3, $5, $9}'
echo "== the other services"; for unit in kryuk-capture.service kryuk-bro-api.service kryuk-armen.service; do echo "$unit: $(systemctl is-active "$unit" || true)"; done
date -u +"%FT%TZ"
echo "== step 3 done"
