# Lane `settle`: decision 127, item E, the report

Branch `lane/d127-settle`, from `main` at `c4c548587`. Built from `dev/plans/d127-plan.md`,
section 1, item E, and the lane's row of section 2. Nothing was pushed, tagged or signed, no
real model was reached, and Purlin's own code was not audited.

## What was built

1. **The refusal.** `purlin:audit <feature> RULE-N --settle` plants nothing for a proof whose
   bug reads `survived` and whose own tests are as they were when the bug got past them. It
   prints, under the rule, the plan's line word for word,
   `  PROOF-2: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`,
   the bug stays `survived` with its two findings, and the rule reads `weak` by "The verdict".
   A rule whose every surviving bug is refused is read and asks no model; where nothing at all
   changed, its entry is left as it was (the writer's `_same_audit` finds nothing new).
2. **The option, `--sound PROOF-N`.** Given once per proof beside `--settle`:
   `purlin:audit <feature> RULE-N --settle --sound PROOF-N`, which is
   `purlin_run.py --audit --feature <f> --settle RULE-N --sound PROOF-N`. It lets the settle go
   on for that proof as today. The entry the settle writes for the proof holds
   `test_unchanged: true` (whatever its result: `caught`, `not run`, `not made`, the
   two-survivors `not made`), unless a new bug for it reads `survived`, which is a new finding
   and carries nothing. `no_bug` gains
   `PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
   A later audit that keeps the entry gives the sentence again from the field. Where the model
   could not be reached for the new bug, the proof has no entry and `no_bug` holds the sentence
   alone, so no finding is cleared without a record.
3. **What "the test has not changed" is measured on.** The evidence did not hold it:
   `break_key` is the sha256 of the proof's tests' source hash and the feature's `code` part
   together, so it cannot tell a changed test from changed code. A bug recorded as `survived`
   now holds `test_key`, the sha256 of the sorted lines `<file> <test name> <sha256 of the
   test's source>`, one per test tied to that proof, the source as `marked_tests.source` reads
   it: the test's own lines, not its file (`audit_run.test_source_hash`, the hash `break_key`
   already used for its test half). No other result holds `test_key`; a settle that moves a bug
   off `survived` drops it.
4. **An entry recorded before `test_key`.** Chosen: it reads as unchanged, and is refused, only
   where that is certain: its `break_key` equals the one taken now, or the rule's entry is not
   out of date on `test` (the rule-level `test_hash`). Once the rule's tests change it is
   settled as any bug is, so it never refuses forever. The cost: for a rule with two proofs and
   an old entry, a change to one proof's test lets the other's unchanged test settle as it did
   before this change. A refused old entry gains its `test_key` in memory; it is written only
   when the rule's entry is rewritten for another reason. A test whose source is not found
   reads as changed, for the same reason: nobody can show it is the same.
5. **Two proofs, one test changed.** `RULE-4` of the sample lab with a surviving bug for
   `PROOF-6` and `PROOF-7`, the test of `PROOF-7` alone strengthened: `PROOF-7` reads `caught`,
   `PROOF-6` is refused and stays `survived`, the rule reads `weak`, and no model is asked.
   With `--sound PROOF-6` and a new bug that is caught, the rule reads `strong`.
6. **Refusals of `--sound`, before a test starts.**
   - Without `--settle`: `purlin: --sound goes with --settle.`, exit 2 (with the usage, as
     every exit 2 of the run script).
   - With no value: `purlin: --sound needs a proof, as PROOF-N.`, exit 2.
   - A proof of no rule `--settle` names (or no proof at all):
     `<feature> PROOF-N is not a proof of a rule named with --settle. Run purlin:status <feature> to see its rules.`, exit 1.
   - A proof whose bug on record is not `survived`:
     `<feature> PROOF-N has no planted bug that survived: nothing to settle.`, exit 1.
   - `--sound` for a proof whose test did change records nothing; the settle goes on as any.
7. **`scripts/run/purlin_run.py`**, touched only where `--settle` is parsed, refused and handed
   on: the docstring's usage line and one paragraph, `USAGE`'s third line, `Args.sound`, the
   parse of `--sound`, its exit 2 refusal beside `--settle`'s, the exit 1 check beside the
   `--settle` rule check (calling `audit_run.sound_refusals`), and `sound=args.sound` in
   `_audit`. Lane `run3` may meet it there on merge.

## The pages

- `references/review_criteria.md`, "Settling a finding" (the one home): a new part, "A test
  that has not changed", with what is compared, the old-entry reading, `--sound`, its
  refusals and its one non-effect; step list scoped to proofs whose test changed or that
  `--sound` names; the two-proofs case under the verdict paragraph; the refusal line among the
  lines printed and not stored; the closing limit now says the audit checks that the test
  changed, and under `--sound` records the judgment and does not check it. "What the audit
  reports" counts the new `no_bug` sentence. The file is sent to the model verbatim, so every
  entry's `criteria` hash moves.
- `skills/build/SKILL.md`, step 2: the assertion goes in the test's own body (a helper or
  fixture change alone is not a changed test and is refused); where the test was read against
  the proof line by line and already asserts it, leave it and settle with `--sound PROOF-N`,
  saying which line asserts which words. Step 4: the command, for those proofs only, never to
  get past a refusal. Step 5: the two new lines.
- `skills/audit/SKILL.md`: the usage line, when Step 1 adds `--sound`, and three Step 2 bullets
  (the refusal, the sentence, the two `--sound` refusals).
- `references/purlin_commands.md`: the row's syntax `--settle [--sound PROOF-N]` and when build
  passes it; one syntax line,
  `purlin:audit <feature> RULE-N --settle --sound PROOF-N  The same, where that proof's test was judged sound and left as it was`.
- `references/glossary.md`, *settle*: two sentences.
- `docs/audit.md`, the reasoning part, after "A test run settles a surviving bug": "A finding
  cannot be cleared without either a stronger test or a recorded judgment that the test was
  already sound: a settle is refused for a test that is as it was when the bug got past it.
  Where `purlin:build` read the test against the proof and left it alone, it says so with
  `--sound`, and the evidence records that the test was not changed. Purlin records that
  judgment and does not check it."

**The six bullets under "What to do with a finding"** are unchanged. Each read against the code:
1 to 3, 5 and 6 hold as written. Bullet 4, "The check passes: the bug did not break what the
proof says. The audit plants one more", holds on the path the bullets describe, where
`purlin:build` wrote the check; a settle run by hand over a test nobody changed is now refused
instead and plants nothing. Not untrue as the bullets read, but the owner may want to know the
order: no second bug is planted for an unchanged test without `--sound`.

## Formats

- `references/formats/evidence_format.md`: `> Format-Version:` 13 to 14. A planted bug's entry
  gains two optional fields, `test_key` and `test_unchanged`; `no_bug` gains the second kind of
  sentence; one section says what `test_key` measures, how an old entry reads, and what
  `--sound` writes.
- `references/formats/package_format.md`: 13 to 14. The package copies `breaks` whole
  (`scripts/export/package.py`, `_audit`), so both fields enter it; the `breaks` and `no_bug`
  rows say so.
- `scripts/export/package.py` and `dev/test_export.py` needed no change: neither holds the
  `> Format-Version:` number, and the package's `schema`, `purlin-package/4`, is a separate
  identifier that did not move (as `purlin-evidence/2` did not at earlier bumps).
  `dev/test_export.py` passes.
- Both formats moved in the same commit as the code, `238ff37a9`.

## Where the line shows

The sentence is stored under `no_bug`, which every surface prints:

- **The audit's printout**: under the rule, last, after the settle's own lines.
- **The dashboard's rule page** (`scripts/report/src/rule.js`, `auditPanel`): prints each
  `no_bug` sentence for a `strong` or `weak` rule, and joins them after `The spot tests found
  nothing.` for a `spot-checked` one. It shows with no change. `breaks[...].test_unchanged`
  is in the page's data and drawn nowhere; nothing needs it.
- **`ai_audit.py` and the status's rule view** (`verdict_lines`): shows it with no change.
- **The evidence package**: carries `no_bug` and `breaks` whole.
- **The sign-off's list of findings** (`scripts/review/sign.py`, `audit_list_lines` and the
  stop's `AUDIT_WEAK` lines): lists only the `findings` of rules that read `weak`. The sentence
  is not a finding, and a proof settled under `--sound` leaves its rule `strong` or
  `spot-checked` unless another proof keeps it weak, so the sign-off list does **not** show it.
  If the owner wants it there, the change is lane `sign3`'s file, `scripts/review/sign.py`: in
  `audit_list_lines`, after the loop over the weak rules, add one line per rule of the package
  (any verdict) for each `no_bug` sentence that ends
  `was settled with its test unchanged: it was judged to assert what the proof names.`, in the
  same `AUDIT_LIST` shape (`<feature> <RULE-N>: <sentence>`); and pass the package's rules, not
  only the weak ones, to it. Not made here: it is a question for the owner, not a fault.

## Rules and proofs, word for word

`specs/review/ai_audit.md`: `> Highest-Rule:` 67 to 72, `> Highest-Proof:` 166 to 179.
`specs/skills/skill_build.md`: 21 to 22, 51 to 52. `specs/skills/skill_audit.md`: 30 to 31, 60
to 61. No number used again, none deleted. The `> Description:` of `ai_audit` gains one
sentence. Added or reworded:

- RULE-54: Settling a rule plants again each bug its entry keeps as `survived` whose proof's tests changed since the bug got past them, or whose proof `--sound` names, with no model asked, and runs that proof's tests as they stand; where a test fails, the bug's entry reads `caught` with the same `file`, `line`, `before`, `after`, `aim` and `case`, its two findings leave the rule, and the audit prints under the rule `  <PROOF-N>: the test now catches the bug it missed at <file>:<line>.`
- RULE-68: A settle plants nothing for a proof whose bug reads `survived` and whose own tests are as they were when the bug got past them: the audit prints under the rule `  <PROOF-N>: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`, the bug still reads `survived`, and the rule reads `weak`
- RULE-69: `--sound PROOF-N` lets a settle go on for a proof whose tests are as they were: the entry the settle writes for the proof holds `test_unchanged` `true`, unless a new bug for it reads `survived`, and `no_bug` holds `<PROOF-N> was settled with its test unchanged: it was judged to assert what the proof names.` for as long as the entry is kept
- RULE-70: `--sound` is refused before a test starts: without `--settle` with exit 2; with exit 1 for a proof of no rule `--settle` names, with `<feature> <PROOF-N> is not a proof of a rule named with --settle. Run purlin:status <feature> to see its rules.`, and for a proof that keeps no bug as `survived`, with `<feature> <PROOF-N> has no planted bug that survived: nothing to settle.`
- RULE-71: A bug recorded as `survived` holds `test_key`, the sha256 of its proof's own tests as the audit reads them, and no other result holds one; a `survived` bug recorded without it reads as unchanged only while its `break_key` is the current one or the rule's entry is not out of date on its tests
- RULE-72: `--sound` naming a proof whose tests did change records nothing: the settle goes on as any settle does
- PROOF-142 (RULE-53): `RULE-2` and `RULE-3` of the sample lab project each read `weak`; the audit is run with `--settle RULE-2 --settle RULE-4 --sound PROOF-3`; it prints one line opening `sample_intake RULE-2   ` and none opening `sample_intake RULE-3   `, asks `claude` about `RULE-2` alone, and the entry of `RULE-3` is as it was
- PROOF-145 (RULE-55): The test of `PROOF-5` still takes its expected age from the helper, and `RULE-3` is settled with `--sound PROOF-5` and a model whose new bug adds 1 to the age the record stores; `claude` is started exactly `1` time, asked for `PROOF-5` alone, the new bug reads `caught`, and `RULE-3` reads `strong`
- PROOF-146 (RULE-55): `RULE-3` is settled with `--sound PROOF-5`, the kept bug for `PROOF-5` still survives and the model's new bug is caught; the first line the audit prints under `sample_intake RULE-3   strong` is `  PROOF-5: the bug at src/intake.py:17 did not break what the proof says. A new bug was planted.`
- PROOF-147 (RULE-56): Settled with `--sound PROOF-5`, the kept bug for `PROOF-5` and the model's new bug both survive; the entry of `PROOF-5` reads `not made` with the reason `two planted bugs left the proof's check passing`, `no_bug` opens with `No bug was caught for PROOF-5: two planted bugs left the proof's check passing.`, and `claude` was started exactly `1` time
- PROOF-150 (RULE-58): Under `--sound PROOF-2` the bug kept for `PROOF-2` still survives, the model answers `no break: nothing breaks it`; the audit prints `  PROOF-2: the bug at src/login.py:12 did not break what the proof says.` then a line opening `  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-2: nothing breaks it.`
- PROOF-151 (RULE-58): `RULE-2` is settled with `--sound PROOF-2`, the bug kept for `PROOF-2` still survives, and `claude` exits `1`; no bug is on record for `PROOF-2`, `RULE-2` reads `spot-checked`, and its `no_bug` opens with `No bug was planted: the model could not be reached: claude exited with an error.`
- PROOF-153 (RULE-60): The helper's line `return int(seconds // 3600)`, which the bug kept for `PROOF-5` changes, is written as two lines, and `RULE-3` is settled with `--sound PROOF-5`; `claude` is asked for `PROOF-5`, its bug `hours = seconds // 3600 + 1` reads `survived`, and under `sample_intake RULE-3   weak` the audit prints that bug's two findings and nothing else
- PROOF-154 (RULE-61): `RULE-2` has `PROOF-3`, whose bug reads `survived`, and `PROOF-4`, whose entry reads `not made`; `RULE-2` is settled with `--sound PROOF-3`; `claude` is asked a bug for `PROOF-3` alone, and the entry of `PROOF-4` is as it was
- PROOF-158 (RULE-56): Under `--sound PROOF-5` the kept and the new bug for `PROOF-5` both survive; printed: `sample_intake RULE-3   spot-checked`, then `  PROOF-5: the bug at src/intake.py:17 did not break what the proof says. A new bug was planted.`, then a line opening `  The spot tests found nothing. No bug was caught for PROOF-5: two planted bugs left the proof's check passing.`
- PROOF-163 (RULE-66): The test of `PROOF-11` checks nothing and its bug reads `survived`; `RULE-7` is settled with `--sound PROOF-11`, the test as it was, and a model that names no new bug; `RULE-7` reads `weak`, and its one finding is `tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.`
- PROOF-166 (RULE-60): The spec's `> Scope:` is changed to name `src/__init__.py` alone, so the feature no longer covers `src/intake.py`, the file the bug kept for `PROOF-5` changes, and `RULE-3` is settled with `--sound PROOF-5`; `claude` is asked a bug for `PROOF-5`, and no line the audit prints holds `did not break what the proof says`
- PROOF-167 (RULE-68): The bug kept for `PROOF-5` reads `survived` and nothing has changed since; `RULE-3` is named with `--settle`; the audit prints `sample_intake RULE-3   weak`, then `  PROOF-5: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`, `claude` is started `0` times, and the entry of `RULE-3` is as it was
- PROOF-168 (RULE-68): `RULE-4` keeps a bug as `survived` for `PROOF-6` and for `PROOF-7`; the test of `PROOF-7` alone is changed, to hand in a sample exactly 72 hours old, and `RULE-4` is settled; the bug of `PROOF-7` reads `caught`, the entry of `PROOF-6` is as it was, `RULE-4` reads `weak`, and `claude` is started `0` times
- PROOF-169 (RULE-68): `RULE-4` is settled after the test of `PROOF-7` alone changed, so the settle is refused for `PROOF-6`; the findings of `RULE-4` are the two of `PROOF-6` and no other: `PROOF-6: the test still passes when src/intake.py:52 reads "if status == 'accepted':"`, then the line opening `PROOF-6: the AI says this breaks: `
- PROOF-170 (RULE-69): The test of `PROOF-6` is as it was when its bug survived; `RULE-4` is settled with `--sound PROOF-6` and a model whose new bug sets the limit to 73 hours; the entry of `PROOF-6` reads `caught` and `test_unchanged` `true`, and `no_bug` is exactly `PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
- PROOF-171 (RULE-69): `RULE-4` is settled with `--sound PROOF-6`, and the model's new bug for `PROOF-6` is caught; the last line the audit prints under `sample_intake RULE-4   strong` is `  PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
- PROOF-172 (RULE-69): `PROOF-6` was settled with `--sound PROOF-6` and its new bug caught; every rule is then read again with nothing changed; the entry of `PROOF-6` still reads `test_unchanged` `true`, and the line under `sample_intake RULE-4   strong` is `  PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
- PROOF-173 (RULE-72): The test of `PROOF-5` is changed to expect `25`, and `RULE-3` is settled with `--sound PROOF-5`; the bug of `PROOF-5` reads `caught`, its entry holds no `test_unchanged`, and `no_bug` is empty
- PROOF-174 (RULE-70): The run is started on the sample lab project with `--audit --feature sample_intake --sound PROOF-5`; it exits 2, prints `purlin: --sound goes with --settle.` and starts no test
- PROOF-175 (RULE-70): `PROOF-3` is a proof of `RULE-2`; the run is started with `--audit --feature sample_intake --settle RULE-3 --sound PROOF-3`; it exits 1, prints only `sample_intake PROOF-3 is not a proof of a rule named with --settle. Run purlin:status sample_intake to see its rules.`, starts no `claude` and leaves the evidence file as it was
- PROOF-176 (RULE-70): The bug of `PROOF-6` reads `caught`; the run is started with `--audit --feature sample_intake --settle RULE-4 --sound PROOF-6`; it exits 1, prints only `sample_intake PROOF-6 has no planted bug that survived: nothing to settle.`, starts no `claude` and leaves the evidence file as it was
- PROOF-177 (RULE-71): The sample lab project is audited; the entry of `PROOF-5`, whose bug reads `survived`, holds a `test_key` of 64 hexadecimal characters, and the entry of `PROOF-6`, whose bug reads `caught`, holds none
- PROOF-178 (RULE-71): The entry of `PROOF-5` reads `survived` and holds no `test_key`, as an earlier audit wrote it, and nothing has changed since; `RULE-3` is named with `--settle`; the first line under the rule is `  PROOF-5: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`, and `claude` is started `0` times
- PROOF-179 (RULE-71): The entry of `PROOF-5` reads `survived` and holds no `test_key`; the test of `PROOF-5` is changed to expect `25` and `RULE-3` is settled; the audit prints `  PROOF-5: the test now catches the bug it missed at src/intake.py:17.`, and `RULE-3` reads `strong`
- RULE-31: The audit skill shows the line that refuses a settle for a test that has not changed and the sentence a settle under `--sound` leaves, each in the words `references/review_criteria.md` gives under its heading `Settling a finding`
- PROOF-61 (RULE-31): The audit skill and the part of `references/review_criteria.md` under the heading `Settling a finding` each hold `its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.` and `was settled with its test unchanged: it was judged to assert what the proof names.`
- RULE-22: The build skill says how it settles a proof whose test it left alone because the test already asserts what the proof names: with `purlin:audit <feature> RULE-N --settle --sound PROOF-N`, and only for a test it read against its proof
- PROOF-52 (RULE-22): The text of `skills/build/SKILL.md` under the heading `Strengthening a weak rule` holds `purlin:audit <feature> RULE-N --settle --sound PROOF-N` and `Never pass it for a test you did not read against its proof`

Reworded and why: `ai_audit` RULE-54 now names the proofs a settle plants again (those whose
test changed, or that `--sound` names). PROOF-142, 145, 146, 147, 150, 151, 153, 154, 158, 163
and 166 each settle with the test as it was, which is now refused, so each names `--sound`;
146, 147, 150, 151 and 158 now say "opens with" or "the first line" where the new sentence
follows the line they pin. Each of their tests changed on a kept line in the same commit.
PROOF-164's test changed its setup so the fixture is taken by the test itself (its own lines
change), and its words still hold; PROOF-148's test now expects the second `no_bug` sentence,
and its words still hold.

Over 60 words, not this lane's: `ai_audit` PROOF-111 (61) and PROOF-160 (63) were already over.

## Seen failing first

- The 13 new tests of `TestASettleOnAnUnchangedTest` before the code: 12 failed (the refusal,
  the two-proof case, `--sound`'s field, sentence, printout and refusals, `test_key`, the old
  entry refused). PROOF-179, an old entry whose test was strengthened settling as before,
  passed before and after: it guards the reading that never refuses forever.
- Then 14 existing settle tests failed, each a settle on an unchanged test, now refused; each
  was given `--sound` (and PROOF-164's test, whose fixture had changed outside the test's own
  lines, was made to take the fixture). A finding of note: a change to a fixture or helper is
  not a changed test by the plan's measure.
- `skill_build` PROOF-52 and `skill_audit` PROOF-61 failed with the skill pages and the
  criteria stashed, and passed with them.

## The copy of the real project

The three upgraded copies of the real project hold no audit entry and no surviving bug, and an
audit needs a real model, so no settle could run there. On a fresh `cp -Rc` copy of
`RLabGenMusic-upgrade-3` in the scratch folder: `--audit --feature honest_answers --sound
PROOF-1` printed the usage and `purlin: --sound goes with --settle.`, exit 2;
`--settle RULE-1 --sound PROOF-1` printed
`honest_answers PROOF-1 is not a proof of a rule named with --settle. Run purlin:status honest_answers to see its rules.`,
exit 1, before any test ran, and the copy's tree was left unchanged.

## Lines a person reads that this lane chose

- `PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
  (stored under `no_bug`, printed under the rule)
- `purlin: --sound goes with --settle.`
- `purlin: --sound needs a proof, as PROOF-N.`
- `<feature> PROOF-N is not a proof of a rule named with --settle. Run purlin:status <feature> to see its rules.`
- `<feature> PROOF-N has no planted bug that survived: nothing to settle.` (the shape of the
  rule's existing line)
- The usage's third line gains `[--sound PROOF-N ...]`.
- The prose listed under "The pages", and the format sections.

## Calls the plan did not make

1. **The option is `--sound PROOF-N`**, once per proof, the proof named alone (a proof's number
   is unique in its spec). The field is `test_unchanged`, a boolean present only where true,
   beside the optional `kept` and `reason` the format already has.
2. **`test_key` is stored on `survived` bugs only**, the one result a settle reads.
3. **An old entry is refused only where certain** (point 4 above), never forever.
4. **The sentence lives in `no_bug`**, so every surface shows it with no change; the field's
   definition in both formats widens to say so.
5. **`test_unchanged` is written whatever the settled result**, `not run` and `not made`
   included, but not on a new `survived` bug; and where no entry is written (model not
   reached) the sentence alone is kept.
6. **`--sound` with no surviving bug is a refusal, exit 1, before a test starts**, where a rule
   with nothing to settle is only a printed line. The plan asked for a refusal; the check reads
   the evidence and builds the payload once more.
7. **`--sound` for a test that did change is accepted and records nothing.** Refusing it would
   punish a build that strengthened the test after first judging it sound.
8. **A refused proof's rule entry is written as any settled rule's**: the entry takes current
   hashes, keeping the bug, its `break_key` and its `test_key`, so the next plain audit leaves
   the proof alone until its test or code changes, and the finding stands until then.
9. **A test whose source is not found reads as changed.**

## What is left, and what waits on another lane

- **Lane `sign3`** (`scripts/review/sign.py`): the sign-off list does not show the sentence;
  the exact change is above, for the owner to decide.
- **`README.md`** (no lane's) and **`docs/running-and-evidence.md`** (lane `run3`): each
  repeats `purlin:audit <feature> RULE-N --settle` and is still true. If the owner wants the
  option there: README's command row `--settle [--sound PROOF-N]`, as
  `references/purlin_commands.md` now reads, and the syntax block of
  `docs/running-and-evidence.md` line 320 gains the line
  `purlin:audit <feature> RULE-N --settle --sound PROOF-N  The same, where that proof's test was judged sound and left as it was`.
- **`agents/purlin.md`** (no lane's): it routes a weak rule to `purlin:build`; nothing stale.
- **Merge with `run3`**: both lanes edit `scripts/run/purlin_run.py`; this lane's hunks are the
  docstring, `USAGE`, `Args`, `parse_args`, the check after the `--settle` rule check, and
  `_audit`'s call.
- **Purlin's own evidence** holds no `survived` bug today, so no settle of Purlin's own rules is
  refused by this change. Every `criteria` hash moves with `review_criteria.md`, and the
  `ai_audit`, `skill_build` and `skill_audit` entries go out of date.
- Not done, by the brief: integration, `windows_run.py`, the dashboard look, the re-audit.
