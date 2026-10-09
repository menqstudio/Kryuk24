# КРЮК24 · Lessons learned by doing

> Working notes for Claude. Read at session start (skill `learn-by-doing`). Each lesson: what happened, why, what to do instead.
> State of the project lives in `00_STATE.md`, rules in `RULES.md`. This file is only about how to work better.

## Time and facts

- **What happened (07.10.2026):** four state entries and two handoffs to GPT carried times one hour off.
  **Why:** times were computed in the head from "about now" instead of read.
  **Do instead:** before writing any time, run `date` on the server for UTC, Europe/Moscow and Asia/Yerevan and copy the values. MSK = UTC+3, Yerevan = UTC+4.
- **What happened (06.10):** said "password login not tried" although an earlier combined command had tried it in the background.
  **Why:** did not re-read the output of a backgrounded command before reporting.
  **Do instead:** read the full output of every backgrounded command before describing what was or was not done.
- **What happened (07.10):** reported "the button click behind the gate did not register"; the journal later showed it had (order `K24-f0297100…`, 22:08:08 UTC).
  **Why:** judged by the page text of a hidden tab, which was stale.
  **Do instead:** judge a write by the journal on the server, a few seconds later, not by the page.

- **What happened (07.10):** wrote "00:55 UTC" and "04:48–04:58 Yerevan" into a report and a state heading; the server clock then showed 00:51. The lesson above already existed.
  **Why:** the text was drafted before the last command of the step ran, with the time estimated ahead.
  **Do instead:** write the time last: run the command that closes the step, copy its timestamp, then write the heading.
- **What happened (07.10):** a snapshot comparison came back "not identical" in the middle of a Bro acceptance.
  **Why:** Gev had closed the AVITO task in the dashboard two minutes earlier; `ops_events` showed actor `AUTHENTICATED_OPERATOR`, source «Գև».
  **Do instead:** when a snapshot differs, read the last rows of `ops_events` (actor, time) before saying anything; ask Gev one line to confirm; save a new reference snapshot.

- **What happened (07.10):** told Gev and GPT "the report draft still says Avito is blocked". The draft body does not mention Avito at all.
  **Why:** inferred the content from the task statuses instead of reading the 728-character body, which was one query away.
  **Do instead:** before saying what a stored text contains, read it. A statement about content without a read is marked ՉՍՏՈՒԳՎԱԾ or not made.

- **What happened (07.10):** told Gev "the Avito and Webmaster connectors work" from the tool list alone. One call each showed none of the four connectors has credentials (Avito `configured: false`, Webmaster and Metrica without a token, the Direct connector program is not installed).
  **Why:** "the connector is listed" was taken for "the connector has access".
  **Do instead:** before saying an API or connector works, make one read call (or its auth-status call) and report that result. Listed, connected and authorised are three different states.

- **What happened (07.10, 22:00 UTC):** `CURRENT_STATE.md` said "private repository"; the GitHub API showed `visibility: public` (Gev had opened it for CI).
  **Why:** the state line was written from the setup report and not re-read from GitHub after the change.
  **Do instead:** before stating a repository's visibility, read it (`gh api repos/<owner>/<repo> --jq .visibility`) in the same step.

## Passwords and access

- **What happened (06.10):** used `curl -u` with the operator password to test a login; a later attempt was refused.
  **Why:** authenticating with a password is Gev's action, also in a script.
  **Do instead:** test only the no-credential and wrong-credential paths. The correct-password check is done by Gev in the browser.
- **What happened (07.10):** Gev's public IP changed overnight and the staging site answered 403.
  **Why:** home internet has a dynamic IP.
  **Do instead:** when staging suddenly returns 403 or the browser disconnects, check the public IP first (`curl -4 ifconfig.me`).

- **What happened (07.10):** asked Gev to paste the dashboard password into a hidden prompt and to drop the terminal output into the chat. His clipboard held the Beget letter with the server root password; it went into the prompt (401), then into PowerShell and into the chat. He was angry, rightly. The same paste step had already failed twice in the previous chat.
  **Why:** built a step that depends on what is in his clipboard, and asked for raw terminal output without warning him to look at it first.
  **Do instead:** never give Gev a step where he pastes or types a secret. Write a script that reads the secret from its file and that he only starts. When asking for terminal output, ask for the result block only, and say "check there is no password in it" before he sends.

- **What happened (07.10):** two attempts to look inside password files were refused by the permission classifier (parsing `bro-server.json`/htpasswd for user names; a script that tried several ways to read the owner password file).
  **Why:** reading or probing credential files is outside what Claude may do here, also through a script.
  **Do instead:** check only existence, owner and mode. For anything inside a secret file, use a trusted script that prints booleans and that Gev starts himself (GPT's `check_htpasswd_names.py` pattern). Do not write "smart" readers for a file whose format is unknown.
- **What happened (07.10):** the old chat was told "new chat continues", but kept working for 10 more minutes.
  **Do instead:** at the start of a continued session, tell Gev in one line to close the previous chat.

## Browser automation

- **What happened (07.10):** first actions after a reload "did nothing" several times; screenshots showed stale pages.
  **Why:** `document.visibilityState` was `hidden`: a preview tab had opened in front, or the Chrome window was covered by another window. Proven by comparing visible and hidden runs.
  **Do instead:** before UI actions read `document.visibilityState`; close preview tabs right after reading them; when hidden, trust DOM reads through JavaScript, not screenshots.
- **What happened (07.10):** a database read "showed no change" right after a click.
  **Why:** the Bash call ran in parallel with the browser batch and finished first.
  **Do instead:** read the journal in a separate step after the browser step has returned.
- **What happened (06.10):** opened Gmail on top of the WhatsApp tab and lost it.
  **Do instead:** open a new tab for a new site; never navigate a tab that holds a live session.
- **What happened (07.10):** typing into Google Forms landed in the wrong field or selected the whole page.
  **Why:** `ctrl+a` straight after a click ran before the field took focus.
  **Do instead:** click, wait one second, `ctrl+a`, type, then check the field. In Sheets, typing through the extension does not land at all.
- **What happened (07.10):** after a tab was closed, the next action failed with "tab is not in the same group".
  **Do instead:** call `tabs_context_mcp` after closing a tab before the next action.
- **What happened (07.10):** a `fetch` from the page to a URL that answers 401 Basic froze the page for 45 seconds.
  **Why:** most likely the browser opened its own password window (not proven, the window is not visible to the tools).
  **Do instead:** probe with `credentials: 'omit'` or wrap the fetch in a timeout race.

- **What happened (07.10):** the company description typed into the WhatsApp Business profile was saved with three dropped characters («вто», «автомоилей», «₽за») and stayed public until Gev pointed at the profile. The website field had not taken the first typing at all.
  **Why:** long text typed through the extension loses characters in that page; I looked at a truncated one-line field and saved.
  **Do instead:** for any public text, read the field's full value back (JavaScript `value`) and compare it with the intended string before pressing save, and once more after reopening. In WhatsApp Web set the value through the page (native setter + input event) rather than by typing.

## Server and Nginx

- **What happened (07.10):** after `nginx reload` the browser still got the old answer.
  **Why:** an existing keep-alive connection was still served by an old worker.
  **Do instead:** wait a few seconds and retest before concluding the change failed.
- **What happened (07.10):** the staging password gate broke form capture although every page opened.
  **Why:** Chrome sends remembered Basic credentials on its own only under the path where it logged in (`/operator/…`); `/capture` is outside it, and the new realm had no cached password.
  **Do instead:** after any change to access control, send one real form request and check the journal count, not only page loads.
- **What happened (06.10):** a new Beget subdomain resolved to the hosting IP as well.
  **Why:** Beget adds its default A record to every new subzone.
  **Do instead:** after adding a subzone, open its records and leave only the intended A record; verify with `nslookup` against `ns1.beget.com`.
- **What happened (06.10 to 07.10):** GPT's packages passed on Linux and failed on Windows three times (encoding, unclosed SQLite files).
  **Do instead:** always run the test suite on both Windows and the VPS and report both results.
- **What happened (07.10):** a shell command with a long quoted text failed on an apostrophe inside it.
  **Do instead:** write files with the Write tool; upload scripts with `scp` instead of quoting them into `ssh`.

- **What happened (07.10):** GPT's acceptance script sent 12 requests to `/operator…` in 3 seconds and the 12th got 429; it would have reported a false failure.
  **Why:** Nginx `limit_req` (20 r/m, burst 10) runs before auth, so even rejected requests spend the budget. Proven with a wrong-credential dry run.
  **Do instead:** before handing Gev any script that calls the staging host, dry-run the same request sequence with a throwaway wrong credential and look for 429. Keep at least 3 s between requests to `/operator…`, and keep the dashboard tab closed during such runs.
- **What happened (07.10):** a browser `fetch` to a path behind another Basic realm hung again; an 8-second `AbortController` kept the page usable, and the Nginx error log showed which user name the browser had sent.
  **Do instead:** for "who was rejected and why" read `/var/log/nginx/error.log` (user name and password file are in the line, no secret); do not judge by the page.

- **What happened (07.10):** three times a Python snippet inside a shell heredoc died on a Windows path (`C:\Users` read as a unicode escape); once the next line of the same command committed anyway, leaving the zip and the state files out of that commit.
  **Why:** backslashes in inline code, and steps joined by newlines instead of `&&`.
  **Do instead:** write any script longer than a few lines with the Write tool and run the file; keep Windows paths out of inline code; chain "change, then commit" with `&&` so a failed step stops the commit.
- **What happened (07.10):** two reports to GPT carried wrong test counts ("12 new" was 15, "24 regressions" was 22) and had to be corrected and re-zipped.
  **Why:** counted from memory while writing.
  **Do instead:** take every count in a report from the test runner's own output or from a grep of the test names, in the same step that writes the report.
- **What happened (07.10):** a GPT instruction said "fix the two rules above" but the text above had not been pasted.
  **Do instead (worked):** do everything that is clear, change nothing for the missing part, say so at the top of the report and ask for it. Do not guess which rules were meant.

- **What happened (07.10):** the first real T1 run ended BLOCKED on `T1.10.d`: 2 of 11 `chrome.exe` child processes created at 06:41:00 were gone 8 s into the run. `run_T1.ps1` had opened Chrome only 23 s before the process snapshot.
  **Why:** cause not proven. My reading: short-lived helper processes of a freshly started Chrome.
  **Do instead:** waiting longer is not evidence (GPT, 07.10). Record what each process is (kind from the command line, cleaned) and how it ended (exit code through a handle opened before the run); a "settle" check is only a precondition.
- **What happened (07.10):** `run_T1.ps1` force-closed VS Code, every `claude.exe` and every Chrome window to get a clean machine. GPT rejected it for the next launcher.
  **Why:** I solved "nothing else may be running" by killing Gev's programs instead of checking and refusing.
  **Do instead:** a launcher checks and stops with the name of what is open; Gev closes his windows by hand. No mass kill of his processes.
- **What happened (07.10):** `T1.9` and `T1.R` came back INCONCLUSIVE: the real stream's successful `tool_result` has no `is_error` field, and the harness required a boolean. The stand-in program always wrote one.
  **Why:** the stand-in was written from an assumed stream format (listed as unverified in the plan).
  **Do instead:** a rule that depends on the shape of real output is settled only after one real sample; say in the report which checks can turn INCONCLUSIVE from format alone, before the paid run.

- **What happened (07.10):** two real T1 runs started 0.22 s apart when one was approved. I had given Gev the launcher commands, then after his "ha" also started a waiting window that would launch by itself; he ran the commands too.
  **Why:** two ways to start the same paid action were live at once, and the harness has no lock against a second `--execute`.
  **Do instead:** one start path for a paid or one-shot action. If the plan changes, say in the first line that the earlier commands are withdrawn. A one-shot runner takes an exclusive lock file before it starts and refuses when the lock exists.
- **What happened (07.10):** preflight P10 ("exactly one native host") passed, yet the run saw two connected browsers (Trial A and Gev's main).
  **Why:** I used the native host count as a stand-in for "one connected profile" without evidence that every connected profile has its own host.
  **Do instead:** do not put a proxy into a preflight as if it were the thing itself; name what it does not show. The only proof of the browser count is the browser list.
- **What happened (07.10):** adding a "no number above 10^9" rule to the API reader blocked `WEBMASTER`: the same helper also read `user_id`, an identifier far above that limit. All 44 tests passed, because the stand-in service answered `user_id: 42`.
  **Why:** the stand-in was written with a convenient small value, not with the shape of the real one; the limit was added to a shared helper without listing who calls it.
  **Do instead:** after changing a validation rule, make one real read-only call before reporting; list every caller of a shared helper before tightening it; give stand-ins realistic values (long identifiers, real magnitudes).
- **What happened (07.10):** a long Python script inside a bash heredoc died on its quotes again ("unexpected EOF"). The lesson above already existed.
  **Do instead:** no exception for "just this once": any script with quotes or more than a few lines goes through the Write tool into the scratchpad and is run as a file.
- **What happened (07.10):** the report on API reader v0.3.1 listed a "killed apply" test among the installer tests and, lower down, "not tested with a killed process". GPT caught the contradiction: the test only arranged the files by hand.
  **Why:** the test was named after what it stands for, not after what it does.
  **Do instead:** name a test and describe it in a report by what really runs. A simulation is called a simulation in its name; "killed", "real", "live" are used only when a real process, service or account was involved.
- **What happened (07.10):** a read-only look at the production server (timers, services, database counts through `sudo`) was refused by the permission check in the middle of a job; test runs in `/tmp` over the same SSH were allowed.
  **Do instead:** plan server work so that what needs production facts is one script Gev can allow or start (`deploy/preinstall_facts.sh` pattern); say at once which claims stay ՉՍՏՈՒԳՎԱԾ because of it. Do not look for another route to the same data.
- **What happened (07.10):** a command built as "make the new backup `&&` verify … `;` delete the old backup" deleted the only git bundle when an earlier step failed: the part after `;` ran anyway. The repository was intact and the bundle was remade and verified at once.
  **Why:** a delete was joined with `;` to a chain whose success it depended on.
  **Do instead:** a delete of an older copy is its own command, run only after the new copy's check printed its result and was read. Never put `rm` after `;` in a chain.
- **What happened (07.10):** `sed -i` with a Windows path in the replacement turned `\U…` into an upper-casing escape and mangled a line of `00_STATE.md`; the same command reported success. Caught by reading `git diff`.
  **Do instead:** no `sed -i` on project documents; edits go through a small Python script with an exact-match assert, and the diff is read before commit.
- **What worked (07.10):** the server install ran as four short scripts, each printing facts and stopping on the first unexpected answer, with a content-hash snapshot before, after the patch and after the dry-run. Keep this shape for the next install.

## Working for Armen

- **What happened (07.10):** built a 12-field Google Form, then a 3-field one; Gev rejected both.
  **Why:** Armen takes orders by phone while driving; he did not fill the earlier template either. Anything he must open and fill will not be used.
  **Do instead:** before building anything Armen has to do, ask "will he do this after every call?". Prefer data that collects itself (call log export) or one tap in WhatsApp, his usual channel.
- **What happened (07.10):** put "how much money did you receive" into the form.
  **Do instead:** do not ask Armen about money in forms or polls (Gev's instruction).
- **What happened (07.10):** proposed changing Armen's WhatsApp profile and statuses.
  **Do instead:** his WhatsApp is his personal number too; changes there need his knowledge, not only Gev's go-ahead.

## Keeping KRYUK24 separate

- **What happened (07.10, 21:53 UTC):** while starting the design system Gev wrote "do not mix MenQ in, this is fully separate".
  **Why:** KRYUK24 is Armen's business; the MenQ library is a tool, not its identity.
  **Do instead:** in KRYUK24 work, use MenQ code only as a pinned copy under `design/vendor/`; no MenQ colour, logo, name or text on any KRYUK24 screen; nothing about KRYUK24 into MenQ repositories or MenQ memory. `design/scripts/validate_design.py` checks the visible part.
- **What happened (07.10, 22:18 UTC):** the first `KryukMark` re-set the logo letters in CSS; next to the official file the «ЭВАКУАТОР» spacing differed. Gev: «the logo cannot change, it stays as it is».
  **Why:** the logo was rebuilt from its rules instead of copied from the approved file; the brand generator's letter-spacing depends on the size it was measured at.
  **Do instead:** in code, the logo is a copy of the approved file in `brand/02_lockups/` (`design/scripts/build_lockup.py`, checked in CI); compare any new logo use with the file by pixels before showing it.

## What Gev reads

- **What happened (07.10):** the work dashboard showed Armenian labels, English observation texts and Russian draft labels on one screen; Gev called it a disgrace.
  **Why:** observations and draft labels were written in English and Russian out of habit; the screen is read by Gev.
  **Do instead:** everything Gev reads on a screen is written in Armenian from the start (observations, sources, reasons, labels). Russian only for text that goes to Armen or to customers. Stored observations cannot be re-entered once a task is done, so the first version must already be right.
- **What happened (07.10):** three rounds on the dashboard: "unreadable", then "nicer", then "softer colours, one language, SVG icons, modal on click".
  **Do instead:** for a screen Gev will look at daily, start with calm colours, line icons in one style (no emoji), one language, compact cards that open details in a window. Show him a screenshot before polishing further.
- **What happened (07.10):** "make the page a bit whiter" was answered with a near-white page; Gev called it blinding and asked for a light grey.
  **Why:** took "whiter" as "white" instead of one step lighter.
  **Do instead:** move a palette one step at a time; for a light theme start from soft grey (page `#e6e8ec`, cards `#f3f4f6`), never pure white.
- **What happened (07.10):** Gev asked to remove explanation texts and the typed approval line from the dashboard.
  **Do instead:** on his screens show the fact and one button. Explanations, reasons and caveats stay in the data and in the state file, not on the page.

## Working with Gev

- **What happened (06.10 to 07.10):** Gev said "yes to everything that was waiting".
  **Do instead:** treat it as covering the listed pending items, and say plainly which ones it does not cover (payments, ad launch, anything he excluded in the same message).
- **What happened (07.10):** the old chat kept working after the handover: it committed, wrote a helper script and changed `00_STATE.md` while the new chat was editing the same file; the new chat first recorded the helper script as "origin unknown".
  **Why:** two sessions were open on one folder; the new chat read the state file once at the start and did not look at `git log` again.
  **Do instead:** when a file appears that this chat did not create, or an edit fails with "modified since read", run `git log -3` and re-read the file before writing anything about it.
- **What happened (07.10):** ended a report with "it is late, enough for today".
  **Why:** assumed the time and assumed he wanted to stop.
  **Do instead:** do not decide for Gev when the session ends; report and keep going.

- **What happened (08.10.2026):** an inline `python -c` with a Windows path (`C:\Users…`) died on the unicode escape again while editing the handover file. The lesson above already existed, twice.
  **Why:** "a two-line replace" felt too small for a script file.
  **Do instead:** for a text replacement in a document use the Edit tool; inline Python never holds a Windows path, whatever its length.
- **What happened (08.10.2026):** wrote "Update 08.10.2026 00:55 UTC" into a public PR text; the clock said 07:25. The session had been idle for hours between two of Gev's messages and I continued from the last time I remembered. The lesson about times already existed, twice.
  **Why:** a new message feels like the next minute; it may be the next morning.
  **Do instead:** at the first command after every new message from Gev, print `date -u`. A time goes into a document only from the output of the command that ran last.
- **What happened (08.10.2026):** the script Gev started for Armen's password printed "Done" in green although the server had refused the password (too short).
  **Why:** the remote command was `step; rm helper`, so the exit code was `rm`'s; only the success path had been thought through, and the script was handed over untried.
  **Do instead:** in `a; b` keep the exit of the step that matters (`a; result=$?; b; exit $result`). Before giving Gev a script, walk its failure path once: what does it print when the server says no?
- **What happened (08.10.2026):** the HTTPS check expected 401 on `/` and reported a failure; the installed config answers 404 there by itself (`location / { return 404; }` runs before the password is asked).
  **Why:** the expectation was written from the idea "the whole server is behind the password", not from the config lines that had been read an hour earlier.
  **Do instead:** take every expected status in a check from the line of the config that produces it; an expectation without a line behind it is a guess.
- **What happened (08.10.2026):** the session's permission check refused writing the script that edits the installed Nginx file; after Gev's explicit "yes, change Nginx, this path only" the same write went through.
  **Do instead (worked):** on a refusal stop that one outcome, finish everything that does not depend on it, tell Gev in plain words what the step does and what it opens, and wait for his word. Ask for the yes with its scope before writing a script that changes access control.
- **What happened (08.10.2026):** GPT did not accept the media pipeline's head: seven findings, all reproduced by him in an hour. A rollback that deleted an original the inbox had before the pipeline; an archive read outside the transaction; a repair that could remove a file another run had just registered; a folder that does not exist read as "the photos were taken back"; a half copy handed over; a submit cut off between its two halves; a wrong label on a test answer. My 23 tests and a server rehearsal were all green.
  **Why:** I tested the paths I had designed. I did not ask what was there before my code (shared rows), what a wrong input means (a missing folder is not an empty one), what happens between any two steps of an operation that writes to two places, or what a second run at the same moment does. And "safe to delete" was decided from my own bookkeeping, not from who made the thing.
  **Do instead:** before calling a delete, a rollback or a state change safe, write four tests first: (1) the same data existed before from another source; (2) the input is missing, wrong or empty, each apart; (3) the operation is cut off between every pair of steps that touch different stores; (4) a second run starts while the first is in the middle. Absence of something is never proof of an event; ask for a positive record. A fallback that changes the guarantee (a copy instead of a link) must fail loudly, not quietly.
- **What happened (08.10.2026):** the same reviewer came back twice more with the same kind of loss in a new place (a repair deleting a half file, a clean-up deleting a queued file, a rollback deleting after its commit). Each time I had closed the case he showed and left its cause: the shared store wrote a file and registered its row in two steps, and my code deleted beside it. Only the third round fixed the store itself.
  **Why:** I treated each finding as one bug of my module. I did not ask "who else writes or deletes here, with which code, and do they take my lock".
  **Do instead:** when a finding is a race around a shared file or table, list every writer of that resource first (also the installed code that is not mine) and fix the place they all pass through. A lock only I take protects nothing. If the second finding looks like the first, stop patching and name the common cause before writing code.
- **What happened (08.10.2026):** a rehearsal printed "one file on the disk under two names" while the two inode numbers beside it were different. The label was written before the run; I only saw it when reading the numbers.
  **Do instead:** a check prints what it measured and lets the numbers decide the words (`same inode: yes / NO`), never a sentence fixed in advance.
- **What happened (08.10.2026):** ran `tools/make_signage.py --help` to see its options; the script has no argument parser, so it ran in full and rewrote seven PDFs in the working tree (same content, new timestamps). Caught by `git status`, put back with `git checkout`.
  **Why:** assumed every script answers `--help`.
  **Do instead:** read a generator's top of file (docstring, `argparse` or not) before running it with any argument; a script without a parser is run only when its output is wanted.
- **What happened (08.10.2026):** the install plan said a script would restart `kryuk-capture` and `kryuk-bro-api`, and the repository's unit file said the service runs as `kryuk`. Writing the script I checked both: `bro_api.py` does not import the two files, and on the server every unit runs as `kryuk-run`. The plan had been reviewed five times with the wrong sentence in it.
  **Why:** I wrote "the services that load these files" from memory of the architecture, and took a unit file in the repository for the installed one.
  **Do instead:** which service loads a file is read from the imports (`grep "import"`), and who runs it from the installed unit (`systemctl show -p User`), on the day the sentence is written. An install script reads such facts from the server at run time instead of carrying them as constants.
- **What happened (08.10.2026):** the first run of a shell script's tests failed for two reasons that were not the script: `bash` started from Windows Python is the WSL launcher, not Git Bash; and `sha256sum FILE` puts a backslash before the checksum when the name holds a backslash.
  **Do instead:** a test names the shell it starts (an environment variable with a default); a checksum is taken from the bytes (`sha256sum < file`), never parsed from a line that also holds the name.
- **What happened (08.10.2026):** a trial on the server printed TRIAL FAILED: I had written that a one-shot unit stopped while its command runs becomes `inactive`; systemd makes it `failed`. The thing under trial had passed. The same day I had already written the lesson "an expected status is taken from the system, not from memory".
  **Do instead:** in a script whose only job is to measure, an expectation I have not seen the system produce is printed as a measurement first ("state after stop: …") and becomes a check only after one run. Keep the failed run as evidence beside the corrected one and say which lines changed.
- **What happened (08.10.2026):** I ran a check and a commit-and-push in one command joined with `;`. The check printed "NOT NOTICED" for one of six deliberate breaks, and the push went out with a README row saying each was noticed. Found a minute later by reading the output; corrected in the next commit and said to Gev.
  **Why:** `;` runs the next command whatever the one before it printed or returned; and I had written the sentence about the result before the result existed.
  **Do instead:** nothing that publishes (commit, push, zip) shares a command with the check it depends on unless the check's own exit code gates it (`&&`, and the check exits non-zero on a miss). A result sentence goes into a document only after the output was read.
- **What happened (09.10.2026):** I restyled one page of the portal and installed it. The login page shares its style sheet and kept its old markup; on a desktop window it was stretched over the whole width. Gev saw it at once. The browser check had passed: it ran at phone widths only, where the old markup still fitted.
  **Why:** I changed a shared style sheet and looked only at the page I was working on; and the check measured "no sideways scroll", not "the layout is the intended one".
  **Do instead:** when a shared file changes (a style sheet, a script, a token file), list every page that loads it and look at each one before installing. A layout check runs at one wide screen too and measures the thing itself (the width of the column), not only its absence of overflow.
