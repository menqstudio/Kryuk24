# GitHub: actual result of the setup and of the first push

Recorded by Claude on 07.10.2026. Target: `https://github.com/menqstudio/Kryuk24`. No secret value appears here.

## 1. What was found before anything was changed

| Check | Result |
|---|---|
| Repository | exists, created 07.10.2026 13:26 UTC, **empty** (no commit, no branch): there was no history to preserve or overwrite |
| Visibility | private |
| Authenticated account | `menqstudio` (a user account); permissions on the repository: admin, maintain, push, triage, pull |
| `gh` on this machine | two accounts are logged in; the active one is another account and was **not** switched. The `menqstudio` token is taken per command and is never written into the repository configuration |
| Plan | not readable with the token's scopes; the refusals below show it is a free plan |
| `GIT_AUTHOR_*` / `GIT_COMMITTER_*` in the environment | none set; the import command also unsets them explicitly |

## 2. Commit identity

| Item | Result |
|---|---|
| Repo-local `user.name` | `MenQ` |
| Repo-local `user.email` | `300099401+menqstudio@users.noreply.github.com` |
| Why this address | the account's verified addresses could not be read (the token has no `user` scope). This is GitHub's own no-reply address for the account id; GitHub linked the commits to `menqstudio` (see the test below). If Gev prefers another verified address, it is one config line and applies to later commits |
| Co-author and tool lines | none; `tools/check_commit_identity.py` refuses `Co-Authored-By`, "Generated with" and the tool's address, and CI runs it on every new commit |
| Signing | off; commits show as `unsigned` |
| Merge | made locally as a merge commit by the same identity, then pushed; the web merge button is not used |

**Test commit (the initial import), read back from GitHub:**

```
sha        8bc7233
author     MenQ <300099401+menqstudio@users.noreply.github.com>   -> GitHub account: menqstudio
committer  MenQ <300099401+menqstudio@users.noreply.github.com>   -> GitHub account: menqstudio
trailers   none
tree       equal to the tree of the local branch cleanup/stage2-structure (same tree hash)
```

## 3. Repository configuration: what took effect

| Setting | State (read back) |
|---|---|
| Private, default branch `main` | yes |
| Actions: which actions may run | only actions owned by GitHub; **pinning to a full commit SHA is required** by the repository |
| Actions: workflow token | read-only; cannot approve pull requests |
| Workflow | `permissions: contents: read`; `actions/checkout` and `actions/setup-python` pinned to full SHAs; no job writes to the repository, no real API, no credentials, no deployment |
| Dependabot alerts | on |
| Dependabot security-update pull requests | **off on purpose**: the bot would create commits, and every commit must be by MenQ. Alerts still arrive |
| Wiki, Projects | off |
| Pull request template, issue template (blank issues off), `CODEOWNERS` (`* @menqstudio`) | in the repository |
| `.gitignore`, `.mcp.json.example` (no secret, no id), `tools/requirements.txt` | in the repository |

## 4. BLOCKED: not supported for a private repository on the current plan

No paid upgrade was made.

| Wanted | What GitHub answered |
|---|---|
| `main`: pull request required, required green CI, no force-push, no branch deletion (rulesets) | 403 "Upgrade to GitHub Pro or make this repository public to enable this feature." |
| The same through classic branch protection, tried again after the first push | 403, same text |
| Secret scanning and push protection | 422 "Secret scanning is not available for this repository." |
| Private vulnerability reporting | 404 |

Consequence: **`main` is not protected by GitHub.** A direct push, a force-push or a branch deletion is technically possible for the account. The rule is kept by procedure (branch, pull request, green CI, local merge commit) and by the identity check in CI, not by enforcement. Options are Gev's: GitHub Pro for the account, or accept this.

## 5. First push and CI

| Step | Result |
|---|---|
| First push of the clean tree | done 07.10.2026, one commit `8bc7233`, 500 files |
| What was not uploaded | the old history (kept in a verified bundle), `_private/`, `_drive_staging/`, databases, credentials, the local `.mcp.json` |
| First CI run on `main` | **failed.** `commit-identity` passed, `linux` passed, `windows` failed in "API reader": the Windows runner converted line endings on checkout, so the server fixtures no longer had the sha256 the installer expects. Local checks had not shown it, because this machine does not convert |
| Fix | branch `fix/byte-exact-checkout`, one file `.gitattributes` (`* -text`), pull request #1, commit by MenQ |
| CI on the fix | first run on the branch: `commit-identity` and `linux` passed; `windows` passed API reader (the step that failed before), gate and job runner, and proxy, then **failed in the trial harness self-test**: 3 of 68 tests ended INCONCLUSIVE or BLOCKED on the hosted runner (`test_deny_cases`, two `test_tab_id_…`); locally all 68 pass, the cause is not established. Second commit on the branch (`a6a8fe7`): the harness self-test is left out of CI with that reason written in the workflow and in `runtime/wip/README.md`. After it both runs (push and pull request) were **green**: `commit-identity`, `linux`, `windows` |
| Merge of the fix | merged locally as a merge commit by MenQ (`0abf9b0`, two parents), pushed 07.10.2026 14:07 UTC; GitHub shows pull request #1 as MERGED; `tools/check_commit_identity.py` accepts all 4 commits; **CI on `main` at `0abf9b0`: green.** The remote branch `fix/byte-exact-checkout` was left in place |

## 6. Off-disk copies made before the push

`E:\Kryuk24\backup_2026-10-07\` on an external USB disk (a different physical disk): the git bundle with all refs (167 commits, checked by a clone), the media for Drive (336 files), the private materials (16 files), the files git never held (16 files). Every copy was compared with its source by sha256.

Drive (`kryuk24msk` account): Gev uploaded the whole `backup_2026-10-07` folder, so Drive holds the media **and also** the bundle, the private materials and the untracked files. Gev decided on 07.10.2026 to leave it so. Seen on the page: the four folders, the five media groups and the manifest file. **Not verified:** that each of the 336 files arrived intact; the Drive page shows no hashes, and no Drive API access exists in this session.

## 7. After the first report: the harness cause, pull request #2

The three failing harness tests were investigated the same day. A throwaway branch (`diag/harness-probe`, not merged, deleted afterwards) printed the timing of the harness's own marker requests on the hosted runner (run 37636463957): every request was answered in under 0.02 s, yet a test failed, and a different one than in run 37631911135. Cause: `runtime/wip/trial/fixture_server.py` sent the answer first and wrote its access-log row after; the harness reads that log right after the answer, so the marker row could be missing. The check then became INCONCLUSIVE and the case BLOCKED. The effect was fail-closed.

Fix: the row is written before the answer leaves. Pull request #2 also puts the harness self-test back into the Windows job and repeats the three affected tests five times. CI on the branch: runs 37637395946 (pull_request) and 37637379902 (push), all jobs green, including the self-test and the five repeats. Merged locally as a merge commit by MenQ (`d96e4f2`).

The description of pull request #1 was corrected after its merge: it first named only the `.gitattributes` change and now also names the removal of the harness step from CI.

Not examined: whether the same race affected the recorded real trial attempts (T1, T2).
