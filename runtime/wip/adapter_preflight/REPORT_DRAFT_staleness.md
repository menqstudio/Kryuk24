# REPORT_DRAFT can outlive the facts it was built from

Recorded by Claude, 07.10.2026, 01:01 UTC (04:01 MSK, 05:01 Yerevan). Read-only finding. The current draft was not changed and not approved.

## What happened (VERIFIED in the live STAGING database)

| Time (UTC) | Event |
| --- | --- |
| 06.10 23:10:51 | DAILY_REPORT `DRAFT_READY`, revision 8, digest `3e0c111c6393758628d7578b52a428b48ba77396030f86ef5cedd7e7b0fa3ecb`. At that moment: 8 tasks DONE, AVITO `BLOCKED` |
| 07.10 00:45:38 | AVITO `CLAIMED` by `AUTHENTICATED_OPERATOR` (owner, dashboard) |
| 07.10 00:46:25 | AVITO `DONE`, revision 4, new observation with source «Գև», trust `OPERATOR_REPORTED` |
| 07.10 01:01 | DAILY_REPORT still `READY_REVIEW`, revision 8, same digest |

So a task of the same day changed status and received a new observation 1 h 35 min after the report draft was built, and the draft stayed approvable as if nothing had changed.

## Why (installed `ops_work.py`)

- `approve()` requires only `status == 'READY_REVIEW'` and `row['digest'] == digest`. The digest covers the draft itself (`action, account, destination, body, reason, assets`), not the day's inputs.
- Nothing in `claim` / `observe` of another task touches the report task. Only `revise()` resets it to PENDING.
- The Bro API has the same shape: `draft` computes the digest from the normalized draft only.

## Impact in this instance

None on content, by luck: the body of the current draft (728 characters, Russian, for Armen) does not mention Avito at all, so it did not become false. Correction to my earlier report of 00:52 UTC: I wrote "the draft still says Avito is blocked". That was an assumption; I had not read the body. It is wrong.

The general problem stands: had the changed task been Yandex Business or the hosting balance, the owner would be approving text built from an observation that is no longer the latest.

## What the system cannot tell today

- which observations a draft was built from (no input fingerprint is stored with the draft);
- whether any task of that day changed after `DRAFT_READY`;
- on the dashboard: nothing marks the draft as older than the newest observation.

## Options (for GPT to choose; nothing implemented)

1. **Input fingerprint.** Store with the draft a hash of the day's `(task id, status, revision)` list at build time; `approve()` rejects when the current list differs ("draft is stale, revise"). Smallest change, fail-closed.
2. **Automatic stale mark.** Any status change of a same-day task after `DRAFT_READY` writes a `DRAFT_STALE` event and the dashboard shows it; approval still possible but explicit.
3. **Leave as is**, and treat the daily report as a snapshot "as of time X" with that time printed in the body.

My recommendation: option 1, plus the build time shown next to the approve button. Also relevant for Bro: with the real adapter, DAILY_REPORT is claimable once every other task is DONE/BLOCKED; an owner edit after that is exactly this case.

## Not done

No `revise`, no approval, no edit of the draft, no change of code. Whether Gev wants the current draft rebuilt is his decision.
