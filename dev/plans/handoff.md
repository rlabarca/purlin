# Handoff, 2026-10-03: the goal-seek test, the stale sweep and decision 129

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
  say where a result was carried from. The evidence and package formats are at version 15;
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

Formats: spec 24, anchor 12, marker 5, evidence 15, package 15, signature 16.
The dashboard's data is schema 16.

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
   and `docs/sign-off.md` (carried results), `docs/upgrading.md` ("A project this release set
   up"), and the first ten minutes on the README and `docs/getting-started.md`.
2. **A finding can still leave with no stronger test**: where the code changed so that the
   unchanged test now fails with the old bug in place, the bug reads `caught`. The audit page
   says so.
3. **No real session has used `--settle --sound` or met the settle's refusal.** The second
   goal-seek session judged the sound test right and then audited again in place of settling.
   With the old bug now planted again, that audit would have left the rule `weak` and named
   `purlin:build`.
4. **A session runs the scripts directly** where a skill names `purlin:test` or
   `purlin:audit`, and guesses their options; a wrong guess got the usage line and was
   corrected at once.
5. **The first run commits the settings file without `--commit`**, after the yes to its
   question. Where the person gives a command of their own, the test skill tells the agent to
   make that commit.
6. **The code's own word for a planted bug is still `break`**: the file
   `scripts/review/targeted_break.py`, the evidence fields `breaks` and `break_key`, the
   model's reply line `no break:`. No person reads them.
7. **`docs/sign-off.md` and the package format use `(URS-042)` as their example**; kept, since
   tracing a requirement is the point made there.
8. **Left by earlier rounds, unchanged**: a rule can read `strong` while one of its proofs has
   no caught bug; the four rules on how `--settle` is typed read `spot-checked`; a plain
   `purlin:test` reruns a feature whose rule stays `not run`; `evidence_writer` RULE-16's "or
   `unknown`" has no proof; `ai_audit` RULE-56's "until its test or code changes" has no
   proof; a capitalised `No break:` is not read; a session's status tool keeps the code it
   loaded when the session started.
9. **`dev/plans/three-levels.md` still points at plan files deleted in earlier rounds**
   (`d100-plan.md`, `d115-plan.md`, `d119-plan.md`, `d122-plan.md` and others) and its parts A
   to C describe a design decisions 23 to 106 replaced. It is the decisions log and was left.
10. **`.github/workflows/windows.yml`'s setup step** still holds `if [ -f package.json ]; then
    npm ci; fi`, which this repository has no use for. Not changed, since it runs only on a
    push.
11. **The deck is published at version 135**: the `slow`, `signoff`, `remote`, `audit` and
    `start` slides say what decision 129, the audit and the first run now do. The live deck
    is changed whenever its source is; nothing waits for a later publish.

## What is left

1. The owner's review: the release notes, the README, the docs, the deck.
2. The audit of the specs whose results are out of date, settled, before signing. This round
   changed the audit's code again, so more read `out of date`.
3. `purlin:sign` on Purlin, the tag pushed, `main` pushed.

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
