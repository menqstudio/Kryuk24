#!/bin/sh
# Armen portal install, step 1 of 3: user, folders, code, isolated Python, tests, unit file.
#   sudo sh install_1_prepare.sh /tmp/armen_pkg
# The package folder holds the files of runtime/armen_portal and SHA256SUMS made from the repository.
# Starts nothing, enables nothing, creates no password and does not touch Nginx or the existing runtime.
# Stops at the first unexpected answer.
set -eu
umask 022
SRC=${1:?package folder required}
CODE=/opt/kryuk24-armen
DATA=/var/lib/kryuk24-armen
CRED=/etc/kryuk24-armen
UNIT=/etc/systemd/system/kryuk-armen.service
NAME=kryuk-armen
FILES="portal.py provision.py app.js login.js index.html login.html style.css requirements.txt"
stop() { echo "STOP: $1"; exit 1; }

echo "== time"; date -u +"%FT%TZ"
echo "== preconditions"
[ "$(id -u)" = 0 ] || stop "run with sudo"
if id "$NAME" >/dev/null 2>&1; then stop "user $NAME already exists"; fi
if getent group "$NAME" >/dev/null; then stop "group $NAME already exists"; fi
for path in "$CODE" "$DATA" "$CRED" "$UNIT"; do
  if [ -e "$path" ]; then stop "$path already exists"; fi
done
if ss -ltnH | awk '{print $4}' | grep -q ':8790$'; then stop "port 8790 is in use"; fi
(cd "$SRC" && sha256sum -c SHA256SUMS) || stop "the package differs from the repository"
echo "preconditions: ok"

echo "== python3-venv (the system Python has no ensurepip)"
if python3 -c "import ensurepip" 2>/dev/null; then echo "already present"; else
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-venv 2>&1 | grep '^Setting up\|^E:\|newly installed' || true
  python3 -c "import ensurepip" || stop "python3-venv did not install"
fi

echo "== user"
useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --user-group "$NAME"
id "$NAME"

echo "== folders and code"
install -d -o root -g root -m 755 "$CODE"
for file in $FILES; do install -o root -g root -m 644 "$SRC/$file" "$CODE/$file"; done
install -d -o "$NAME" -g "$NAME" -m 700 "$DATA"
install -d -o root -g "$NAME" -m 750 "$CRED"
stat -c '%U:%G %a %n' "$CODE" "$CODE"/* "$DATA" "$CRED"

echo "== isolated Python"
python3 -m venv "$CODE/.venv"
"$CODE/.venv/bin/pip" install --quiet --no-cache-dir --disable-pip-version-check --only-binary :all: -r "$CODE/requirements.txt"
"$CODE/.venv/bin/pip" freeze --disable-pip-version-check
find "$CODE" ! -user root | grep -q . && stop "something in $CODE is not owned by root"
echo "code folder: everything owned by root"

echo "== the service user can load the code and cannot write it"
runuser -u "$NAME" -- "$CODE/.venv/bin/python" -B -c "import sys;sys.path.insert(0,'$CODE');import portal,PIL;print('python',sys.version.split()[0],'Pillow',PIL.__version__)"
if runuser -u "$NAME" -- sh -c "touch $CODE/x 2>/dev/null"; then rm -f "$CODE/x"; stop "the service user can write the code folder"; fi
echo "write to the code folder refused: ok"

echo "== tests on this server, as the service user (package copy, temporary folders only)"
WORK=$(mktemp -d /tmp/armen_tests.XXXXXX)
cp "$SRC"/*.py "$SRC"/*.js "$SRC"/*.html "$SRC"/*.css "$WORK"/
chown -R "$NAME":"$NAME" "$WORK"
if (cd "$WORK" && runuser -u "$NAME" -- "$CODE/.venv/bin/python" -B -m unittest test_portal > "$WORK/result.txt" 2>&1); then TESTS=0; else TESTS=$?; fi
tail -n 4 "$WORK/result.txt"
if [ "$TESTS" != 0 ]; then grep -n 'FAIL\|ERROR' "$WORK/result.txt" | head -20; fi
rm -rf "$WORK"
[ "$TESTS" = 0 ] || stop "tests failed on the server; the unit file was not installed"

echo "== unit file (not started, not enabled)"
install -o root -g root -m 644 "$SRC/kryuk-armen.service" "$UNIT"
systemctl daemon-reload
echo "active: $(systemctl is-active "$NAME.service" || true); enabled: $(systemctl is-enabled "$NAME.service" || true)"
systemd-analyze verify "$UNIT" 2>&1 | grep -i "$NAME" || echo "systemd-analyze verify: nothing reported for this unit"
echo "== step 1 done"; date -u +"%FT%TZ"
