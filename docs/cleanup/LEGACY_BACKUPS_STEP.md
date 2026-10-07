# Old database copies in `/var/lib/kryuk24`: extra access, and the prepared step

Recorded by Claude on 07.10.2026. **Prepared, not executed. Nothing is deleted.**

## The extra access

Since the API reader install (07.10.2026, 13:01 UTC) the folder `/var/lib/kryuk24` is `kryuk-run:kryuk-db 2770`. The collector's user `kryuk-api-read` is in `kryuk-db`, so it can enter the folder. Several old copies of the database lie directly in it with mode `644`, which lets any user who can enter the folder read them. Before the install only `kryuk-run` could enter, so the mode did not matter. Now the collector can read:

| Files (as listed on 07.10.2026, 13:08 UTC) | Mode | Readable by the collector |
|---|---|---|
| `manual-backup.sqlite` (+ `-shm`, `-wal`) | 644 | yes |
| `pre-bilingual-20261006T231051Z.sqlite` (+ `-shm`, `-wal`) | 644 | yes |
| `pre-translation-20261006T225523Z.sqlite` | 644 | yes |
| `pre-v070-20261006T201302Z.sqlite` (+ `-shm`, `-wal`), `pre-v080-20261006T215723Z.sqlite` (+ `-shm`, `-wal`) | 644 | yes |
| `observations-before-bilingual-…json`, `observations-before-translation-…json` | 644 | yes |
| `pre-bro010-…`, `pre-bro011-…`, `pre-bro020-….sqlite` | 600 root | no |
| `pre-v070-…-restored.sqlite`, `pre-v080-…-restored.sqlite`, `restore-check.sqlite` (+ side files) | 600 kryuk-run | no |
| folders `backups/`, `operations-backups/`, `operations-reports/`, `restore-check-*` | 700 kryuk-run | no |

The collector can read and write the live database anyway, so this adds no new kind of data. It is still wider than needed, and the collector can also delete or replace these files, because it may write to the folder.

## What uses them (checked on the server, 13:08 UTC, read-only)

- No Python or shell file in `/opt/kryuk24` and no unit in `/etc/systemd/system` contains any of the names (`manual-backup`, `pre-bilingual`, `pre-translation`, `pre-v070`, `pre-v080`, `pre-bro`, `restore-check`, `observations-before`).
- No process had any of them open.
- The scheduled jobs write elsewhere: `kryuk-backup.service` into `backups/`, `kryuk-operations.service` into `operations-reports/` and `operations-backups/`.
- One side file (`pre-bilingual-….sqlite-shm`) has a modification time of 07.10 08:40 UTC: something opened that copy that morning. What did it is not known.

So they are hand-made copies from the patches of 06.10. Whether any of them is still wanted as a restore point is Gev's and GPT's call.

## The step (to run only on Gev's word)

```sh
sudo install -d -o kryuk-run -g kryuk-run -m 700 /var/lib/kryuk24/legacy-backups
cd /var/lib/kryuk24
sudo sh -c 'sha256sum manual-backup.sqlite* pre-*.sqlite* restore-check.sqlite* observations-before-*.json > /root/api-read-install/legacy-backups-before.sha256'
sudo mv manual-backup.sqlite* pre-*.sqlite* restore-check.sqlite* observations-before-*.json legacy-backups/
sudo sh -c 'cd legacy-backups && sha256sum -c /root/api-read-install/legacy-backups-before.sha256'
sudo -u kryuk-api-read sh -c 'ls /var/lib/kryuk24/legacy-backups >/dev/null 2>&1 && echo ALLOWED || echo DENIED'
```

Expected: every file `OK` after the move, and `DENIED` for the collector. Owner and mode of each file stay as they are; only the folder around them closes. A move inside one filesystem does not copy data. Before running: no service needs to stop, but check again that no process has the files open. To undo: move them back.

Not part of this step: the three `restore-check-*` folders and the scheduled backup folders, which are already `700`.
