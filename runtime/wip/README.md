# Work in progress: not installed, not accepted for use

Three packages for letting a model read cabinets through Chrome under a restriction that does not depend on a hook.
**None of this runs anywhere.** The tests here prove the logic of the tools against stand-ins, not the behaviour of a real model.

| Folder | What | State on 07.10.2026 |
|---|---|---|
| `adapter_preflight/` | the gate (`bro_gate_hook.py`), the Windows job runner (`win_job.py`, explicit environment, whole process tree), tool schemas | tests pass (gate 50, job 31); used by the two packages below |
| `chrome_proxy/` | proxy between Claude Code and the Chrome tools; refuses a call when the policy or the gate is missing | 12 tests with a stand-in upstream; one live check without a model; **never run with a real model** |
| `trial/` | trial harness v5.3: cases T1 to T11 against fake pages | self-test 68 pass; T1 accepted by GPT (attempt 4); T2 run once and BLOCKED: two Chrome tools worked without a hook; T3 and later not started |

Waiting for: GPT's decisions on the proxy package v5.3 (accept the proxy as the restriction layer, the shape of the trials with it, Windows or Debian for the first run). No new model run without Gev's word. Windows only: the job runner and the harness use Windows APIs; a Linux variant does not exist.

CI runs all four suites on Windows. The trial harness self-test was out of CI for one merge (pull request #1), because 3 of its 68 tests failed on GitHub's hosted runner while passing on the development machine. The cause was a race in `trial/fixture_server.py`: the page server sent the answer first and wrote its access-log row after, so the harness, having received the answer to its own marker request, could read the log before the row was there, find its marker missing, and call the check INCONCLUSIVE (which blocks the case). Which test failed changed from run to run. A diagnostic run showed every marker request answered in under 0.02 s. The server now writes the row before the answer leaves. The effect was fail-closed: it could turn a PASS into INCONCLUSIVE, never the other way. It may also have touched real trial runs; the recorded T1 and T2 attempts were not re-examined for it.

`chrome_proxy/` and `trial/` find the gate at `../adapter_preflight`.
