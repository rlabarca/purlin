# Lane `audit`: decision 123, and the audit's part of decision 122

Branch `lane/d122-audit`, worktree `/Users/richlabarca/LocalCode/purlin-wt/d122-audit`.

## What was built

**Decision 122, section 2.9: no cost and no call count.**

- `scripts/review/audit_run.py`: `CALLS_ONE`, `CALLS_MANY`, `COST`, `EXPERIMENTAL`,
  `RUNTIME_PATH`, `write_costs` and `_plural` are deleted. The run prints each rule it read and
  the share, and writes no file under `.purlin/runtime/`. `planted_bugs` answers three values,
  not four: `asked` fed only the deleted file.
- `scripts/review/ai_audit.py`: `_cost`, `cost_usd`, `seconds` and `spent` are deleted from
  `ask_model`, `_call`, `audit_one` and `audit_all`.
- `dev/fake_claude.py`: `cost` is deleted.
- `ai_audit` RULE-45 and PROOF-121 are deleted with their test.
- `skills/audit/SKILL.md` and `references/review_criteria.md` lose every sentence on a cost or
  a count of calls.

**Decision 123: the audit aims its bug past the test.**

- `ai_audit.REQUEST_BUGS` is the plan's instruction, word for word. `ai_audit.REPLY_PARTS`
  shows a part with its `aim:` and `case:` lines.
- `targeted_break.parse_answer` reads the two lines. `aim` is `past the test` or `plain`;
  any other word, or no line, is `plain`. `case` is one line, outer spaces cut, at most 300
  characters.
- Two refusals, both before the copy is made and before any test runs: a part that names a
  change and no case (`the answer named no case of the proof`), and a change that differs from
  the lines it replaces only in blank lines and comment lines (`the change touches only a
  comment`). Both read `answer unusable` in `cause_of`.
- The entry under `breaks` carries `aim` and `case`. An entry that carries neither is read as
  `plain` and `''`.
- A bug that survived adds two findings, the second `targeted_break.AI_SAYS`, for a bug planted
  now and for a kept one (`audit_run.survived_findings`). A kept entry with no case adds the
  first alone.
- `references/review_criteria.md`: "The planted bug" and "What the model is sent, and what it
  decides" are rewritten; "What the audit reports" names the second finding and the two new
  fields; checks 4 and 6 say what Konstantinou et al. measured.
- `skills/audit/SKILL.md`: the description of d122 section 6.9, step 2 of its list, Step 2's
  block with the second finding line and its bullet.
- `docs/audit.md` was checked against the code. Every line it shows is printed as shown.
  Nothing was changed on it.
- `dev/sample_lab.py` (new) builds the trial's sample lab project and audits it with the fake
  `claude`. `dev/fake_claude.py` gains `change(path, before, after, case, aim)`.

## Rules and proofs, word for word

### `ai_audit`

`> Highest-Rule:` 45 before, 50 after. `> Highest-Proof:` 124 before, 135 after.

Deleted:

- RULE-45: Before its first call the audit prints `The audit reads <n> rules: <n> model calls.`, and after its last, where `claude` reported a cost, `The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.`, the sum of what each call reported
- PROOF-121 (RULE-45): The audit reads 2 rules and each call reports `total_cost_usd` `0.05`; it prints `The audit reads 2 rules: 2 model calls.` before the first call and, after the last, `The model was asked 2 times for 2 rules: $0.10 in all, $0.05 a rule.`

Added:

- RULE-46: Where a bug is to be planted the request says each proof's test is shown, asks for the smallest change after which the case the proof names gives a different result from the one it names, says to choose the change the proof's test, as it is written, is most likely to miss, or the plainest such change where the test checks the proof's case and its result, and rules out a change that leaves the proof's case as it was
- RULE-47: The shape the request gives for a proof's part holds, before `file:`, a line `aim:` taking `past the test` or `plain` and a line `case:` taking the proof's case, the result the proof names and the result the changed code gives
- RULE-48: A planted bug's entry under `breaks` carries `aim`, either `past the test` or `plain`, and `case`, the model's line for it
- RULE-49: A planted bug that survived adds two findings to its rule, `<PROOF-N>: the test still passes when <file>:<line> reads "<the changed line>"` and directly after it `<PROOF-N>: the AI says this breaks: <case>`, whether the bug was planted by this audit or kept from an earlier one, and the audit prints both under the rule
- RULE-50: A planted bug that was caught adds no finding to its rule

- PROOF-125 (RULE-46): The audit reads `sample_intake RULE-3` of the sample lab project; its request holds, after the source of the test, `Plant one bug for each of: PROOF-5.`, `Each proof's test is shown above.` and `the case the proof names gives a different result from the one it names`
- PROOF-126 (RULE-46): The request for `sample_intake RULE-3` holds the sentence `Choose the change the proof's test, as it is written, is most likely to miss: a value it never compares, a case other than the proof's, an expected value taken from the code.`
- PROOF-127 (RULE-46): The request for `sample_intake RULE-3` holds the sentences `Where the test checks the proof's case and its result, make the plainest such change.` and `Never a change that leaves the proof's case as it was, and no comment about the bug.`
- PROOF-128 (RULE-47): The request for `sample_intake RULE-3` shows a part as the lines `=== PROOF-5 ===`, `aim: <past the test, or plain>`, `case: <the proof's case; the result the proof names; the result the changed code gives>` and `file: <the path, as given above>`, one after the other
- PROOF-129 (RULE-48): The model's part for `PROOF-5` reads `aim: past the test` and `case: a sample collected at 2026-03-01T08:00 and received at 2026-03-02T09:30; the proof names an age of 25 hours; the changed code gives 26 hours`; after the audit, the entry of `PROOF-5` under `breaks` holds that `aim` and that `case`
- PROOF-130 (RULE-48): The model's part for `PROOF-6` reads `aim: plain`; after the audit, the entry of `PROOF-6` under `breaks` reads `aim` `plain`
- PROOF-131 (RULE-49): The test of `PROOF-5` takes its expected age from the code's own helper, and the model's bug rounds that helper to the nearest hour; `sample_intake RULE-3` reads `weak`, with the finding `PROOF-5: the test still passes when src/intake.py:17 reads "return int(round(seconds / 3600))"`
- PROOF-132 (RULE-49): Under `sample_intake RULE-3` the audit prints, on the line after that finding, `  PROOF-5: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-02T09:30; the proof names an age of 25 hours; the changed code gives 26 hours`
- PROOF-133 (RULE-49): The model's bug for `PROOF-3` hands back the record of `LC-12345678` and stores nothing, and the test still passes; the second finding of `sample_intake RULE-2` reads `PROOF-3: the AI says this breaks: ` and then the model's case word for word, ending ``never stores it, so the bench's `received` stays empty``
- PROOF-134 (RULE-49): The sample lab project is audited again, every rule read again and nothing changed; the request for `sample_intake RULE-3` asks for no bug, and the entry of `RULE-3` holds the same two findings for `PROOF-5`, in the same order
- PROOF-135 (RULE-50): The test of `PROOF-6` checks the proof's own case, and the model's bug sets the limit to 73 hours with `aim: plain`; the bug is caught, `sample_intake RULE-4` reads `strong`, its `findings` are empty, and no line the audit prints names `PROOF-6`

Reworded, the Description: `once for the rule's planted bugs and its reading` reads `for a
small bug for each proof, aimed past that proof's test, and for its reading`, and it gains `A
bug that survived is shown with the case the model says it breaks.`

No other rule or proof was reworded. PROOF-96's wording stands; its test now reads both
findings.

### `planted_bug`

`> Highest-Rule:` 14 before, 18 after. `> Highest-Proof:` 21 before, 31 after.

Added:

- RULE-15: A part's `aim:` line is recorded as `past the test` or `plain`, and any other word, or a part with no `aim:` line, is recorded `plain`
- RULE-16: A part's `case:` line is kept as the model wrote it, with outer spaces cut and at most its first 300 characters
- RULE-17: A part that names a change and holds no `case:` line, or an empty one, is not planted: the result reads `not made` with the reason `the answer named no case of the proof`, the audit prints `No bug was planted: the model's answer for <PROOF-N> could not be used: the answer named no case of the proof.`, and the proof's test is not run
- RULE-18: A change that differs from the lines it replaces only in blank lines and comment lines is not planted: the result reads `not made` with the reason `the change touches only a comment`, the audit prints `No bug was planted: the model's answer for <PROOF-N> could not be used: the change touches only a comment.`, and the proof's test is not run; a comment line starts, after its indent, with `//` in any file or with `#` in a file ending `.py`, `.sh`, `.bash`, `.rb`, `.yml`, `.yaml` or `.toml`

- PROOF-22 (RULE-15): The model's part for `PROOF-1` opens `aim: past the test`; after the audit, the bug's entry reads `aim` `past the test`
- PROOF-23 (RULE-15): The part for `PROOF-1` opens `aim: around the test` and the part for `PROOF-2` holds no `aim:` line; after the audit, each bug's entry reads `aim` `plain`
- PROOF-24 (RULE-16): The part for `PROOF-1` holds the line `case:   a stamp of 2026-01-01; the proof says 90; the changed code gives 0  `; after the audit, the bug's entry reads `case` `a stamp of 2026-01-01; the proof says 90; the changed code gives 0`
- PROOF-25 (RULE-16): The part's `case:` line holds 320 characters; after the audit, the bug's entry holds a `case` of its first 300
- PROOF-26 (RULE-17): The part for `PROOF-1` names `file: src/age.py`, `before:` `return days` and `after:` `return 0` and holds no `case:` line; the audit prints `age RULE-1   spot-checked` and under it `  The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: the answer named no case of the proof.`, and the test of `PROOF-1` runs in no copy of the project
- PROOF-27 (RULE-17): The part for `PROOF-1` holds the line `case:` with nothing after it; the bug's entry reads `not made` with the reason `the answer named no case of the proof`
- PROOF-28 (RULE-18): The model's change adds the one line `# off by one` above `return days` in `src/age.py`; the audit prints `  The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: the change touches only a comment.`, and the test of `PROOF-1` runs in no copy of the project
- PROOF-29 (RULE-18): The feature covers `src/age.js`, and the model's change adds the one line `// planted` to it; the bug's entry reads `not made` with the reason `the change touches only a comment`
- PROOF-30 (RULE-18): The feature covers `src/notes.txt`, and the model's change adds the one line `# 90` to it; the bug is planted, and its entry reads `survived`
- PROOF-31 (RULE-18): The model's change turns `return days` into the two lines `# planted` and `return 0`; the bug is planted, and its entry reads `caught`

Reworded, the Description:

```
> Description: One planted bug per proof, aimed past that proof's test, the audit's third step.
>   For a proof whose test or covered code changed since the audit last read it, the model is
>   shown the proof, its test and the code, and asked for the smallest change to one file the
>   feature covers after which the case the proof names gives a different result, choosing the
>   change that test is most likely to miss, and for the case the change breaks. The change is
>   made in a copy of the project, never in the project itself, and only the proof's own test
>   runs against it there; the copy is then deleted. A test that still passes reads `survived`,
>   with the change as the finding and the case the model named under it; a test that ran and
>   failed reads `caught`; a test that did not run reads `not run`; a change that cannot be made,
>   names no case or touches only a comment reads `not made`. A check before the model is asked
>   and after the last bug stops the audit if the project changed.
```

### `skill_audit`

`> Highest-Rule:` 29 and `> Highest-Proof:` 59, both unchanged. The Description's `the
heuristic spot tests, one model call per rule and one planted bug per proof, writes` reads `the
heuristic spot tests and one planted bug per proof, aimed past that proof's test, writes`.

## What was seen failing first

- **The cost removal.** `git grep -n -i -E 'cost_usd|total_cost|audit_run\.json|CALLS_|EXPERIMENTAL'
  -- scripts dev/fake_claude.py dev/test_ai_audit.py` printed 33 lines before, and nothing
  after. Two of them were names in `dev/test_ai_audit.py` that only matched `CALLS_`:
  `SETUP_CALLS_LOGIN_TEST` is now `FIXTURE_USES_LOGIN_TEST`, and
  `test_six_rules_six_calls_each_answer_beside_its_rule` is now
  `test_six_rules_are_each_asked_once_and_answered_in_order`.
- **Decision 123.** The specs and the tests were written first. Against the code as it stood,
  42 tests failed and 48 passed: all 11 tests of `ai_audit` PROOF-125 to 135, all 10 of
  `planted_bug` PROOF-22 to 31, and 21 existing tests whose fake reply now carries a `case:`
  line the old reader could not read. After the code, 90 passed.

## The tests run on sample projects

- `dev/sample_lab.py` holds the trial's three files, byte for byte: the spec `sample_intake`
  (8 rules, 12 proofs), `src/intake.py` and `tests/test_intake.py`. `audited(folder)` builds
  the project, runs its tests, and audits it twice with the fake `claude`. The 11 new tests of
  `ai_audit` read what those two audits printed and wrote. The project is built once for the
  module.
- The fake answers what the real model answered in the trial, variant `v3`, run 1: PROOF-3's
  and PROOF-5's change and case are copied word for word. PROOF-6's change is the trial's
  plain one, `MAX_AGE_HOURS = 73`.
- The 10 new tests of `planted_bug` each build the small `age` project of that file and run
  the audit there.
- What the audit prints on the sample lab:

```
sample_intake RULE-2   weak
  PROOF-3: the test still passes when src/intake.py:52 reads "return record"
  PROOF-3: the AI says this breaks: a sample with the barcode `LC-12345678` is handed in; the proof names it stored with the status `accepted`; the changed code returns a record with status `accepted` but never stores it, so the bench's `received` stays empty
  No bug was planted: the model's answer for PROOF-4 could not be used: it holds none.
sample_intake RULE-3   weak
  PROOF-5: the test still passes when src/intake.py:17 reads "return int(round(seconds / 3600))"
  PROOF-5: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-02T09:30; the proof names an age of 25 hours; the changed code gives 26 hours
sample_intake RULE-4   strong
  No bug was planted: the model's answer for PROOF-7 could not be used: it holds none.
The audit found 1 of 8 rules strong (12%): 1 strong, 3 weak, 4 spot-checked.
```

## Lines a person reads that this lane chose

The plan gave the request's instruction, the two reasons, the second finding and the skill's
step 2. These it did not give:

1. The request's sentence above the shape of a part, in `ai_audit.REPLY_PARTS`, read by the
   model: `Answer in this shape and with nothing else. One part for each proof named above,
   the lines under before: copied exactly from the file, and aim: reading plain where the
   proof's test leaves no way past it:`
2. The `aim:` line of that shape: `aim: <past the test, or plain>`. The `case:` line is the
   plan's.
3. `references/review_criteria.md`, the intro: `the heuristic spot tests; then the model is
   asked for a small bug for each proof, aimed past that proof's test, and for its reading;
   then each bug is planted and its proof's test run.`
4. `references/review_criteria.md`, "The planted bug", in full. Its new sentences:
   - `The audit runs each proof's own test against one small change to the code, aimed past
     that test.`
   - `the model is shown the proof, its test and each file the feature covers. It is asked for
     the smallest change to one of those files after which what the proof says no longer
     holds: the case the proof names gives a different result from the one it names.`
   - `**The aim.** Of the changes that break the proof's case, the model chooses the one the
     proof's test, as it is written, is most likely to miss: a value the test never compares, a
     case other than the proof's, an expected value the test takes from the code. Where the
     test checks the proof's case and its result, no change gets past it, and the model makes
     the plainest change that breaks the case. A change that leaves the proof's case as it was
     is never the bug, and the change carries no comment about the bug.`
   - `` `aim:` reads `past the test`, or `plain` where the test leaves no way past it. Any
     other word, or no `aim:` line, is recorded `plain`. ``
   - `` `case:` is one line: the proof's case, the result the proof names and the result the
     changed code gives. It is the model's claim, and the audit does not check it. It is kept
     as written, up to 300 characters. ``
   - `**Caught.** ... The test noticed, and nothing is added to the rule's findings.`
   - `**Survived.** ... The rule reads weak, with two findings, the change and then the case
     the model says it breaks:`, the two lines, then `A person reads the second line to judge
     the first.`
   - `Two of those reasons are refusals of a change the model did name:`, the two printed
     lines, `The part holds no case: line, or an empty one.` and `The lines after the change
     differ from the lines before it only in blank lines and comment lines. A comment line
     starts, after its indent, with // in any file, or with # in a file ending .py, .sh,
     .bash, .rb, .yml, .yaml or .toml.`
   - `a kept bug that survived adds its two findings again.`
   - The example part's case, taken from `docs/audit.md`: `a sample collected 90 minutes ago;
     the proof says 90; the changed code gives 150`.
5. `references/review_criteria.md`, "What the model is sent, and what it decides": `The model
   is asked for a small bug for each proof and for its reading. The request holds this file,
   ... then the proofs to plant a bug for, the aim of "The planted bug" and the text of each
   file the feature covers. ... The model decides nothing: the test run says whether a bug was
   caught, the case it names is shown as its claim, and its reading explains.`
6. `references/review_criteria.md`, "The call": `Each request is written to the command's
   standard input and given 300 seconds:`
7. `references/review_criteria.md`, "What the audit reports": `the spot tests' sentences and,
   for each planted bug that survived, the change and then the case the model says it breaks`,
   and `each planted bug under breaks with its aim, its case, its file, line, ...`.
8. `references/review_criteria.md`, check 4: `Shown buggy code, a model more often rejects the
   right expected answer`. Check 6: `and a model shown buggy code more often rejects the right
   expected answer`.
9. `skills/audit/SKILL.md`, the opening paragraph: `a small bug the model writes for each
   proof, aimed past that proof's test, with its reading of the tests`.
10. The case of the fake's plain bug for PROOF-6, which the trial's plain bugs did not carry:
    ``a sample collected at 2026-03-01T08:00 and received at 2026-03-04T09:00, 73 hours later;
    the proof names it stored as `expired`; the changed code stores it as `accepted` ``. It is
    read only by a test.

## Calls this lane made that the plan did not

- **A new file, `dev/sample_lab.py`.** The plan asks for one helper and names no file. Two
  test files use it, so it is a module of its own. No lane owns it.
- **Where the two refusals stand among the checks.** Both come directly after the part is
  read, before the path checks. A part with no case that also names a file outside the scope
  reads `the answer named no case of the proof`.
- **A change that leaves the lines as they were** is not a comment-only change. It still reads
  `the change leaves <file> as it was`.
- **A trailing comment on a line of code** is a change to a code line and is planted. The
  plan's definition is of a comment line.
- **An entry with no change** (`no break`, no part, a part that cannot be read) records `aim`
  `plain` and `case` `''`, so both fields are always strings.
- **`ai_audit` RULE-2, RULE-3 and RULE-4 and their proofs stand as they were.** None says how
  the bug is chosen. RULE-4's `One call is made per rule` and PROOF-113's `started exactly 1
  time` hold the call as a mechanism, which the plan keeps. The new instruction is RULE-46,
  not a longer RULE-2.
- **The refusals' printed lines are proofs of `planted_bug`** (RULE-17, RULE-18), beside the
  result they print, as RULE-6 already holds a printed line. `ai_audit` gains no rule for them.
- **`four at once` leaves `references/review_criteria.md`** with `One call per rule`: the
  sentence counted calls. The command block stays.
- **`audit_run.planted_bugs` answers three values.** The fourth fed only the deleted file.
- **A duplicate `_number` in `audit_run.py`** was deleted in passing.
- **`fake_claude.change`** builds a part, so the three test files write one shape.
- **Existing tests that asserted only `not made`** for a path outside the copy, a change found
  twice and a file out of scope now assert the reason too. With a `case:` required, `not made`
  alone would pass for the wrong reason.

## The acceptance

- The six files, `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`,
  `dev/test_planted_bug.py`, `dev/test_plain_checks.py`, `dev/test_skill_audit.py` and
  `dev/test_purlin_docs.py`: `121 passed`, before and after the rebase onto `main` at
  `e02c9b4f5`.
- The grep prints nothing.
- `bash dev/run_tests.sh --fast`: `855 passed, 9 skipped`, `Suites: 1 passed, 0 failed`, on the rebased branch. No failure, so nothing waits on another lane.

## One thing to know

While its first fast sweep was being restarted, this lane ran `pkill -f "dev/run_tests.sh"`. The
pattern was not limited to this worktree, so a sweep another lane had running at that moment
may have been stopped by it. Whether one was running was not checked. A lane whose sweep ended with no result around then should run it again.

## Left, or waiting on another lane

- **The formats.** `evidence_format.md` and `package_format.md` gain `aim` and `case` at
  integration, by the coordinator.
- **`words`.** `docs/running-and-evidence.md`, `references/purlin_commands.md` and
  `RELEASE_NOTES.md` still carry the cost lines and `one model call`; they are that lane's.
  `references/spec_quality_guide.md`'s cell table does not name the second finding.
- **`surfaces`.** `dev/fixtures/report/regulated.json` shows a surviving bug with one finding.
  A second line there would show the dashboard's `Audit` panel with the AI's case.
- **The audit of Purlin itself** is the coordinator's, once, at integration.
