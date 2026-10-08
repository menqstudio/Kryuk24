#!/bin/sh
# Rehearsal on this server, in a temporary place, of what INSTALL_PLAN.md proposes:
#   the narrow access (the runtime user reads the outbox and nothing else of the portal), the test account,
#   an intake cut off in the middle, a repeated run, the backup, the rollback and a restore.
#   sudo sh chain_rehearsal.sh /tmp/media_chain_pkg
# What it is NOT: not a phone, not Armen's account, not the real portal's data, not the runtime's database, not
# Nginx or HTTPS. The real runtime data folder is made invisible to every process started here.
# It uses the real users kryuk-armen and kryuk-run on temporary folders, and one temporary group that it removes.
# Everything it creates it removes at the end.
set -eu
PKG=${1:?package folder required}
PORTAL=/opt/kryuk24-armen
PY=$PORTAL/.venv/bin/python
UNIT=kryuk-media-chain
PORT=8791
G=kryuk-rehearsal-in
stop() { echo "STOP: $1"; exit 1; }
[ "$(id -u)" = 0 ] || stop "run with sudo"
[ -x "$PY" ] || stop "the portal's Python is not installed"
if ss -ltnH | awk '{print $4}' | grep -q ":$PORT\$"; then stop "port $PORT is in use"; fi
if getent group "$G" >/dev/null; then stop "group $G already exists"; fi
(cd "$PKG" && sha256sum -c --quiet SHA256SUMS) || stop "the package differs from the repository"
W=$(mktemp -d /var/lib/kryuk24-media-chain.XXXXXX)
cleanup() {
  systemctl stop "$UNIT" 2>/dev/null || true
  case "$W" in /var/lib/kryuk24-media-chain.*) chmod -R u+w "$W" 2>/dev/null || true; rm -rf "$W";; esac
  groupdel "$G" 2>/dev/null || true
  echo "temporary portal stopped; temporary folder removed: $([ -e "$W" ] && echo no || echo yes); temporary group removed: $(getent group "$G" >/dev/null && echo no || echo yes)"
}
trap cleanup EXIT
groupadd --system "$G"
chmod 755 "$W"
install -d -o root -g root -m 755 "$W/code"
cp "$PKG"/*.py "$PKG"/portal_files/* "$W/code/"; chmod 644 "$W/code"/*
# The outbox is a folder INSIDE the portal's data folder, so that a photo and its outbox name are one file on the disk
# (a hard link needs one file system, and the service sees each writable path as its own). The data folder lets the
# outbox group pass through (710) without listing it; the database (600) and the photo folder (700) stay closed.
install -d -o kryuk-armen -g "$G" -m 710 "$W/portal"
install -d -o kryuk-armen -g "$G" -m 2750 "$W/portal/outbox"
OUT="$W/portal/outbox"
install -d -o kryuk-run -g kryuk-run -m 700 "$W/runtime"
install -d -o kryuk-armen -g kryuk-armen -m 700 "$W/make"
# The portal side: kryuk-armen with the outbox group. The runtime side: kryuk-run with the outbox group, the live
# runtime data hidden, writing only in its temporary folder.
armen() { runuser -u kryuk-armen -- env PYTHONPATH="$W/code:$PORTAL" "$PY" -B "$@"; }
run() { systemd-run --quiet --wait --pipe --collect -p User=kryuk-run -p Group=kryuk-run -p SupplementaryGroups="$G" -p UMask=0077 \
  -p ProtectSystem=strict -p ProtectHome=true -p InaccessiblePaths=/var/lib/kryuk24 -p ReadWritePaths="$W/runtime" -p WorkingDirectory="$W/runtime" \
  env PYTHONPATH="$W/code:$PORTAL" "$@"; }
cli() { run "$PY" -B "$W/code/media_cli.py" --db "$W/runtime/runtime.sqlite" --media-root "$W/runtime/media" "$@"; }
back() { run "$PY" -B "$W/code/media_rollback.py" "$@"; }
flat() { tr -d '\n ' ; echo; }
brief() { "$PY" -c "import json,sys;[print(' ', w['id'][:14], w['status'], 'attempts', w['attempts'], 'actor', w['actor'], 'sha256', w['sha256'][:12], 'variants', sorted(w['variants'])) for w in json.load(sys.stdin)]"; }
pick() { "$PY" -c "import json,sys;d=json.load(sys.stdin);print(json.dumps({k:d[k] for k in sys.argv[1:] if k in d}))" "$@"; }

echo "== time"; date -u +"%FT%TZ"
echo "== 0. the tests of both packages on this server"
T=$(mktemp -d /tmp/media_tests.XXXXXX); cp "$PKG"/*.py "$PKG"/portal_files/* "$T/"; chown -R kryuk-armen:kryuk-armen "$T"
(cd "$T" && runuser -u kryuk-armen -- "$PY" -B -m unittest test_portal 2>&1 | tail -n 3 | tr '\n' ' '; echo)
(cd "$T" && runuser -u kryuk-armen -- "$PY" -B -m unittest test_media_pipeline 2>&1 | tail -n 3 | tr '\n' ' '; echo)
rm -rf "$T"

echo "== 1. a temporary portal with an outbox, sample pictures, the accounts armen and test"
armen "$W/code/chain_client.py" make "$W/make"
systemd-run --quiet --unit="$UNIT" --collect -p User=kryuk-armen -p Group=kryuk-armen -p SupplementaryGroups="$G" -p UMask=0077 -p NoNewPrivileges=true \
  -p PrivateTmp=true -p ProtectSystem=strict -p ProtectHome=true -p ReadWritePaths="$W/portal" -p MemoryMax=768M -p WorkingDirectory="$W/code" \
  "$PY" "$W/code/portal.py" --db "$W/portal/portal.sqlite" --photos "$W/portal/photos" --credentials "$W/make/users.json" --port "$PORT" --outbox "$OUT"
tries=0
until ss -ltnH | awk '{print $4}' | grep -q "^127.0.0.1:$PORT\$"; do
  tries=$((tries + 1)); [ "$tries" -le 20 ] || stop "the temporary portal did not open its port"; sleep 0.5
done
echo "== 2. uploads over HTTP: armen (two pictures, the first twice, one answer) and the test account (one picture, one answer)"
armen "$W/code/chain_client.py" upload "$W/make" "$PORT"
echo "the portal's own folder: $(ls "$W/portal/photos" | wc -l) files (three originals and three previews: armen's two and the test account's one)"
echo "== 3. the outbox: all that leaves the portal (owner:group mode size name)"
stat -c '%U:%G %a %s %n' "$W/portal" "$W/portal/portal.sqlite" "$W/portal/photos" "$OUT" "$OUT"/* | sed "s#$W/##"
echo "one file on the disk under two names (same inode in the portal's folder and in the outbox):"
for f in "$OUT"/*.jpg; do n=$(basename "$f"); echo "  $n: portal inode $(stat -c %i "$W/portal/photos/$n"), outbox inode $(stat -c %i "$f"), links $(stat -c %h "$f")"; done
echo "the facts of one photo:"; cat "$(ls "$OUT"/*.json | head -1)"; echo

echo "== 4. what the runtime user can and cannot reach"
FIRST=$(ls "$OUT"/*.jpg | head -1)
echo "reads an outbox photo: $(run sh -c "sha256sum '$FIRST' >/dev/null 2>&1 && echo yes || echo NO")"
echo "reads the portal's database: $(run sh -c "cat '$W/portal/portal.sqlite' >/dev/null 2>&1 && echo YES || echo no, refused")"
echo "lists the portal's photo folder: $(run sh -c "ls '$W/portal/photos' >/dev/null 2>&1 && echo YES || echo no, refused")"
echo "reads a preview or the test account's photo by its path: $(run sh -c "cat '$W/portal/photos/'* >/dev/null 2>&1 && echo YES || echo no, refused")"
echo "lists the portal's data folder: $(run sh -c "ls '$W/portal' >/dev/null 2>&1 && echo YES || echo no, refused")"
echo "writes into the outbox: $(run sh -c "touch '$OUT/x' 2>/dev/null && echo YES || echo no, refused")"
echo "removes an outbox file: $(run sh -c "rm -f '$FIRST' 2>/dev/null; test -e '$FIRST' && echo no, refused || echo YES")"
echo "sees the live runtime data folder: $(run sh -c "ls /var/lib/kryuk24 >/dev/null 2>&1 && echo YES || echo no, hidden for this rehearsal")"

echo "== 5. the temporary runtime: today's tasks, a snapshot and a backup BEFORE the pipeline"
run "$PY" -B "$W/code/chain_client.py" plan "$W/runtime/runtime.sqlite" "$W/runtime/media"
back snapshot --db "$W/runtime/runtime.sqlite" > "$W/before.json"
back backup --db "$W/runtime/runtime.sqlite" --to "$W/runtime/before-media.sqlite" | pick bytes integrity sha256
echo "tables before: $("$PY" -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$W/before.json")"

echo "== 6. intake: first cut off in the middle of a copy, then run, then run again"
SHA=$(sha256sum "$FIRST" | cut -c1-64)
run sh -c "mkdir -p '$W/runtime/media/originals' && head -c 1000 '$FIRST' > '$W/runtime/media/originals/$SHA.jpg'"
echo "left by the cut-off run: $(stat -c '%s bytes' "$W/runtime/media/originals/$SHA.jpg") under the name of a $(stat -c %s "$FIRST")-byte photo"
cli intake --outbox "$OUT" | flat
cli intake --outbox "$OUT" | flat
echo "originals in the inbox, each checked against its name:"
for f in "$W"/runtime/media/originals/*.jpg; do n=$(basename "$f" .jpg); [ "$(sha256sum "$f" | cut -c1-64)" = "$n" ] && echo "  $n whole"; done
cli queue | brief
set -- $(cli queue | "$PY" -c "import json,sys;print(' '.join(w['id'] for w in json.load(sys.stdin)))"); A=$1; B=$2
install -o kryuk-run -g kryuk-run -m 600 "$W/make/masks.json" "$W/runtime/masks.json"
cli claim --work "$A" --worker agent-1 > /dev/null
cli prepare --work "$A" --worker agent-1 --masks "$W/runtime/masks.json" > /dev/null
cli queue | brief

echo "== 7. rollback: the history is kept, the photos are whole in the outbox, the other tables are as before"
back rollback --db "$W/runtime/runtime.sqlite" --media-root "$W/runtime/media" --outbox "$OUT" --archive "$W/runtime/history-1.json" | pick done history_rows originals_removed originals_kept_only_copy variants_removed kept_published
echo "archive: $(stat -c '%a %s bytes' "$W/runtime/history-1.json"); events in it: $("$PY" -c "import json,sys;print([e['kind'] for e in json.load(open(sys.argv[1]))['media_work_events']])" "$W/runtime/history-1.json")"
back snapshot --db "$W/runtime/runtime.sqlite" > "$W/after.json"
"$PY" "$W/code/chain_client.py" compare "$W/before.json" "$W/after.json"
echo "files left in the temporary media folder: $(find "$W/runtime/media" -type f | wc -l); outbox photos still whole: $(for f in "$OUT"/*.jpg; do sha256sum "$f" | cut -c1-12; done | tr '\n' ' ')"
echo "a second rollback:"; back rollback --db "$W/runtime/runtime.sqlite" --media-root "$W/runtime/media" --outbox "$OUT" --archive "$W/runtime/history-1.json" | flat

echo "== 8. restore from the backup of step 5: a copy of it has the same content as the snapshot taken before"
run sh -c "cp '$W/runtime/before-media.sqlite' '$W/runtime/restored.sqlite'"
back snapshot --db "$W/runtime/restored.sqlite" > "$W/restored.json"
"$PY" "$W/code/chain_client.py" compare "$W/before.json" "$W/restored.json"

echo "== 9. put in again, then the only-copy case: one photo is no longer in the outbox when the rollback runs"
cli intake --outbox "$OUT" | flat
rm -f "$FIRST" "${FIRST%.jpg}.json"
back rollback --db "$W/runtime/runtime.sqlite" --media-root "$W/runtime/media" --outbox "$OUT" --archive "$W/runtime/history-2.json" | pick done originals_removed originals_kept_only_copy
echo "the original that had no other copy is still in the inbox: $([ "$(sha256sum "$W/runtime/media/originals/$SHA.jpg" | cut -c1-64)" = "$SHA" ] && echo yes, whole || echo NO)"
date -u +"%FT%TZ"
echo "== rehearsal done"
