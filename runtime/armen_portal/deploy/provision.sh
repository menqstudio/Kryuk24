#!/bin/sh
# Armen's password, typed by Gev in his own terminal. Nobody else sees it and it is in no command line or log.
#   ssh -t ... 'sudo sh /tmp/armen_provision.sh'      (started by provision_from_windows.ps1)
# The password is asked twice by provision.py (hidden input, 16 characters or more) and only its salted hash
# is stored. This script prints owner, mode and a yes/no; it never prints the file.
set -eu
CODE=/opt/kryuk24-armen
FILE=/etc/kryuk24-armen/users.json
ACCOUNT=${1:-armen}
stop() { echo "STOP: $1"; exit 1; }
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -x "$CODE/.venv/bin/python" ] || stop "step 1 of the install has not run"
case "$ACCOUNT" in armen|gev) ;; *) stop "account must be armen or gev";; esac
echo "Password for the account: $ACCOUNT. Nothing you type is shown."
(cd "$CODE" && "$CODE/.venv/bin/python" -B provision.py --credentials "$FILE" --user "$ACCOUNT") || stop "no password was stored"
chown root:kryuk-armen "$FILE"
chmod 640 "$FILE"
stat -c '%U:%G %a %n' "$FILE"
"$CODE/.venv/bin/python" -B -c "import json;print('account $ACCOUNT stored:', '$ACCOUNT' in json.load(open('$FILE')))"
if systemctl is-active --quiet kryuk-armen.service; then echo "The portal is running: the new password works after its restart."; fi
date -u +"%FT%TZ"
