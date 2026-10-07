# Edge acceptance helper v0.2.1 / Ստուգիչ

Fixes v0.2.0's missing pacing and owner-positive-control coupling. No bridge API/runtime change. No timer or adapter.

Claude: preserve original helper, deploy new bro_edge_check.py into trusted Windows folder and run its8 unit tests separately. Verify installed secure_server.py still parses JSON before POST dispatch. Existing credentials/ACL unchanged.

Gev runs privately, no typing/pasting of any password:

```powershell
cd C:\Users\Admin\KRYUK24-Bro
python bro_edge_check.py --config bro-client.json --bro-only
```

Close operator dashboard/other probes and allow at least60 seconds after earlier probes before starting. The script waits3.1s before every request;14 requests take at least43.4s plus network time. Shared-IP concurrent requests can still cause429. A429 is inconclusive, not credential-isolation failure; rerun after the rate-limit window without weakening Nginx. No password prompt in --bro-only. Config contents stay inside trusted process; only status/path/check results are printed.

Expected: BRO_DIRECTION_PASS, scope BRO_ONLY, owner_to_worker_tested=false. Bro queue200 first;4 owner GETs and7 owner POSTs401;2 extra worker paths403. POST bodies are invalid JSON so they cannot dispatch valid mutations. Any403 on owner route is not auth-isolation evidence (could be Origin denial);404/429/transport failure are inconclusive. All response bodies discarded. Full matrix still supported for an independently available correct owner password; do NOT retry guessed file formats, read the owner password file, paste credentials or place them in AI tool environments.

Հայերեն՝ --bro-only-ը կատարում է14 ստուգում՝ առանց owner credential-ի։ Հաջողությունը հաստատում է միայն Bro→owner մեկուսացումը և Bro-ի scope-ը։ Այն չի հայտարարում owner→worker-ի ճիշտ credential փորձ։ Ընդհանուր միջակայքը3.1վ է՝ operator20r/m սահմանը հարգելու համար։

Membership proof already reported: worker file exactly bro-win, owner excludes bro-win and contains gev. Reverse identity denial can be assessed separately from routing+membership+installed sidecar username validation: request identity gev is absent from worker file, irrespective of its password. That is structural evidence, not an actual correct-owner-credential HTTP matrix. Do not rename structural evidence into executed tests.

For optional no-password browser confirmation: using Gev's already authenticated owner browser, GET operator/work and then GET bro/v1/queue via same-origin fetch with credentials:'include'. Basic-auth cache may NOT send owner Authorization across paths or may select another saved credential. Therefore a401 alone proves nothing; count the reverse check only if matching Nginx log explicitly shows user gev rejected on the worker path in this same request. Do not extract or log Authorization headers. If no gev identity was sent, leave the dynamic test UNVERIFIED; do not trigger password experiments.

After run: old table snapshot identical, bro_runs=0, bro_receipts=0, views hash6efc2235…, report READY_REVIEW revision8 digest3e0c111c…, health STAGING/sending=false, sidecar active/disabled. Credentials, htpasswd, Nginx limits and backend unchanged. No enable/timer/real adapter.

Local checks:8 unit tests PASS (original4 plus bro-only matrix, pacing callback, invalid Bro stop, CLI no-prompt). No VPS/Windows edge run performed by GPT. Membership helper unchanged from v0.2.0. Root/SSH credential incident does not supply an operator password: keep root and operator identities separate; do not use provider/root credentials here.
