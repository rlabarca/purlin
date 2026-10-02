# Lane `review-fixes`: the seven certain findings of the review

Branch `lane/d124-review-fixes`, cut from `main` at `c9196119a`. The review is beside this file,
`review.md`. Every edit, run and commit was made in the worktree
`purlin-wt/d124-review-fixes`. No test reaches a real model, Purlin was not audited, and nothing
was pushed, tagged or signed. Nothing under `.purlin/` is staged.

## 1. A settle keeps another proof's stale result (C1)

**Code.** `scripts/review/audit_run.py`, `bug_plan`: under `settle`, a result other than
`survived` is `kept` only where its `break_key` is the current one. Any other is left out of the
plan, as a proof with no result is. The entry the settle writes then holds no result for that
proof, `ai_audit.is_read` finds it missing, and the next plain audit plants a bug for it.

**Rules and proofs**, `specs/review/ai_audit.md`:

- RULE-61, reworded. Before: "Settling a rule leaves a proof with no bug kept as `survived` with
  the entry it has". After: "Settling a rule leaves a proof whose result is not `survived`, and
  whose test and code are unchanged since that result, with the entry it has"
- RULE-65, new: "Settling a rule keeps no result other than `survived` that was taken on another
  test or code: the proof is left out of the rule's entry, the rule's verdict comes from the
  results the entry holds, and the next audit without `--settle` plants a bug for that proof"
- PROOF-161 (RULE-65), new: "The bug of `PROOF-6` reads `caught` and the bug of `PROOF-7` reads
  `survived`; the test of `PROOF-7` is changed to hand in a sample exactly 72 hours old, the
  test of `PROOF-6` to check only that a status is stored, and `RULE-4` is settled; `RULE-4`
  reads `strong`, and its entry holds a result for `PROOF-7` alone"
- PROOF-162 (RULE-65), new: "`RULE-4` was settled after the test of `PROOF-6`, whose bug read
  `caught`, was changed to check only that a status is stored; `sample_intake` is then audited
  without `--settle`; `claude` is asked a bug for `PROOF-6` alone, its bug `MAX_AGE_HOURS = 73`
  reads `survived`, and `RULE-4` reads `weak`"

**Tests**, `dev/test_ai_audit.py`, on the sample lab (`sample_lab.MORE_SURVIVE`,
`change_both_tests_of_rule_4`, and `settled(..., reply=)`):
`test_a_result_taken_on_another_test_is_left_out_of_the_entry` and
`test_the_next_audit_plants_a_bug_for_the_proof_left_out`.

**Seen failing first**, on the code as it was:

```
assert ['PROOF-6', 'PROOF-7'] == ['PROOF-7']
assert [] == [['PROOF-6']]
```

The settle kept `PROOF-6` `caught` under its old key, and the plain audit started `claude` 0
times.

**Pages.** `references/review_criteria.md`, "Settling a finding", and
`references/formats/evidence_format.md` (wording only; no field, no version).

**The call the brief asked for: the rule's word meanwhile.** The rule reads what the verdict
gives over the results its entry still holds: `weak` where a spot test fires or a bug survived,
else `strong` where another proof holds a caught bug, else `spot-checked`. It does not read
`out of date`: that word is for an entry whose rule, proof, test or code changed after the
entry was written, and the settle writes its entry on the test and code as they stand. The
proof left out is "a proof it plants a bug for with no result recorded" (RULE-1), so the next
audit without `--settle` reads the rule and plants for it. No line is printed for the proof
left out, and `no_bug` gains no sentence for it, as for a proof with no result on record
before this change. So a `spot-checked` rule can stand with no reason given for that proof
until the next plain audit. A sentence for it would be a new line a person reads; it is not
added.

## 2. An indented directive changed is refused as a comment (C2)

**Code.** `scripts/review/targeted_break.py`, `_without_end_comment`: a line opening, after its
indent, with `#!`, `//go:` or `// @ts-` is returned whole.

**Rules and proofs**, `specs/review/planted_bug.md`:

- RULE-30, reworded. Before: "A line opening `#!`, `//go:` or `// @ts-` is code to the comment
  check, so a change to one is planted". After: "A line opening `#!`, `//go:` or `// @ts-`,
  after any indent, is code to the comment check, so a change to one is planted"
- PROOF-59 (RULE-30), new: "The feature covers `src/age.ts`, where the line `// @ts-ignore`
  stands two spaces in, above `return 90;`, and the model's change turns that line into
  `// @ts-expect-error`; the bug is planted, and its entry reads `survived`"
- PROOF-60 (RULE-30), new: "The feature covers `src/age.go`, where the line `//go:noinline`
  stands one tab in, and the model's change turns it into `//go:norace`; the bug is planted,
  and its entry reads `survived`"

**Tests**, `dev/test_planted_bug.py`: `test_an_indented_typescript_directive_changed_is_planted`,
`test_an_indented_go_directive_changed_is_planted`.

**Seen failing first**: both, `assert 'not made' == 'survived'`.

**Page.** `references/review_criteria.md`: "A line opening `#!`, `//go:` or `// @ts-`, after any
indent, is read as code."

## 3. The criteria said a person judges (C3)

`references/review_criteria.md`, under "Survived": "A person reads the second line to judge the
first." is now "A test run settles the first, as "Settling a finding" says."

No test holds that sentence. `dev/test_ai_audit.py` reads the file as it is and compares the
request and the hash with it, so they follow. The stored hash is each audit entry's `criteria`, under
`.purlin/evidence/`: the sha256 of the file as it was sent to the model for that entry. It is a
record, no reader compares it with the file, and the entries on file stay as they are. Nothing
under `.purlin/` was changed.

## 4. The summary where the share counts no rule (C4)

`references/evidence_and_signoff.md`. The code is unchanged. The sentence now reads: "`a`
counting the rules that pass their tests, have a tested proof and are not an anchor's, read by
the audit or not", and "Where `a` counts no rule, the part is ` The audit found <counts>.`".

`specs/review/ai_audit.md` RULE-35 made the same claim and is reworded. Before: "where every
rule read is an anchor's the line is `The audit found <counts>.`". After: "where no rule
counted is other than an anchor's the line is `The audit found <counts>.`". PROOF-159 stands.

`docs/`, `skills/`, `references/glossary.md` and `references/review_criteria.md` do not make the
claim. **`specs/mcp/summary.md` RULE-26 does**: "Where every rule the audit read is an anchor's,
the sentence ends `The audit fo...`". That file is outside this lane and is left as it is.

## 5. The dashboard's `Strong` count box (C5)

`docs/dashboard.md`: "It is there once any rule has an audit entry and at least one rule that is
not an anchor's passes its tests with a tested proof." No code change.

## 6. The endings of a settle on the pages (C6)

The six bullets of `docs/audit.md`, "What to do with a finding", are unchanged.

- `references/review_criteria.md`, "Settling a finding", the one home, gains: "A proof whose two
  bugs both survived holds no caught bug, and the rule still reads `strong` where another of its
  proofs does." and "from the results the entry holds".
- `docs/audit.md`, under the six bullets, before the link to the one home: "A rule with several
  proofs reads what they give together: `weak` while a spot test fires or a bug still survives,
  else `strong` where any of its proofs has a caught bug, else `spot-checked`. A proof left with
  no bug gets a new one once its test or code changes." The reasoning part makes no claim about
  a rule's word after a settle and is unchanged.
- `docs/running-and-evidence.md`: the two bullets are three, and one paragraph follows:
  - "The test fails: the finding was right, and the bug reads `caught`."
  - "The test still passes: the bug did not break what the proof says. It is dropped, and one
    new bug is planted. If that one survives too, the proof gets no further bug until its test
    or code changes."
  - "The test does not run: the bug reads `not run`."
  - "The rule then reads what the verdict gives: `weak` where a spot test fires or a bug still
    survives, else `strong` where any of its proofs has a caught bug, else `spot-checked`, with
    the reason. A rule can read `strong` through another proof. Where no new bug can be planted,
    the printed line ends at `did not break what the proof says.`"
- `skills/build/SKILL.md`, step 5 and the sentence after it:
  - "5. Report what the settle printed for each proof, and the word the rule then reads:"
  - "The test now catches the bug: the finding was right, and the bug reads `caught`."
  - "The bug did not break what the proof says, and a new bug was planted: the finding was
    wrong. Where the new bug survives too, two bugs left the proof's check passing, and the
    proof gets no further bug until its test or code changes."
  - "The same line ending at `did not break what the proof says.`: no new bug could be planted,
    and the rule's block says why."
  - "The test did not run with the bug in place: the bug reads `not run`."
  - "The rule then reads what the verdict gives: `weak` where a spot test fires or a bug still
    survives, else `strong` where any of its proofs has a caught bug, else `spot-checked`. A
    rule can read `strong` through another proof."
  - "A rule that still reads `weak` has a finding left: start again at step 1 with it."
- `skills/audit/SKILL.md`, Step 2, after the bullet for the line ending `A new bug was planted.`:
  - "That proof gets no further bug until its test or code changes, and the rule can still read
    `strong` through another proof."
  - "The same line ending at `did not break what the proof says.` is printed by a settle where
    no new bug can be planted. The rule's block says why."
  - "A line `A bug was planted for PROOF-N and its test did not run.`, or one ending
    `its test ended in an error, not a failure.`, says the bug reads `not run`. After a settle
    it is the bug that survived, planted again."
  - "After a settle the rule reads what the verdict gives, as after any audit: `weak` where a
    spot test fires or a bug still survives, else `strong` where any of its proofs has a caught
    bug, else `spot-checked`."

**Specs that pin these pages.** None pinned the words that changed: no rule, proof or test
counts "three ways", and `purlin_docs` RULE-17 and PROOF-25 (the six bullets, `strong`,
`spot-checked`) and `skill_audit` RULE-30 and PROOF-60 (the two printed lines) still hold. No
file under `specs/skills/` or `specs/instructions/` is changed.

## 7. Five breaks the tests missed (C7)

Each of the review's breaks was planted in a scratch copy of the finished tree
(`lane-review-fixes/mut.sh`, `mut.log` in the scratchpad) and the new test run there.

| The review's break | Rule and proof | Test | What it printed with the break planted |
|---|---|---|---|
| a settle runs no spot test | `ai_audit` RULE-66 and PROOF-163, new | `test_a_settle_runs_the_spot_tests` | `assert [] == ['tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.']` |
| a replayed `not run` loses its `why` | `ai_audit` RULE-59, PROOF-164, new | `test_a_test_that_ends_in_an_error_with_the_kept_bug_says_so` | `assert ('not run', '') == ('not run', 'the test ended in an error, not a failure')` |
| a settle that asks no model keeps the old `explanation` | `ai_audit` RULE-67 and PROOF-165, new | `test_a_settle_that_asks_no_model_writes_no_explanation` | `assert ['PROOF-5: the test takes its expected age from the code.'] == []` |
| no `check_unchanged` after the replays | `planted_bug` RULE-6, PROOF-61, new | `test_a_project_that_changes_as_a_bug_is_planted_again_stops_the_settle` | `assert 2 == 1`, the calls `claude` took |
| `replay` skips the scope refusal | `ai_audit` RULE-60, PROOF-166, new | `test_a_kept_bug_in_a_file_the_scope_no_longer_names_is_asked_for_anew` | `assert ['  PROOF-5: the bug at src/intake.py:17 did not break what the proof says.'] == []` |

The break of item 1, put back, fails both of its tests there too.

Word for word:

- RULE-66: "Settling a rule runs the spot tests again over the rule's tests, and a finding of
  theirs makes the rule `weak` as in any audit"
- RULE-67: "A settled rule that needs no new bug is written with no model asked: its entry holds
  no `explanation` and keeps the `model` and the `criteria` of the entry it replaces"
- PROOF-163 (RULE-66): "The test of `PROOF-11` checks nothing and its bug reads `survived`;
  `RULE-7` is settled with the test as it was and a model that names no new bug; `RULE-7` reads
  `weak`, and its one finding is
  `tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.`"
- PROOF-164 (RULE-59): "The test of `PROOF-2` is changed so that its setup raises an error where
  the status is not `401`, and `RULE-2` is settled; the entry of `PROOF-2` reads `not run`, and
  `no_bug` is exactly
  `A bug was planted for PROOF-2 and its test ended in an error, not a failure.`"
- PROOF-165 (RULE-67): "The entry of `RULE-3` holds the explanation
  `PROOF-5: the test takes its expected age from the code.` and the model `claude-fake-1`; the
  test of `PROOF-5` is changed to expect `25` and `RULE-3` is settled; `claude` is started `0`
  times, the entry's `explanation` is empty, and its `model` still reads `claude-fake-1`"
- PROOF-166 (RULE-60): "The spec's `> Scope:` is changed to name `src/__init__.py` alone, so the
  feature no longer covers `src/intake.py`, the file the bug kept for `PROOF-5` changes, and
  `RULE-3` is settled; `claude` is asked a bug for `PROOF-5`, and no line the audit prints holds
  `did not break what the proof says`"
- `planted_bug` PROOF-61 (RULE-6): "The bug kept for `PROOF-1` reads `survived`, and its test,
  each time it runs in a copy of the project, writes `notes.txt` in the project; `RULE-1` is
  settled; the audit prints
  `The audit stopped: notes.txt changed while the audit ran. Nothing in the project was written by the audit.`,
  exits `1`, and the settle starts `claude` `0` times"

`> Highest-Rule:` and `> Highest-Proof:` were read before each number was taken: `ai_audit`
64 and 160, now 67 and 166; `planted_bug` 30 and 58, now 30 and 61.

## Calls the brief did not make

1. **The rule's word after a stale result is left out** is the verdict over the results that
   stand, never `out of date`, and no line is printed for the proof left out (item 1).
2. **A second proof for item 2**, the indented `//go:` line, since the review names both.
3. **RULE-30 and the criteria gain "after any indent"**, so the rule says what the fix does.
4. **Two new rules for item 7**, RULE-66 and RULE-67: the spot tests on a settle and the empty
   `explanation` were stated in the criteria and the evidence format and in no rule.
5. **`ai_audit` RULE-35 is reworded** with item 4, since it made the reference's claim.
6. **`specs/mcp/summary.md` RULE-26 is left**, outside the lane. It needs the same rewording.
7. **The check after the replays is proved by the model not being asked.** With the check
   removed the audit still stops, at the check after the new bug, so the only thing a caller
   sees differ is that `claude` was started.
8. **The scope refusal is proved with a model that names no bug**: the settle then prints no
   `did not break what the proof says` line, where the break prints it.
9. **`docs/audit.md` gains two sentences under the six bullets**, so the page is true for a rule
   with several proofs while the six stay word for word.
10. **The build skill's step 5 names what was printed, not a count of endings**, and points at
    the audit skill's Step 2 and the criteria as before.
11. **No rule, proof or test was added to pin the new page sentences.**
12. **Not done, though the review names them as unproved:** a proof that RULE-56's "until its
    test or code changes" plants again once the test changes. The review ran it (`t2.py` B5)
    and it holds.
13. **Commits were split by item**, with the shared files staged part by part; each of the
    first three commits was not run alone, the finished tree was.

## Acceptance

`dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py`,
`dev/test_skill_*.py`, `dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`: `191 passed`.
`bash dev/run_tests.sh --fast`: `981 passed, 9 skipped`, `Suites: 1 passed, 0 failed`.
