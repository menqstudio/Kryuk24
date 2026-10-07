# v0.6.1 — closed HTTPS staging / փակ HTTPS փորձ
This adds an authenticated synthetic form at /operator/staging. No live site edits and no outbound messenger opening. Existing Nginx /operator prefix already proxies these routes. Preserve the existing IP allowlist and Basic Auth. No DNS or env changes.

Apply only: secure_server.py, staging-form.html, test_secure_server.py. Other files remain compatible. Code root-owned/read-only; keep current kryuk-run service identity. Do not copy or replace /var/lib/kryuk24 or /etc/kryuk24.
Run python3 -m unittest discover -v (37 OK), node test_handoff_js.cjs (4 PASS), restart kryuk-capture.service, inspect active status. Open https://runtime.kryuk24.ru/operator/staging from allowed IP; Basic username gev, existing password. No credentials in chat.

Expected: synthetic form opens protected preview, POST /capture 201 test=true. ID in preview and journal identical. Same fields/channel twice => one new order, two creation events total. Changing destination => another order. No WhatsApp/Telegram window, no messages sent. These synthetic integration controls do not verify actual live-site design or original calculator/prebooking behavior. Full-site staging UI remains a separate acceptance step before live attachment.

ORDER_RECEIVED and WHATSAPP_HANDOFF_REQUESTED are creation events; the latter means intent only, including Telegram/preview, NOT successful delivery. Legacy name preserved for compatibility. Inspect event kinds for the specific ID, not only global count.
Backup output restore_test=NOT_PERFORMED means backup command did not itself test recovery. Separate recovery.py + comparing restored records is independent recovery evidence; do not rewrite backup JSON as proof.
Local Linux Python3.12: 37/37 + 4 mocked JS scenarios passed. VPS/Windows v0.6.1 and browser execution not yet verified.
