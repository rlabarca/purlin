# Review of decisions 124 and 125 (`2dedc6eff..0cf0c983c`)

Reviewer built none of it. Everything ran in the worktree `purlin-wt/d124-review` at `0cf0c983c`
and on sample projects under the scratchpad (`p/`), with `dev/fake_claude.py` as `claude`. No
real model was reached, Purlin's own code was not audited, and nothing was written in the
repository. The try-out scripts are `h.py` and `t1.py` to `t8.py` beside this file; the mutation
runs are `mut.sh` and `mut.log`, made on a scratch copy of the tree.

Counts: **7 certain, 3 likely, 8 judgment calls.**

---

## Certain

### C1. A settle leaves another proof's result standing after its test changed, and no plain audit reads it again (wrong result)

- **Where:** `scripts/review/audit_run.py:303-308` (`bug_plan` under `settle`), with
  `scripts/review/ai_audit.py:173-177` (`is_read`).
- **Input (ran, `t3.py` C2):** sample lab, `RULE-4` with `PROOF-6` `caught` and `PROOF-7`
  `survived`. The test of `PROOF-7` is strengthened (72 hours) and the test of `PROOF-6` is
  weakened to `assert record['status']`. Then `--audit --feature sample_intake --settle RULE-4`,
  then a plain `--audit --feature sample_intake`.
- **Output:** the settle writes `PROOF-6 caught` with its old `break_key` `37989b10` and the
  rule `strong`. The plain audit starts `claude` 0 times and leaves it. `--audit --all` then
  plants for `PROOF-6` and finds `survived`, `RULE-4` `weak`.
- **Expected:** `references/review_criteria.md:310` and the plan: "Any other audit asks for a
  new bug for a proof whose test changed". Lane audit's call 5 says "A later plain audit plants
  for either as it would have". It does not: the settle writes a current entry for the rule, so
  `is_read` sees no proof missing from `breaks` and never compares a `break_key`.
- **Smallest fix:** in `bug_plan` under `settle`, keep a non-`survived` entry only where
  `kept.get('break_key') == key`; leave any other out of the plan, as a proof with no result is
  left out. `is_read` then finds the proof missing and the next plain audit plants for it. Add a
  proof: a rule with one `survived` and one `caught` proof, both tests changed, settled, then
  audited plain.

### C2. A change to an indented `// @ts-` or `//go:` line is still refused as a comment (wrong result)

- **Where:** `scripts/review/targeted_break.py:213-221` (`_without_end_comment`), called from
  `only_comment` at `:234-235`.
- **Input (ran, `t5.py`):** `only_comment('a.ts', '    // @ts-ignore\n    return f(x);',
  '    // @ts-expect-error\n    return f(x);')`.
- **Output:** `True`, so the bug is `not made`, `the change touches only a comment`. The same at
  column 0 gives `False`. An indented `\t//go:noinline` changed gives `True` too.
- **Why:** `_code_lines` keeps the directive line, then `_without_end_comment` finds `\s//` in
  the line's own indent and cuts the whole line to `''`, before and after.
- **Expected:** `planted_bug` RULE-30, "A line opening `#!`, `//go:` or `// @ts-` is code to the
  comment check, so a change to one is planted", and lane call 9, "is code after any indent".
  `PROOF-58` passes only because it adds a line, which adds a `''` to the list.
- **Smallest fix:** in `_without_end_comment`, return the line whole where
  `line.strip().startswith(DIRECTIVES)`. Add a proof that changes an indented `// @ts-ignore`.

### C3. The criteria still say a person judges a finding (wrong words, and sent to the model)

- **Where:** `references/review_criteria.md:219`: "A person reads the second line to judge the
  first."
- **Expected:** decision 124: "No person judges a finding". The glossary, `docs/`, and the two
  skills lost this sentence in this range; the criteria, which is the file the request holds,
  kept it. Read.
- **Smallest fix:** replace with "A test run settles the first, as "Settling a finding" says."

### C4. The summary sentence where only an anchor was read is not what the reference says (wrong words)

- **Where:** `references/evidence_and_signoff.md:67-68`: "Where every rule the audit read is an
  anchor's, the part is ` The audit found <counts>.`"; code `scripts/mcp/purlin/summary.py:245-268`.
- **Input (ran, `t8.py`):** sample lab plus an anchor of 2 rules; `--audit --feature house_rules`.
- **Output:** the audit's last line: `The audit found 2 spot-checked.` The status printed
  directly under it: `11 rules. 10 pass their tests. The audit found 0 of 8 rules strong (0%):
  0 strong, 2 spot-checked, 8 not audited.`
- **Why:** `audit_share`'s `over` counts every rule that is not an anchor's, `not audited`
  included, so the short form is used only where no such rule passes, or where the audit's last
  line counts the anchor alone.
- **Smallest fix:** reword the reference: "Where no rule that passes its tests with a tested
  proof is other than an anchor's". Whether the status should say `0 of 8 (0%)` for 8 rules no
  audit read is J5.

### C5. The dashboard's `Strong` count box is there before the audit has read a feature's rule (wrong words)

- **Where:** `docs/dashboard.md:83`: "It is there once the audit has read a rule that is not an
  anchor's."; code `scripts/report/src/board.js:34-35` and `app.js:118-125`, `auditRead`.
- **What the code does:** the box is drawn where `audited()` (any rule has an audit entry, an
  anchor's included) and `auditShare().over` is not zero, and `over` counts rules whose strong
  cell reads `not audited`. In the project of C4 the anchor alone was read and `over` is 8, so
  the box is drawn, reading 0, amber. Read; the payload is the one `t8.py` wrote.
- **Smallest fix:** either the page ("once any rule has an audit entry and a rule that is not
  an anchor's passes its tests with a tested proof") or `auditRead` leaving `not audited` out of
  `over` for the box's presence.

### C6. The three pages give two endings of a settle; the code has more (wrong words)

- **Where:** `docs/audit.md:53-56`, `docs/running-and-evidence.md:389-392`,
  `skills/build/SKILL.md:168-172` ("Report which of three ways it ended"),
  `skills/audit/SKILL.md:101-104`.
- **Sentences:** "The check fails: ... the rule reads `strong`." "If that one is wrong too, the
  rule reads `spot-checked` and nothing more is asked." "two bugs left the proof's check
  passing, and the rule reads `spot-checked`."
- **What the code does (ran):**
  - two bugs survive for `PROOF-7` and `PROOF-6` keeps a caught bug: `RULE-4   strong`, with
    `No bug was caught for PROOF-7: ...` under it (`t3.py` C1);
  - the kept bug is dropped and a spot test fires: `RULE-7   weak` (`t3.py` C3);
  - the test does not run with the bug in place: `not run`, `spot-checked` or `weak` (`t4.py` D4);
  - the model names no bug, its part cannot be used or it is not reached: `spot-checked` with
    that sentence, and the printed line ends at `did not break what the proof says.`
    (`t4.py` D6, D7). `skills/audit/SKILL.md:101` describes only the line with
    `A new bug was planted.`
  - "nothing more is asked" holds only until the proof's test or code changes (`t2.py` B5: the
    test strengthened, a plain audit plants again and reads `strong`).
- **Smallest fix:** in each place, "the rule reads what "The verdict" gives: `spot-checked`
  where no other proof holds a caught bug", and in the build skill a fourth ending, "anything
  else: report the line the settle printed". Add the short line to `skills/audit/SKILL.md`.

### C7. Five ways to break the settle code leave every new test passing (weak tests)

Each was made in a scratch copy and the 53 tests of `-k "Settling or PROOF or directive or
hash_bang or case or reason"` in `dev/test_ai_audit.py` and `dev/test_planted_bug.py` run:
`53 passed` each time (`mut.log`).

| Break | Where | The test that should fail |
|---|---|---|
| a settle runs no spot test (`spot = []` under `settle`) | `audit_run.py:526` | none: no proof settles a rule a spot test fires on. `review_criteria.md:294` "The spot tests run again" is unproved |
| a replayed `not run` loses its `why` | `audit_run.py:377` | none: `PROOF-152` covers a skip only, so `ended in an error` after a replay is unproved (RULE-59 names three causes) |
| a settle that asks no model keeps the old `explanation` | `audit_run.py:560` | none: `PROOF-143` does not read `explanation`; `evidence_format.md` says it is empty |
| no `check_unchanged` after the replays | `audit_run.py:543` | none: no proof changes a file during a replay |
| `replay` skips the scope refusal | `targeted_break.py:287-288` | none: RULE-60's "can no longer be planted" is proved for missing `before` lines only |

Also unproved: C1's case (`PROOF-154` settles beside a `not made` neighbour, never a `caught`
one with a changed test), and RULE-56's "until its test or code changes" (`PROOF-148` reads
again with nothing changed).

No new test is vacuous: each of `ai_audit` PROOF-138 to 160 and `planted_bug` PROOF-51 to 58
asserts what its proof names, read line by line. `PROOF-58` misses C2. `PROOF-160` would not
notice a timed-out `claude` left running.

- **Smallest fix:** one proof each for the first, second and third rows; the others with C1.

---

## Likely

### L1. `No break:` with a capital is no answer after a `case:` line (cosmetic, not from this range)

`targeted_break.py:100`: `_NO_BREAK_RE` is case-sensitive while `_AIM_RE`, `_CASE_RE` and
`_OPENS_RE` are not. `parse_answer('case: one\nNo break: nothing')` gives `None`, so
`the answer named no change` (ran, `t5.py`). Fix: `re.I` on `_NO_BREAK_RE`.

### L2. `The audit found 2 out of date.` and `The audit found 2 not audited.` (cosmetic)

`summary.py:262-266`: where the share is over no rule, `AUDIT_FOUND` lists every count. A
settle naming an anchor's rule printed `house_rules RULE-1 has no planted bug that survived:
nothing to settle.` then `The audit found 2 out of date.` (ran, `t8.py`). `audit_line` with all
counts zero gives `The audit found .`; `sentence` and `share_line` both guard it, so no run
reached it. Fix: `AUDIT_FOUND` only where a count other than `not audited` is not zero.

### L3. A rule made `strong` by one proof hides that another proof's two bugs survived (cosmetic)

`t3.py` C1: `RULE-4   strong`, and under it `No bug was caught for PROOF-7: two planted bugs
left the proof's check passing.` The line is printed and stored, and the dashboard's cell is
`strong`. The verdict is decision 121's. See J1.

---

## Judgment calls

- **J1. A settle with nothing changed clears a `weak` rule.** `t2.py` B1: `RULE-3` weak, no
  edit, `--settle RULE-3`, a second bug survives: `spot-checked`, and `rules to strengthen`
  falls from 3 to 2. `t3.py` C1: the same on a rule with one caught proof gives `strong`. The
  contract asks for exactly this, since the build may leave a sound test alone. The audit
  cannot tell a sound test from an untouched weak one, and `review_criteria.md:313` says so.
  A guard is possible: where the kept bug's `break_key` is the current one, print that nothing
  changed since the bug survived.
- **J2. `did not break what the proof says` is printed for a test that checks nothing.**
  `t3.py` C3: the line stands directly above `the test checks nothing.` The bug survived
  because the test asserts nothing, which says nothing about the proof.
- **J3. A kept bug that can no longer be planted is dropped with no line.** `t4.py` D5: the
  helper rewritten and `claude` exiting 1: `RULE-3   spot-checked`, the survived bug gone and
  nothing printed about it. A plain audit does the same after a code change.
- **J4. An always-skipped test is selected by every plain run.** `t6.py`: three `--test` runs in
  a row print `Selected 1 of 1 feature: sample_intake (1 rule to test).` The status says
  `1 rule to test: purlin:test` each time, so the two agree; neither ends.
- **J5. `0 of 8 rules strong (0%) ... 8 not audited` after an audit that read an anchor alone**
  (C4's run). `not audited` rules were in the share's `over` before this range too.
- **J6. An anchor's cell is empty where one rule is `spot-checked` and one `not audited`**
  (`board.py:161-168`, `board.js` `anchorWord`; both agree). Ran `anchor_word` alone.
- **J7. `docs/audit.md:285-299`, "On Purlin's own tests", says what was**, in the past tense,
  and `:290` says "Each bug was put in by hand and its test read against the proof": a person
  judged the 35 findings. `:269` "an earlier measurement". It is the page's account of a trial.
- **J8. The stated narrow limits.** A case over three lines, or with a blank line inside, gives
  `the answer named no change`. `//@ts-ignore` with no space, `/// <reference`, and an
  end-of-line `# type: ignore` or `// @ts-ignore` are comments to the check. `#!` anywhere in a
  `.py` file is code (ran, `t5.py`). RULE-28 and RULE-30 say as much.

---

## Checked and found sound

**The five outcomes (ran).** Replay caught: `caught`, same `file`, `line`, `before`, `after`,
`aim`, `case`, new `break_key`, findings gone, `strong`, `claude` started 0 times, the line
`PROOF-5: the test now catches the bug it missed at src/intake.py:17.` Replay survives and the
new bug is caught: `strong`, 1 call, asked for that proof alone. Both survive: `not made`,
`two planted bugs left the proof's check passing`, null `file`, `line`, `before`, `after`.
No new bug, by `no break`, an unusable part and exit 1: each with any audit's sentence and the
short line. Not run (a skip): `not run`, the change kept, 0 calls. Cannot be planted: asked
anew, and a survivor reads `survived`.

**Other settle cases (ran).** Two `survived` in one rule: one request for both, one caught by
replay and one replaced. A spot finding beside a bug: the spot tests run and set `weak`.
`--settle` twice: the second prints `nothing to settle` and starts no `claude`. Four rules in
one run: only those needing a new bug are asked about. A rule whose test fails: exit 1, the
`fails:` line, its entry untouched, other named rules settled. A rule with no test: `has no
test`. `rule-3`, `RULE-03`, `3`: exit 1 with the `not a rule` line. `--commit`: the changed
test, then the evidence, in two commits; without it, both left uncommitted.

**No trace of a dropped bug (ran).** Neither `after` line nor the case is in any file under
`.purlin/`, `report-data.js` included, nor in the printed output. The request for the second
bug does not hold the first. The package (`scripts/export/package.py:584-590`) copies the
entry, so it holds none (read). Git history keeps an evidence file committed earlier.

**After a settle (ran).** A plain audit and `--audit --all` plant nothing for a proof settled
`caught` or `not made` and keep its sentence; once the test changes, a plain audit plants one
new bug.

**The evidence against `evidence_format.md`.** Every entry written matched the page, the new
paragraph included; no field was added and `Format-Version` did not need to move.

**The three faults.** A `no break` reason in the module's own words prints as the model's,
when asked and when kept. A case over two lines, and one after `file:`, is read. `#!`, `//go:`
and `// @ts-` at column 0 are planted. The timeout proof reads the rule again with one call.

**The summary and the cells (ran).** With an anchor: `1 of 8 rules strong (12%): 1 strong,
3 weak, 6 spot-checked`, the same in the audit's last line, the status and `report-data.js`.
An anchor's cell: `weak`, else `out of date`, else `spot-checked`; `board.py` and `board.js`
agree. No rule passing: the sentence has no audit part.

**The selection (ran and read).** A feature with a current fingerprint and a rule the status
counts `to test` is selected, with the status's own words. It cannot select nothing while the
status says to test: every other state already gives a reason. `build_payload` does not call
`selection`, so there is no loop. The count is per feature and the status's per project, from
the same `left`.

**The pages.** No emoji in any page named. No cost and no count of model calls outside the
quoted papers. The `--settle` syntax, its refusals and exit codes, the two lines, `nothing to
settle`, what a plain test run selects, the anchor's cell and its hover, the two top-bar boxes
and the theme button read as the code does. README, the glossary, `purlin_commands.md`,
`agents/purlin.md`, `docs/how-purlin-works.md`, "Slow proofs" and the 0.10.0 release notes
hold no statement the code contradicts.
