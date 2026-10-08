#!/bin/sh
# Rehearsal of the whole chain on this server, in a temporary place:
#   upload over HTTP -> the portal stores it -> intake into the shared inbox -> the agent's queue and lease ->
#   an interrupted attempt taken over -> covered variants -> a draft waiting for Gev's approval -> clean-up.
#   sudo sh chain_rehearsal.sh /tmp/media_chain_pkg
# What it is NOT: not a phone, not Armen's account, not the real portal's data, not the runtime's database, not
# Nginx or HTTPS. A temporary portal instance (installed portal code, port 8791, SAMPLE password), a temporary
# runtime database and media folder, sample pictures made here. Everything it creates it removes at the end.
set -eu
PKG=${1:?package folder required}
PORTAL=/opt/kryuk24-armen
PY=$PORTAL/.venv/bin/python
NAME=kryuk-armen
UNIT=kryuk-media-chain
PORT=8791
stop() { echo "STOP: $1"; exit 1; }
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -x "$PY" ] || stop "the portal's Python is not installed"
if ss -ltnH | awk '{print $4}' | grep -q ":$PORT\$"; then stop "port $PORT is in use"; fi
(cd "$PKG" && sha256sum -c --quiet SHA256SUMS) || stop "the package differs from the repository"
W=$(mktemp -d /var/lib/kryuk24-media-chain.XXXXXX)
cleanup() {
  systemctl stop "$UNIT" 2>/dev/null || true
  case "$W" in /var/lib/kryuk24-media-chain.*) chmod -R u+w "$W" 2>/dev/null || true; rm -rf "$W";; esac
  echo "temporary portal stopped, temporary folder removed: $([ -e "$W" ] && echo no || echo yes)"
}
trap cleanup EXIT
mkdir "$W/code" "$W/out"
cp "$PKG"/*.py "$W/code/"
chown -R "$NAME":"$NAME" "$W"; chmod 700 "$W"
as() { runuser -u "$NAME" -- env PYTHONPATH="$W/code:$PORTAL" "$PY" -B "$@"; }
cli() { as "$W/code/media_cli.py" --db "$W/runtime.sqlite" --media-root "$W/media" "$@"; }
ids() { cli queue | "$PY" -c "import json,sys;print(' '.join(w['id'] for w in json.load(sys.stdin)))"; }
brief() { "$PY" -c "import json,sys;[print(' ', w['id'][:14], w['status'], 'attempts', w['attempts'], 'actor', w['actor'], 'purpose', w['purpose'], 'sha256', w['sha256'][:12], 'variants', sorted(w['variants'])) for w in json.load(sys.stdin)]"; }

echo "== time"; date -u +"%FT%TZ"
echo "== 0. the module's own tests on this server"
(cd "$W/code" && as -m unittest test_media_pipeline 2>&1 | tail -n 3)

echo "== 1. sample pictures and a temporary portal"
as "$W/code/chain_client.py" make "$W"
(cd "$W" && sha256sum sample-0.jpg sample-1.jpg)
systemd-run --quiet --unit="$UNIT" --collect -p User="$NAME" -p Group="$NAME" -p UMask=0077 -p NoNewPrivileges=true \
  -p PrivateTmp=true -p ProtectSystem=strict -p ProtectHome=true -p ReadWritePaths="$W" -p MemoryMax=768M -p WorkingDirectory="$PORTAL" \
  "$PY" "$PORTAL/portal.py" --db "$W/portal.sqlite" --photos "$W/portal-photos" --credentials "$W/users.json" --port "$PORT"
tries=0
until ss -ltnH | awk '{print $4}' | grep -q "^127.0.0.1:$PORT\$"; do
  tries=$((tries + 1)); [ "$tries" -le 20 ] || stop "the temporary portal did not open its port"; sleep 0.5
done
echo "== 2. upload over HTTP: two pictures, the first one twice"
as "$W/code/chain_client.py" upload "$W" "$PORT"
echo "files the portal holds: $(ls "$W/portal-photos" | wc -l) (two originals and two previews)"

echo "== 3. intake into the shared inbox, twice"
cli intake --portal-db "$W/portal.sqlite" --portal-photos "$W/portal-photos" | tr -d '\n '; echo
cli intake --portal-db "$W/portal.sqlite" --portal-photos "$W/portal-photos" | tr -d '\n '; echo
echo "originals in the inbox (name is the sha256 of the file):"; ls "$W/media/originals"
echo "== 4. what an agent sees in the queue"
cli queue | brief
set -- $(ids); A=$1; B=$2

echo "== 5. agent-1 claims the first, reads the original, covers the plate"
cli claim --work "$A" --worker agent-1 > /dev/null
cli fetch --work "$A" --worker agent-1 --out "$W/out/a.jpg" | tr -d '\n '; echo
echo "the copy the agent got: $(sha256sum "$W/out/a.jpg" | cut -c1-64)"
echo "another worker asks for the same original:"; cli fetch --work "$A" --worker agent-2 --out "$W/out/x.jpg" 2>&1 || true
echo "prepare without regions and without a declaration:"; cli prepare --work "$A" --worker agent-1 2>&1 || true
cli prepare --work "$A" --worker agent-1 --masks "$W/masks.json" > /dev/null
cli queue | brief

echo "== 6. an interrupted attempt on the second: agent-1 claims for 30 s, leaves a half-written file and never returns"
cli claim --work "$B" --worker agent-1 --seconds 30 > /dev/null
as -c "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.mkdir(parents=True);(p/'FULL.jpg').write_bytes(b'half written')" "$W/media/tmp/$B"
echo "agent-2 tries at once:"; cli claim --work "$B" --worker agent-2 2>&1 || true
sleep 32
cli claim --work "$B" --worker agent-2 > /dev/null
echo "after the lease ran out agent-2 holds it; temporary files left by agent-1: $(find "$W/media/tmp" -type f | wc -l)"
echo "agent-1 comes back late:"; cli prepare --work "$B" --worker agent-1 --masks "$W/masks.json" 2>&1 || true
cli prepare --work "$B" --worker agent-2 --masks "$W/masks.json" > /dev/null
cli queue | brief

echo "== 7. the variants: size, EXIF, and the plate region"
as -c "
import sys,pathlib
from PIL import Image
k={1600:1600/4000,747:747/4000}
for f in sorted(pathlib.Path(sys.argv[1]).rglob('*.jpg')):
    im=Image.open(f);s=k[max(im.size)];l,t,r,b=[round(v*s) for v in (1800,2200,2600,2400)]
    lo,hi=im.crop((l+3,t+3,r-3,b-3)).convert('L').getextrema()
    print(' ',f.parent.name[:17],im.format,im.size,'EXIF tags:',len(im.getexif()),'contrast left inside the plate region:',hi-lo,'of 255')
" "$W/media/prepared"

echo "== 8. the draft for Gev: a named platform, waiting for his approval"
as "$W/code/chain_client.py" plan "$W/runtime.sqlite" "$W/media"
DAY=$(TZ=Asia/Yerevan date +%F)
cli submit --works "$A,$B" --day "$DAY" --worker agent-2 --platform YANDEX_BUSINESS --account KRYUK24 --body "SAMPLE: two pictures for the card" --reason "SAMPLE rehearsal" | tr -d '\n '; echo
echo "sync (nothing decided yet):"; cli sync | tr -d '\n '; echo
cli queue | brief

echo "== 9. clean-up while the work is unfinished, then storage"
cli cleanup --portal-photos "$W/portal-photos" | tr -d '\n '; echo
cli storage --portal-photos "$W/portal-photos" | tr -d '\n '; echo
echo "originals still in the inbox, checked against the uploaded files:"
for f in "$W"/media/originals/*.jpg; do n=$(basename "$f" .jpg); [ "$(sha256sum "$f" | cut -c1-64)" = "$n" ] && echo "  $n intact"; done
echo "files the portal still holds: $(ls "$W/portal-photos" | wc -l)"
date -u +"%FT%TZ"
echo "== rehearsal done"
