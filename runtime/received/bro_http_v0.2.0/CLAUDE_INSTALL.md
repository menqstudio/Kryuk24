# Bro HTTP bridge v0.2.0 — STAGING candidate / տեղադրման թեկնածու

## Scope / Սահմաններ

EN: Four worker routes on a dedicated loopback sidecar: GET `/bro/v1/queue`, POST `claim`, `observe`, `draft`. VPS owns SQLite. One random dedicated Basic credential is validated by BOTH Nginx's worker-only password file and the sidecar's SHA256 verifier. Existing operator gate stays intact with realm `KRYUK24 operator`; no IP gate is added. Worker identity is `BRO:<principal>:<unique run UUID>`, fenced by revision and active 600-second lease. Receipts and unique runs are committed atomically with business changes in two additive tables (`bro_receipts`, `bro_runs`). No plan, approve, ledger, media, messages or external action capability. Read only current Yerevan day, consistent with existing Operations planner. BLOCKED tasks are not retried through worker credentials. No schedule/timer is supplied.

HY: Չորս սահմանափակ ուղի, առանձին localhost ծառայություն, նույն VPS բազա։ Bro-ի credential-ը չի ավելացվում Գևի password file-ին։ Nginx-ը և API-ն ստուգում են նույն առանձին credential-ը։ Հին ծառայությունները, operator gate-ը և վահանակը մնում են իրենց տեղում։ Նոր երկու աղյուսակները պահում են հարցումների և փորձերի նույնականացումը։ Timer չկա, արտաքին կատարում չկա։

## Ground truth / Ընդունված վիճակ

User/Claude acceptance, NOT independently reverified here: `/opt/kryuk24`, STAGING; sending=false; Windows/VPS 78 tests; counts 20 orders /36 contact_interactions /10 ops_tasks /9 ops_observations; 8 DONE, AVITO BLOCKED, DAILY_REPORT READY_REVIEW; existing report digest prefix `3e0c111c`; installed `ops_views.py` prefix `1c145a4d8864223b`. Preserve the full current hashes, not merely prefixes. Light default and `kryuk-theme` must remain unchanged.

Դրանք ընդունված տվյալներ են՝ Գևի/Claude-ի զեկույցից։ Տեղադրողը նորից ստուգում է իրական VPS-ը։ Այս փաթեթում `ops_views.py`, `ops_work.py`, `secure_server.py`, հին ծառայությունների փոխարինումներ և DB չկա։

## 1. Inspect and preserve / Սկզբում ստուգել ու պահել

1. Read actual `/opt/kryuk24` instructions, installed service units (`systemctl cat kryuk-capture` and operations/backup units) and `nginx -T` PRIVATELY. Never paste secrets/config wholesale into chat. Determine actual DB path, interpreter, service user/group, TLS host and active owner htpasswd. Old examples are NOT deployed truth. Stop if the baseline differs materially; report the difference.
2. Extract this package into a separate staging directory. Verify all entries in `SHA256SUMS.txt`. Do not overlay the archive onto `/opt/kryuk24`.
3. Run existing 78 tests plus `test_bro_http` in a fresh COPY of the installed runtime with the NEW Python files overlaid. Tests create temporary SQLite files; do not pass live DB into tests. Run on Windows and VPS: `python -m unittest discover -v`. Record interpreter/version and counts. No tests from the historical bridge archives should overwrite installed files.
4. Before installation, run the supplied read-only `bro_snapshot.py` with actual DB/views paths and a NEW `--backup` path. Save its JSON as `before.json`; keep backup privately with owner-only permissions. It uses SQLite backup API including WAL. Verify backup integrity/restore on a separate path. No DB download is needed.
5. Confirm protected digest, statuses/counts, views hash, `/health`, existing timers and service state. Preserve Nginx and installed files separately. Do not claim live verification from a copied fixture.

HY: Սկզբում կարդալ իրական տեղադրման հրահանգները, ծառայություններն ու Nginx-ը։ Թեստերը՝ պատճենում, ոչ իրական բազայի վրա։ `before.json`-ը պահում է բոլոր հին աղյուսակների քանակն ու ամբողջ բովանդակության hash-ը՝ առանց հաճախորդների տվյալները արտածելու։ Բեքափը ստուգել առանձին պատճենում։

## 2. Dedicated credentials / Առանձին credential

Generate a random password locally in a trusted password manager (32+ random characters), unique to Bro. Do not use owner password. Do not put credentials in chat, command arguments, AI requests, logs or environment variables.

- On VPS, trusted interactive command: `python3 bro_provision.py server --output /etc/kryuk24/bro-server.json --username bro-win`. Paste the random password only into hidden getpass prompt. Restrict file to root + actual service group, e.g. mode 0640.
- Create a NEW worker-only Nginx password file interactively: `htpasswd -cB /etc/kryuk24/bro.htpasswd bro-win`. Enter the SAME random password; verify ownership/mode permits only root/Nginx group. NEVER use the owner htpasswd path or add this username to it. `-c` is for a NEW path only; preserve any existing file instead of truncating it.
- On Windows, in a private trusted-client folder: `python bro_provision.py client --output bro-client.json --username bro-win --origin https://ACTUAL_TLS_HOST`. Enter the same password privately. Restrict NTFS ACL to the trusted user + SYSTEM; remove inherited access before use. Windows chmod alone does not set adequate NTFS ACLs. Do not place this folder in the AI project/workspace, cloud sync or repository.
- The client validates certificate trust/hostname, rejects redirects and plain HTTP, ignores proxy environment config, and uses 10-second HTTP timeout with one identical retry. Use trusted OS certificate store; no insecure TLS flag exists.

HY: Նույն, պատահական ու առանձին գաղտնաբառը ստուգում են Nginx-ը և sidecar-ը։ Այն պահվում է միայն վստահելի client-ում։ AI-ին չի փոխանցվում credential, config-ի ուղի, authorization header կամ parent environment։ Իրական AI-ի filesystem access-ի սահմանափակումը դեռ ընդունված չէ, ուստի իրական adapter-ը անջատված է։

## 3. Add sidecar and Nginx route / Ավելացնել ծառայությունը

1. Install ONLY new `bro_api.py`, `bro_pull.py`, `bro_provision.py`, `bro_snapshot.py` and `test_bro_http.py` into approved locations. `bro_api.py` uses standard library and does NOT import/initialize Runtime or Operations; it refuses nonexistent DB/missing operations schema.
2. Adapt `deploy/kryuk-bro-api.service.example` to ACTUAL service user/group, interpreter and DB path. Install as a NEW service. Start manually for acceptance (`systemctl start kryuk-bro-api`), NOT enable. It binds only 127.0.0.1:8789; check for port conflict before starting. Startup only adds two Bro tables. Existing capture/backup/operations services need no restart.
3. Insert ONLY the supplied worker location inside existing HTTPS server, preserving all other rules. Keep separate htpasswd, explicit Authorization forwarding and realm. Do not use `auth_basic off`, `satisfy any` or owner credentials. Inspect inherited access/auth_request rules; resolve any stronger inherited restriction explicitly without removing owner protection. `nginx -t` MUST pass before reload. Reload Nginx; do not replace the full active config.
4. Run `bro_snapshot.py` again WITHOUT backup; compare with `before.json`. All old table hashes/counts and views hash must match. Verify original report full digest and review state unchanged. `/health` still STAGING/sending=false. Existing services/timers remain active as before. New tables excluded intentionally; no old table is excluded.

HY: Միայն նոր ծառայություն ու Nginx location։ Գործող ծառայությունների և վահանակի ֆայլերը չփոխարինել։ Հին աղյուսակների hash-երը սկզբում և վերջում պետք է նույնը լինեն։ Timer կամ autostart չմիացնել։

## 4. Acceptance / Ընդունում

Windows pull smoke: `python bro_pull.py --config PRIVATE_PATH/bro-client.json --queue-only`. No claim/AI execution occurs. Empty current-day queue means no plan for today; IDLE is not a connected adapter. Never create/reopen real tasks to manufacture success. The normal owner planner remains the only planner.

At actual HTTPS edge, using trusted tools that do not expose credentials:
- No password/wrong password => 401; correct Bro => queue 200.
- Bro on `/operator/work`, `/operator/work/report`, approve/plan routes, customer ledger and message routes => DENIED; owner access remains as before.
- Owner credential on worker routes => DENIED. Worker file must contain ONLY Bro username, owner file must NOT contain it.
- Disallowed worker paths/verbs/query strings => DENIED. Check `/bro/v1/../operator` and encoded traversal at Nginx edge too; normalization must never grant owner access.
- Loopback sidecar accepts only worker credential; port not publicly reachable. HTTPS chain, hostname and realm correct.
- Queue fields: structured task IDs/day/job/kind/status/revision + lease expiry boolean; daily job statuses only. No raw observations, customer data, credentials, free-text titles or existing report body.

Race, leases, fences, current-day scope and idempotency tests use synthetic temporary DB and real local HTTP handlers. Test two simultaneous claims => one winner; expired/foreign/old attempt rejects; repeat same mutation => no extra observation/event; conflicting reused request ID rejects; reused run rejects; report draft repeats once and stays READY_REVIEW. HTTP timeout is injected deterministically at transport boundary. Subprocess test executes a real synthetic child and verifies secret environment variables absent. These are NOT actual Claude/Chrome or Windows process-tree acceptance.

Կենդանի հերթում գործողություններ չանել․ ընդունման mutation-ները միայն սինթետիկ բազայում։ HTTPS gate-ը առանձին ստուգել իրական հասցեով։ Իրական 78 baseline թեստերի արդյունքները և նոր փաթեթի տեղային արդյունքները չխառնել։

## Client recovery / Կրկնակի ուղարկում և վերականգնում

Trusted `run_one()` implementation is available for a future accepted adapter; CLI enables queue-only. Test seam accepts an injected adapter, never executable configuration from HTTP/AI. Each run needs a UNIQUE private journal path. One process must own that journal; multi-process same-file coordination is not implemented. The journal stores task/run/revision/result, never credentials. Sensitive result output still requires private ACL/retention. Persist submission BEFORE HTTP write; on response loss retry identical request ID/body, without rerunning adapter. Completed journals return saved result; use a new journal for new work. Crash during adapter leaves `adapter_started` and refuses silent rerun; after lease expiry a new run/journal can reclaim. An abandoned claim's old result cannot write. Keep server receipts/runs; no automatic pruning supplied. A receipt replay after a successful mutation is an acknowledgement only, not another write. Cross-day retries reject, even if an earlier request succeeded; owner resolves uncertainty using VPS state.

Report API creates exact `REPORT_DRAFT`/KRYUK24/INTERNAL_REVIEW/empty assets draft, never other action types. Status metadata alone does not prove metrics: detailed unobserved data must remain UNKNOWN. There is no report-evidence endpoint in this scope.

## Rollback / Հետադարձ քայլ

Remove only added Nginx location (restore preserved config), nginx -t then reload; stop new sidecar. Keep additive tables/receipts to preserve audit/retry history. Do not restore an old whole DB over newer work or drop tables as a shortcut. Old service and UI files were not changed. Recheck old gate, health, timers and report digest.

## Still blocked / Դեռ չմիացնել

Real Claude/Chrome adapter, browser permissions, subscription allowance and Windows process-tree cleanup are NOT accepted. No timer, scheduled task, real AI command or external messaging is supplied/enabled. Child environment is an explicit allowlist, cwd isolated temporary folder, no shell, no inherited descriptors. Parent kill is not proof of descendant cleanup; subprocess access to same-user files is not an OS security boundary. A separately accepted process/filesystem/tool-permission design is required before real adapter use.

HY: Credential-ի environment փոխանցումը փակված է, բայց նույն OS user-ի ֆայլերին հասանելիությունը դրանով չի փակվում։ Հենց դրա համար իրական adapter-ը և ավտոմատ աշխատանքը դեռ չեն միացվում։

References: Nginx official Basic auth documentation https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html . Active VPS config remains authoritative; examples cannot prove installation.
