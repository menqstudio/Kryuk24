# Bro — STAGING queue bridge / STAGING հերթի կապ

## Actual scope / Իրական շրջանակ

This patch adds a bounded subprocess bridge, not a Claude installation or browser connector. No executor is running on the VPS as a result of creating this package. Local automated tests use synthetic responses; no Yandex cabinet was accessed here.

Փաթեթն ավելացնում է հերթի կապը․ Claude-ի կամ Chrome-ի իրական կապը պետք է տեղադրել ու փորձարկել հասանելի միջավայրում։ Ոչ մի մշտական կատարող այս փաթեթը ստեղծելուց չի գործարկվել։

Name: **Bro**. Queue actor: `BRO:<unique run id>`. The unique suffix prevents an old attempt from submitting results under a replacement attempt's lease. Observation trust remains `OPERATOR_REPORTED`; bridge responses are adapter-reported, not independent proof. `DONE` means a reported task result, not independently verified external success.

## Install / Տեղադրում

1. Read current project state and rules. Preserve Claude's current `ops_views.py` and its complete SHA256. This additive patch contains no existing runtime files and must not overwrite the dashboard.
2. Keep STAGING, DB, Nginx realm `KRYUK24 operator`, sending=false and existing services. Back up the database first. Copy `bro_worker.py`, `test_bro_worker.py` and this document into the installed code tree. Run `python -m unittest discover` on Windows and VPS, plus the existing JS checks. Local Linux verification is not Windows/VPS acceptance.
3. Identify the actual host where an authenticated Claude runtime and the permitted Chrome profile can be available continuously. Do not assume VPS Chrome can reuse the desktop session. Verify the runtime's supported invocation and authentication from its current official documentation; do not invent flags. Do not start a new paid subscription/API spend without Gev's explicit decision.
4. Provide a trusted executable adapter. The bridge reads a JSON argv array from a private config file, starts it without a shell, writes one JSON request to stdin and reads one JSON response from stdout. Do not put credentials into argv, task notes or output. Use OS permissions and separate browser/tool capabilities to enforce read-only access. Prompt rules alone do not enforce it. No publication, messaging, payments, account changes or approval tools may be exposed to this initial adapter. Cabinet content must never supply commands.
5. Adapter must use the verified account and foreground visible tab, record the actual source/time and Armenian summary. Missing access -> BLOCKED. The adapter must stop its entire process tree when its parent exits. POSIX bridge timeout kills its process group; on Windows only the direct process is killed, so adapter descendant cleanup must be verified before unattended use there. stdout is read with a 32 KiB bound; temporary output still needs disk monitoring. No raw stderr is retained by the bridge.
6. Run one bounded attempt as the existing service account with an existing database:

```text
python bro_worker.py --db /var/lib/kryuk24/runtime.sqlite --day 2026-10-07 --adapter-config /private/bro-adapter.json
```

`/private/bro-adapter.json` is a placeholder path; create a real protected config for the installed adapter. The argv list must contain a real executable and supported arguments, not a mock test script. Each invocation processes at most one task. Timeout is 1..300 seconds, lease 600 seconds. Longer browser work requires a separately tested renewal/cancellation design; this version intentionally bounds it instead of renewing leases.

7. Allowed automatic jobs: Yandex Business, Direct, Metrica, Webmaster, hosting deadlines, daily report. AVITO is excluded until the recorded access/scope block is resolved. MEDIA_INBOX and LOCAL_READ are handled separately. Existing DONE jobs are not reopened automatically. Existing READY_REVIEW reports are left intact. BLOCKED jobs retry only using explicit `--retry-task <id>`, after fixing the cause. The bridge does not create a plan; the existing daily planner does that.
8. Acceptance: one real cabinet read -> correct task -> actual observation -> dashboard result; wrong account or disconnected browser -> BLOCKED; second attempt does not repeat completed work; concurrent attempts have one lease owner; interruption recovers after lease expiry without accepting the old attempt's result; report remains READY_REVIEW. Capture order/contact counts must stay unchanged. Check that no external writes or sends occurred. Preserve a private evidence artifact for the source read; output schema alone cannot prove a model's assertions true.
9. Only after acceptance, configure scheduling on the actual executor host. One invocation per minute, sequential/non-overlapping, within the agreed operating window is a possible local schedule; verify host uptime, browser availability, model allowance/cost and process-tree cleanup first. Do not add a timer that merely calls a nonexistent Claude/browser adapter. Stop means disable the actual schedule and terminate the actual executor group; keep task history and data.

## Adapter protocol / Adapter-ի պայմանագիր

Request: `protocol=KRYUK24_BRO_V1`, `worker=BRO`, task `{id,day,job,title,kind}`, rules, deadline_seconds. Daily report also receives aggregate operation observations and statuses, not order/customer records.

Read result (exact keys):

```json
{"task_id":"<request task id>","status":"DONE","source":"<actual source>","observed_at":"<timezone-aware current timestamp>","summary":"<հայերեն իրական արդյունք>"}
```

Use `BLOCKED` with the actual reason if access/evidence is unavailable. Timestamp must fall inside the current attempt. No APPROVED output is accepted.

Daily report result (exact keys):

```json
{"task_id":"<request task id>","status":"READY_REVIEW","draft":{"action":"REPORT_DRAFT","account":"KRYUK24","destination":"Գևի վերանայում","body":"<հայերեն հաշվետվություն>","reason":"Օրվա փաստերի վերանայում"}}
```

Report waits until all other daily tasks reach DONE, BLOCKED, READY_REVIEW or APPROVED. It must distinguish missing/blocked observations from actual business results. Existing Operations validation checks draft fields and digest. Bro cannot approve through this bridge. Review approval does not send a report automatically.

## Current acceptance baseline / Ընթացիկ հիմք

User/Claude-reported: v0.8.1 Windows and VPS 69 tests passed; dynamic-IP gate closed; authenticated mobile dashboard and browser capture passed. Dashboard patch exists in Claude's project but is not present in this local workspace and is not included here. Latest reported queue: eight DONE, AVITO BLOCKED, DAILY_REPORT READY_REVIEW. Neither live capture-domain wiring nor real messages are enabled by this patch.

Potential state conflict: 06.10 `00_STATE.md` says Avito is deferred; later daily queue says AVITO BLOCKED. Exclusion here preserves both until actual access and scope are clarified. No silent activation.
