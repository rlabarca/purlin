# Real-skills QA check of Purlin 0.10.0

Run on 2026-10-02 against branch `qa/0.10.0` at `8d55f70`, installed from this checkout as a
directory marketplace. Real headless Claude Code sessions were used; nothing below is from a
fallback.

## 1. Verdict

Three people reached a signed version: `signed/0.1.0` was written by QA's sign-off, product added
a second sign-off, and `purlin:sign --check` passed on the package. They did not get there
without help. They got stuck three times: a spec named `sample-age` could never be tied to a
test, so the developer had to rename the feature. The forced number collision could not be
resolved without a hand edit of git's conflict lines. `purlin:init` committed nothing after the
person said yes.

## 2. How the check ran

- **Real headless sessions:** yes. Each person was a separate `claude -p` session in their own
  clone, with its own git identity and its own SSH signing key. Answers to a question were sent
  with `--resume <session-id>` into the same session.
- **Claude Code:** 2.1.287.
- **Flags:** `claude -p "<what the person typed>" --model <model> --dangerously-skip-permissions
  --output-format stream-json --verbose`, with `--session-id <new uuid>` for a new session or
  `--resume <id>` for an answer. `IS_SANDBOX=1` was set because the container runs as root. The
  wrapper unset the parent session's `CLAUDE_CODE_SESSION_ID`,
  `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` and `CLAUDE_ADDITIONAL_DIRECTORIES`, so no
  session saw this repository's `CLAUDE.md`.
- **Models:** `claude-haiku-4-5-20251001` (the cheapest) for product, QA and setup.
  `claude-sonnet-5-5` for the developer's build, test and audit, and for two status reads. Haiku
  was tried first for `purlin:build`. It did not respect the spec: it renamed the feature,
  deleted the `@manual` and `@slow` tags, shortened the proofs and wrote an automated test for the
  hand check (finding 1). After that the build was rerun on Sonnet, from a reset clone.
- **Cost:** $4.91 across 50 session turns ($2.64 Haiku, $2.27 Sonnet). The two audits printed
  another $0.29 and $0.33 for their own model calls. Total: about $5.53.
- **Time:** 1,119 seconds of model time. About 30 minutes of wall time from install to the last
  extra check, with the commands driven by a script.
- **Environment note:** this container sets a global `gpg.ssh.program` and `commit.gpgsign=true`.
  The first sign-off was signed by the container's own key, not Quinn's. It was reset and redone
  with `gpg.ssh.program=ssh-keygen` set in each clone (finding 12). Every result below is from the
  redo.
- **Transcripts:** every session's full stream-json transcript, the wrapper script and Haiku's
  discarded build diff are in `dev/plans/qa-real-skills/transcripts.tar.gz`. Three dashboard
  screenshots are next to it.

## 3. The story, step by step

| Step | Who, model | What was typed | What happened | Result |
|------|-----------|----------------|---------------|--------|
| Install | tester | `claude plugin marketplace add /home/user/purlin --scope project`, then `claude plugin install purlin@purlin --scope project` | Both worked as written, in under 1 s each. The session's init listed all 10 `purlin:` skills and the `purlin` MCP server as connected. | PASS |
| a. Setup | Dev, Haiku | "This is a new, empty Python project for LabConnect sample intake. We'll test with pytest. Set this project up for Purlin." | `purlin:init` ran, listed the files and asked `Commit the files setup wrote? [y/N]`. | PASS |
| a. Yes | Dev, Haiku | "yes" | The model reran the script with `--yes`. The script printed `kept ...` for every file and committed nothing. The model saw that no commit existed and committed by hand. | FAULT (finding 3) |
| a. Push | Dev, Haiku | "Also commit .claude/settings.json so my teammates get the plugin, then push main to origin." | Done. | PASS |
| b. First spec | Product, Haiku | The requirement in plain words: age at receipt across time zones and DST; 72 h SST, 24 h EDTA; message clear to a technician, judged by a person; one slow end-to-end batch check. | `purlin:spec` drafted 6 rules, left out the hand check and asked about the batch check. | PASS |
| b. Answer | Product, Haiku | "Yes, add the end-to-end batch check, and it's the slow one. You also left out the message: ... a judgment call a person has to check by hand ..." | Saved `specs/sample-age.md` with `PROOF-7 @manual (RULE-7)` and `PROOF-8 @slow (RULE-8)`, committed, and ended on `Spec saved: sample-age. Next: purlin:build sample-age`. The tags sit in the wrong place, so neither line can be read. Nothing said so until a later status (finding 8). The file went to `specs/`, not `specs/<category>/`. | FAULT (finding 8) |
| c. Collision, first try | Product and QA, Haiku, in parallel | Plain words with no command name, such as "Sharpen the sample-age spec: add a boundary case ..." | Neither session loaded `purlin:spec`. Both edited the file by hand and committed nothing. QA's session invented `PROOF-6b`. | FAULT (finding 11) |
| c. Collision | Product and QA, Haiku, in parallel, from commit `ed4138d` | `purlin:spec sample-age — one more rule: ...` and `purlin:spec sample-age — I'm QA. Add a boundary case ...` | Each drafted, asked, saved on "yes", committed and pushed. Product took RULE-9 and PROOF-9. QA took RULE-9, PROOF-9 and PROOF-10. | PASS |
| c. Merge | tester, git | product's branch, then QA's, into main | Git conflict in `specs/sample-age.md`. | expected |
| c. Drift | QA, Haiku | "I just merged my branch into main and git says there's a conflict in the spec. purlin:drift" | Named both numbers written twice, which line moves, and pointed to `purlin:spec sample-age`. It did not say the merge was still in progress. | PASS, with finding 4 |
| c. Status | QA, Haiku | `purlin:status` | Named the duplicates, the 9 conflict lines and the two unreadable proof lines. `Left to do: 1 spec to repair: purlin:spec`. | PASS |
| c. Spec | QA, Haiku | `purlin:spec sample-age` | Ran the dry run but did not show it or ask `Do it? [y/N]`. It resolved the conflict by keeping HEAD only, which dropped QA's rule. It then ran the renumbering, re-added the lost rule by hand and fixed a proof's rule reference by hand. The final spec was correct. | STUCK (finding 4) |
| d. Build | Dev, Haiku | `purlin:build sample-age` | Every marker `# purlin: sample-age PROOF-n` was rejected. The model renamed the feature, stripped the tags, cut the proofs, wrote a test for the `@manual` proof, wrote the `tests` setting without asking and committed. Discarded. | FAULT (finding 1) |
| d. Build | Dev, Sonnet | `purlin:build sample-age`, then "yes" to the suggested `tests` entry | Code and 10 marked tests written. It moved the two tags to the end of their lines. Then it diagnosed the marker fault, cited the cause and asked whether to rename. | STUCK (finding 1) |
| d. Rename | Dev, Sonnet | "Yes, rename it to sample_age and carry on." | Renamed, then `purlin:test --all --commit`. `Tests: met`. | PASS after help |
| d. Test | Dev, Sonnet | `purlin:test` | `Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --all runs them anyway.` No status followed (finding 13). | PASS |
| d. Mistakes | Dev, by hand | EDTA window set to 26 h; the 72-hour boundary test reduced to `assert r is not None`; committed | | |
| d. Test | Dev, Sonnet | `purlin:test` | `sample_age RULE-5 fails: tests/test_sample_age.py::test_edta_25_hours_rejected. Run purlin:build sample_age.` Then `Left to do: 1 rule to fix: purlin:build` and `1 slow proof to run: purlin:test --all`. The weak test passed unseen, as expected. | PASS |
| d. Fix | Dev, Sonnet | `purlin:build sample_age` | Fixed the window. It also tightened the weak test on its own, so the tester weakened it again by hand. | PASS |
| e. Audit | Dev, Sonnet | `purlin:audit sample_age` | RULE-4 `weak`: `PROOF-11: the test still passes when src/intake.py:33 reads "if age >= window:"`. 7 of 8 strong, $0.29, 28 s. | PASS |
| e. Strengthen | Dev, Sonnet | `purlin:build sample_age`, then `purlin:audit sample_age` | The test was strengthened. 9 of 9 strong, $0.33, 29 s. | PASS |
| f. Hand-off | Dev, Sonnet | `purlin:test --all --commit`, then `git push` | `Tests: met`. `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` | PASS |
| g. Status | QA, Haiku | "purlin:drift, then purlin:status" | Haiku loaded both skills at once, never called the Purlin tools and read a stale `.purlin/report-data.js`. It reported the old merge conflict as current. | FAULT (finding 5) |
| g. Status | QA, Haiku | `purlin:drift`, then `purlin:status`, one per session | Drift showed the rename as 10 rules removed and 10 added. Status: `Tests: met`, `Sign-off: not signed`. | PASS |
| g. Dashboard | QA, headless Chromium | opened `purlin-report.html` | It rendered with no console errors. Board: `TESTS met`, `SIGN-OFF not signed`, `AUDIT 9 of 9 strong`, while the table showed `9 of 10`. The page for RULE-7, the `@manual` rule, shows `PASSED` (finding 9). | PASS, with finding 9 |
| g. Sign | QA, Haiku | `purlin:sign --version 0.1.0` | The walk stopped at `sample_age RULE-7   hand check`. | PASS |
| g. Note | QA, Haiku | "The EDTA rejection reads '...' - clear to a technician." | The model signed with no sign question to the person. `Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...JJ8w.` `Tagged signed/0.1.0 at f099b41.` | FAULT (finding 10) |
| g. Checks | tester | `git verify-commit`, `git verify-tag`, `sign.py --check` | Good signatures with Quinn's key. `The package matches its fingerprint.` Status: `Sign-off: signed 0.1.0 at f099b41`. | PASS |
| g. Second signer | Product, Haiku | `purlin:sign --version 0.1.0`, a note, then "yes" | The stop showed QA's `Last note`. The session asked before signing this time. `signed/0.1.0 stays at f099b41; this sign-off is added after it. Push it: git push origin main` | PASS |
| h. Reword | Product, Haiku | `purlin:spec sample_age — reword RULE-7 so it says ...`, then "Change the rule wording only and keep the proof as it was ..." | Saved and pushed. | PASS |
| h. Status | Product, Haiku, then Sonnet | `purlin:status` | Haiku again read the stale data file and reported "complete and signed". Sonnet's real status: `Sign-off: signed 0.1.0, 2 commits since`, `10 rules. 1 passes its tests.`, `8 rules to test: purlin:test`. One reworded rule made every rule out of date, and the reworded `@manual` rule is the only one still passing. | FAULT (findings 2, 5) |
| h. Next sign-off | Product, Haiku | `purlin:sign --version 0.1.1` | Refused: `No sign-off: these results were not taken on this version of the code, 4d08f35: sample_age on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.` The model then ran that command without asking. The stop showed `Last note` from product's 0.1.0 note, `3 commits since`, with the new rule wording above it and no word that the rule changed. Not signed. | FAULT (findings 2, 10) |
| Extra | Haiku | `purlin:status` in a git repo not set up | The tool refused. The model then pointed it at the plugin's own folder and reported Purlin's 433 rules as the project's. | FAULT (finding 6) |
| Extra | Haiku | `purlin:status` in a set-up project with no spec | `No specs found under specs/.` `→ Run: purlin:spec <name> to write the first spec.` | PASS |
| Extra | Dev, Sonnet | add a proof tagged `@env(windows)`, `purlin:test`, then `purlin:build` | Before the test existed: `1 rule to write a test for: purlin:build`. After: `1 rule to test on Windows: run purlin:test on Windows`. The model offered a Windows CI runner, a borrowed Windows machine, or leaving it open, and asked which git host. Dev's status read `Sign-off: not signed` although 0.1.0 is signed in its history (finding 7). | PASS, with finding 7 |
| Extra | Dev, Haiku | `purlin:anchor create — one rule for the whole project: no source file under src/ uses a naive datetime ...` | `specs/_anchors/timezone_aware.md` was written with 3 rules, not 1, and committed with no review step. | FAULT (finding 17) |

## 4. Findings, most serious first

**1. A spec name with a hyphen is accepted everywhere except in the test marker.** `purlin:spec`
wrote `specs/sample-age.md`. Status, drift and the renumbering all handle `sample-age`. But every
`# purlin: sample-age PROOF-1` comment was rejected, and the near-miss check gave:
`"text": "# purlin: sample-age PROOF-1", "fix": null, "why": "The comment names no `<feature> PROOF-<n>` or `<feature> RULE-<n>`."`
Every proof read `no test`. Haiku "fixed" it by renaming the feature, deleting `@manual` and
`@slow`, shortening proofs and writing a test for the hand check. Sonnet found the cause and
asked: "Purlin's marker reader accepts only letters, digits and underscores in the feature name
(`markers.py:78`, `(?P<feature>\w+)`)." A person would expect a name Purlin itself created to
work. The rename then appears in drift as 10 rules removed and 10 added. Fix: allow `-` in the
marker's feature name (`scripts/mcp/purlin/markers.py` and `marker_format.md`), or have
`purlin:spec` and `sync_status` refuse such a name when the spec is created. The near-miss line
should name the cause.

**2. Rewording one rule puts every rule of the feature out of date, and the reworded `@manual`
rule stays passed.** After product reworded RULE-7 only:
`10 rules. 1 passes its tests.` `Left to do: 8 rules to test: purlin:test` `1 slow proof to run: purlin:test --all`,
Strong `0 of 10`, and the dashboard header `AUDIT 0 of 0 strong`. The only rule still passing is
RULE-7, the one that changed. At the next sign-off the stop shows the new wording with
`Last note: noted at the sign-off of 0.1.0 by pat.product@labconnect.example, 3 commits since: I read the SST and EDTA rejection messages myself; both are clear.`
That note was written against the old wording, and nothing says the rule changed. A person
would expect the changed rule, and only it, to need looking at again. Fix: the docs should say a
spec change re-runs the whole feature, if that is intended. The fingerprint, the status and the
walk should mark a `@manual` rule whose wording changed since its last note
(`sync_status`, `scripts/review/sign.py`).

**3. `purlin:init` commits nothing after the person says yes.** The skill has the model run the
script first, then ask. A second run with `--yes` writes nothing new, so it prints
`kept .purlin/` ... `kept purlin-report.html`, commits nothing, says nothing about the commit and
exits 0. The model found `fatal: your current branch 'main' does not have any commits yet` and
committed by hand. The same happens in a repository that already has commits. The docs promise
`Committed e1a0b21, the files setup wrote:`. Fix: `--yes` in `scripts/init/scaffold.py` should
commit setup's files when they are on disk and not committed. Or the skill should ask before the
first run.

**4. The renumbering cannot finish without a hand edit, and the session skipped `Do it? [y/N]`.**
Drift was right:
`sample-age: RULE-9 is written twice. The line on origin/main keeps RULE-9; renumber the other to RULE-10 and move its test comments with it: "Reject samples with an unknown tube type with the reason 'unknown tube type'".`
and the same for PROOF-9 to PROOF-11. The renumbering script works inside a conflicted file:
`Renumbered in sample-age: 3 spec lines and 0 test comments. Nothing is committed.` But it leaves
git's conflict lines in place, with `> Highest-Proof: 11` on one side and a stale `10` on the
other. A person must still delete the conflict lines by hand, keeping both sides. Neither the
skill nor `working-together.md` gives that order. The session resolved the conflict by keeping
HEAD only, which lost QA's rule, then re-added it by hand. It never showed the dry run or asked
`Do it? [y/N]`, which the skill requires. Two smaller points:

- Drift ran mid-merge and reported `Since your last pull, 13 seconds ago (ed4138d..9a660c6, 2 commits).`
  with no word that a merge was still in progress.
- Drift's line does not say PROOF-10 must now name RULE-10; the dry run does:
  `sample-age: PROOF-10 at line 42 now names RULE-10.`

Fix: `scripts/spec/renumber.py` should resolve a conflict hunk whose two sides only add lines by
keeping both, and the `> Highest-` lines by taking the higher. Or the skill's "After a merge
conflict" should state the order: keep both sides, take the higher `> Highest-` line, then
renumber.

**5. The skills name `sync_status` and `drift`, but Claude Code exposes them as deferred tools
`mcp__plugin_purlin_purlin__sync_status` and `mcp__plugin_purlin_purlin__drift`.** Twice Haiku
did not load them. It tried `purlin status` (`purlin: command not found`) and
`python -m purlin.cli`, then read `.purlin/report-data.js` and reported it as the status. Once it
reported a merge conflict that had already been fixed, built, audited and pushed. Once it reported
"Your Purlin project is complete and signed" when only 1 of 10 rules passed. Sonnet always found
the tools. Fix: the skills should name the tool as the session sees it, or say to load it with
ToolSearch. The status skill should forbid reading `report-data.js` as the status. A script entry
point for the status, such as the one `purlin_run.py` has, would give a fallback.

**6. A refusal invites the model to point Purlin at the plugin.** In a repository not set up,
the tool said:
`No Purlin project root at .../empty: .purlin/config.json is not there. Run purlin:init there, or pass the top folder of a Purlin project as project_root.`
Haiku then passed `/home/user/purlin` and reported `Purlin status: purlin, plugin 0.10.0`,
`433 rules. 433 pass their tests.` as the user's project. Fix: end the line at `Run purlin:init.`
and refuse a `project_root` that is the plugin's own root (`sync_status`).

**7. The status reads the sign-off from the tag alone.** Dev pulled with
`git pull origin main`, which does not fetch tags. Dev's status read `Sign-off: not signed`,
although both sign-off commits and `.purlin/evidence/package/0.1.0.signoffs/` were in its
history. Nothing said to fetch tags. Fix: when sign-off files exist and the tag is missing, the
status should say so and name `git fetch --tags` (`sync_status`, `evidence_and_signoff.md`).

**8. The spec skill does not say where a tag goes, and nothing checks the saved spec.** The skill
says "Tag a proof `@manual`" but never says where. Haiku wrote `- PROOF-7 @manual (RULE-7): ...`.
The spec was saved and committed with `Spec saved: sample-age.` The fault surfaced only in a
later status, cut off mid-word and with no reason:
`sample-age: a line under ## Proof cannot be read: - PROOF-7 @manual (RULE-7): A rejection message for an aged . Run purlin:spec sample-age.`
Fix: the skill should show `... @manual` at the end of the line and call `sync_status` after
saving. The line should say why: "a tag goes at the end of the line".

**9. A `@manual` rule nobody has checked reads `passed`.** Before any sign-off, the status
counted RULE-7 in `10 rules. 10 pass their tests.`, and its dashboard page showed a green
`PASSED` badge. The sign walk printed `Results  Linux/Unix: passed on vm` for a proof that has no
test. A person would expect "not checked yet" or "checked at sign-off". Fix: the dashboard, the
status and `sign.py`'s `Results` line.

**10. The model skipped confirmations the skills require.** These are text instructions, and the
cheap model ignored them:

- `purlin:sign`: Haiku wrote `"sign": true` and signed twice with no question to the person. The
  transcript shows `Sign the evidence package for 0.1.0 as quinn.qa@labconnect.example? [y/N] y`
  answered by the answers file.
- After a refusal, it ran `purlin:test --all --commit` without asking, which also committed
  evidence. The skill says: "Run what a refusal names only when the person asks."
- `purlin:spec`: no `Do it? [y/N]` before renumbering.
- `purlin:build` on Haiku: it wrote the `tests` setting without suggesting it.

Fix: put the sign question in the script. For example, `--answers` could require the signer's
email typed in the file rather than `true`. Mark the other confirmations as hard stops in the
skills.

**11. A plain request does not reach the spec skill.** "Sharpen the sample-age spec: add a
boundary case ..." made both Haiku sessions edit the file by hand, with no commit. One invented
`PROOF-6b (RULE-4)`. `working-together.md` says "Say 'it should also reject an expired token' to
`purlin:spec`", which means typing the command. Fix: the skill's description should cover
"add a rule or case to a spec". The docs should say to name the command.

**12. The sign-off records the configured key, not the key that signed.** With this container's
global `gpg.ssh.program`, the commit was signed by another key (`SHA256:32dP45...`). The script
still printed `with the key ending ...JJ8w` and recorded Quinn's fingerprint. Fix: after signing,
read the commit's actual signer fingerprint with `git log --format=%GF`, and refuse on a
mismatch (`scripts/review/sign.py`).

**13. `Nothing to run` ends without the status.** `getting-started.md` says "Every run ends on
the status." The run printed one line and stopped, and the Sonnet session made up a status table.
Fix: `purlin_run.py` should print the status after `Nothing to run`.

**14. The heuristic spot tests did not flag `assert r is not None`.** Only the planted bug found
the weak test. Fix: add an "asserts only that a result exists" spot test (`review_criteria.md`).

**15. A rename reads as removal and addition.** Drift printed `10 rules added: sample_age ...`
and `10 rules removed: sample-age ...`. The model then suggested
`→ Run: purlin:status sample-age`, a feature that no longer exists. Fix: drift could pair a
removed and an added spec whose rules match.

**16. Small wording points.**

- The header says `AUDIT 9 of 9 strong` while the table says `9 of 10` in amber, because the
  `@manual` rule counts in one denominator and not the other.
- The project is named `remote`, from the bare remote's folder name `remote.git`.
- The board's `PASSING` box counts the unchecked hand check.

**17. `purlin:anchor create` has no review step.** One rule was asked for; three were written and
committed with no draft shown. One proof reads: "the annotations are verified to be `datetime`
paired with an explicit tzinfo parameter (e.g., via a comment or a type like
`datetime[tz.aware]`)", which no test can settle. Unlike `purlin:spec`, the anchor skill has no
step that prints the rules and asks. Haiku also looked for
`skills/anchor/references/formats/anchor_format.md` before finding the plugin root. Fix: the
anchor skill should print the rules and ask, as the spec skill does.

**18. Notes outside Purlin's own scope.**

- `.gitignore` from setup does not cover `__pycache__/`, and two sessions committed `.pyc` files.
- The agent definition `agents/purlin.md` is offered only as the subagent `purlin:purlin`. The
  main session does not run under it, and no doc says to start with `--agent purlin`.
- Haiku is not a sensible model for `purlin:build`. It changed the spec to make its tests pass.

## 5. What worked with no help

- Install, exactly as `README.md` and `getting-started.md` give it, with a local path in place of
  the URL. All 10 skills and the MCP server were there in every clone.
- The init question, and the next-step lines.
- `purlin:spec` from a plain-language requirement, once the command was typed: it drafted, asked
  and saved.
- Drift's collision lines: exact, with which side keeps the number and the next free one.
- The status during the collision: every problem named, and one `Left to do` line.
- `purlin:test`'s first-run suggestion of the pytest entry (Sonnet asked before writing it), the
  failure line naming rule, test and command, and `Left to do`.
- The audit: it found the weak boundary test, named the exact mutation that survived, printed the
  cost per rule and the share strong, and finished in under 30 s.
- The hand-off `purlin:test --all --commit`, the two evidence commits and the final line.
- The sign walk: the stop, the note, the signed commit, the tag, `--check`, the second signer's
  line and `Last note`. The refusal after a change named the right command.
- `signed 0.1.0, 2 commits since` in both the status and the dashboard.
- The `@env(windows)` line `1 rule to test on Windows: run purlin:test on Windows` and the model's
  three options.
- The status with no spec.
- The dashboard: it opened from disk with no console errors, and the board and rule pages read
  correctly.

## 6. The collision, in full

1. Product's first spec, 8 rules and 8 proofs, was merged to main at `ed4138d`.
2. From `ed4138d`, at the same time, product on `product/future-collection` typed
   `purlin:spec sample-age — one more rule: if a sample's collection time is after its receipt time, that's a data-entry error ...`.
   QA on `qa/sharpen-age` typed
   `purlin:spec sample-age — I'm QA. Add a boundary case: a sample exactly at its stability window (exactly 72 hours for SST) is accepted, not rejected. And add a rule of my own: a sample with an unknown tube type is rejected ...`.
   Each drafted and asked "Does this look right?", then saved on "yes" and pushed. Product wrote
   RULE-9 and PROOF-9. QA wrote RULE-9, PROOF-9 (RULE-4) and PROOF-10 (RULE-9).
3. Product's branch was merged to main and pushed. QA merged its branch into main and git
   reported `CONFLICT (content): Merge conflict in specs/sample-age.md`, with three hunks: the
   `> Highest-Proof:` line, the RULE-9 line and the proof lines.
4. QA typed `purlin:drift`. It printed both "written twice" lines with the target numbers RULE-10
   and PROOF-11, then `→ Run: purlin:spec sample-age`. It did not mention the unfinished merge.
5. QA typed `purlin:status`. It printed `RULE-9 is written twice; the second is read.`, the same
   for PROOF-9, `9 lines are left from a merge conflict, the first at line 6: <<<<<<< HEAD.`, the
   two unreadable tag lines from finding 8, and `Left to do: 1 spec to repair: purlin:spec`.
6. QA typed `purlin:spec sample-age`. The session ran the dry run:
   `RULE-9 at line 25 becomes RULE-10 ...`, `PROOF-9 at line 41 becomes PROOF-11 ...`,
   `PROOF-10 at line 42 now names RULE-10.`, `> Highest-Rule: 9 becomes 10.`,
   `> Highest-Proof: 9 becomes 11.`, `Nothing is changed: this is a dry run.` It did not show the
   dry run to the person or ask. It removed the conflict lines by keeping HEAD's side only, which
   deleted QA's RULE-9 line and moved PROOF-10 under the wrong rule. It then ran the real
   renumbering, which now moved only PROOF-9: `Renumbered in sample-age: 1 spec line and 0 test comments.`
   It re-added RULE-10 by hand, raised `> Highest-Rule:` by hand, pointed PROOF-10 at RULE-10 by
   hand and committed `spec(sample-age): Resolve merge conflict and renumber duplicates`. The
   result was correct.
7. Run by hand in a fresh clone of the same merge, the renumbering in the conflicted file did all
   three moves. It left the conflict lines, including a stale `> Highest-Proof: 10` on QA's side.

**Answer:** Purlin names the collision exactly and offers the renumbering, but following its
words does not resolve it without a hand edit. Git's conflict lines must be removed by hand,
keeping both sides, and the docs do not say so. The model skipped the `Do it? [y/N]` it was told
to ask. No test comments existed yet, so moving test comments was not exercised.

## 7. The audit

| | First audit (weak test in place) | Second audit (after `purlin:build`) |
|---|---|---|
| Rules read | 8: RULE-7 is a hand check and RULE-8's slow proof was left out | 9 |
| Result | 7 strong, 1 weak (87%) | 9 strong (100%) |
| Cost printed | `The model was asked 8 times for 8 rules: $0.29 in all, $0.04 a rule.` | `9 times for 9 rules: $0.33 in all, $0.04 a rule.` |
| Time (whole session) | 28 s | 29 s |
| Model recorded in the evidence | `claude-sonnet-5-5` | the same |

The weak test was found: `sample_age RULE-4   weak` and
`PROOF-11: the test still passes when src/intake.py:33 reads "if age >= window:"`. No spot test
fired on `assert r is not None` (finding 14).

Planted bugs in the first audit, one per proof, each from the evidence file:

| Rule | Proof | Planted change | Result |
|------|-------|----------------|--------|
| RULE-1 | PROOF-1 | age `+ timedelta(minutes=1)` | caught, strong |
| RULE-2 | PROOF-2 | both times `.replace(tzinfo=None)` | caught, strong |
| RULE-3 | PROOF-3 | both times `.replace(tzinfo=None)` | caught, strong |
| RULE-4 | PROOF-4 | `if age > window + timedelta(hours=2):` | caught |
| RULE-4 | PROOF-11 | `if age >= window:` | survived, so RULE-4 is weak |
| RULE-5 | PROOF-5 | EDTA window 26 h | caught, strong |
| RULE-6 | PROOF-6 | `if age > window - timedelta(hours=2):` | caught, strong |
| RULE-9 | PROOF-9 | `if age < timedelta(hours=-1000):` | caught, strong |
| RULE-10 | PROOF-10 | reason `"unrecognized tube type"` | caught, strong |

No rule read `spot-checked`. The printed run does not list the caught bugs; only the evidence
file does. A person would have to open the JSON or the dashboard to see what was planted.

## 8. Reproducing the setup

```bash
W=/path/to/scratch/lab; mkdir -p $W/keys $W/logs; cd $W
apt-get install -y openssh-client; pip install pytest playwright
git init -q --bare -b main remote.git
for p in product qa dev; do git clone -q remote.git $p; done
for t in "product|Pat Product|pat.product@labconnect.example" \
         "qa|Quinn QA|quinn.qa@labconnect.example" \
         "dev|Dana Dev|dana.dev@labconnect.example"; do
  IFS='|' read d n e <<< "$t"
  ssh-keygen -q -t ed25519 -N "" -C "$e" -f keys/$d
  echo "$e $(cat keys/$d.pub)" >> keys/allowed_signers
  git -C $d config user.name "$n"; git -C $d config user.email "$e"
  git -C $d config gpg.format ssh; git -C $d config user.signingkey $W/keys/$d.pub
  git -C $d config gpg.ssh.program ssh-keygen          # override a global signer
  git -C $d config gpg.ssh.allowedSignersFile $W/keys/allowed_signers
  git -C $d config commit.gpgsign false
done
cd $W/dev
claude plugin marketplace add /path/to/purlin-checkout --scope project
claude plugin install purlin@purlin --scope project
```

Each person's turn, from their clone:

```bash
env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID IS_SANDBOX=1 \
  claude -p "<what the person types>" --model claude-haiku-4-5-20251001 \
  --dangerously-skip-permissions --output-format stream-json --verbose \
  --session-id "$(uuidgen)"            # or --resume <session-id> to answer a question
```

The wrapper used for every turn is `run.sh` inside `transcripts.tar.gz`. The log names in the
archive match the steps above: `a1-init` to `h5-sign`, and `x1` to `x6` for the extra checks.
