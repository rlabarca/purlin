# Lane `review`

You are lane `review` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/review`, branch `lane/review`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/review -b lane/review main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-review`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q9, Q12, Q13, Q25, Q26, Q37 and report questions 25, 26; the fault list item for
   `ai_audit` (report line 51, fixed on `main` in `6f8a54cc2`).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/review/ai_audit.py`, `scripts/review/marked_tests.py`
- `specs/review/ai_audit.md`
- `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`
- `references/review_criteria.md`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q12 and Q26** (C1.10, **PENDING OQ15**): `ai_audit.py --feature <f> --rule <RULE-N>`, where
   `reading_for` finds no such rule (around lines 537 to 551), prints
   `sign.not_a_rule(feature, rule)` (C1.10) and never formats `sign.NOT_A_RULE` itself: import
   `not_a_rule` from `scripts/review/sign.py`, which P2 wrote, since the number of values the
   line takes depends on the owner's words. It exits 1. RULE-13 says it "prints the line and
   exits 1"; PROOF-76 is reworded (test around line 771).
2. **Q25** (C3.10, **PENDING OQ17**): `render` (around lines 465 to 480) prints, after the
   findings, a blank line, `What the audit noted`, and each note indented two spaces; nothing
   where there are no notes. RULE-14 reads "... each finding, and its notes under their own
   heading after the findings"; a new proof. The sign walk's audit block does not change.
3. **Q9:** RULE-14 drops "and no emoji"; PROOF-29 drops "with no emoji"; the `_emoji`
   assertions in its test go (around line 791).
4. **Q13's reason, applied** (**PENDING OQ14**): RULE-15 (an internal "returns nothing" shown
   only through RULE-13) folds into RULE-13, PROOF-7 re-pointed. With OQ14's second option
   RULE-15 and PROOF-7 stay as they are.
5. **`references/review_criteria.md`** (the one home of what the model is sent; C12, S2):
   - decision 94: what the model is shown about strength is the feature's one share, in every
     language; no per-rule number (around lines 71 to 74, 88 to 89, 98 to 100);
   - Q37: where nothing was measured, or the engine cannot run on this system, the model is
     shown `test strength: not measured`; when that leaves a rule weak is said once, in
     `references/hard_gates.md` (the paragraph under the gate table), and this file points at it
     in one clause rather than restating it;
   - Q25: the notes are printed after the findings (around lines 112 to 113).
   Tests of other lanes read this file's hash at run time; check none asserts the lines you
   change.
6. Confirm nothing in `scripts/review/` prints `n/a` (decision 93, fixed in `6f8a54cc2`).
7. **Q65, the audit reader** (C1.9, C3.4; **PENDING OQ1**): `ai_audit.py` `main`, after the
   command line is read and before the payload is built (around line 537), prints
   `config_engine.config_problem(project_root)`'s sentence when it answers, writes nothing and
   exits 1. One new rule, or one proof under RULE-13 if it already says what the reader does
   when it cannot start, with a test whose `.purlin/config.json` holds a trailing comma. The
   module docstring's exit paragraph names it, as C6's `scripts/review/ai_audit.py` row does.
8. **Split by claim and one case per proof** (C11): candidates RULE-7, 14.

**You consume** `sign.not_a_rule(feature, rule)` and `config_engine.config_problem` (P2, C1.10,
C1.9).


## How to number, split and write proofs

- A new id is one more than the highest the spec file has held since it was last written whole
  (`git log -p --follow -- <spec>`); a deleted number is never reused.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words, names no file of code, function or test framework, and has a test of
  its own with `# purlin: <feature> PROOF-<n>` directly above it. A proof whose test loops over
  gates, inputs or systems with one expected result becomes one proof per case (Q1, Q8).
- Split by claim (decision 94): split a rule of your specs where its text states two or more
  claims, its proofs fall into groups each showing exactly one, and no proof shows two. The first
  claim keeps the id; each other claim takes a new id; proofs keep their ids and text, only their
  `(RULE-N)` changes; markers do not change. Do not split a rule whose claims share every proof.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`, no reader of an old spelling.
- A format you change updates its file under `references/formats/` in the same commit, with the
  bump the contracts name.

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/review
.venv/bin/python -m pytest dev/test_ai_audit.py dev/test_ai_audit_tests_named.py -q      # your own files, whole
bash dev/run_tests.sh --fast                     # the fast sweep, in your worktree
```

If `.venv` is missing in the worktree, use `/Users/richlabarca/LocalCode/purlin/.venv/bin/python`.
Do not run the full sweep; integration runs it once.

Before you break code on purpose to see an assertion fail, confirm the test that runs it uses
`dev/fake_claude.py` or no model at all, that no real `claude` is on its `PATH`, and that it
reaches no real git host, `gh`, `az` or network service. Restore the file with
`git checkout -- <that file>`; never `git checkout -- specs/`.

A failure in a test file you do not own: check `phase3-contracts.md` C7. If the contracts predict
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that file.

## Limits

- Commit on `lane/review` only, with the prefixes of `references/commit_conventions.md`, ending
  each message with the attribution lines your session gives. Push nothing, tag nothing, open no
  pull request.
- Run no `purlin:audit` and no `purlin:sign`, never start the real `claude` program or any real
  service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, screenshots.
- Keep each skill and `agents/purlin.md` within its line ceiling; a change cuts as many lines as
  it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files where a
  lane merged earlier changed a result the contracts predict.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id now, and its rule and proof counts before
  and after.
- Tests in your files before and after, and the `--fast` result.
- Every split, as `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`.
- Every proof deleted, moved or re-pointed.
- Every word a person reads that you chose because no decision or contract gave it.
- Every item left as it stands, and why.
- Every failure in a file you do not own.
