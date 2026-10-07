# Monitor v0.1.1 — self-review / Ինքնաստուգում

Review scope: all files of the offline engine package (code, tests, sample contract/policy and EN/HY integration instructions). This is the author's self-review, not an independent reviewer or production acceptance. No existing repository code or CI check was modified.

Three findings were reproduced on v0.1 before changing the code:

1. A 5000-digit JSON integer caused the CLI to terminate with a traceback instead of a structured UNKNOWN result. The parser now bounds integer literals before conversion and normalizes parse failures. A real subprocess regression verifies exit 2, UNKNOWN JSON, empty stderr. It does not rely on Python's configurable integer-string limit.
2. JSON `1e999` was parsed as infinity even though named NaN/Infinity constants were rejected. The parser now rejects overflowed numeric exponents too. Tests cover both signs and other invalid JSON cases.
3. Fresh `reachable=false` with unavailable mode/sending fields returned UNKNOWN, hiding a known outage. It now gives ALERT/unreachable. Null details are allowed in this case only; a reachable service with missing details remains UNKNOWN, and a reachable service with unexpected mode/sending remains ALERT.

The full 25-test suite passes on Linux Python 3.12. Tests also traverse malformed values for every observation value field, preserve unknown rows beside alerts, exercise replay determinism and actual CLI exit codes/Unicode paths, and retain the original strict-input and boundary tests. No skipped tests or relaxed CI gates.

Checks inspected in this review: time-zone normalization, future/stale evidence, backup observation versus backup success time, restore-unverified handling, integer money arithmetic, certificate expiry boundaries, malformed-input privacy, global versus per-check invalidity, input-size/JSON parser limits, CLI outputs and lack of external effects. The engine contains no persistent/concurrent state, so no database recovery or locking claim is made. Repeating the same input and evaluation time gives the same result.

Open integration limits: real collection/authentication of evidence, binding restore proof to the actual backup procedure, real TLS chain/hostname checks, Windows CI, VPS integration, approved thresholds, persistence and alert channel. `OK` is conditional on truthful trusted inputs and does not prove these integrations. Sample data is never a live reading. No installed monitor, timer or accepted phase completion is claimed.

Claude: use this v0.1.1 ZIP instead of the earlier v0.1 ZIP. If v0.1 was already integrated, replace only this new module's files after checking for intervening edits; preserve other PR work. Run the 25 tests on Windows and Linux, then exact-head repository CI. Keep the package's limits in CURRENT_STATE. No deployment or schedule is requested here.

HY: Ամբողջ այս փաթեթի ինքնաստուգումն ավարտված է՝ երեք վերարտադրված սխալը ուղղված է, 25 թեստն անցնում է Linux-ում։ Սա հեղինակի review-ն է, ոչ անկախ ընդունում։ Իրական collector-ները, Windows/CI-ն, VPS-ը, restore-ի իրական ապացույցն ու հաղորդման ալիքը դեռ բաց են։ Հին v0.1-ի փոխարեն օգտագործել v0.1.1-ը։ Ոչ մի թեստ չի անջատվել, արտադրական պատրաստության պնդում չկա։


## Follow-up audit/fix loop — v0.1.2

A second pass found two additional operational semantics defects and two resource-boundary gaps:

- Reachable health with mode unavailable but sending known to be unexpectedly enabled was UNKNOWN. Known violations now remain ALERT; unavailable fields are listed separately. A healthy verdict still requires every required field. Contradictory/invalid typed data is not treated as healthy.
- Negative balance was classified as invalid rather than a known low-funds condition. Signed bounded integer balances now give ALERT below threshold; estimated whole days cannot be negative. Float/bool money remains invalid.
- A FIFO input could block the old regular open. The reader now uses a nonblocking descriptor where supported and checks the opened file's type; directories/devices/FIFOs are rejected. A subprocess test ensures prompt UNKNOWN instead of a hang (FIFO on POSIX, directory on Windows).
- Nesting relied on interpreter recursion limits. A separate lexical depth bound of 64 now precedes JSON parsing; quoted/escaped brackets do not count. The limit was verified against a 2000-container input.

Final validation: 30/30 tests on Linux Python 3.12, including a second run with integer string conversion limits disabled; 156 additional document/policy/observation mutations produced only a structured result or ContractError, no unexpected exceptions. Re-reviewed full engine and documentation after these edits. No remaining known defect was found within this offline engine scope in this pass. This is not a guarantee of zero bugs, an independent review or a Windows/VPS acceptance result.

Use v0.1.2 instead of v0.1 and v0.1.1. Tests/checks were not removed or skipped; new regression tests and bounds were added. The previous 25-test result above is the historical v0.1.1 result; the current suite has 30 tests.

HY: Երկրորդ audit→fix շրջանում հայտնի sending խախտման կորուստն ու բացասական balance-ի սխալ դասակարգումը ուղղվեցին, ֆայլի տեսակի և JSON խորության պաշտպանություններ ավելացվեցին։ Վերջնական 30 թեստն անցնում է, 156 հավելյալ սխալ մուտքային տարբերակ էլ ստուգված է։ Ամբողջ այս offline scope-ի հերթական անցումն ավարտված է․ Windows/VPS/իրական collector-ների ընդունումը բաց է։ Օգտագործել v0.1.2-ը, հին փաթեթների փոխարեն։
