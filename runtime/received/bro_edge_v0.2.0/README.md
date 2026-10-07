# Bro v0.2.0 credential isolation acceptance / Credential-ի մեկուսացման ստուգում

This is a separate acceptance helper, NOT an API upgrade or adapter. No service, timer, approval or real task is enabled.

## Windows — Gev runs privately / Գևը գործարկում է անձամբ

Claude places ONLY bro_edge_check.py in C:\Users\Admin\KRYUK24-Bro, alongside the existing private bro-client.json. Do not open or share config. Verify the installed secure_server.py still parses JSON before operator POST dispatch; this helper sends deliberately INVALID JSON, never {} or a valid plan/approval. The v0.8.1 baseline does that; verify the installed source before running.

In a private native PowerShell terminal (not an AI tool session, recorded screen or transcript):

```powershell
cd C:\Users\Admin\KRYUK24-Bro
python bro_edge_check.py --config bro-client.json
```

Enter the EXISTING owner `gev` password at the hidden getpass prompt. Bro password is read inside the trusted script from private config. Neither is printed or saved. No AI subprocess runs. Share only the final JSON result. Do not pass passwords as arguments/environment variables and do not share terminal recordings or config files.

Սկզբում ստուգվում են երկու ճիշտ մուտքերը՝ Bro→queue200, gev→operator200։ Եթե դրանցից մեկը չի անցնում, բացասական թեստերը չեն հաշվվում որպես ապացույց։ Հետո սպասվում է credential-ների խաչաձև մերժում՝401։ Operator POST ուղիներին ուղարկվում է դիտավորյալ անվավեր JSON՝ առանց առաջադրանքի ID-ի կամ approval-ի։ Պատասխանների body-ները չեն կարդացվում և չեն արտածվում։

A403 on an operator POST is NOT accepted as credential isolation evidence: it can be an Origin rejection.404/429/redirect/transport errors also do not prove authentication isolation. Expected denied cross-credential requests are exactly401; correct Bro on disallowed worker route/query is403. A failure is NOT_ACCEPTED: report status/path only, inspect gate privately; do not loosen controls to make it pass. Probe uses HTTPS validation, no redirects, no environment proxies,10s timeout and no automatic POST retry.

## VPS — username membership / Username-ների կազմ

The trusted local script reads password files internally and emits only three booleans. It never displays hashes or lines. Resolve ACTUAL owner password-file path from current Nginx privately; do not assume it.

```sh
sudo python3 check_htpasswd_names.py --worker-file /etc/nginx/kryuk-bro.htpasswd --owner-file ACTUAL_OWNER_HTPASSWD
```

Expected: worker_exactly_one_bro_win=true, owner_excludes_bro_win=true, owner_contains_gev=true. No editing or replacement of password files occurs.

## Preservation / Պահպանում

After checks, repeat existing snapshot comparison, views hash and full report digest, health and service/timer status. bro_receipts and bro_runs must stay0; no valid queue mutation was sent. Keep sidecar active/disabled during acceptance; no enable, Bro timer or real adapter is authorized by this helper.

Local validation:4 unit tests PASS, testing the expected status matrix, positive-control failure, Origin403 not being auth proof, and invalid-JSON-only POST payload. Actual VPS/HTTPS/Windows execution NOT performed by GPT. Original bridge files are not changed.
