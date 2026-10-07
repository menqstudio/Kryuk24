# v0.7.2 — UTF-8 diagnostics and pending form identity / նույն հայտի ID

## Confirmed vs unknown / հաստատված և անհայտ
Claude reported v0.7.1 VPS49+4+10+6 tests and realChrome calculator/booking wa/tg acceptance, no duplicateindependentCLICK, repeated/invalidforms stable. Treat duplicationfix as browseraccepted based on that report.
Windows real_markup failure cause remains UNKNOWN: only Nodeversion line supplied. Locally the old Pythonfixture reproducibly fails with PYTHONIOENCODING=cp1252; this is a demonstrated portability hazard, not proof of that specific Windowsfailure.

## Changes / փոփոխություն
html_dom_fixture.py now writes explicitUTF8bytes to stdout, independent of platformencoding. Node fixture launcher uses PythonUTF8mode/env, larger boundedbuffer and includes subprocesserror/status/signal/stderr in failures. Actualmarkup/source preserved.
Form drafts: ID reuse across page reload within SAME tab/sessionStorage, exact same formpayload/channel and mode/endpoint. Lifetime24hours from firstcreation; afterexpiry becomes anewrequest. Each form retains only its latestpendingidentity. Changing payload/channel creates a newidentity. A «Новая заявка» button deliberately resets identity while retaining visibleformvalues.
Only SHA256payloadfingerprint, requestID, initialcontactmetadata and timestamp are cached, NOT raw addresses/phone/message/formtext. SHA256 compared to Nodecryptooracle acrossUnicode and paddingboundarycases. Hash is identity aid, not encryption or authentication. Initial contactmetadata is reused on retry/reload so referrer/device changes do not break backendidempotency. Closing/replacingtab, blockedstorage, expiry, differentmode/endpoint or differentdata can create a newID. No crossvisitor/globaldedup, no restoration of typedformfields; refill samevalues if browserclearedthem.
WeakSet formownershipfix from0.7.1 remains.

## Apply / տեղադրել
Replace ONLY whatsapp-handoff.js, html_dom_fixture.py, test_real_markup_contacts.cjs, test_handoff_js.cjs. Add test_handoff_persistence.cjs and test_fixture_encoding.py. contact-clicks.js stays0.7.1 (samebytes). No DB/env/Nginx/serviceidentity changes, no backendrestart required for rereadJS. Keep IP/Basicprotection and STAGING. Source site/index.html staysunchanged.
Hard reload/close oldpreviewtabs. Backend49existingtests plus newfixtureencodingtest ->50 OK.

## Tests / թեստեր
python3 -m unittest discover -v ->50 OK
node test_handoff_js.cjs ->4 PASS
node test_contact_clicks_js.cjs ->10 PASS
node test_real_markup_contacts.cjs ->6 PASS
node test_handoff_persistence.cjs ->10persistence cases +11SHA256oracle cases PASS
PowerShell if python3 unavailable:
$env:KRYUK_TEST_PYTHON='python'
node test_real_markup_contacts.cjs *> real_markup_test.log
Get-Content real_markup_test.log -Raw
node test_handoff_persistence.cjs
Capture fullerror if Windows stillfails; do not infer its cause from lastline. Regression checks directly parse actualsite/index.html; listenerharness is not actualbrowser/fullapp.js.

## Real browser acceptance / զննարկիչ
On /operator/site/, use inventeddata and realUIclicks. Record baseline beforetests.
1.Calculatorwa: captureoneID -> reloadsameTAB -> restoreidenticalfieldvalues -> clickwa -> SAMEID, sameorder/contactcounts, noidempotency400. Referrer changes fromreload mustnotalter storedmetadata/payload.
2.Repeat forbookingvalidday/time with identicalvalues. PreviewID match.
3.«Новая заявка» then samevalues -> NEWID and exactly+1order/+1linkedcontact. Differentdestination alsoNEWID.
4.Headerdirectphone stillCLICKorder_idNULL; formhand-offs noindependentCLICK. Invalidbooking createsnone. No realmessenger/callopens inprotectedpreview.
5.Check desktop/mobilewidth usability ofnewbutton; truephone/externalmaproute remainseparateacceptance.
LocalLinux tested; actualWindows/VPS/browser0.7.2 remainpending untilClaude reports.
