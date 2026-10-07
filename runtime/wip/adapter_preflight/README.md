# Bro adapter preflight package, v3

> v3.2 (07.10.2026, 02:26 UTC (05:26 MSK, 06:26 Yerevan)), additions for the supervised trial, both optional and explicit in the policy: `trial_origins` (local `http://127.0.0.1:<port>`, only for the job `TRIAL`) and `max_connected_browsers` (absent = unchanged behaviour). `win_job.py` accepts an optional `stderr_path`. Suites: gate 50 OK, job 31 OK. Details in `../bro_runtime_trial/TRIAL_PLAN.md`, section 8.

From Claude, 07.10.2026, 01:33 UTC (04:33 MSK, 05:33 Yerevan). Replaces v2 of 01:18 UTC. No real Claude/Chrome adapter run, no subscription use, no timer, no autostart. Everything executed here is synthetic and local.

HY: Երրորդ տարբերակը՝ GPT-ի v3 դիտողություններով։ Հիմա «երևացող» թաբն ու «այս գործարկման ստեղծած» թաբը տարբեր բաներ են. ցուցակում երևալը սեփականության ապացույց չի։ Կրկնված ID-ներն ու իրար հակասող պատասխանները փակում են գործարկումը։ Ելքը կարդացող կամ մուտքը գրող թելի սխալը այլևս չի թաքնվում, վերադառնում ա որպես ձախողում։ Իրական գործարկում չի եղել։

## What changed against v2

| Your point | Done |
| --- | --- |
| Separate visible tabs from tabs created by this run; a context listing is not proof of ownership; if the created tab's identity is not reliably confirmed → BLOCKED | Two sets in the state: `visible` (ids in the latest listing) and `tabs` (owned). A tab becomes owned only through a bracketed creation. Read, navigate and close work on owned tabs only. Any failure of the bracket taints the run; the verdict is reject |
| Reject repeated tab/device IDs and contradicting structured results | Duplicate `tabId`, duplicate `deviceId`, duplicate JSON keys → `Unknown` → taint. More than one browser in use, changed tab group, own tab missing from a listing, closed tab listed again → taint |
| Tests for read/close/navigate on a pre-opened allowed tab and for repeated IDs | Added (table below) |
| A reader/writer thread error must not be hidden from the wrapper; the return must be a failure | Both threads record any exception, end the run at once, and `run_in_job` raises `JobIOError`; `returncode` and `stdout` are cleared so a caller cannot read a result out of it |
| New ZIP, hashes, test report | Below |

## 1. Visible versus owned tabs

A tab becomes **owned** only this way, with nothing in between (one call at a time is already enforced):

1. `tabs_context_mcp` → verified listing A (the call completed immediately before the creation);
2. `tabs_create_mcp` → no fact is taken from its result, whatever it says;
3. `tabs_context_mcp` → verified listing B. Required: every id of A is still in B, **exactly one** id of B is not in A, and that tab's URL is `chrome://newtab/` or `about:blank`. That id is the tab of this run.

Anything else → `created tab identity not confirmed` → run tainted → wrapper reports BLOCKED. Cases covered by tests: no new tab, two new tabs, new tab already on a page, new tab on a foreign host, a baseline tab vanished, any call other than a listing after the creation, a creation without a listing right before it.

Tabs that are only **visible** (open before the run, or appearing without a creation of ours) are tolerated in listings and can never be used: `get_page_text`, `read_page`, `find`, `navigate`, `tabs_close_mcp` on such an id are denied with `tab was not created by this run`, even when the tab sits on an allowed host. Host rules apply to owned tabs; a foreign tab's URL is neither checked nor trusted.

How reliable this is, stated plainly:
- It is inference from two structured listings around the creation, not an identity returned by the creation itself. The result of `tabs_create_mcp` has not been observed in this session, so no structure of it is treated as known.
- Residual: if another actor adds exactly one blank tab to the same tab group between listing A and listing B while our creation silently fails, that tab would be taken as ours. It would be blank, and everything done to it afterwards is still limited to allowed hosts.
- If the supervised trial shows that `tabs_create_mcp` returns the new id in a stable structure, the rule should become: structured id from the creation **and** the bracket must agree; disagreement → BLOCKED. Not implemented now because the structure is ՉՍՏՈՒԳՎԱԾ.

## 2. Duplicates and contradictions

| Input | Result |
| --- | --- |
| same `tabId` twice in `availableTabs` (same or different URLs) | `duplicate tab id` → taint |
| same `deviceId` twice in the browser list (any `inUse` combination) | `duplicate device id` → taint |
| duplicate key inside any JSON object of a structured result (`"tabId"` twice, `"url"` twice, `"deviceId"` twice, `"availableTabs"` twice) | `duplicate key in a structured result` → taint. Python's default would silently keep the last value |
| more than one browser with `inUse: true` | taint (v2 only refused to confirm) |
| `tabGroupId` differs from an earlier listing of the same run, or is not an integer | taint |
| an owned tab is missing from a listing | `a tab of this run disappeared` → taint |
| a tab this run closed is listed again | taint |
| profile confirmed earlier, later listing does not show the pinned device as the only one in use | taint (unchanged) |

## 3. Reader and writer errors in the job runner

- The output reader and the input writer run in their own threads. Any exception in either (not only `OSError`) is recorded as `output reader: <Type>` / `input writer: <Type>`, sets a flag, and the main loop ends the job immediately instead of waiting for the timeout.
- A thread that has not finished 5 s after cleanup is recorded as well.
- If anything was recorded and the run did not time out, `run_in_job` raises **`JobIOError`** with `.result`; in that result `returncode` is `None` and `stdout` is empty, also when the command itself exited with 0 and printed something that looks valid.
- On a timeout the function returns as before (`timed_out: True`, `returncode: None`), now with the `io_errors` list included.
- A returned result with a return code therefore always has `io_errors == []`.
- Real case this now catches without any injection: the command exits without reading its input (2 MB request, child exits at once) → `input writer` error → failure. In v2 this was swallowed.

## 4. Tests executed

Gev's machine, Windows 10.0.26200, Python 3.12.10, 07.10.2026 01:30–01:33 UTC, from a clean folder, with `-W error::ResourceWarning`:

| Suite | Tests | Result | Time |
| --- | --- | --- | --- |
| `test_bro_gate_hook` | 43 | OK | 91 s |
| `test_win_job` | 30 | OK | 28 s (run twice, both OK) |

During development two gate tests failed once; the cause was the test helper itself producing two browsers with the same device id, which v3 correctly rejects. The helper was fixed, the gate was not changed for it.

New gate tests in v3 (15):

| Test | Shows |
| --- | --- |
| `tab_that_was_already_open_cannot_be_read_closed_or_navigated` | pre-opened tab on an **allowed** host: `get_page_text`, `read_page`, `find`, `tabs_close_mcp`, `navigate` each denied; run tainted; verdict reject |
| `already_open_tab_stays_foreign_after_this_run_creates_its_own` | same three operations denied on the foreign tab while the own tab keeps working |
| `listing_alone_never_makes_a_tab_ours` | three listings of a tab on an allowed host → read still denied |
| `tab_that_appears_without_a_creation_is_foreign` | new id in a later listing without a creation → denied |
| `creation_needs_a_listing_right_before_it` | no listing, or another call in between → creation denied |
| `after_creation_only_a_listing_is_allowed` | navigate straight after create → denied; verdict reject |
| `created_tab_identity_not_confirmed_blocks` | five failing brackets → taint, read denied, verdict reject |
| `result_text_of_the_creation_is_not_trusted` | creation result naming another tab id and an allowed URL → ignored |
| `duplicate_tab_ids_taint` | three listings with a repeated tab id |
| `duplicate_device_ids_taint` | three browser lists with a repeated device id |
| `duplicate_json_keys_taint` | four results with a repeated key |
| `contradicting_listings_taint`, `two_browsers_in_use_taints`, `closed_tab_cannot_be_used_again`, `tab_limit_counts_owned_tabs` | group change, own tab gone, closed tab back, group id form; two in use; reuse after close; limit on owned tabs |

Of the 31 tests of v2, 28 are kept and adapted to the creation bracket. Three were replaced by stricter ones: `created_tab_is_unknown_until_a_context_lists_it` (now the ownership tests above), `too_many_tabs` (now `tab_limit_counts_owned_tabs`) and `tab_gone_after_the_read` (now part of `contradicting_listings_taint`). 28 + 15 = 43.

New job tests in v3 (6):

| Test | Shows |
| --- | --- |
| `output_reader_error_is_a_failure` | injected `OSError`, `ValueError`, `RuntimeError` in the reader → `JobIOError`, result cleared, three-level tree ended, 0 survivors |
| `reader_error_is_not_masked_by_a_clean_exit` | command exits 0 and prints `{}`; reader failed → still `JobIOError`, no return code, no output |
| `input_writer_error_is_a_failure` | injected writer error → `JobIOError` in under 20 s of a 60 s timeout, tree ended |
| `input_that_was_never_read_is_a_failure` | nothing injected: child ignores 2 MB of input → `JobIOError` |
| `normal_run_reports_no_io_errors` | success has `io_errors == []` |
| `timeout_result_carries_io_errors_field` | timeout result shape |

All 24 tests of v2 are kept unchanged.

## 5. Zip and hashes

`KRYUK24_Bro_Adapter_Preflight_v3_from_Claude.zip`; its sha256 and the per-file hashes are in the message that carries this report and in `SHA256SUMS.txt` inside the zip (the zip cannot contain its own hash).

Files: `README.md`, `bro_gate_hook.py`, `test_bro_gate_hook.py`, `win_job.py`, `test_win_job.py`, `browser_tool_schemas.json`, `policy.example.json`, `settings.trial.example.json`, `REPORT_DRAFT_staleness.md`, `SHA256SUMS.txt`. Unchanged since v2: the last four data/notes files.

## Limits that stand from v2

- No trusted mechanism ties a read to a host and a profile; the before/after tab check is prevention only as far as inputs allow and otherwise detection that makes the wrapper discard the run.
- A hook is fail-open on its own; the construction relies on a default-deny permission layer where only the hook can say yes.
- Same Windows user for Claude and the credential files.
- A separate, single-purpose Chrome profile for Bro remains the control that does not depend on any of this. Gev's decision; not done.

## Still ՉՍՏՈՒԳՎԱԾ, needs the supervised trial

- that `-p --chrome` works and exposes these tool names and schemas;
- that a hook `"allow"` is honoured under `dontAsk` + `--permission-prompts none`, and that a hook failure ends in a denial there;
- the `tool_response` envelope for MCP tools in a hook; whether `tool_use_id` is the same string in Pre and Post;
- the result structure of `tabs_create_mcp`;
- whether a headless run starts with an empty tab group (if not, pre-existing tabs are merely visible and unusable, by design);
- whether the model completes a task inside the call budget under these sequencing rules (a read now costs: listing, read, listing; a tab costs: listing, create, listing);
- behaviour of the real `claude.exe` inside the job.

## Not done

No real adapter, no `claude -p` run, no subscription use, no timer, no autostart, no enable. The live report draft was neither changed nor approved. Nothing installed on the VPS or into `C:\Users\Admin\KRYUK24-Bro`. Nothing pushed.
