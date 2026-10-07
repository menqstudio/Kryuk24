# v0.8.0 — durable operations, private media and dynamic-IP staging gate

## Delivered behavior

Python 3.10+; standard library only. Existing capture/contact/idempotency source remains unchanged. New backend code requires service restart; copying JS alone is insufficient.

`/operator/work` is a Basic-authenticated internal work dashboard. A daily plan has ten distinct jobs: local ledger, local runtime health, Yandex Business, Direct, Metrica, Webmaster, Avito, hosting deadlines, media inbox, daily report. Creation is idempotent by day/job. Creating a queue is not completing checks. Local worker actually reads SQLite and loopback `/health`; browser jobs remain PENDING until real observations are recorded. Lease, source, observation time, reporter and result persist in the existing DB. Expired read/preparation leases can be reclaimed. This is not an always-on Claude browser agent.

Draft workflow: claim → prepare exact account/destination/body/assets/reason → READY_REVIEW → Gev approves this digest with a reference → APPROVED → separately record actual execution evidence. Runtime never publishes, sends messages, changes budgets or pays. Gev approval references must originate from Gev; Claude must not invent them or approve itself just because it can access the protected account. A changed draft invalidates approval. Evidence supplied by an operator is labelled OPERATOR_REPORTED; only bounded local checks have MACHINE_OBSERVED status.

## Media

`ops_cli.py media-original` stores a private hash-named copy with provenance and permission reference. `media-prepared` imports an already edited file, requires explicit review and edit notes, links it to the original. JPEG/PNG/WebP signature and size checks are not full image decoding or automatic masking. No client photos were supplied or processed in this build. Actual polish/masking must happen in the photo editor; hide faces/plates, correct light mildly, preserve the real scene, then review the result and import it. The runtime has no photo editing connector.

Only known prepared assets are viewable via `/operator/media/ASSET-…`, with authentication and hash verification; original photos have no HTTP route. Drafts pin exact asset SHA256. Changed/missing files block approval/result recording. No public photo endpoint and no upload endpoint were added.

Data: existing SQLite gets `ops_*` tables without resetting orders, events or clicks. Media lives in `/var/lib/kryuk24/media/{originals,prepared}`. Report HTML: `/var/lib/kryuk24/operations-reports`; full backup: `/var/lib/kryuk24/operations-backups`. These must survive releases. Protect and back up as private data. Never put passwords, tokens, customer names/phones or raw chat contents into operation notes. State sources and aggregate counts instead. No retention period is invented and no automatic deletion is introduced; agree retention separately. Disk usage needs monitoring as reports/backups grow.

## VPS installation — Claude

1. Keep STAGING, existing DB/env/port and actual `kryuk-run` service user. Do NOT copy legacy example capture/backup units over the installed ones (`kryuk` in old examples is not the current account).
2. Before update, existing SQLite backup plus restore-to-new-path check. Preserve old code for rollback. Run all tests below on local Windows and VPS.
3. Copy new `ops_*.py`, updated `secure_server.py`, `test-orders.html`, tests, docs and new daily unit files to root-owned `/opt/kryuk24`. Existing site source and both contact JS files are unchanged.
4. Restart only `kryuk-capture.service`; verify loopback `/health` STAGING and sending false, old ledger counts unchanged, `/operator/work` without credentials401/with credentials200. Existing Nginx `/operator` location already proxies the new paths.
5. Copy only `deploy/kryuk-operations.service` and `.timer` to `/etc/systemd/system/`. Check the calendar with `systemd-analyze calendar '*-*-* 06:00:00 UTC'`. It runs about09:00 Moscow/10:00 Yerevan, plus up to60s jitter; Persistent catches a missed run, not a whole historical backlog.
6. `systemctl daemon-reload`; `systemctl start kryuk-operations.service`; inspect status and results. Then `systemctl enable --now kryuk-operations.timer`. Running twice same day must keep ten tasks, not twenty. Two local checks close with actual results or BLOCKED. External jobs do not close themselves. HTML is a draft, not delivered to Armen.
7. Daily service includes a new full DB+media `.tar.gz` backup. Old SQLite-only backup timer stays. New archive integrity/hash checks are real, but restore_test is NOT_PERFORMED until separately restored. Validate restore using a NEW private directory: read trusted archive members (runtime.sqlite and media/ only), restore SQLite with recovery.py to a new file, compare ops/order/contact counts and SHA256 of all original/prepared files. Never replace a running DB while testing recovery. Don't expose archives via Nginx. For rollback, restore code and disable the new timer; do not delete data or new tables.

## CLI example (private local files)

All CLI commands use `--db /var/lib/kryuk24/runtime.sqlite` and run as `kryuk-run`. `report --day 2026-10-07` lists IDs. `claim --task WORK-… --worker CLAUDE_SESSION` takes a read/preparation job. `observe --task … --worker CLAUDE_SESSION --source 'Yandex Business cabinet' --observed-at '2026-10-07T09:15:00+03:00' --summary-file /private/summary.txt` records actual evidence. If login/access is unavailable, use `--blocked`, never guessed numbers.

For prepared changes, `draft --task … --worker … --file /private/draft.json`. JSON fields: action (REPORT_DRAFT/PHOTO_BATCH/PUBLICATION/MESSAGE/AD_CHANGE), account, destination, body, reason, assets (optional list of {id,sha256}). Draft preparing is local. Gev can approve the displayed exact version in `/operator/work`; CLI `approve --task … --digest … --reference …` is only for an explicit Gev instruction. `revise` invalidates the previous draft. `result` records source/evidence AFTER a separately authorized actual action; it does not execute it.

## Claude daily session protocol

Bring the correct account/profile and tab to foreground before browser actions; verify visibilityState visible. Check identity, not Browser1/2 names. Do not infer business demand from WhatsApp history: most existing orders arrive by phone. Claim jobs, read actual cabinets, record date/source/time and uncertainties. Avito account/access is not verified, so BLOCKED is a valid outcome. Changes become review drafts; don't publish/send without Gev's explicit approval. Batch related prepared changes for one review. Use customer/Armen communication only under separately authorized scope.

To make the session truly automatic, a persistent agent/browser executor, credential/profile isolation and a tested schedule still need connection. This package provides durable queue and evidence, not that connection. Google continuous sync and real WhatsApp/Telegram sending are also not connected.

## Accepted staging evidence (reported by Claude)

v0.7.2 Windows/VPS tests and Chrome acceptance passed; latest additional 07.10 00:32–00:35MSK: PREBOOKING same-tab reload sameID; changed calculator destination newID; New Request at500px newID/no overflow; +4 forms/+4 linked contacts, independentCLICK0. This is reported external evidence, not a new test performed here. Hidden-tab first-action issue is an automation condition: foreground tab before proceeding; no speculative handler patch. Remaining real acceptance:24h expiry, actual phone360–400px, external map/route. Staging CSP currently blocks external maps; don't loosen it incidentally.

## Tests

`python -m unittest discover`
`node test_handoff_js.cjs`
`node test_contact_clicks_js.cjs`
`node test_real_markup_contacts.cjs`
`node test_handoff_persistence.cjs`

Set `KRYUK_TEST_PYTHON=python` on Windows if needed. New Python tests cover persistent/idempotent plan, simultaneous claim, expired lease, evidence restrictions, exact approval/revision, manual execution evidence, escaping, media review/tamper checks, private HTTP/Origin guards, daily plan and full backup content/recovery. JS harnesses are not browser tests. New operations UI must still be accepted in a real browser on VPS. No live deployment/message was performed here.
