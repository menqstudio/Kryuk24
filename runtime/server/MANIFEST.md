# Server code as installed (`/opt/kryuk24`)

Fetched read-only from the STAGING server on 07.10.2026, 13:08 UTC, after the API reader install. Nothing on the server was changed by the fetch.
This folder is a record of what runs there, so that the runtime can be rebuilt from the repository. **Do not edit files here**; a change goes through a package with a manifest, as the API reader did.

## What is not here, on purpose

| Left out | Why |
|---|---|
| the database and everything in `/var/lib/kryuk24` | data, not code |
| `/etc/kryuk24*` (operator password file, Bro credential, collector credentials) | secrets; they are created on the server by the provisioning scripts |
| the server's `GOOGLE_SHEET.json` | holds an account-specific sheet id and link. **The `GOOGLE_SHEET.json` in this folder is a test fixture** with made-up values, so that `sheets_plan.py` and its test run from a checkout. It is the one file here that differs from the server, and it must never be copied there |
| 4 files `*.before-api-read` | saved copies made by `install_patch.py`; they equal `runtime/api_reader/fixtures/server_base/` |
| `reference/` (19 files) | copies of project documents that GPT's release carried along; the project's own documents are the source |

`site/` **is** here although it equals the repository's `site/` byte for byte (59 files): the server's own tests read it from this place.

## Where each file comes from

Compared on 07.10.2026 with GPT's release manifest found on the server (`RELEASE_SHA256.txt`, `SOURCE_SHA256.txt`), with GPT's v0.8.1 package, with the Bro bridge packages in `runtime/received/` and with `runtime/api_reader/`.

| Group | Files | Evidence |
|---|---|---|
| Runtime release v0.8.x as GPT shipped it | all files not named below | sha256 equals the release manifest; `ops_backup.py` and `test_ops.py` equal the v0.8.1 package |
| Operator page `ops_views.py` | 1 | Gev's design, installed 07.10.2026; sha256 `f5f6e9d8…`; **protected: never overwritten, never part of a patch** |
| Bro queue bridge and HTTP bridge | `bro_provision.py`, `bro_pull.py`, `bro_snapshot.py`, `test_bro_worker.py` and their install notes | equal to the packages in `runtime/received/` |
| Patched by the API reader install | `ops_work.py`, `bro_api.py`, `bro_worker.py`, `test_bro_http.py` | sha256 equals what `install_patch.py` produces from the pre-patch files |
| Added by the API reader install | `bro_api_reader.py`, `ops_api.py`, `reader_provision.py` | sha256 equals `runtime/api_reader/` |

## Tests

`python3 -m unittest discover -p "test_*.py"` here, on Linux (the server's Python 3.14.4, in a temporary folder, 07.10.2026): 102 pass. On Windows several suites fail for platform reasons (console encoding, file locking); the server code is meant for Linux.
The `*.cjs` and `test-*.js` files are Node tests from GPT's release; they were not run in this stage.

## Files (sha256, bytes, path)

```
ebc5cd54d4873b638179862d5cfadbeec1780cc753bd2453c0ba290ea0b7e320    11483  bro_api.py
503e5d60e653126814498ec026969a54481c34af47631956cf2417bf55d59f67    21871  bro_api_reader.py
4f3b5305aaf24b22b8c5c0d1e37854e66686cd358048380427a023a73efe6ad4     1134  bro_provision.py
e2a5fd1984849682f49c7ddbe81fa2d3193f9e7cabe6c4c162c4702840b1396b     8030  bro_pull.py
863781491ef8046b50520643cfef25bb7bbd0f9a862665de700b1744dc7bddc9     1330  bro_snapshot.py
e5c123894874d9b17136c52cedc2be2498fb2c4113f27a9d03e6324af9ce4e91     7375  bro_worker.py
9e3cfc89b4b2912dbe06dd0dd62f98e410fa94fc8aca5844a1d239e89e1661a0     3664  contact-clicks.js
410c31f7a1cb58087ab85f861a95e55c18c66495b646838e3cb6abc6553f9200     2761  contact_metrics.py
5f47afdb311a672686376f955e01c1cd6ee196eabe1ef306b97d83f2820e17ab     5116  demo_server.py
ec84e1c93530e2b8417ae090269dd217f2b57657017aa87fef171267b9a29e23      941  deploy/backup_daily.py
4d14a6a089510176dc29e9889c1d89f8b2347d42b942cc4cd6b6342e72787465      232  deploy/capture.env.example
4c5c43e38b443ad2b6bf1a0165ceb060355bc4b89ada2ee0c27af16993c69d12     3305  deploy/FINISH_ON_VPS.md
4b5c649267a3850994acf2385c1931f1644429fffa5f209d8ff7ae26cfa9f803      335  deploy/kryuk-backup.service
cb36b0e50153bc7fada0655e2e953bd8f13e3c529a2563acfe44c03c98f56a6a      139  deploy/kryuk-backup.timer
9688f1eac02660e079e511009f41a91205959dd9cf13229050b2044237b9ba95      483  deploy/kryuk-capture.service
6e621f32686db8c86662cd545d993da665076444ff6400654b784b053bac168b      489  deploy/kryuk-operations.service
d9825e6bc24fe64d5134768549559c5b281587cc989ca7076f2837463303e223      217  deploy/kryuk-operations.timer
e750b05db5ecdb2a314e0d2a2def29589c64aea6b7915eb2c25e47a41768cbf0     1700  deploy/make_staging_password.py
92de86caafa524cab532e80dad02cbe04952eacb6e22d71b42ddd872741c54e6     1659  deploy/nginx-https.conf.example
8b9a04da76a0ce7b76f58e7c905e379f63a1cb9a017af5610f085e00817c5558     3251  deploy/STAGING.md
67f3fe4fcd241fd5e0655dccd7214ce666b269180b1ef97b8319361d80701da3     1867  deploy/V061_PATCH.md
39ebe664f0a47339be8149eda79442e3ffec7174f41ab4f790f42cceb3d26d2d      991  deploy/V062_PATCH.md
8915b04e914c38f3bfcce915964e6ccd19c82599e59ff583d815e924e4a37413     6113  deploy/V070_PATCH.md
be2899cf1bb92228e6c01b05eafbe8a8ee7c734a7880d14dba50932c24d076e5     3713  deploy/V071_PATCH.md
6f5a698fa7dd2cb2cb7516f84a3f9d578433b49959a4c9179eb68f24f2d0e8d2     3943  deploy/V072_PATCH.md
be13b75626d47430eb1d0227ba5f93f5dd5db5d7acdc281bb7ac147542f2a571     4631  deploy/V081_PATCH.md
8db52cdfdd2493c80fa2cd00e9fa1fda0a5476caa9d49ea3260368b0a0f2c0d2     1319  handoff-preview.html
63ce29665060f3af76bb6a347ed78891d77be23a8f18f561c8599f58b0eaf90b     1127  html_dom_fixture.py
a9377add862bb7800eecd5d29817a536baffa1aa565a9ad4eed9af50ef77f871     4492  kryuk_operator.py
66112b057ce3c9a756896a38c85e2ffb705fa0afe1c8453527e66b8fddb8e901     3964  NEXT_HANDOFF.md
ac8ed806b5663964608443cbd21bd2e187134f6fd68e5d110bc7cf070c21a891     7171  operations/BRO_INSTALL.md
21a3d514fe4d968030bfde7f7c0eb9be5269548f62d68fd4317dae6d8a0f3f87     2871  operations/BRO_V011_PATCH.md
8c3ae77cef715b45bc52f7c315b8086eca9a8a6f66c797a1e3ddf0a8a1827298    13330  operations/BRO_V020_INSTALL.md
54b3af7f1db9700bfa70cc6632d5a384e3acce8634203159bfe039ba71bfa664     1954  operations/CLAUDE_DAILY_REHEARSAL.md
1c55deeca578d52448593a8e07744e0b2c57bfc0c6c71a9511b1e95247e2bfe5     1016  operations/CONTACT_BUTTON_INVENTORY.json
87567549954c3ac4e234e6a3eff3dab3d58200fc2e72e4218ba7e6df743d6c39     5327  operations/DAILY_OPERATIONS.md
771c92003eab3f2b34f3370e25004c8c9cb7223009deb7202263db5d788acc31     7229  operations/MASTER_ROADMAP.md
75dc4da9c639c00b43ed59e4ed2ae743400d36330b461569676215b117beb0ca     3127  operations/STAGING_WITH_DYNAMIC_IP.md
97ea0cd8aba99776dd62dbe103146ba1649dade9f8875553f1f35b77902daa0c     8333  operations/V080_HANDOFF.md
f194e425fe12c3725b04ed1c4bd0a78a661e0ba2b35af75944bbacc6fb093469     7082  ops_api.py
21739d62a1747c0d85f2930659c20a645be126aba49488eeeca495fc6a6dcea5     1987  ops_backup.py
e05b5b6a4a6cf517ca9531b19f011379f13daf50d40932a69f030d5e23bce3f0     3640  ops_cli.py
b00a415b7d31f0d8130539ff72fbd615fe9f19431afd4300b909052152937278     1535  ops_daily.py
7f7b2556486ffe08d82dad6033dbcf1e7d52d0bf833326ef8f9497bbb7672ffa     2766  ops_local.py
5ca3e4dea8b0b11040a4a85ff0985c4c881ac80348abfaf7c8058cca2dbbda4c     4427  ops_media.py
f5f6e9d8a8d87ae3dadb7a9ccc2a990040e455a5d06394c9d0a810c0a5cf8752    65185  ops_views.py
d1e6a2dfa653f40ddbf886c170e8c0d143b1750ad59c1703c647313f7e8818d6    10092  ops_work.py
157f7df23feee71a881cdfb88f71d0dcbf037904d59f321f6b4411702c8a164c     3051  reader_provision.py
be1af05e27fec218900e28c18b86a536dba877b3a0b4c9e307bba90cc780349d    11004  README.md
ca7ae2664d11d004c77fc4140c6dec7c0b033b542a17d81e9531bb46f4a7149a     1316  recovery.py
20a0bc0a9a2955ff6e59ee9c89a049968666b33d6324e0db648d5c33f824515e    13468  RELEASE_SHA256.txt
6814523e5f3b376de05c7742b3014ecce0074cfe7163c0759ccf9e1c02fa007b     3854  report_html.py
bf938c7022eace87b6347dd9c6648cd4dc45c1210ccda73bb4af3dc8cbe5d1f0    15896  runtime.py
06ed93fc884bd9e2e579af7405737a439a197c85100acf9eb9e1d37785cb909a    10986  secure_server.py
57d6f1b3753693b9b2f832a888a3e99de0b62c048cb7140727956e32b1fdd616     2670  sheets_plan.py
397032d042c1fa41bbe99b490ec85d5c53cd479161c02b5a93f677120b3a196a     1380  site/.htaccess
a15265fda715c76738f83667b8f8e12e290366c0c9878a112509ec08ef170724     1983  site/404.html
33e5ed6aa3237a5685db82c04711b25e331228b44ece68e77a22f8266d598db6    32249  site/app.js
c8519b9a4893add266da79041ed4201fa1d066230bbf2a1edd6034c0152b6ad1     7342  site/apple-touch-icon-180.png
a957881b215ac1760189b8e82dbd81ffc0719f6d6bb000a26a9f675a625959b2    10283  site/assets/favicon.svg
17d048ca05cb1218af3c0d6dcdf882989e6d1cc5dcb598ea50eaf54850ff7229    22032  site/assets/fonts/golos-400-cyrillic.woff2
9a69d0aa4734c4022224c002a3d944a702e0204972a49d892789f5668b922c2a    37916  site/assets/fonts/golos-400-latin.woff2
17d048ca05cb1218af3c0d6dcdf882989e6d1cc5dcb598ea50eaf54850ff7229    22032  site/assets/fonts/golos-500-cyrillic.woff2
9a69d0aa4734c4022224c002a3d944a702e0204972a49d892789f5668b922c2a    37916  site/assets/fonts/golos-500-latin.woff2
17d048ca05cb1218af3c0d6dcdf882989e6d1cc5dcb598ea50eaf54850ff7229    22032  site/assets/fonts/golos-700-cyrillic.woff2
9a69d0aa4734c4022224c002a3d944a702e0204972a49d892789f5668b922c2a    37916  site/assets/fonts/golos-700-latin.woff2
7b9ef131039e058b622d4da5cbb6d2e783526d137cbf74738f8984c25c2d3fbf    12144  site/assets/fonts/robotocond-700-cyrillic.woff2
ab74f0c2d7ec37e44e017b9586675dd00c519591207dc3bbc8e003c5628dc9b7    21128  site/assets/fonts/robotocond-700-latin.woff2
d7843d21337308a2785acf10b4e52b1473b39dacf0d9866936ccf6d8ed39b6ce     2308  site/assets/fonts.css
ea6e0d38ed5e18c9415eb866f0d63c6dcc38da763034f964e2d8b8050f415316   207459  site/assets/img/evakuator-24-chasa-moskva-oblozhka.jpg
964a8d8a1bd8766db873975a699c39b6530b7711959cfd20f35072a9e68b2dad   264344  site/assets/img/hero-bg-desktop.jpg
1536b52ab5330c3891525df20d7adb5fd324e3116eb6b0d3c8df26191a6bee58   161120  site/assets/img/hero-bg-mobile.jpg
a4da0f22698a837b6f35f3a05c59fda76ff58a8c70d30056ae64a2cce337dcae    96297  site/assets/img/rabota-01-mercedes-cla.jpg
e9aeb293d3dcb6784ca33a9e06b7e4a6a5a9673a3496e692bfd2a5edc34fc836    90624  site/assets/img/rabota-02-iz-kyuveta.jpg
7f37d4a770fd7b691999acd034b6f2af82a5221dd4a42407dc42c1bf91f1f8c6    70925  site/assets/img/rabota-03-bmw-x6.jpg
202ebcbcc0799a1e6220bca655fb8db9ce809f6a0b439c8d4bedd1582bca290a   112450  site/assets/img/rabota-04-mini-pogruzchik.jpg
2cd2ebce116db43e44fb77167fd2fa26fc4b16cf2845e6798e2e6da587c4ead4    97593  site/assets/img/rabota-05-audi-a8.jpg
4e778488f2119256b387884a0bc242104d2ece0c4323b12b0ccd6a1b573856ac   117318  site/assets/img/rabota-06-posle-dtp.jpg
95c21e04f071717680e2a74105215a25f2f5f42d300ff97f9684607056bafc0f    94627  site/assets/img/rabota-07-mikroavtobus.jpg
a445df5dab37d6fcb39b72dcabf442576f7f44b11bbdf795b5bc4c00f3f96972    79586  site/assets/img/rabota-08-rolls-royce.jpg
fc1a6dc9bcc371911783488769fe7040560f47b44b7c96cbe7d4178b30924c14   101658  site/assets/img/rabota-10-volkswagen-golf.jpg
73bc6e5330101df055d263409a71afb88246ba4ab7942d8df70de37db26ef677    41765  site/assets/img/rabota-11-manipulyator.jpg
b9162d7656e6d9cb78da07f668551f583ea0262cbf1c899c4a6fe53cc5693d92    45556  site/assets/img/rabota-12-posle-dtp-pogruzka.jpg
a033a33c32f9ed4c09a315cdab233c7e2246623fd6e8a2c88776eba15b5de76a   104484  site/assets/img/rabota-13-mikroavtobus-osen.jpg
5f4ada5553bac626a7dde712835fc786933ae9023da2c5836d9a70ddbeb7f33d    82016  site/assets/img/rabota-14-manipulyator-posle-dtp.jpg
620b279544620200dd768acc9fd2f6eb0f518f68ca1286c911a7a5a449845226    84987  site/assets/img/rabota-15-mini-pogruzchik-s-kovshom.jpg
6dbfb05ff5781340d86d2637dfceb0b659549917fa0e7cddbaa73cceaa812588    78516  site/assets/img/rabota-16-vilochnyy-pogruzchik.jpg
aad8ebaf8d87ae85ce1b3c0ee5c54e14e94b73477ae3b46b936985e3c58aceb4    79275  site/assets/img/rabota-17-pogruzka-po-apparelyam.jpg
85ad6d7205e52674864a6263a07255f1e006475950d8cee061fcb3cef27b4278    39922  site/assets/img/rabota-18-pogruzchik-na-platformu.jpg
ef24bb8d0b9e21a5a42675c38ec26de125e24e5ab8193876cbb4ebc8dd2f4495   102779  site/assets/img/rabota-19-miniven-kia.jpg
d57a13eb8bf0b17c2d00b9445904d9312fa2904651f028c7d7f5bc4d67645a11    20243  site/assets/logo-dark.png
052f342936553070f03d7358ba97005db3a540f255b288e1840a8ff86a444f22    31480  site/assets/mark-orange.svg
78a02a7cdc7cd8b5e883305186ca449403126d2769e9ac133d55914290184ff5     2045  site/assets/pages.css
f4c444a900e9fa4568388c0236674aea760db62371ad08c864c11a914b333504    22039  site/evakuator-balashikha/index.html
4dd0d58713e1e236ea3d6d678a8d45e85752ec9c37c541ffbba0535205fa3236    22205  site/evakuator-domodedovo/index.html
d439f157555097ddd8b421c0fd6e2d44db2ba06c66c3a09ac1b6667cfeec3019    21893  site/evakuator-khimki/index.html
07c4c5610d8573895ad01eca2607bdff016afe5892284dda27939068c78aad9c    22067  site/evakuator-lyubertsy/index.html
10c37722bdf1e27c11d60a9e0f192c654784f979bbe06bfda2c5454e814520ae    22196  site/evakuator-podolsk/index.html
512f718b70c0d0a121d4ab778e3e2505504b1fb26a1ba3f6cff83eed65be0dc5      510  site/favicon-16.png
07229421be4f8ea18602fc60e23b2782b498a07ccd499e15a36ff264b1887490     1215  site/favicon-32.png
e87d0e1d76247cf92c976ce17a5c594ade974c910c879fec14efc9e913e8b426     2110  site/favicon-48.png
70556a43cdec6325c5c3d95b88efe33bad10d1b3bbed97d771f6b8a291d8424e     4982  site/favicon-96.png
e4ce3a32d7262fc7450eae1f46eb87f4c91ad664b08ca72f3128e18de8c99dc3     3889  site/favicon.ico
5f1ac586adbda5697b090abfbec2830e3ac18ce89f3780c631bd6dbf652788ab       53  site/google60aaad671c02b3da.html
498dbe4d12f4102cdef9932fb4737a176dbc8973f0e2c7124b081b27b41236a4     7123  site/icon-192.png
af98b633ec22afc47a48aa6a0cc80e9a1f8f84b0f468f6a4c33b8efe411fd4a9    34294  site/icon-512.png
5c6438c77203f52d2a5f6c95321d962d911c170da2645f6d24e8a2e49dc5afef    53788  site/index.html
f74d4abfd5ff39142d80f9d5f75716a774889f631b031654c600804c8f4cf499    21350  site/manipulyator/index.html
d91cde23b582b3b24d180392d87fa15e236ebe44a1ea028e0407d86b9006bbe6    21475  site/perevozka-spetstekhniki/index.html
308d54cacb8dfb0c660fc6c9d8b9a675838c1a89a0ccfef93b314a5d5db714ee     2771  site/README.md
60d76e5df4451669261740f1efca53e8c1f9e104593f25015ab1262e6c6aa274       86  site/robots.txt
7b651abb8dfad4b34b77c6a8c6347899e59d9cf5e6b9c078642d76db0fc4b62a      470  site/site.webmanifest
102c96f2083b8b963e101190f01e67893732be566342c9130586e998112ad59a     1044  site/sitemap.xml
8c876f640761221391745aef37c686dc7219ef81b15728af5d05422b28636d7b    55181  site/styles.css
336f7a9576c11d923cc3a964e33ca623e7b16cfda9145c488d7eb96f5cee3171     5894  SOURCE_SHA256.txt
4490eed7d4ef14f6cea920d72cdfad50fc54dcdbcfa9022ab3b804cbb6468c5d     3223  staging-form.html
d574b929ca98e252f0c22ed2e8a90108b4e61ddb21459671d3cbf2aa3b3d4918     2427  staging_site.py
0cc7a70fa57f244ae570e9bdda10a4ad48b0e98ed040a413e048dc3ca5238548     2537  test-intake.js
d331362cb81cccdeabd4df20ef3ef6e17f926d75f012b64c584ee8874f42bff7     8192  test-orders.html
19277af5c892f72f40600bd6f5f269379d8e9b20ddadb2a3475baa08c908eefd     2823  test_adapter.py
60d08729512e459cc8d551f42e56f424ff38161fe5969767b8d322ac312125cb     9829  test_bro_http.py
6cea7e9eec2810372e24448c9fcfb4ee6e8d424777e510e1a975995b891e031c     5419  test_bro_worker.py
26a6ca14064fb769c3030248bc1940c809f72a33b73cbdc15053cfc6131f1b16     3541  test_contact_clicks_js.cjs
33ab6113fb84cd1863a51308ab80e2b2df79bf970f3e23b8459ef09fe424ca5b     3932  test_contact_metrics.py
425598d815ce4836b6762e962f2c5a515f0a29a6dc87ff6a6462202215ea92f1      571  test_fixture_encoding.py
d92112ddd192a1a8cfda0df163de9e89dd93efc5147d645f06211b135e47490b     2037  test_handoff.py
539fbbc5d8534edb1d8f84fa7cf069f53938b7ce88a3f946c292f599e60b32cc     2807  test_handoff_js.cjs
4dc2ce907803f3be3afc735d74857f5b529f52ff199b5897e8031c46800b521f     4926  test_handoff_persistence.cjs
d00a9684c536f7d1660bfd65f87efc8716e616960a33351fdcef301f3c740292     1910  test_notifications.py
015e7b748784269913470d8a79c881cf0c46bc9ff8d5ac97326ef725a32766f2     9955  test_ops.py
d1b54bd2b857034b23a6b92f228a5a3a35f13ce694a5bd4dbbfb3f4edb4cf10b     6156  test_real_markup_contacts.cjs
a5dda449fc4dd56c4c768cad10c90017fce7495a0f7b3c29bda2c2e725d42a14     1473  test_recovery_report.py
fa3d2caaefa948d9d341897340665f01634c7f67aa8568ee36733227df858d04     2838  test_runtime.py
834c6b1993bf587d2501b8bd13949189256c9bc0374b6beb9b91be823a81589e     6801  test_secure_server.py
4c8d2ad0f746a102b9e1f426484a124b2c1171df06b896203a9cd4cebef98b0f     1405  test_sheets_plan.py
a87d28425d658e79b62655a0ba1c81ae3288a469423cc54d9d31cf480efbe982      766  VALIDATION.txt
8d865e37007bd531ad3d6de15245596e64b3917caceed0899816715fa046144a     1128  VALIDATION_V080.md
cada550a710a4d0b0135c5f335a69db6ac1ca2ca955c41782cf8b94d10fb1ac0     1557  VALIDATION_V081.md
90b0938e03f50ab4be4d4ea6bdddcb248a4888c0ef059f5fac02a2518683058a     7150  whatsapp-handoff.js
```
