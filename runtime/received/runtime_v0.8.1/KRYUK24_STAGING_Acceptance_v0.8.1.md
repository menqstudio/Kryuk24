# KRYUK24 v0.8.1 — current STAGING acceptance / ընթացիկ ընդունում

## Evidence / Ապացույց

All deployment and browser statements below are **CLAUDE/GEV-REPORTED**, supplied by Gev. They were not independently executed from this workspace. Claude reports the patch check at07.10 01:13–01:14MSK; supplied timestamps are retained without assuming chronological consistency with earlier reports.

- Windows11/Python3.12.10 and VPS/Python3.14.4:69 Python tests OK; WinError32 absent. JS4/10/6/10+11PASS.
- Only ops_backup.py and test_ops.py replaced; hashes match release manifest/VPS. No capture restart or DB/env/service-user change.
- Operations service succeeds with integrityOK/media_files0. New archive restored to a new directory: orders20/events40/contact36/tasks10/observations9/ops_events30 match live database at that checkpoint. These are checkpoint counts, not business KPIs; no media exists yet.
- Real calculator WhatsApp UI action behind Nginx gate stored TEST request K24-f029710091ff412f952d034001659c3d at22:08:08UTC, CALCULATOR/wa/form, linked contact. A saved handoff is not proof of a sent/received WhatsApp message.
- Earlier phase5: IP restrictions removed. Two networks reject absent/wrong credentials401. Basic gate remains.

## Required correction to earlier setup documentation

Use the tested Nginx realm matching the backend:

```nginx
auth_basic "KRYUK24 operator";
auth_basic_user_file /etc/nginx/kryuk-staging.htpasswd;
satisfy all;
```

Same current gev username/password, forwarded Authorization header, existing route limits/TLS/ACME protections remain. Gev/Claude report capture failed with realm KRYUK24 STAGING and passed after matching KRYUK24 operator. Record this as observed installation behavior; matching realms alone is not proof of every authentication path. Do not restore the old realm or repeat the historical IP-rule migration. The already-issued v0.8.1 ZIP is retained unchanged so its release hashes remain reproducible; this addendum supersedes its old realm example.

HY: Նախորդ հրահանգի «KRYUK24 STAGING» realm-ը սխալ էր այս տեղադրման համար։ Պահել ստուգված «KRYUK24 operator»-ը։ Սա փաստաթղթի ուղղում է․ նոր կոդ կամ restart պետք չէ։ Հին zip-ը չի վերագրվում։

## Remaining gate acceptance / Մնացած փորձը

Gev from a different network, for example phone mobile internet with Wi-Fi off: open https://runtime.kryuk24.ru/operator/work, use the current correct credentials, verify the work dashboard actually loads; Claude can record the authenticated response200. Recheck /health200 with STAGING/sendingfalse. Do not send credentials in chat or URLs. Existing absent/wrong-password401 checks remain the negative controls. Correct-password200 from a different network is still UNVERIFIED.

HY: Մյուս ցանցից ճիշտ գաղտնաբառով վահանակի բացվելն ու200-ն են մնացել։ Դրանից հետո դինամիկ IP-ի մուտքի փորձը փակվում է։ Կենդանի կայքին միացնելու թույլտվություն սա չի նշանակում։

## Business automation scope / Ավտոմատացման սահման

STAGING only; no live-site attachment/outbound message verified. Timer planning/local checks work per Claude; this does not establish an always-on external browser executor. Nine observations do not establish all external jobs completed; inspect current task states and their sources before closing them. No photos have been imported/processed. Next work remains actual cabinet observations and connecting a real persistent executor within authorized read/write boundaries.
