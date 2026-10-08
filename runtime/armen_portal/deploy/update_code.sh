#!/bin/sh
# Replaces the portal's installed code with a new package, after the package's tests pass on this server.
#   sudo sh update_code.sh /tmp/armen_pkg
# Only while the portal is stopped. Touches the code folder alone: no data, no credential, no unit, no Nginx.
set -eu
umask 022
SRC=${1:?package folder required}
CODE=/opt/kryuk24-armen
NAME=kryuk-armen
FILES="portal.py provision.py exclude.py app.js login.js theme.js index.html login.html style.css tokens.css fonts.css logo-light.webp logo-dark.webp font-golos-cyrillic.woff2 font-golos-latin.woff2 font-robotocond-700-cyrillic.woff2 font-robotocond-700-latin.woff2 requirements.txt"
stop() { echo "STOP: $1"; exit 1; }
echo "== time"; date -u +"%FT%TZ"
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -x "$CODE/.venv/bin/python" ] || stop "step 1 of the install has not run"
if systemctl is-active --quiet "$NAME.service"; then stop "the portal is running; stop it first"; fi
(cd "$SRC" && sha256sum -c --quiet SHA256SUMS) || stop "the package differs from the repository"
cmp -s "$SRC/requirements.txt" "$CODE/requirements.txt" || stop "requirements changed; this script does not reinstall them"
echo "package: matches its checksums"
echo "== tests of the new package on this server, as the service user"
WORK=$(mktemp -d /tmp/armen_tests.XXXXXX)
cp "$SRC"/*.py "$SRC"/*.js "$SRC"/*.html "$SRC"/*.css "$SRC"/*.webp "$SRC"/*.woff2 "$WORK"/
chown -R "$NAME":"$NAME" "$WORK"
if (cd "$WORK" && runuser -u "$NAME" -- "$CODE/.venv/bin/python" -B -m unittest test_portal > "$WORK/result.txt" 2>&1); then TESTS=0; else TESTS=$?; fi
tail -n 4 "$WORK/result.txt"
if [ "$TESTS" != 0 ]; then grep -n 'FAIL\|ERROR' "$WORK/result.txt" | head -20; fi
rm -rf "$WORK"
[ "$TESTS" = 0 ] || stop "tests failed; the installed code was not changed"
echo "== replace"
for file in $FILES; do
  if cmp -s "$SRC/$file" "$CODE/$file"; then echo "same     $file"; else install -o root -g root -m 644 "$SRC/$file" "$CODE/$file"; echo "replaced $file"; fi
done
(cd "$CODE" && sha256sum $FILES)
find "$CODE" ! -user root | grep -q . && stop "something in $CODE is not owned by root"
echo "code folder: everything owned by root; portal: $(systemctl is-active "$NAME.service" || true)"
date -u +"%FT%TZ"
echo "== update done"
