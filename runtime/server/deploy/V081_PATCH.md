# v0.8.1 — close SQLite backup connections / փակել SQLite միացումները

## Change / Փոփոխություն

Replace only `ops_backup.py` and `test_ops.py` from this release; add `deploy/V081_PATCH.md` and `VALIDATION_V081.md`. The full ZIP also contains the unchanged v0.8.0 code and historical handoffs. Preserve runtime DB/media/reports/backups/env, actual kryuk-run units and Nginx/IP rules. No schema or configuration change. Latest phase5 report below supersedes earlier IP-state notes. No capture-service restart is required for this isolated patch: backup module is imported by each new daily process. Apply between operations-service runs, not while copying into a running backup process. Compare release manifest hashes for the replaced files.

SQLite's connection context manager commits/rolls back but does not close. Two snapshot connections in ops_backup.py and the snapshot creation connection in test_ops.py now use contextlib.closing. This fixes file handles surviving temporary-directory cleanup, observed by Claude on Windows with WinError32. Backup success/error paths now have explicit connection-closure regression tests that also fail on Linux when close is omitted. Existing recovery.py and Runtime.db already explicitly close their connections; no changes needed there.

HY: Փոխարինել միայն նշված երկու Python ֆայլը։ Տվյալները, կարգավորումները, ծառայությունների օգտատերը և Nginx-ի գործող փակումը պահել։ Բեքափի նոր գործարկումը նոր կոդը կկարդա․ capture ծառայության restart պետք չէ։ Windows-ի սխալի պատճառը SQLite-ի with բլոկի սխալ կիրառումն էր․ այն չի փակում միացումը։ Ուղղված են երեք միացումները, և ավելացված են փակվելը ստուգող թեստեր։

## Acceptance / Ստուգում

Windows and VPS: `python -m unittest discover` →69 OK expected. Existing JS commands remain4/10/6/10+11. Run operations service once with corrected backup module, verify success and preserved ledger/ops counts, then separately restore the new archive to a NEW private directory. No outbound messages/LIVE changes. Every invocation intentionally produces a fresh HTML and archive; twice/day does not duplicate tasks/observations. No retention/deletion policy is authorized by this patch.

## Current deployment evidence / Տեղադրված վիճակ

Claude-reported v0.8.0 STAGING07.10 01:55–02:00MSK: VPS67OK and all JS/manifest checks; old orders18/events36/contact35 preserved; timer active06:00UTC; repeated plan tasks10/observations2/events14 unchanged; full archive restored, no media yet. Windows65/67 pass with two SQLite cleanup errors; fixed candidate here, Windows recheck pending.

Dynamic-IP gate phase1–4 reported: root:www-data0640 SHA512 file, Basic+satisfy-all configured; allowedIP unauthenticated routes401 incl POST/OPTIONS, otherIP403, ACME and certificate dry-run passed. Earlier phase1–4 pending checks were superseded in part by the following phase5 report. A404 for unknown /nope caused by Nginx return404 is acceptable: no data is served. Do not add a speculative routing patch merely to make unknown paths401.

HY: IP կանոնը դեռ պահել․ նախ ճիշտ/սխալ գաղտնաբառով մուտքն ու ձևի գրանցումը ստուգել։ Անհայտ ուղու404-ը տվյալ չի բացում և ուղղում չի պահանջում։ Արտաքին ութ աշխատանքը դեռ PENDING է։

## Latest phase5 update / Վերջին փոխանցումը

CLAUDE/GEV-REPORTED07.10 02:10MSK: Gev opened /operator/work in KRYUK24 browser profile using remembered credentials. TLS allow/deny removed; Basic+satisfy-all remains; nginx-t/reload passed. Two different networks: no credentials GET/health,/operator/work,/operator/site and POST/capture401; wrong password401 on both. Correct credentials200 from the other network and real browser capture behind the gate still UNVERIFIED. Do not reintroduce the old IP rule as part of this SQLite-only patch. Preserve the current Nginx gate. No new direct VPS verification was performed here.
HY: IP սահմանափակումը հանված է՝ փոխանցված ստուգմամբ։ Երկու ցանցից առանց/սխալ գաղտնաբառով401։ Դեռ ստուգել ճիշտ գաղտնաբառով200-ն մյուս ցանցից և ձևի պահպանումը զննարկչով։ Այս ուղղմամբ Nginx-ը չփոխել։
