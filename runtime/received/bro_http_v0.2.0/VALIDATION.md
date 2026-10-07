# Validation v0.2.0 / Ստուգում

CONFIRMED locally on Linux, Python3.12: `python -m unittest discover -s work` => **102 tests, OK**, 23.812s. This overlays NEW code on actual runtime v0.8.1 plus exact v0.1.0/v0.1.1 bridge sources. **78 baseline +24 new tests**. Final tested files equal deliverable files.

ՀԱՍՏԱՏՎԱԾ տեղում՝ 102/102։ Windows/VPS-ում այս նոր տարբերակը չի փորձարկվել, տեղադրում չկա։ Օգտագործված հիմքը իրական փաթեթների կոդն է, ոչ ենթադրված implementation։

Coverage: 8 concurrent HTTP claims (one winner); wrong principal/run/revision; expiry; old attempt after reclaim; globally unique run; duplicate claim/observe/draft and altered-body conflict; auth and forbidden routes/verbs; cross-day and task-day fences; excluded local/BLOCKED tasks; report dependencies and REPORT_DRAFT-only restriction; preservation of an existing draft on sidecar startup; minimal queue fields; timestamp/type validation; actual synthetic subprocess environment does not inherit named/unknown credential variables; HTTP timeout injected twice with identical body; HTTPS-only origin/no redirect; durable client recovery after committed write/lost response runs adapter once and writes one observation; real adapter default disabled; missing DB fail-closed.

Separate synthetic snapshot/backup smoke: snapshot before/after adding Bro tables identical for every legacy table+views hash; SQLite backup `PRAGMA integrity_check` => ok; restored backup contains10 original synthetic tasks. All `.py` files compile.

Core provenance, exact SHA256:
- ops_work.py v0.1.1: `0c93a77a1e701352cef4ccfc68f3d836e47f357056599392fae1940d675d455d`
- test_bro_worker.py v0.1.1: `6cea7e9eec2810372e24448c9fcfb4ee6e8d424777e510e1a975995b891e031c`

NOT VERIFIED: actual HTTPS/Nginx authentication chain and inherited rules; owner credential isolation at edge; public port reachability; actual NTFS ACL; Windows execution; current VPS hashes/counts/digest/services/health; real Claude/Chrome execution; subscription allowance; browser permissions; Windows descendant cancellation. No timer or adapter is enabled. Nginx binary was unavailable here; example not nginx -t tested. TLS policy is code/unit-tested, not an actual remote handshake. HTTP timeout is deterministic transport injection, not a remote outage test.

ՉՍՏՈՒԳՎԱԾ կետերը Claude-ի տեղադրման ուղեցույցում հստակ ընդունման քայլեր ունեն։ Թեստերը չեն հաստատում իրական adapter-ի կապ կամ կենդանի բիզնեսի արդյունք։

For reproducible full regression, use the complete `KRYUK24_Operations_Runtime_v0.8.1.zip` (existing project file) as the dependency fixture, overlay bridge v0.1.0 then v0.1.1, then this package's new Python files in a separate folder. The historical runtime archive is deliberately not bundled because it contains old ops_views.py and unrelated site/customer workflow files. Test sources import real Operations; no fake Runtime substitutes were used.
