# Deterministic monitor v0.1.2 / Առանց AI-ի մոնիտոր v0.1.2

## EN

Roadmap item 13, phase 7: prepare deterministic health, backup, hosting balance and certificate checks. This is the offline evaluation engine, not a deployed monitor or a live collector. It has no AI, network calls, credentials, timer, external messages, mutations or new dependencies. Existing runtime and open PRs #12/#13 are untouched.

Every evaluation produces all four checks. Missing, stale, future or malformed observations are UNKNOWN. An ALERT has priority in the overall status, but all UNKNOWN rows remain in the result. OK means only that the supplied observations match the supplied policy; it does not authenticate their source. The source field is a provenance label, not proof. Only trusted collectors may supply real observations. No restored backup or health state has been verified by producing this package.

Input is strict schema-1 JSON with `observations`: optional `health`, `backup`, `hosting`, `certificate` entries, each exactly `source`, `observed_at`, `values`. Missing entries remain UNKNOWN. Timestamps must include a timezone; comparison uses UTC. Observation freshness is independent from the age of the last successful backup. A backup is OK only when it is recent and its trusted observation reports a verified restore; lack of restore verification remains UNKNOWN. Health compares mode and sending to explicit policy. Money uses integer kopecks, never floats; hosting whole days are an estimate, not a provider deadline. Certificates use exact time to expiry, including expired certificates.

Policy fields and value fields are shown in the SAMPLE JSON files. **The sample thresholds are proposals, not owner-approved production settings.** They must be reviewed before using real data. The fixed sample dates are intentional; running them on another date may give stale/future observations, not a fabricated live result. Do not update the date of old real evidence to make it fresh.

JSON input is bounded to 64 KiB per file, UTF-8; duplicate keys and nonfinite numbers are rejected. Invalid global input/policy produces UNKNOWN and exit 2; invalid individual observations produce UNKNOWN for their own check. Malformed values are not echoed. Empty observation files cannot make the result green.

```bash
python -m unittest discover -s runtime/deterministic_monitor -p 'test_*.py' -v
python runtime/deterministic_monitor/monitor.py --policy runtime/deterministic_monitor/policy.SAMPLE.json --observations runtime/deterministic_monitor/observations.SAMPLE.json
```

CLI uses current UTC; exit codes: 0 OK, 1 ALERT, 2 UNKNOWN/input rejected. ALERT results may also contain UNKNOWN checks. Keep all rows in any future display. The CLI prints JSON to stdout; it does not persist evidence. No success response should be inferred from merely starting it.

Verified here: Linux Python 3.12, 30 tests including actual subprocess CLI exit codes and Unicode filenames, threshold boundaries, stale/future/naive timestamps, replay determinism/no input mutations, missing data, invalid booleans/money/schema, backup/restore distinction, private extra fields, duplicate/nonfinite JSON and input size. Windows and repository CI have NOT been run here. No claim that the whole repository CI is green, especially with the separate Windows harness issue.

### Claude integration

Add this new folder in an independent PR on current main; no existing code files are replacements. MenQ author/committer. Add the unittest discovery command to Linux and Windows CI without skipping or weakening other checks. Record repo-only/not deployed in CURRENT_STATE in EN/HY. Read source ROADMAP item 13 again before integration. Run tests on Windows, then exact-head CI. No timer, alert channel, external API access or installation is authorised by this package.

Next integration work: trusted collectors for actual runtime health, backup + restore evidence, timestamped Beget readings and the real TLS certificate; supervised VPS checks; accepted thresholds; an approved alert channel; schedule only with Gev's separate approval. Failed collection must supply missing/unknown evidence, never reuse an old successful reading under a new timestamp. Restored-backup evidence needs a separate real rehearsal. Keep all credentials outside observations and policy files. This package does not close all of roadmap item 13 or phase 7.

## HY

Roadmap-ի 13-րդ կետի ստուգումների շարժիչն է՝ runtime health, backup, hosting-ի մնացորդ, վկայականի ժամկետ։ Առանց AI-ի և նոր կախվածությունների։ Իրական տվյալներ ինքնուրույն չի հավաքում, սերվերում տեղադրված չէ, timer կամ հաղորդագրություն չի ստեղծում։

Բացակայող, հնացած, ապագա ամսաթվով կամ սխալ տվյալը UNKNOWN է։ ALERT-ի կողքին UNKNOWN-ը պահպանվում է։ OK-ն միայն տրված տվյալների ու կանոնների համապատասխանությունն է, ոչ տվյալների իսկության հաստատում։ Իրական դիտարկումները պիտի գան վստահելի collector-ից։ Հին դիտարկման ամսաթիվը նորով փոխելով այն թարմ համարել չի կարելի։

Backup-ի թարմությունը և իրական restore-ի հաստատումը տարբեր են․ չստուգված restore-ը UNKNOWN է։ Գումարները կոպեկներով ամբողջ թվեր են, hosting-ի օրերը՝ գնահատական։ Health-ը ստուգում է նաև mode/sending-ը, certificate-ը՝ իրական վերջնաժամկետը։ SAMPLE շեմերը առաջարկ են, ոչ Գևի հաստատած արտադրական կանոններ։

Linux-ում 30 թեստն անցել է՝ ներառյալ իրական CLI subprocess-ը և հայերեն ֆայլանունները։ Windows-ն ու GitHub CI-ն այստեղ չստուգված են։ Claude-ը նոր առանձին PR-ով ինտեգրում է, երկու հարթակում թեստերը միացնում, փաստացի վիճակը գրում EN/HY։ Այլ ստուգումներ չհանել կամ չթուլացնել։ Ամբողջ repo-ի կանաչ լինելու խոստում չկա․ harness-ի խնդիրը առանձին է։

Հաջորդը իրական collector-ներն են, VPS-ի հսկվող ստուգումը, restore-ի փորձը, հաստատված շեմերն ու հաղորդման ալիքը։ Ժամանակացույցը՝ միայն Գևի առանձին հաստատմամբ։ Այս փաթեթը roadmap-ի ամբողջ կետը փակված չի հայտարարում։

Null health details are explicitly unavailable: known mode/sending violations or a failed connection remain ALERT while unknown_fields names missing details. If there is no known violation and a detail is missing, the result is UNKNOWN. See package REVIEW.md for the v0.1.2 review findings and regressions.

Additional input bounds: regular files only, maximum JSON nesting 64. A negative hosting balance is a known low-funds ALERT, with estimated remaining whole days clamped to zero.

HY: Հայտնի health խախտումը չի թաքնվում պակասող մանրամասների հետևում․ դրանք նշվում են unknown_fields-ում։ Բացասական մնացորդը ALERT է։ Մուտքը միայն սովորական ֆայլ է, JSON խորությունը՝ առավելագույնը 64։
