# Bro Chrome proxy: the restriction that does not depend on a hook

From Claude, 07.10.2026. Prepared and tested offline. **No model run was made for it.** Not yet used in any trial case.

HY: T2-ը ցույց տվեց, որ առանց hook-ի Claude Code-ը երկու Chrome գործիք թողնում ա աշխատել։ Hook-ը մենակ դարպաս լինել չի կարող։ Էս թղթապանակում միջնորդ շերտ ա. Claude-ը Chrome-ի գործիքներին հասնում ա միայն դրա միջով, ու եթե կանոնները չկան կամ gate-ը չի աշխատում, կանչը մերժվում ա մինչև Chrome-ին հասնելը։

## 1. What the official documentation says (fetched 07.10.2026)

| Question | Answer | Source, verbatim |
| --- | --- | --- |
| Can a hook's "allow" open a tool that a deny or ask rule closes? | No. Deny and ask rules win over the hook | "PreToolUse hook decisions don't bypass permission rules. Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns: a matching deny rule blocks the call, and a matching ask rule still prompts even when the hook returned `"allow"` or `"ask"`." — code.claude.com/docs/en/permissions, "Extend permissions with hooks" |
| When do hooks run? | Before the permission prompt | "When Claude Code makes a tool call, PreToolUse hooks run before the permission prompt" — same section |
| What does dontAsk let through? | Whatever needs no approval in Manual mode, plus allow rules, plus calls a PreToolUse hook approved | "If you set `dontAsk` mode, Claude Code auto-denies every tool call that would otherwise prompt you. Claude still runs actions that need no approval in Manual mode, such as file reads inside your working directories and read-only Bash commands, plus actions matching your `permissions.allow` rules and calls approved by a PreToolUse hook." — code.claude.com/docs/en/permission-modes, "Allow only pre-approved tools with dontAsk mode" |
| What does an ask rule do in dontAsk? | The call is denied | "Claude Code denies calls matching your explicit `ask` rules rather than prompting." — same section |
| A hook that times out | Does not block | "A timed-out `command`, `http`, or `mcp_tool` hook doesn't block the tool call. The call continues through the normal permission flow, so don't count on a stalled hook to act as a gate." — code.claude.com/docs/en/hooks |
| A hook that exits with a code other than 0 or 2 | Does not block | "Any other exit code doesn't block on its own for most hook events." — same page |
| A hook that cannot be started | Does not block | "A hook that can't start lands in the same non-blocking bucket. … For most hook events, the action proceeds." — same page |

Not documented, as far as these pages go: why `list_connected_browsers` and `tabs_context_mcp` need no approval; a list of Chrome tools that need none; a way to run the built-in Chrome tool server on its own. The first 100 000 characters of the hooks page were read, not the whole page.

## 2. Can the nine tools be closed reliably when the hook is absent?

Not with settings, in a way that the hook can open again:

- a **deny** or **ask** rule on a tool closes it also when the hook says allow (first row above), so the gate could never let a call through;
- **without** such a rule, a missing, crashing or hanging hook leaves the call to the normal permission flow (rows 5–7), and that flow let two tools run in T2 / attempt-01;
- which tools are exempt is not documented, so a rule set built on "these two are harmless" would rest on an observation of one version (2.1.289).

So the answer to the second question is no, and the third route applies: a mandatory layer in the path of the call.

## 3. The layer

    Claude Code  --stdio MCP-->  bro_chrome_proxy.py  --stdio MCP-->  claude.exe --claude-in-chrome-mcp  -->  Chrome

Claude Code is started **without `--chrome`**, with `--strict-mcp-config` and an `--mcp-config` that names only the proxy. The built-in Chrome server is then not part of the session; the nine tools exist only as `mcp__bro-chrome__<name>`, served by the proxy.

For every `tools/call` the proxy:

1. refuses any name outside the nine read-only tools, and any input that is not an object, without asking anybody;
2. builds a PreToolUse event and runs the unchanged gate (`bro_gate_hook.py --policy …`) on it. The call goes on only when the gate exits 0 **and** prints `permissionDecision: "allow"`;
3. writes the decision and the raw event to the audit log. If that write fails, the call is refused;
4. forwards the call upstream;
5. builds a PostToolUse event with the answer and runs the gate again. The answer is passed to Claude only when the gate exits 0, the gate's state file is readable and the run is not tainted. Otherwise Claude gets "BRO PROXY: result withheld".

Refused before anything is sent upstream: no policy file, policy not JSON, policy incomplete, gate file missing, gate crash, gate hang (timeout), gate silent, gate exits 0 without "allow", gate says allow but exits non-zero, audit log not writable, an error inside the proxy itself.

What this adds over a hook: a hook can only record an answer; the proxy still holds it and can withhold it.

## 4. What is verified, and how

| Claim | Evidence |
| --- | --- |
| The CLI serves its Chrome tools on stdio without a model | `claude.exe --claude-in-chrome-mcp` answered MCP `initialize` (serverInfo "Claude in Chrome" 1.0.0) and `tools/list` (22 tools, none with annotations). Found by probing; **not documented**, so it can change with a CLI update |
| The proxy offers exactly the nine tools | test, and live: `tools/list` through the proxy in front of the real server returned the nine |
| Without a policy nothing passes | 12 offline tests with a stand-in upstream whose own log shows what reached it; live: `list_connected_browsers` → "BRO PROXY: denied", audit "pre deny, gate exit 2, BRO GATE ERROR: policy" |
| With the trial policy the browser list comes through | live, 08:23 UTC, no model: one browser, `0184b121-276c-4128-a6c3-db3039b0ea5c`, `inUse: true`; audit "pre allow", "post recorded"; gate state not tainted; no process left behind |
| The gate is unchanged | `bro_adapter_preflight` hashes equal its SHA256SUMS |

`test_bro_chrome_proxy.py`: 12 tests, all OK (15 s), Windows, Python 3.12.10.

A side effect: the live check above reads the real browser list without a model run. That is the missing pre-run check of "exactly one connected browser".

## 5. Not verified, not done

- **No real Claude run has used the proxy.** Not known: whether Claude Code offers `mcp__bro-chrome__*` tools to the model in `dontAsk` mode, whether they need `permissions.allow` rules (expected from the documentation quoted above), and whether any of them is treated as needing no approval. With the proxy in the path, a call that Claude Code lets through still meets the gate.
- The trial harness (`bro_runtime_trial`) is not adapted: its cases, settings and evidence rules are written for hooks. With the proxy, the events come from the audit log, there is no hook `session_id` to compare with the stream, and the deny cases change meaning ("gate absent / crashes / hangs" become proxy situations, already covered offline here). That is the next package and needs your decisions first.
- The text of a page that redirects after loading can still reach Claude before the next tab check (the T7 limit). The proxy could hold a read result until that check; not built.
- Separate Chrome `--user-data-dir` for the trial browser: not prepared yet. It needs a new browser profile (extension installed, Claude signed in by Gev), and harness rules that look only at that Chrome's process tree.
- The proxy trusts the upstream command it is given. It starts exactly one child and makes no network connection itself.

## 6. Files

| File | Role |
| --- | --- |
| `bro_chrome_proxy.py` | the proxy |
| `fake_upstream.py` | stand-in for the Chrome tool server, for tests only |
| `test_bro_chrome_proxy.py` | 12 tests |

Example MCP config for a run (not used yet):

    {"mcpServers": {"bro-chrome": {"command": "<python.exe>", "args": ["<…>\\bro_chrome_proxy.py",
      "--policy", "<attempt>\\policy.json", "--gate-dir", "<…>\\bro_adapter_preflight", "--audit", "<attempt>\\events.jsonl",
      "--", "C:\\Users\\Admin\\.local\\bin\\claude.exe", "--claude-in-chrome-mcp"]}}}
