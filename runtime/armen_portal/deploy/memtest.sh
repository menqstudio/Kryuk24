#!/bin/sh
# Memory of the portal on this server under two uploads of the largest allowed size at once, over HTTP.
#   sudo sh memtest.sh /tmp/armen_memtest_client.py
# A separate temporary instance: the installed code and Python, the limits of the unit file, port 8791,
# its own temporary folder and a SAMPLE password. It does not touch the real portal's data, credentials or unit.
set -eu
CLIENT=${1:?path of memtest_client.py required}
CODE=/opt/kryuk24-armen
PY=$CODE/.venv/bin/python
NAME=kryuk-armen
UNIT=kryuk-armen-memtest
PORT=8791
stop() { echo "STOP: $1"; exit 1; }
[ "$(id -u)" = 0 ] || stop "run with sudo"
if ss -ltnH | awk '{print $4}' | grep -q ":$PORT\$"; then stop "port $PORT is in use"; fi
if systemctl is-active --quiet "$UNIT"; then stop "$UNIT is already running"; fi
WORK=$(mktemp -d /var/lib/kryuk24-armen-memtest.XXXXXX)
cleanup() {
  systemctl stop "$UNIT" 2>/dev/null || true
  case "$WORK" in /var/lib/kryuk24-armen-memtest.*) rm -rf "$WORK";; esac
  echo "temporary unit stopped, temporary folder removed: $([ -e "$WORK" ] && echo no || echo yes)"
}
trap cleanup EXIT
chown "$NAME":"$NAME" "$WORK"; chmod 700 "$WORK"
install -o "$NAME" -g "$NAME" -m 600 "$CLIENT" "$WORK/client.py"
echo "== time"; date -u +"%FT%TZ"
echo "== memory of the machine before (MiB)"; free -m | sed -n 2p
echo "== test files (made outside the measured unit)"
runuser -u "$NAME" -- "$PY" -B "$WORK/client.py" make "$WORK"
echo "== temporary unit with the limits of kryuk-armen.service"
systemd-run --quiet --unit="$UNIT" --collect -p User="$NAME" -p Group="$NAME" -p UMask=0077 -p NoNewPrivileges=true \
  -p PrivateTmp=true -p ProtectSystem=strict -p ProtectHome=true -p ReadWritePaths="$WORK" -p MemoryMax=768M \
  -p MemorySwapMax=0 -p TasksMax=64 -p WorkingDirectory="$CODE" \
  "$PY" "$CODE/portal.py" --db "$WORK/portal.sqlite" --photos "$WORK/photos" --credentials "$WORK/users.json" --port "$PORT"
tries=0
until ss -ltnH | awk '{print $4}' | grep -q "^127.0.0.1:$PORT\$"; do
  tries=$((tries + 1)); [ "$tries" -le 20 ] || stop "the temporary instance did not open its port"
  sleep 0.5
done
echo "listening on 127.0.0.1:$PORT only: $(ss -ltnH | awk '{print $4}' | grep -c ":$PORT\$") socket"
systemctl show "$UNIT" -p MemoryMax -p MemoryCurrent -p MemoryPeak --no-pager | tr '\n' ' '; echo "(idle)"
echo "== two uploads at once"
if runuser -u "$NAME" -- "$PY" -B "$WORK/client.py" run "$WORK" "$PORT"; then RESULT=0; else RESULT=$?; fi
echo "== after the uploads"
systemctl show "$UNIT" -p MemoryCurrent -p MemoryPeak -p NRestarts --no-pager | tr '\n' ' '; echo
echo "peak in MiB: $(( $(systemctl show "$UNIT" -p MemoryPeak --value) / 1048576 ))"
echo "still active: $(systemctl is-active "$UNIT" || true)"
echo "kernel memory events of the unit: $(cat /sys/fs/cgroup/system.slice/$UNIT.service/memory.events 2>/dev/null | tr '\n' ' ')"
echo "stored files:"; ls -l "$WORK/photos" | awk 'NR>1 {print $1, $5}'
echo "== memory of the machine after (MiB)"; free -m | sed -n 2p
date -u +"%FT%TZ"
[ "$RESULT" = 0 ] || stop "the client reported a failure"
echo "== measurement done"
