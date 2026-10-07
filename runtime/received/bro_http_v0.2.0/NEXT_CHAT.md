# Continue KRYUK24 Bro / Շարունակություն

EN: User requested limited Bro HTTP API + Windows pull client and Claude installation package. v0.2.0 is prepared locally; NOT installed on VPS or Windows. Read README, CLAUDE_INSTALL and VALIDATION first. Package embeds exact v0.1.0 and v0.1.1 bridge archives under reference_archives; do not overwrite deployed files with historical archives.

HY: Հաջորդը Claude-ի STAGING տեղադրումն ու իրական HTTPS gate-ի/Windows client-ի ընդունումն են՝ ըստ CLAUDE_INSTALL.md։ Timer-ը, real Claude/Chrome adapter-ը, tool permissions-ը, subscription allowance-ը և Windows process-tree cleanup-ը դեռ չեն ընդունվել։

Accepted baseline supplied by user/Claude: STAGING /opt/kryuk24, VPS DB, 78 Windows/VPS tests; queue order rowid; 20 orders,36 contact_interactions,10 ops_tasks,9 observations; 8 DONE/AVITO BLOCKED/DAILY_REPORT READY_REVIEW; digest prefix 3e0c111c. Current ops_views.py prefix 1c145a4d8864223b; light default, kryuk-theme storage. Realm KRYUK24 operator, no IP gate. Preserve full hashes, data, approvals, services/timers. LIVE absent, sending=false.

Design: separate localhost:8789 sidecar on existing DB; new bro_receipts + bro_runs tables; dedicated worker Basic credential verified by separate Nginx htpasswd AND sidecar; no owner credential in bridge or subprocess. Queue current Yerevan day only, structured metadata/statuses only. Unique run + revision + active600s lease fence every result. Atomic durable idempotency and claim race control. REPORT_DRAFT only, fixed internal review destination; no approve/plan/customer ledger/message endpoint. BLOCKED not automatically reopened. Real AI CLI disabled, queue-only CLI available. Test-injected adapter proves protocol, not connection. Recovery journals private, unique per run; do not reuse same journal concurrently.

Open acceptance: actual nginx -T/service-user/DB/path inspection, backup+restore, full hashes/counts unchanged, separate credential provisioning and NTFS ACL, nginx -t+edge authentication isolation, actual Windows/VPS tests. No SSH/browser/remote mutation occurred in authoring environment.
