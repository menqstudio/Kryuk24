# Armen mobile portal v0.1 / Արմենի հեռախոսային կաբինետ v0.1

## EN

Requested by Gev 08.10.2026: separate Armen login on the existing runtime host, easy phone photo uploads, and simple one-tap collection of needed business facts.

Target URL: `https://runtime.kryuk24.ru/operator/work/armen/`. Existing `/operator/work` stays Gev's dashboard. Read sources: current GitHub runtime/server/secure_server.py, ops_media.py, ops_views.py, MANIFEST.md and Nginx example. The installed dashboard is protected, so this package creates a separate scoped route/service and never patches ops_views.py or runtime/server's recorded snapshot. It does not replace the installed Nginx config; actual VPS config must be read and reconciled by Claude.

### Implemented

- Separate backend Basic login (`armen`), optional separate `gev` review credential. Username/role is determined by verified credential, never JSON body. Gev review account is read-only in this portal. Armen cannot call owner approval/payment/publication routes; those routes are not implemented and existing backend credentials remain separate.
- Password provisioning is interactive with getpass, salted PBKDF2-HMAC-SHA256 600,000 iterations; plaintext/password hash never embedded in HTML or output. Requires actual HTTPS reverse proxy; loopback test does not validate deployed HTTPS.
- Phone-first Russian UI: gallery multiple selection, camera capture, purpose selection, sequential uploads with individual failures and acknowledgement. Accepts JPEG/PNG/WebP up to 20 MiB/file, single-frame 40 MP maximum. HEIC/video unsupported with visible guidance. Data quota 1 GiB includes private files/orphans; no automatic deletion. Decoder verifies/loads images, bounded upload concurrency; originals preserved byte-for-byte, separate JPEG previews have no supplied EXIF metadata. Original GPS/plates are retained privately; NO masking/publication approval is implied.
- Five one-tap questions: availability now; inquiries today; completed trips today (0/1/2/3/4/5+ or unknown); current service area; main inquiry source. Date is server-selected Moscow date; unknown option on every question. Answer changes append history; network retry uses same key. These are ARMEN_REPORTED statements, not paid orders, verified completions, revenue or profit. No accounting/order row is created and no existing operator task is auto-completed.
- Separate SQLite and media store, outside all existing runtime data/code. Daily view and last 100 photo previews. Browser CSRF header + exact HTTPS Origin on writes; no cross-origin response grants. No iframe embedding, no cache, no external fonts/scripts/analytics. Password brute force: per-process shared failed-auth cap plus required Nginx per-IP rate limit. No persistent session/logout UI; Basic credentials handled by browser. Credential rotation requires portal restart; already-open pages then need reload for CSRF.

### Verification

8 local Linux tests PASS: correct/wrong login, owner route isolation, read-only review role, CSRF/origin rejection, exact answer replay/history, private original/preview/duplicate handling, full decode/corrupt format rejection, HTTP photo upload, typed question/unknown/date checks. app.js syntax checked by Node. Pillow 12.3.0 installed/tested. Windows, actual mobile browsers, visual browser rendering, Nginx integration and VPS deploy NOT verified here. Playwright package was present but Chromium executable absent, so no screenshot or claimed browser visual check is included. No real account or server password has been created by GPT; tests use clearly SAMPLE credentials only.

```bash
python -m pip install -r runtime/armen_portal/requirements.txt
python -m unittest discover -s runtime/armen_portal -v
node --check runtime/armen_portal/app.js
```

### Claude: prepare PR, verify, then supervised install for the requested portal

1. Read actual current VPS Nginx/systemd/path/permissions; check 8790 is free, inspect installed owner/Bro authentication boundaries. Compare current config to supplied fragment; never replace the server block or operator dashboard. Review existing service/backup policy. Existing source-manifest files remain unchanged. GitHub PR for runtime/armen_portal; MenQ author=committer; Linux/Windows CI installs pinned Pillow and runs tests.
2. Create separate `kryuk-armen` nologin system user, without kryuk-db or owner groups. Code `/opt/kryuk24-armen` root-owned/read-only to service. Isolated venv, install dependencies. Data `/var/lib/kryuk24-armen` user/group kryuk-armen, mode 0700. Credential directory `/etc/kryuk24-armen` root:kryuk-armen 0750.
3. Provision actual Armen password interactively using `provision.py --credentials /etc/kryuk24-armen/users.json --user armen`. Gev must choose/enter it through a trusted terminal, or receive it through a separately agreed private handoff; never print/store plaintext in chat, PR, shell argv or logs. Optional `--user gev` for owner review. Set users.json root:kryuk-armen 0640 after provisioning. Password minimum 16 characters; easy-to-type passphrase preferred. Do not reuse Gev's owner-dashboard credentials automatically. No real password is included in this archive.
4. Install supplied systemd unit after path/user checks. Start once; do NOT enable autostart/timers unless separately authorised. Bind loopback only. Install scoped Nginx fragment; `nginx -t` then reload if valid. Preserve a private before-config backup. Do not change owner/Bro/capture paths. Check portal unauthenticated gets login challenge; Armen valid login works; Armen credentials still denied by old `/operator/work`, `/operator/work/approve`, `/bro/v1/`; port 8790 unreachable externally. Test bad Origin/CSRF on portal writes. Credentialed checks must keep values out of logs/output.
5. Open real mobile width and actual phone browser if available: verify initial login, 390 px no horizontal overflow, one-tap saved feedback, duplicate retry, camera/gallery upload and Russian characters. Test actual current iPhone/Android format handling; HEIC is explicitly unsupported, so do not claim universal phone support. Use sample images and label/delete only known test data by an explicit controlled cleanup step, not real uploads. If real operator testing is needed, record it distinctly.
6. Record install state, actual tests, URL and limitations. Add new private data/photos to backup plan before relying on collection; no unapproved backup timer is created. Verify a restore into isolated temp paths. Gev's dashboard UI is preserved; a navigation link, if wanted, needs a targeted separately reviewed edit of protected ops_views.py rather than overwrite.

Rollback: stop new portal service, remove ONLY new scoped Nginx locations and verify/reload; old runtime untouched. Keep private uploaded data and backups; do not delete them. Read data/photos permissions and reconcile any credential/dependency changes. No LIVE acquisition, publishing, advertising or money action is added.

Known limitations: no email/SMS/OTP recovery, no audit export endpoint, no configurable question editor, no offline queue/background upload, no HEIC/video, no automatic masking/publishing, no automatic connection to existing MediaStore or orders. Photo purpose is user reporting, not proof of vehicle ownership/rights. Same image bytes uploaded again are deduplicated; changing purpose on reupload does not overwrite earlier metadata. Originals not directly downloadable through this portal; only private thumbnails are served. A filesystem orphan after DB failure can exist and consumes quota; cleanup is manual. UI usability still needs Claude's actual browser/phone verification.

## HY

Գևի պահանջը՝ Արմենի առանձին մուտք, հեռախոսից հեշտ նկարների վերբեռնում և պարզ մեկ-հպումով հարցեր։

Նոր հասցեն նույն runtime-ի տակ է՝ `/operator/work/armen/`։ Գևի `/operator/work` վահանակը չի փոխարինվում, դրա գաղտնաբառը Արմենին չի տրվում։ Առանձին backend-ը թույլ է տալիս միայն նկարներ և իր պատասխանները. հաստատում/վճարում/հրապարակում չի անում։ Գևի առանձին review մուտքը միայն կարդալու է։

Հինգ հարց՝ հիմա կարող է՞ դուրս գալ, այսօր դիմումներ եղե՞լ են, քանի՞ տեղափոխում է ավարտել (0–4, 5+ կամ չգիտի), որտեղ է հիմա սպասարկում, հիմնականում որտեղի՞ց են դիմումները։ Բոլորը Արմենի հաղորդած տվյալներ են, ոչ հաստատված պատվերներ կամ շահույթ։ Ամսաթիվը Մոսկվայով է, պատասխանների փոփոխությունները պահվում են պատմությամբ։

Կան gallery/camera կոճակներ, մի քանի նկար հերթով վերբեռնում, արդյունքի հաղորդագրություն։ JPEG/PNG/WebP, մինչև 20 ՄԲ, ոչ HEIC/video։ Օրիգինալները պահպանվում են մասնավոր, preview-ն առանձին է։ Համարանիշների/GPS-ի փակումը կամ հրապարակման թույլտվությունը այս վերբեռնումը չի կատարում։

8 Linux թեստերն անցել են, JS syntax-ն էլ ստուգված է։ Իրական հեռախոսի, browser visual-ի, Windows-ի, Nginx/VPS տեղադրման ստուգում դեռ չկա։ GPT-ն սերվերի մուտք չունի և Արմենի իրական հաշիվ/գաղտնաբառ չի ստեղծել. փաթեթը պատրաստ է Քլոդի համար։

Քլոդը առանձին PR-ով ինտեգրում է, CI-ով ստուգում, իրական Nginx-ը նախ կարդում, առանձին համակարգային օգտատեր/բազա/նկարների պանակ ստեղծում։ Գաղտնաբառը մուտքագրվում է trusted terminal-ում, ոչ չատում կամ կոդի մեջ։ Պահպանվում են Գևի/Bro-ի մուտքի սահմանները։ Մեկ հսկվող start է, autostart/timer առանձին թույլտվությամբ։ Հետո փաստացի հեռախոսային ստուգում և հաստատված հասցե։ Գործող runtime-ի բազային, ops_views.py-ին ու հաստատված report-ին փոփոխություն չկա։ Նոր տվյալների backup/restore-ն պետք է ստուգել մինչև իրական աշխատանքի վրա հենվելը։
