# Decision 124: a test run settles every finding; the build plan

Written by the coordinator on 2026-10-02 against local `main` after decisions 122 and 123
(`dev/plans/handoff.md`). Decision 124 is in `dev/plans/three-levels.md`. Nothing here is
built. Three lanes, all local, each in its own worktree. Nothing is pushed, tagged or signed.

## 0. What changes, in six sentences

1. The audit can **settle** a rule: plant each recorded bug that survived again, and run the
   proof's test as it stands now.
2. A recorded bug the test now catches reads `caught`, and the rule reads `strong`.
3. A recorded bug the test still passes was wrong: it is dropped, one new bug is planted for
   that proof, and a second survivor leaves the rule `spot-checked` with the reason.
4. `purlin:build` on a weak rule writes the assertion the proof names, runs the tests, then
   settles the rule; where the proof names too little, it stops and proposes a sharper proof.
5. The pages say what to do with a finding, in the short bullets the owner approved, and where
   to stop.
6. Purlin's 12 loose proofs are sharpened, its 14 weak rules are settled with the new loop, and
   three faults left from the code review are fixed.

## 1. The contract (lane `audit`)

**The command.** `scripts/run/purlin_run.py --audit --feature <name> --settle RULE-N`, with
`--settle` given once per rule and exactly one `--feature`. The skill writes it
`purlin:audit <feature> RULE-N --settle`. `--commit` works as on any audit.

- `--settle` without `--audit`, without `--feature`, with two features, or naming a rule the
  feature does not have, is refused before anything runs, exit 2 (a rule not in the spec: exit
  1, with the existing line `<feature> <RULE-N> is not a rule any spec has. Run purlin:status
  <feature> to see its rules.`).
- The run is an audit run: the feature's tests run first, as today. A rule whose tests do not
  pass is not settled, and the run says so with the status, as today.

**Settling one rule.** For each proof of the rule whose kept entry under `breaks` reads
`survived`:

1. **Replay.** The recorded change (`file`, `before`, `after`) is planted in a copy, by
   `targeted_break`, with every refusal it has today, and the proof's own tests run, once
   before the change and once with it in place. No model is asked.
2. **The test fails**: the entry reads `caught`, with the same `file`, `line`, `before`,
   `after`, `aim` and `case`, and the `break_key` of the test and code as they stand. Its two
   findings leave the rule's `findings`. The audit prints, under the rule,
   `  PROOF-2: the test now catches the bug it missed at src/auth.py:12.`
3. **The test still passes**: the bug is dropped. The model is asked for one new bug for that
   proof, in the usual request, and it is planted as any bug is. The audit prints
   `  PROOF-2: the bug at src/auth.py:12 did not break what the proof says. A new bug was planted.`
   - The new bug is caught: `caught`, as any caught bug.
   - The new bug survives: no bug is kept. The proof's entry reads `not made`, with the `why`
     `two planted bugs left the proof's check passing` and the current `break_key`, and `no_bug`
     gains `No bug was caught for PROOF-2: two planted bugs left the proof's check passing.`
   - The new part cannot be planted, or the model answers `no break`, or the model cannot be
     reached: the sentence that case has today.
4. **The test does not run** with the recorded bug in place (a skip, an error, a timeout): the
   entry reads `not run`, as today.
5. **The recorded change can no longer be planted** (its `before` lines are not in the file
   exactly once): the proof is read as a plain audit reads it, with a new bug, and a survivor
   reads `survived`.

A proof of the rule with no `survived` entry keeps what it has. The spot tests are run again
over the rule's tests. The verdict is decision 121's, unchanged: `weak` where a spot test fires
or a bug survived, else `strong` where a bug was caught, else `spot-checked`.

A rule named with `--settle` that has no kept `survived` bug prints
`<feature> RULE-N has no planted bug that survived: nothing to settle.` and is left as it is.

A dropped bug is kept nowhere: not under `breaks`, not in `findings`, not in the package. The
`not made` entry of step 3 holds the state, so a later plain audit plants nothing for that proof
until its test or code changes.

**What a plain audit does is unchanged.** A test that changed gets a new aimed bug, and a
survivor reads `weak`. Only `--settle` replays.

**Formats.** `evidence_format.md` gains the new `why` and the sentence of `no_bug` in its
wording. No field is added and no version moves. The command's syntax goes into
`references/purlin_commands.md` (lane `words`).

**Three faults left from the code review** (`dev/plans/d122-reports/review-audit.md`, items A5,
A8's rest and A11), each with a rule, a proof and a test seen failing first:

- A `no break` reason whose words match one of the module's own sentences is classed by where
  it came from, not by its words.
- A `case:` line wrapped over a second line is read to the end of that second line where the
  next line opens none of `aim:`, `case:`, `file:`, `before:`, `after:`, `no break:` or `===`;
  a `case:` line standing after `file:` and before `before:` is read.
- The comment check plants a change to a line opening `#!` and to a `//` line that opens
  `//go:` or `// @ts-`. Its narrow limit stays in the rule's words.

Also `ai_audit` PROOF-122 is reworded, with its test brought in step, to: "`RULE-2`'s entry
reads `spot-checked` because the model could not be reached, whether `claude` exited with an
error, was not on PATH or gave no answer, and nothing has changed since; the audit run again,
with a `claude` that answers, reads `RULE-2` and starts `claude` exactly `1` time".

**The tests run on sample projects**, as decision 123's do: `dev/sample_lab.py` and the small
`age` project of `dev/test_planted_bug.py`, with the fake `claude`. At least these proofs:

- The sample lab project's `PROOF-5` test takes its expected age from the code's own helper,
  and the kept bug rounds that helper. The test is changed to expect `25`. Settled, the entry
  reads `caught`, the rule `strong`, and no model is asked.
- The same kept bug with the test left as it was, and a fake that answers with a second bug
  that also survives: the entry reads `not made` with the new `why`, the rule `spot-checked`,
  and the model was asked exactly once.
- The same, with a second bug the test catches: `strong`.
- A kept bug whose `before` lines are gone from the file: a new bug is planted and a survivor
  reads `survived`.
- After a drop, the evidence file holds none of the dropped bug's `after` lines.
- A plain audit after the same test change plants a new bug and replays nothing.

## 2. The words (lane `words`)

**`skills/build/SKILL.md`**, the part for a weak rule, in the skill's own voice:

- A spot test's finding: fix the test, as today.
- A planted bug that survived:
  1. Read the proof, its test, the finding and the case line under it.
  2. Write the assertion the proof names, for the proof's own case: the exact value, line or
     absence the proof gives. Never change the code under test for a finding. Never narrow or
     reword a rule or a proof to make a finding go away. Never change a test that already
     asserts what its proof names.
  3. Where the proof names too little to write that assertion, stop for that proof: say so,
     propose a sharper proof sentence, and send the person to `purlin:spec`.
  4. Run `purlin:test <feature>`, then `purlin:audit <feature> RULE-N --settle`.
  5. Report which of three ways it ended: the test now catches the bug; the finding was wrong
     and a new bug was caught; two bugs left the proof's check passing, and the rule reads
     `spot-checked`.

**`skills/audit/SKILL.md`**: the `--settle` usage line; Step 2's bullets for the two new printed
lines; Step 3: a rule reads `weak`: `→ Run: purlin:build <feature>`, and nothing else.

**`references/review_criteria.md`** (lane `audit` owns the file; it is sent to the model
verbatim): one new section, "Settling a finding", the one home of section 1 above. Every other
page points at it.

**`docs/audit.md`**, top, a new heading after "How it works", `What to do with a finding`:

> - Read each `weak` finding. It names the missed bug and the case the AI says it breaks.
> - Run `purlin:build`. It writes the check the proof names and runs it against that bug.
> - **The check fails**: the finding was right. The test is now stronger and the rule reads
>   `strong`.
> - **The check passes**: the bug did not break what the proof says. The audit plants one more.
>   If that one is wrong too, the rule reads `spot-checked` and nothing more is asked.
> - **The proof is too loose to write a check from**: `purlin:build` stops and proposes a
>   sharper proof.
> - Never change a sound test or narrow a rule to clear a finding.

and under "What it does not do":

> - A rule made `strong` by a strengthened test caught the bug it once missed. That test was
>   written after the bug was seen.
> - The share of strong rules is a guide, not a score. A high share with the rest read is done.

In the reasoning section, a new part after the trial, `On Purlin's own tests`, from
`dev/plans/handoff.md` and `dev/plans/d122-reports/strengthen.md`: ten specs, 28 rules weak, 35
surviving bugs, 33 held, 2 wrong and why each, 12 proofs too loose, and the second audit's 14.
Exact numbers, no cost, no count of model calls.

**Elsewhere**: `references/purlin_commands.md` (syntax and the row), `references/glossary.md`
(*settle*, one definition), `docs/running-and-evidence.md` and `docs/how-purlin-works.md`
wherever they say what a weak rule's next step is, `agents/purlin.md` where it routes a weak
rule, `RELEASE_NOTES.md` 0.10.0 (one sentence: `purlin:build settles a weak rule with a test
run: it strengthens the test, replays the bug the test missed, and the rule reads strong once
the test catches it.`), the ten descriptions only if one changes, and the deck's `audit`
slide's notes (its rows are full; the notes gain two sentences on settling). The deck is not
published by a lane.

`Left to do` keeps `<n> rules to strengthen: purlin:build`: build is the next step for every
kind of finding.

## 3. The proofs (lane `proofs`)

The 11 sentences of `dev/plans/d122-reports/strengthen.md` for `run_script` PROOF-88, 91, 93,
117, 271, 288, 289, `signatures` PROOF-228, 238, `package` PROOF-52 and `evidence` PROOF-88 are
applied (`ai_audit` PROOF-122 is lane `audit`'s). Each is checked against
`references/spec_quality_guide.md`: one case, at most 60 words, no test mechanics; where a
sentence fails that, it is corrected and the report says how. The report lists each proof
before and after, for the owner.

A reworded proof whose test last changed before the rewording is listed as a test comment to
correct. Each such test is read against the new sentence and changed where it does not yet show
it; where it already does, its name is brought in line with the new sentence, as integration did
for `signatures` PROOF-221.

## 4. The lanes

| Lane | Owns, and writes nothing else | Acceptance |
|---|---|---|
| `audit` | `scripts/review/audit_run.py`, `ai_audit.py`, `targeted_break.py`, `scripts/run/purlin_run.py`; `specs/review/ai_audit.md`, `specs/review/planted_bug.md`; `references/review_criteria.md`, `references/formats/evidence_format.md`; `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py`, `dev/sample_lab.py`, `dev/fake_claude.py` | the new tests fail first, then pass; those test files and `dev/test_run_script.py` pass |
| `words` | `README.md`, `docs/`, `skills/*/SKILL.md`, `agents/purlin.md`, every file under `references/` but `review_criteria.md` and `formats/`, `RELEASE_NOTES.md`, `dev/plans/deck/build_deck.py`; `specs/skills/*.md`, `specs/instructions/*.md`; `dev/test_skill_*.py`, `dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`, `dev/skill_checks.py` | its test files pass; the deck's two checks pass with `DECK_ROOT` in a scratch folder |
| `proofs` | `specs/run/run_script.md`, `specs/review/signatures.md`, `specs/export/package.md`, `specs/mcp/evidence.md`; `dev/test_run_script.py`, `dev/test_signatures.py`, `dev/test_export.py`, `dev/test_evidence_reader.py` | its four test files pass |

`purlin_run.py` is lane `audit`'s for the one argument; its rule and proofs for `--settle` go in
`specs/review/ai_audit.md`, so lane `proofs` alone writes `specs/run/run_script.md`. Lane
`audit` runs `dev/test_run_script.py` and changes none of it.

Merge order: `audit`, `proofs`, `words`, each `--no-ff`.

**The lane brief** is section 4 of `dev/plans/d123-plan.md`, with `d124` in every path and
branch, this plan in place of `d122-plan.md`, decisions 100 to 124, and the report at
`dev/plans/d124-reports/<lane>.md`. Its traps hold, and one more: never use `pkill` on anything
but your own process ids.

## 5. Integration, by the coordinator, on `main`

1. The three merges. `bash dev/run_tests.sh` to 0 failed.
2. `python3 scripts/run/purlin_run.py --test --all --commit` to the clean state: every marker
   tied, no test comment to correct.
3. The plan's grep, empty: `git grep -n -i -E 'cost_usd|total_cost|how many (model|AI) calls|one model call' -- . ':!dev/plans' ':!.purlin'`.
4. **The loop on Purlin's own weak rules**, which the owner asked for. For each rule the status
   lists `to strengthen`, by the build skill's steps as written, with the real model, detached
   (`nohup`), one feature at a time, nothing else touching the checkout while it runs:
   strengthen the test, `--test`, `--audit --feature <f> --settle RULE-N --commit`. Record for
   each rule which of the three ways it ended, and each proof the build stopped at as too loose,
   with the sentence proposed. Expect the status to end with no rule to strengthen, or name each
   that is left and why.
5. A reader that built none of it reviews the settle code (as `review-audit.md` did) and reads
   the changed pages against the code; fix what it finds that is certain.
6. `bash dev/run_tests.sh` and `--test --all --commit` again; `python3 dev/windows_run.py`.
7. The dashboard, looked at with playwright from the `.venv`, both themes, 1500 and 390: a rule
   settled `strong`, and a rule left `spot-checked` with the two-bugs reason.
8. The deck's source built and checked; the `audit` slide's notes published only if the owner
   said to; the `together` and `manual` slides are still the owner's to publish.
9. `dev/plans/handoff.md` rewritten for where it stands; `d122-plan.md`, `d123-plan.md` and
   `d122-reports/` removed if the owner has read them, else kept.

## 6. Calls this plan makes

- `--settle` is an argument of the audit, not a new command, and build is the only thing the
  pages tell a person to run for a weak rule.
- A second survivor is recorded as `not made`, which is the existing word for a proof no bug
  stands for, so no new result word and no format version.
- The audit does not check that the test "is the assertion the proof names". Build is told to
  write exactly that, and stops where it cannot. A person who runs `--settle` by hand over an
  unchanged weak test gets the bug dropped and, most likely, the rule `spot-checked`.
- The two printed settle lines are printed and not stored.
- The count of two is not stored between runs: one settle run drops, replants once and ends.
  A second `--settle` on the same rule finds no `survived` entry and does nothing.
- Left out: auditing the 29 specs never read; `evidence_writer`'s duplicate helper; the
  `v0.10.0` tag the docs example names; signing and pushing.
