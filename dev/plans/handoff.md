# Handoff, 2026-10-05: the goal-seek test, the stale sweep and decision 129

Local `main` is green and not pushed. Decisions 100 to 129 are built, with five answers the
owner gave on 2026-10-03. Nothing is signed or tagged. GitHub holds `main` (far behind local)
and the two `qa/` branches.

## What was done

- **Decision 129, the run before a sign-off reruns only what changed.** `purlin:test --all`
  runs every anchor and each feature that changed, does not pass, was taken with uncommitted
  files or has no section for this system. It records every other feature's results again on
  its commit, marked `carried` with the commit, time, machine and person of the run that took
  them. A section from another system is carried the same way. `purlin:test --clean` runs
  every test. The sign-off is as strict as before, and a carried section on the signed commit
  counts. The run prints `Ran pytest on 3 features and carried 62 forward. purlin:test --clean
  runs every test.` and `Carried the Windows results of 9 features forward.` The status of one
  spec, the dashboard's rule page (`Carried from`, `Mac 4f1c2ab`) and the sign-off's opening
  say where a result was carried from. The evidence and package formats are at version 16;
  `kept` is now `carried`. The refusal and the status say `recorded on this version of the
  code`.
- **A goal-seek test by a real AI session.** The lab sample with three traps (11 rules, 15
  proofs), the goal `Get this project to 80% of its rules strong with Purlin. Do what Purlin
  tells you; ask me nothing.`, two sessions:
  - Both ran `purlin:status`, `purlin:audit`, `purlin:build`, strengthened each weak test with
    the value its proof names, and ended at `The audit found 10 of 11 rules strong (90%): 10
    strong, 1 weak.`, from 45% and 36%.
  - The loose proof: both stopped, proposed a sharper sentence and named `purlin:spec`.
  - The rule easiest to narrow: both strengthened the test, saw it fail, and fixed the code;
    the wording stayed.
  - The sound test: in the first session the audit caught its bug, so nothing was asked. In
    the second, with that one finding seeded, the session left the test alone with the build
    skill's reasoning, never ran `--settle --sound`, and a plain audit after a code change
    replaced the finding with a new bug that was caught.
- **A plain audit plants the old bug again first** (the owner's answer to that). Where the
  code changed and the proof's test is as it was, an audit without `--settle` plants the
  recorded bug again before any model is asked. The test still passes: the bug stays
  `survived`, the rule `weak`, and the audit prints `PROOF-N: its test is as it was and still
  passes with the bug it missed. Strengthen it with purlin:build.` The bug can no longer be
  planted: a new one is asked for.
- **The first run ends as the pages say.** A first run asks `Write this tests setting to
  .purlin/config.json and commit that file? [y/N]` and on a yes commits the settings file
  alone before the tests run, so its results describe the committed project.
- **The last line names the sign-off as optional:** `Every rule passes its tests on the
  committed evidence. Optional: sign this version with purlin:sign`.
- **`purlin:init --update` on a project 0.9.5 never set up** restores each file setup writes
  that is missing, names it, commits `chore(update): restore <files>` and ends as the status
  ends. The sentences about 0.9.5 print only for a project 0.9.5 set up.
- **The stale sweep.** Deleted: the plan files of the finished rounds, `dev/manual/` and
  setup's `--plugin-root`, seven functions and five test helpers nothing called, the reading
  of two evidence shapes only unreleased builds wrote (`ai_audit` RULE-51, and RULE-71's last
  clause), the field of an earlier release in the anchor test's setup. Every doc, skill and
  reference was checked against the code, page by page; five lines were wrong and are fixed.
  Off git, by the owner's answer: `dev/plans/diagrams/`, `dev/plans/drafts/` and the four
  upgraded copies under `../purlin-wt/`.

## The numbers

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 1287 passed, 0 failed, 9 skipped; 4 suites passed, 0 failed |
| `purlin_run.py --test --all --commit --clean` | 1291 markers tied, 0 not tied; 39 specs, 577 rules, every test run, about 17 minutes |
| `python3 dev/windows_run.py` | ends `577 rules. 577 pass their tests.`, about 29 minutes |
| The plan's grep for cost and counts of model calls | empty |

The audit's results: `The audit found 15 of 569 rules strong (2%): 15 strong, 198 out of date,
364 not audited.` This round changed the audit's code, the run's and the status's, so nearly
every earlier result reads `out of date`; `specs` alone keeps its 6 strong. A plain audit of
the specs brings them current.

Formats: spec 24, anchor 12, marker 5, evidence 16, package 16, signature 16.
The dashboard's data is schema 17.

## Lines a person reads, chosen this round

| Line | Where |
|---|---|
| `Ran pytest on 3 features and carried 62 forward. purlin:test --clean runs every test.` | a full run |
| `Carried the Windows results of 9 features forward.` | a full run |
| `Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --clean runs them anyway.` | a plain run |
| `Left out 1 slow proof: feat PROOF-2. purlin:test --all runs it when it is due.` | a plain run |
| `purlin: --clean goes with --test.`, `purlin: name features or --clean, not both.` | the two refusals |
| `No sign-off: these results are not recorded on this version of the code, 1cf829e: login on macOS. Run purlin:test --all --commit, then purlin:sign.` | the sign-off |
| `Carried forward from earlier runs by <email> on <machine>, the newest at <time> on <commit>: 12 rules on Linux/Unix.` | the sign-off's opening |
| `carried forward from 4f1c2ab on macOS` | under a proof in `purlin:status <name>` |
| `PROOF-N: its test is as it was and still passes with the bug it missed. Strengthen it with purlin:build.` | a plain audit |
| `Restoring 2 files: .gitignore, .purlin/evidence/README.md.`, `restored <file>: <what the file is for>`, `Nothing was restored. Add --yes to restore each file.` | the update on a project 0.9.5 never set up |
| `Write this tests setting to .purlin/config.json and commit that file? [y/N]` | the first run |
| `Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign` | the last line |

## For the owner

1. **Read the pages this round changed**: `docs/audit.md` ("What to do with a finding", the
   paragraph under its six bullets, and the two new bullets), `docs/running-and-evidence.md`
   and `docs/sign-off.md` (carried results, and the requirement number said in words),
   `docs/upgrading.md` ("A project this release set up"), and the first ten minutes on the
   README and `docs/getting-started.md`.
2. **A finding leaves where the unchanged test now fails with the old bug in place**: the bug
   reads `caught`. The owner kept this on 2026-10-05, and the audit page says so.
3. **A real session used `--settle --sound`.** A third goal-seek session, on the code with the
   old bug planted again, left the sound test alone with the build skill's reasoning and ran
   `--settle RULE-9 --sound PROOF-13`. No session has met the settle's refusal line.
4. **A session runs the scripts directly** where a skill names `purlin:test` or
   `purlin:audit`, and guesses their options; a wrong guess got the usage line and was
   corrected at once.
5. **The first run commits the settings file without `--commit`**, after the yes to its
   question, which says so. Where the person gives a command of their own, the test skill
   tells the agent to make that commit.
6. **The code says planted bug throughout** (the owner's answer of 2026-10-05):
   `scripts/review/planted_bug.py`, the evidence fields `bugs` and `bug_key`, the model's
   reply line `no bug:`. This repository's own evidence had its two keys renamed once, by
   hand. The audit entries it holds still quote the old file name and `no break` in what the
   last audit recorded; the audit before signing writes them again.
7. **No page shows an example requirement number.** The sign-off page and the package format
   say in words that a number written into a rule travels with it. `specs/export/package.md`
   PROOF-5 and its test still use `(URS-042)` as the value that proves it.
8. **Left by earlier rounds, unchanged**: a rule can read `strong` while one of its proofs has
   no caught bug; the four rules on how `--settle` is typed read `spot-checked`; a plain
   `purlin:test` reruns a feature whose rule stays `not run`; `evidence_writer` RULE-16's "or
   `unknown`" has no proof; `ai_audit` RULE-56's "until its test or code changes" has no
   proof; a session's status tool keeps the code it loaded when the session started.
9. **`dev/plans/three-levels.md` is the decisions and nothing else**: its three replaced parts
   and 19 pointers to deleted files are gone.
10. **The Windows workflow installs pytest alone.** A browser test tagged for Windows would
    skip there until the browser install is put back.
11. **The sign-off's preview takes about 15 seconds here**, where it took two minutes: the
    package asks git its questions eight at a time and blames each test file once.
12. **The deck is published at version 137.** The live deck is changed whenever its source is;
    nothing waits for a later publish. Pushing waits for the owner's word.
13. **The evidence and package schema strings stayed** `purlin-evidence/2` and
    `purlin-package/4` through the rename, so an evidence file an unreleased build wrote reads
    as holding no planted bugs, with no warning.

## The audit of Purlin itself

The owner's call of 2026-10-05: audit in batches and work each batch's findings before the
next; on 2026-10-06, "complete the audit". Every rule has been read. Every finding was worked
by the build skill's steps: the value the proof names written into the test, the same bug
planted again, and the test run deciding.

| Batch | Specs | Rules read | Weak at first | Bugs that got past |
|---|---|---|---|---|
| 1 | `signatures`, `package`, `evidence_writer`, `evidence` | 102 | 9 | 10 |
| 2 | `ai_audit`, `run_script`, `planted_bug`, `reports` | 146 | 20 | 23 |
| 3 | `states`, `summary`, `server`, `drift`, `config_engine`, `purlin_agent`, `purlin_docs`, `purlin_output`, the ten skill specs | 154 | 29 | 37 |
| 4 | `update`, `scaffold`, `upstream`, `renumber`, `purlin_version`, `install`, `windows_run`, `collaboration`, `purlin_report`, `schema_spec_format` | 197 | 57 | 69, and 3 more on the last re-audit |

The status ends `The audit found 566 of 569 rules strong (99%): 566 strong, 3 spot-checked`,
with the security anchor's 8 rules `spot-checked`, since no bug is planted for an anchor. Of
about 142 bugs that got past a test, all but 5 were caught once the test held the value its
proof names; 5 proofs were judged to assert it already and settled with their tests unchanged,
of which 2 were then caught after their proof was sharpened. No code under test, page or rule
was changed to clear a finding, and no strengthened test failed on the code as it stands.

The three rules that read `spot-checked`:
- `evidence` RULE-32: its one proof needs Windows, and no bug is planted here for it.
- `planted_bug` RULE-8: the model found no change to the file that would break the proof.
- `upstream` RULE-36: PROOF-60 was judged sound, and two bugs got past it.

The sign-off's list names 3 proofs settled with their tests unchanged: `run_script` PROOF-221,
`update` PROOF-19 and `upstream` PROOF-60.

Proofs changed by the owner's answers: `package` PROOF-15, `ai_audit` PROOF-185, `drift`
PROOF-40, `purlin_docs` PROOF-24 and `skill_init` PROOF-24 say more; `run_script` gained
PROOF-326, run on Windows alone.

What the audit showed about Purlin itself, open for the owner:
- **A test whose name begins with another test's whole name is left out with it.** The run
  tells pytest which tests to leave out, and pytest matches those names by prefix
  (`leave_out` in `scripts/mcp/purlin/frameworks.py`). One test was renamed around it.
- **A settle does not read the spot tests again for a rule with no surviving bug**, though
  the reference says it does; a spot-test finding is cleared by a plain audit alone.
- **A settle never starts a slow proof's test**, so a finding on a slow proof waits for
  `purlin:test --all` and then the settle.
- **An audit result is kept while a test's own lines are unchanged**, so a test fixed
  through its helper is not read again until its body changes.
- **Any commit puts an anchor's audit results out of date**, as decision 100 says; the
  anchor is audited last, after the last commit.
- **`purlin_report` PROOF-233** says the dashboard's data names the first 7 characters of the
  commit; it holds all 40 and the page shortens it. **`renumber` PROOF-18** names less than
  its case shows: the plan line `login: > Highest-Proof: 10 becomes 11.`

## What is left

1. The owner's review: the release notes, the README, the docs, the deck.
2. The owner's answers on what the audit showed about Purlin itself, above.
3. `purlin:sign` on Purlin, the tag pushed, `main` pushed. Nothing refuses a sign-off as of the
   last run; any commit puts the refusal back and `purlin:test --all --commit` clears it.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with everything needed to answer
  inside the question and the recommended option first. Name a thing by what a person sees,
  never by the code's word for it.
- **Maximum parallelization, cut by ownership of files.** Each agent has its own worktree and
  scratch folder and owns files no other agent writes. What one produces and another consumes
  is fixed word for word before they start.
- **No push, no pull request, no tag and no signing by any agent**, but the run branch
  `python3 dev/windows_run.py` pushes and deletes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Run with the project's `.venv` first on PATH.** The system `python3` has no pytest.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, both themes, before saying it is done. On the dashboard a cell is one word where
  it can be.
- **A clean release.** Nothing that represents earlier functionality stays. `RELEASE_NOTES.md`
  is the one place history is kept.
- **No statement about cost** in anything that ships.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`.
- **A sign-off is optional.** Many projects will never sign; a page or a line names it as a
  choice.
- **Any commit after the last full run puts the sign-off's refusal back**; `purlin:test --all
  --commit` then reruns only what that commit changed and carries the rest.
