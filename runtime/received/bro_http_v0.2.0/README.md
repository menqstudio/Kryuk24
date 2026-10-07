# KRYUK24 Bro HTTP API + Windows pull client v0.2.0

Start with `CLAUDE_INSTALL.md`. STAGING candidate, not installed. New sidecar uses the existing real queue/schema and does not replace any existing runtime/operator/dashboard file. Actual accepted core dependency is runtime v0.8.1 + bridge v0.1.0 + v0.1.1 ordering patch. Python 3.10+ standard library.

Սկսել `CLAUDE_INSTALL.md`-ից։ Նոր API-ն իրական հերթի վրա է, Windows client-ը՝ HTTPS-ով։ Այս միջավայրում VPS կամ Windows տեղադրում չի կատարվել։ Իրական adapter-ը, timer-ը և հաղորդագրություններն անջատված են։

| File | Purpose / Նպատակ |
|---|---|
| bro_api.py | Restricted loopback worker HTTP API / սահմանափակ API |
| bro_pull.py | Trusted HTTPS client, durable per-run recovery; CLI queue-only / վստահելի client |
| bro_provision.py | Hidden interactive credential setup / credential-ի պատրաստում |
| bro_snapshot.py | Read-only before/after preservation hashes + optional SQLite backup / պահպանում |
| test_bro_http.py | Synthetic local HTTP/DB/client/subprocess tests / թեստեր |
| deploy/*.example | NEW sidecar and worker-only Nginx location examples / նոր ծառայության օրինակներ |
| VALIDATION.md | Actual test result and acceptance boundaries / ստուգման փաստեր |
| NEXT_CHAT.md | Concise handoff / հաջորդ չատի փոխանցում |
| reference_archives/*.zip | Exact previous bridge releases, reference ONLY; never bulk-overlay / նախորդ փաթեթներ |

No `ops_views.py` exists in this archive or the nested bridge archives. No DB, customer records, credential or real adapter config is distributed. Deployment code does not include replacements of `ops_work.py` or `secure_server.py`; historical v0.1.1 archive contains its original ops_work.py solely for code provenance.
