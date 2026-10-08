#!/bin/sh
# Read-only facts for the Armen portal install. Changes nothing and opens no secret file.
#   sudo sh preinstall_facts.sh > facts.txt
# Run it before the install and again after it; the two outputs are the evidence.
CODE=/opt/kryuk24-armen
DATA=/var/lib/kryuk24-armen
CRED=/etc/kryuk24-armen
PORT=8790
HOST=runtime.kryuk24.ru
echo "== time"; date -u +"%FT%TZ"
echo "== system"; . /etc/os-release 2>/dev/null; echo "$PRETTY_NAME"; uname -r; systemctl --version | head -1
echo "== cgroup (MemoryMax needs cgroup2fs)"; stat -fc %T /sys/fs/cgroup
echo "== memory and swap (MiB)"; free -m
echo "== disk"; df -h /opt /var/lib /etc | awk '{print $1, $2, $4, $5, $6}'
echo "== python"; python3 -c "import sys,sqlite3;print(sys.version.split()[0], sqlite3.sqlite_version)"
python3 -c "import venv,ensurepip;print('venv and ensurepip: present')" 2>&1 | tail -1
echo "== listening sockets (port $PORT must be absent before the install, loopback only after it)"
ss -ltnH 2>&1 | awk '{print $4}' | sort
echo "== user and group of the portal"
id kryuk-armen 2>&1
getent group kryuk-armen || echo "group kryuk-armen: absent"
echo "== folders of the portal (owner:group mode name)"
for path in "$CODE" "$DATA" "$DATA/photos" "$DATA/portal.sqlite" "$CRED" "$CRED/users.json"; do stat -c '%U:%G %a %n' "$path" 2>&1; done
echo "== files in the code folder (sha256)"
if [ -d "$CODE" ]; then (cd "$CODE" && sha256sum *.py *.js *.html *.css requirements.txt 2>&1); else echo "absent"; fi
echo "== counts in the data folder (no file is opened)"
if [ -d "$DATA/photos" ]; then echo "files in photos: $(find "$DATA/photos" -type f | wc -l)"; else echo "absent"; fi
echo "== unit of the portal"
stat -c '%U:%G %a %n' /etc/systemd/system/kryuk-armen.service 2>&1
echo "active: $(systemctl is-active kryuk-armen.service 2>&1); enabled: $(systemctl is-enabled kryuk-armen.service 2>&1)"
systemctl show kryuk-armen.service -p MainPID -p MemoryCurrent -p MemoryPeak -p MemoryMax -p NRestarts --no-pager 2>&1 | tr '\n' ' '; echo
echo "== the other kryuk units: active / enabled"
for unit in $(ls /etc/systemd/system 2>/dev/null | grep '^kryuk'); do
  printf '%s: %s / %s\n' "$unit" "$(systemctl is-active "$unit" 2>&1)" "$(systemctl is-enabled "$unit" 2>&1)"
done
echo "== timers"; systemctl list-timers --all --no-pager | grep -i 'kryuk\|NEXT'
echo "== nginx"; nginx -v 2>&1; echo "active: $(systemctl is-active nginx)"
echo "== nginx files that name $HOST (sha256)"
FILES=$(grep -rls "$HOST" /etc/nginx 2>/dev/null | sort)
for file in $FILES; do sha256sum "$file"; done
echo "== enabled sites"; ls -la /etc/nginx/sites-enabled 2>&1 | awk '{print $1, $9, $10, $11}'
echo "== rate limit zones and body limits anywhere in the nginx config"
grep -rn 'limit_req_zone\|limit_conn_zone\|client_max_body_size' /etc/nginx 2>/dev/null
echo "== the nginx files that name $HOST, in full (configuration, no credential)"
for file in $FILES; do echo "---- $file"; cat "$file"; done
echo "== password files the config points at: owner:group mode (not opened)"
for file in $(grep -rhs 'auth_basic_user_file' /etc/nginx | awk '{print $2}' | tr -d ';' | sort -u); do stat -c '%U:%G %a %n' "$file" 2>&1; done
echo "== nginx -t"; nginx -t 2>&1
echo "== end"
