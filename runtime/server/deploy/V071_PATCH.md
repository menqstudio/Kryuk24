# v0.7.1 — form contact ownership / ձևի սեղմման մեկ գրանցում

## Root cause / պատճառ
v0.7.0 relied on an event flag set by the target handoff listener, checked from a document-capture queueMicrotask. Native event callbacks can be separated by a microtask checkpoint, so the independent CLICK could be emitted before target handler sets that flag. Prior mocks used an already-marked event and did not model this boundary.
Reference:https://html.spec.whatwg.org/multipage/webappapis.html#clean-up-after-running-script
The real source-markup harness reproduces unwanted independent requests on0.7.0 and passes afterfix. Actual browser0.7.1 still must be verified; harness does not run all app.js or simulate a fullbrowser.

## Fix / ուղղում
whatsapp-handoff.js registers each exact managed WhatsApp/Telegram anchor in window.KRYUK_FORM_CONTACTS (WeakSet) when its listener is installed. contact-clicks.js checks ownership before queuing/sending an independent click. The event flag remains secondary compatibility guard. Form-linked metadata still goes atomically with /capture. No setTimeout, waiting for server, orderschema change or suppression of genuine unmanaged direct links. Phone link inside a form is not owned by the handoffhandler and remains a directcontact.

## Install / տեղադրել
Update only contact-clicks.js and whatsapp-handoff.js from this version. Add html_dom_fixture.py and test_real_markup_contacts.cjs for regression checks. Preserve actual source site/index.html; test parser reads it as input. If applying the fullzip instead, preserve data/env/currentkryuk-rununits/currentNginx and IPallowlist. No restart needed solely for JS files (server reads files perrequest); an ordinary service restart is permissible aftertests, not a live-mode switch. Hard reload/close old previewtabs so old scripts do not remain.
No database/environment/Nginx changes are needed for this patch. Existing TEST data retained; measure new testdeltas from freshbaseline.

## Tests / թեստեր
python3 -m unittest discover -v ->49 OK
node test_handoff_js.cjs ->4 PASS
node test_contact_clicks_js.cjs ->10 PASS
node test_real_markup_contacts.cjs ->6 PASS
On Windows parser command defaults to python3; if unavailable, PowerShell:
$env:KRYUK_TEST_PYTHON='python'
node test_real_markup_contacts.cjs
New harness parses actual site/index.html into DOMnodes and retains actuala/svg/formancestry/attributes. It explicitly checkpoints between document capture and target callbacks. Covers CALCULATOR/PREBOOKING x wa/tg, invalidbooking and capturefailure. It is a listener harness, not actualChrome.

## Browser acceptance / զննարկչային փորձ
Keep STAGING and currentIP/Basicprotection. Hard reload https://runtime.kryuk24.ru/operator/site/.
For CALCULATORwa, CALCULATORtg, PREBOOKINGwa and PREBOOKINGtg: click via actual browser UI (not JS element.click(), whose callstack may hide the checkpoint). Fill only fictitiousdata; booking day/time must be valid.
Each successful firstclick: orders+1, contact_interactions+1, new contact row id=K24requestID and order_id=sameID, position=form and correctchannel. There must be ZERO independent CLICK rows for that action. PreviewID mustmatch.
Repeated sameform/channel in sameopenpage: neither orders nor interactions grows. Invalidbooking: no order/contact. Genuine header/hero/footer/sticky links keep recording asdirect CLICK withorder_idNULL. Use newdestination/case or freshtab to distinguish newtestcases.
No real tel:/wa.me/t.me opens from stagingwrapper. Externalgeocoding/maps remain blocked by stagingCSP, realphone still requires separateverification. FormID persistence acrossreload remains a separategap.
