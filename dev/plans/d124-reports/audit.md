# Lane `audit`: decision 124, the report

Branch `lane/d124-audit`, rebased on `main` at `2dedc6eff`. Built from `dev/plans/d124-plan.md`,
section 1, the one new section of `references/review_criteria.md`, and the lane's row of
section 4. Nothing was pushed, tagged or signed, and Purlin's own code was not audited.

## What was built

1. **`--settle`.** `scripts/run/purlin_run.py --audit --feature <name> --settle RULE-N`, given
   once per rule. The run script parses it, refuses it and hands the rules to the audit;
   `scripts/review/audit_run.py` settles them (`bug_plan` under `settle`, `replayed`,
   `planted_bugs`' `second` proof, `run`); `scripts/review/targeted_break.py` gains `replay`,
   which plants a recorded change with every refusal `break_proof` has and asks no model.
2. **The three faults left from the code review** (`review-audit.md` A5, the rest of A8, A11),
   in `targeted_break.py` and `audit_run.no_bug_sentence`.
3. **`ai_audit` PROOF-122** reworded to the proposed sentence, its test counting the calls.
4. **`references/review_criteria.md`** gains "Settling a finding", the one home of the contract.
   `references/formats/evidence_format.md` gains the new `why` and the `no_bug` sentence in its
   wording. No field was added and `> Format-Version:` stays 13.
5. **Tests on sample projects.** `dev/sample_lab.py` gains `settled`, which builds the lab,
   audits it once and runs the script with `--settle` as its own process; the small `login`
   project of `dev/test_ai_audit.py` and the `age` project of `dev/test_planted_bug.py` carry
   the rest. Every call lands on the fake `claude`.

`scripts/review/ai_audit.py`, `dev/fake_claude.py` and `dev/test_ai_audit_tests_named.py` needed
no change. `dev/test_run_script.py` was run and not changed.

## The commits

| Commit | What it holds |
|---|---|
| `fix(planted_bug): a reason is classed by where it came from, a wrapped case is read, and a directive line is code` | the three faults, `planted_bug` RULE-27 to 30, PROOF-51 to 58, one sentence of the criteria |
| `spec(ai_audit): PROOF-122 names the three ways the model is not reached` | the reworded proof and its test |
| `spec(planted_bug): PROOF-52 within 60 words` | one proof shortened |
| `feat(ai_audit): purlin:audit --settle plants a kept bug again and runs the test as it stands` | the settle code, `ai_audit` RULE-52 to 64, PROOF-138 to 158, both references |

## The `> Highest-*` lines

| Spec | Before | After |
|---|---|---|
| `ai_audit` | rule 51, proof 137 | rule 64, proof 158 |
| `planted_bug` | rule 26, proof 50 | rule 30, proof 58 |

No number is used again and none was deleted.

## Rules and proofs, word for word

Reworded, `ai_audit`:

- PROOF-122 (RULE-1): `RULE-2`'s entry reads `spot-checked` because the model could not be reached, whether `claude` exited with an error, was not on PATH or gave no answer, and nothing has changed since; the audit run again, with a `claude` that answers, reads `RULE-2` and starts `claude` exactly `1` time

Also changed in `ai_audit`: the `> Description:` gains two sentences on `--settle`. Nothing was
deleted in either spec.

### `ai_audit`

Added:

- RULE-52: `--settle RULE-N` is taken only beside `--audit` and exactly one `--feature`: any other use is refused before a test starts, with exit 2, and a rule the feature's spec does not have with exit 1 and `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`
- RULE-53: An audit run with `--settle` reads the rules it names and no other rule
- RULE-54: Settling a rule plants again each bug its entry keeps as `survived`, with no model asked, and runs that proof's tests as they stand; where a test fails, the bug's entry reads `caught` with the same `file`, `line`, `before`, `after`, `aim` and `case`, its two findings leave the rule, and the audit prints under the rule `  <PROOF-N>: the test now catches the bug it missed at <file>:<line>.`
- RULE-55: A bug planted again that its proof's tests still pass with is dropped: the model is asked for one new bug for that proof, in the request any audit sends, the new bug is planted as any is, and the audit prints under the rule `  <PROOF-N>: the bug at <file>:<line> did not break what the proof says. A new bug was planted.`
- RULE-56: Where the new bug survives as well, no bug is kept for the proof: its entry reads `not made` with the reason `two planted bugs left the proof's check passing`, `no_bug` gains `No bug was caught for <PROOF-N>: two planted bugs left the proof's check passing.`, and no audit plants a bug for the proof again until its test or code changes
- RULE-57: A dropped bug is kept nowhere in the evidence: not under `breaks` and not among the `findings`
- RULE-58: Where no new bug is planted after a drop, because the model names none, its part cannot be used or the model cannot be reached, `no_bug` holds the sentence that case has in any audit, and the line the audit prints for the drop ends at `did not break what the proof says.`
- RULE-59: A bug planted again whose test does not run with it in place, because it is skipped, ends in an error or runs past its limit, reads `not run`
- RULE-60: A kept bug whose recorded change can no longer be planted is read as any audit reads its proof: one new bug is asked for, and one that survives reads `survived`
- RULE-61: Settling a rule leaves a proof with no bug kept as `survived` with the entry it has
- RULE-62: A rule named with `--settle` that keeps no bug as `survived` prints `<feature> <RULE-N> has no planted bug that survived: nothing to settle.`, and its entry is left as it is
- RULE-63: A rule named with `--settle` whose tests do not pass is not settled: its entry is left as it is, and the run exits 1 and names the rule as failing
- RULE-64: Only `--settle` plants a recorded bug again: any other audit asks the model for a new bug for a proof whose test changed
- PROOF-138 (RULE-52): The run is started on the sample lab project with `--test --feature sample_intake --settle RULE-3`; it exits 2, prints `purlin: --settle goes with --audit.` and starts no test
- PROOF-139 (RULE-52): The run is started with `--audit --settle RULE-3` and no `--feature`; it exits 2, prints `purlin: --settle needs exactly one --feature.` and starts no test
- PROOF-140 (RULE-52): The run is started with `--audit --feature sample_intake --feature billing --settle RULE-3`; it exits 2, prints `purlin: --settle needs exactly one --feature.` and starts no test
- PROOF-141 (RULE-52): The run is started with `--audit --feature sample_intake --settle RULE-99`; it exits 1, prints only `sample_intake RULE-99 is not a rule any spec has. Run purlin:status sample_intake to see its rules.`, starts no `claude` and leaves the evidence file as it was
- PROOF-142 (RULE-53): `RULE-2` and `RULE-3` of the sample lab project each read `weak`; the audit is run with `--settle RULE-2 --settle RULE-4`; it prints one line opening `sample_intake RULE-2   ` and none opening `sample_intake RULE-3   `, asks `claude` about `RULE-2` alone, and the entry of `RULE-3` is as it was
- PROOF-143 (RULE-54): The bug kept for `PROOF-5` rounds the helper its test takes the expected age from, and reads `survived`; the test is changed to expect `25` and `RULE-3` is settled; the entry of `PROOF-5` reads `caught` with the same change, `RULE-3` reads `strong` with no finding, and `claude` is started `0` times
- PROOF-144 (RULE-54): The test of `PROOF-5` is changed to expect `25` and `RULE-3` is settled; under `sample_intake RULE-3   strong` the audit prints exactly `  PROOF-5: the test now catches the bug it missed at src/intake.py:17.`
- PROOF-145 (RULE-55): The test of `PROOF-5` still takes its expected age from the helper, and `RULE-3` is settled with a model whose new bug adds 1 to the age the record stores; `claude` is started exactly `1` time, asked for `PROOF-5` alone, the new bug reads `caught`, and `RULE-3` reads `strong`
- PROOF-146 (RULE-55): The kept bug for `PROOF-5` still survives and the model's new bug is caught; under `sample_intake RULE-3   strong` the audit prints exactly `  PROOF-5: the bug at src/intake.py:17 did not break what the proof says. A new bug was planted.`
- PROOF-147 (RULE-56): The kept bug for `PROOF-5` and the model's new bug both survive; the entry of `PROOF-5` reads `not made` with the reason `two planted bugs left the proof's check passing`, its `no_bug` sentence is `No bug was caught for PROOF-5: two planted bugs left the proof's check passing.`, and `claude` was started exactly `1` time
- PROOF-148 (RULE-56): Two bugs for `PROOF-5` were dropped; every rule is then read again with nothing changed; the request for `RULE-3` asks for no bug, and `RULE-3` still reads `spot-checked` with `No bug was caught for PROOF-5: two planted bugs left the proof's check passing.`
- PROOF-149 (RULE-57): Two bugs for `PROOF-5` were dropped; the evidence file of `sample_intake` holds neither `return int(round(seconds / 3600))` nor `return int(seconds // 3600) + 1`, and the entry of `RULE-3` holds no finding
- PROOF-150 (RULE-58): The bug kept for `PROOF-2` still survives, and the model answers `no break: nothing breaks it`; the audit prints `  PROOF-2: the bug at src/login.py:12 did not break what the proof says.` and then `  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-2: nothing breaks it.`
- PROOF-151 (RULE-58): The bug kept for `PROOF-2` still survives, and `claude` exits `1`; no bug is on record for `PROOF-2`, `RULE-2` reads `spot-checked`, and its `no_bug` is exactly `No bug was planted: the model could not be reached: claude exited with an error.`
- PROOF-152 (RULE-59): The test of `PROOF-2` is changed to skip where the status is not `401`, and `RULE-2` is settled; the entry of `PROOF-2` reads `not run` and still holds `return 200`, `RULE-2` reads `spot-checked` with `A bug was planted for PROOF-2 and its test did not run.`, and `claude` is started `0` times
- PROOF-153 (RULE-60): The helper's line `return int(seconds // 3600)`, which the bug kept for `PROOF-5` changes, is written as two lines, and `RULE-3` is settled; `claude` is asked for `PROOF-5`, its bug `hours = seconds // 3600 + 1` reads `survived`, and under `sample_intake RULE-3   weak` the audit prints that bug's two findings and nothing else
- PROOF-154 (RULE-61): `RULE-2` has `PROOF-3`, whose bug reads `survived`, and `PROOF-4`, whose entry reads `not made`; `RULE-2` is settled; `claude` is asked a bug for `PROOF-3` alone, and the entry of `PROOF-4` is as it was
- PROOF-155 (RULE-62): `RULE-4` reads `strong`, its one bug `caught`; named with `--settle`, the audit prints `sample_intake RULE-4 has no planted bug that survived: nothing to settle.` once and no line opening `sample_intake RULE-4   `, and the entry of `RULE-4` is as it was
- PROOF-156 (RULE-63): The test of `PROOF-5` is changed to expect `24`, so it fails, and `RULE-3` is named with `--settle`; the run exits 1 and prints `sample_intake RULE-3 fails: tests/test_intake.py::test_age_is_whole_hours. Run purlin:build sample_intake.`, the entry of `RULE-3` is as it was, and `claude` is started `0` times
- PROOF-157 (RULE-64): The test of `PROOF-5` is changed to expect `25`, and `sample_intake` is audited without `--settle`; `claude` is asked a bug for `PROOF-5`, the entry of `PROOF-5` holds the model's change `return int(seconds // 1800)` and reads `caught`, and the audit prints no line under `sample_intake RULE-3`
- PROOF-158 (RULE-56): The kept bug for `PROOF-5` and the model's new bug both survive; the audit prints `sample_intake RULE-3   spot-checked`, then `  PROOF-5: the bug at src/intake.py:17 did not break what the proof says. A new bug was planted.`, then `  The spot tests found nothing. No bug was caught for PROOF-5: two planted bugs left the proof's check passing.`

### `planted_bug`

Added:

- RULE-27: A `not made` result is worded by where its reason came from: a reason the model gave on a `no break:` line prints `No bug was planted: the model found no change that would break <PROOF-N>: <why>.` whatever its words, when the bug is asked for and each time the kept result is read again
- RULE-28: A `case:` line wrapped over a second line is read to the end of that second line, the two joined by one space, where the second line is not blank and opens none of `aim:`, `case:`, `file:`, `before:`, `after:`, `no break:` or `===`
- RULE-29: A `case:` line standing after the `file:` line and before `before:` is read as one above `file:` is
- RULE-30: A line opening `#!`, `//go:` or `// @ts-` is code to the comment check, so a change to one is planted
- PROOF-51 (RULE-27): The part for `PROOF-1` reads `no break: the refund path the proof names is not in the project`; the audit prints `age RULE-1   spot-checked` and under it `  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-1: the refund path the proof names is not in the project.`
- PROOF-52 (RULE-27): `PROOF-1` keeps the result of `no break: the refund path the proof names is not in the project`; the rule is read again with nothing changed, and the audit prints `  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-1: the refund path the proof names is not in the project.`
- PROOF-53 (RULE-28): The part for `PROOF-1` holds the line `case: a stamp of 2026-01-01; the proof says 90;`, then the line `the changed code gives 0`, then `file: src/age.py`; the bug is planted and reads `caught`, and its entry reads `case` `a stamp of 2026-01-01; the proof says 90; the changed code gives 0`
- PROOF-54 (RULE-28): The line after `case: a stamp of 2026-01-01; the proof says 90` reads `aim: past the test`; the bug's entry reads `case` `a stamp of 2026-01-01; the proof says 90` and `aim` `past the test`
- PROOF-55 (RULE-29): The part for `PROOF-1` reads `file: src/age.py`, then `case: a stamp of 2026-01-01; the proof says 90; the changed code gives 0`, then `before:`; the bug is planted and reads `caught`, and its entry reads `case` `a stamp of 2026-01-01; the proof says 90; the changed code gives 0`
- PROOF-56 (RULE-30): The feature covers `src/run.sh`, and the model's change turns its first line, `#!/bin/sh`, into `#!/bin/bash`; the bug is planted, and its entry reads `survived`
- PROOF-57 (RULE-30): The feature covers `src/age.go`, and the model's change turns its line `//go:build linux` into `//go:build windows`; the bug is planted, and its entry reads `survived`
- PROOF-58 (RULE-30): The feature covers `src/age.ts`, and the model's change adds the one line `// @ts-ignore` above `return 90;` in it; the bug is planted, and its entry reads `survived`


## What was seen failing first

- `planted_bug` PROOF-51, 52, 53, 55, 56, 57 and 58: 7 failed before the fix, each on the
  fault it names (`could not be used` in place of `found no change`; `not made` in place of
  `caught` or `survived`).
- `planted_bug` PROOF-54 passed before and after. It bounds RULE-28: an `aim:` line after the
  case is no second line of it.
- `ai_audit` PROOF-138 to 156 and 158: 19 failed before the settle code, the refusals on their
  printed line, the rest on `--settle` being an unknown argument.
- `ai_audit` PROOF-157 passed before and after. It holds what the plan says is unchanged: an
  audit without `--settle` replays nothing.
- `ai_audit` PROOF-122's test passed before and after; the code it covers did not change.

## The acceptance

- `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py` and
  `dev/test_run_script.py`: `219 passed in 235.60s (0:03:55)`, after the rebase.
- `bash dev/run_tests.sh --fast`: `956 passed, 9 skipped in 690.41s (0:11:30)`, then `Suites: 1 passed, 0 failed`, after the rebase. No failure, so none waits on another lane.

## Lines a person reads that this lane chose

The plan gives the lines of the contract, used word for word. These it does not give:

- `purlin: --settle goes with --audit.`
- `purlin: --settle needs exactly one --feature.` One line for no feature and for two.
- `purlin: --settle needs a rule, as RULE-N.` Where `--settle` is the last argument.
- The usage's third line: `purlin_run.py --feature NAME --audit --settle RULE-N [--settle
  RULE-N ...] [--commit] [--write-tests] [--arm-timeout SECONDS] [--project-root DIR]`.
- `  PROOF-2: the bug at src/auth.py:12 did not break what the proof says.` The plan's line
  without its second sentence, printed where the bug was dropped and no new bug was planted.
- The prose of "Settling a finding", the sentence added to the comment check's paragraph and
  to "What the audit reports" in `references/review_criteria.md`, and the paragraph added to
  `references/formats/evidence_format.md`.

## Calls the plan did not make

1. **`A new bug was planted.` is left off where none was.** After a drop, where the model
   answers `no break`, its part cannot be used or it cannot be reached, the line ends at
   `did not break what the proof says.` The plan's full line would stand directly above
   `No bug was planted: ...`.
2. **Any refusal of the replay counts as "can no longer be planted".** The plan names the
   `before` lines not being in the file exactly once. A file out of scope, a file gone, a
   recorded bug with no case and a test that does not pass in the copy are read the same way:
   a new bug is asked for, as any audit asks.
3. **A settle that asks no model keeps the last entry's `model` and `criteria` and writes an
   empty `explanation` and no `notes`.** The reading on file described the test as it was.
4. **A rule named that does not pass its tests is skipped without a line of its own.** The
   run's `<feature> RULE-N fails: ...` line and its exit 1 say so; `nothing to settle` is not
   printed for it.
5. **A proof with no `survived` entry keeps its entry whatever its `break_key`,** and a proof
   with no entry at all is left with none. A later plain audit plants for either as it would
   have.
6. **A rule not in the spec is printed on standard output,** as `ai_audit.py` prints the same
   line, and before any test runs. The three exit 2 refusals go to the error output with the
   usage, as every refusal of the run script does.
7. **A kept `not made` result is worded from the sentence its audit wrote.** A5's fix carries
   the cause from where the reason came from, and the evidence has no field for it. For a kept
   result the audit finds its sentence under the last entry's `no_bug`; only an entry with no
   such sentence is read by the words of its reason, as before.
8. **A wrapped case is joined with one space, and one second line is read.** A blank second
   line is no part of the case.
9. **A line opening `#!`, `//go:` or `// @ts-` is code after any indent,** as a comment line
   is one after any indent. `planted_bug` RULE-18 and RULE-19 keep their words; RULE-30 states
   the three openings.
10. **The `--settle` rule and proofs of the run script are in `ai_audit`, and `ai_audit`'s
    `> Scope:` was not widened to `scripts/run/purlin_run.py`.** Widening it would end every
    `ai_audit` result on any change to the run script. So a bug for PROOF-138 to 141 can be
    planted only in the audit's own files, and those proofs will likely read `spot-checked`.
11. **`planted_bug` PROOF-52 and `ai_audit` PROOF-147 and 150 were shortened to 60 words**
    after first being written longer; PROOF-158 was split from PROOF-147.
12. **PROOF-143's same-change check compares `file`, `line`, `before`, `after`, `aim` and
    `case`** and that the `break_key` moved.

## What is left, and what waits on another lane

- **Lane `words`**: `references/purlin_commands.md` (the syntax), `skills/audit/SKILL.md`,
  `skills/build/SKILL.md`, `docs/audit.md`, the glossary. "Settling a finding" is the section
  they point at. The script's usage and its docstring already name `--settle`.
- **Lane `proofs`**: nothing is asked of `specs/run/run_script.md`. Its usage proofs still pass
  with the third usage line.
- **`scripts/run/evidence.py`** (no lane's file here): `_same_audit` does not compare `breaks`.
  Every settle outcome changes the verdict, the findings or a hash, so each is written; noted
  because a later change to settle should not rely on a `breaks`-only difference being written.
- **Decision 125** landed on `main` while this lane ran. Nothing of it was built here.
- **Not done by this lane, by the brief**: the loop on Purlin's own weak rules, the review by a
  reader that built none of it, the dashboard look, `python3 dev/windows_run.py`.
- **Windows**: the new tests start `purlin_run.py` as a process with the fake `claude` first on
  PATH, as `dev/test_planted_bug.py` already does. They were run on macOS only.
