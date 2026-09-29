# Lane `reports`

You are lane `reports` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/reports`, branch `lane/reports`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/reports -b lane/reports main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-reports`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q22, Q23, Q24 and report questions 22, 23, 24; the fault list item for `reports`
   RULE-8 (report line 50).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/reports.py`, `scripts/mcp/purlin/markers.py`
- `specs/run/reports.md`, `dev/test_reports.py`
- `references/formats/marker_format.md`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q22, the report side:** P1 moved `marker_problems` into `markers.py`. PROOF-19 drops
   "still ends on `Nothing left to do.`": "... the run prints
   `tests/test_login.py:13 names nosuch PROOF-1, which no spec has. Correct the comment, or run purlin:build to repair it.`
   and exits 1". The ending's new line is lane `core`'s proof.
2. **Q23** and fault RULE-8: RULE-8 reads that `Passed`, `Warning`, `Completed` and
   `PassedButRunAborted` pass, `Failed`, `Error`, `Timeout` and `Aborted` fail, and any other
   outcome is skipped, as the code already reads; one new proof for each of the three rarer
   passing outcomes (test near line 395); `references/formats/marker_format.md` (around line
   134) says the same, with no Format-Version bump (clarified wording).
3. **Q24** (C3.9; **PENDING OQ18**): `markers.near_miss` (around lines 1003 to 1012) suggests
   only ids a comment may name. Where the nearest id is a rule with exactly one proof, the fix
   names that proof and the `why` reads
   `` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3` ``;
   a rule with no proof keeps today's fix and why; a rule with two or more proofs gives no near
   miss. An exact comment naming a rule with one proof is not a near miss: the run's own line
   names it. RULE-24 is reworded; PROOF-91 becomes: where `login`'s `RULE-3` has the one proof
   `PROOF-3`, `# purlin: login RULE-30` is listed with the fix `# purlin: login PROOF-3`; new
   proofs: two proofs under RULE-3 give no near miss; no proof gives the fix `# purlin: login RULE-3`.
4. **Decision 95, `{files}`** (C12, S1): `references/formats/marker_format.md` says that
   `{files}` holds the test files carrying the markers of the proofs the run selected, and
   points at `references/hard_gates.md`, "Where a runner runs", for which proofs a remote
   runner selects, in one clause. No bump (the placeholder's shape does not change).
5. **The interpreter lookup** (C9): the example command in `marker_format.md` (around line 211,
   `python3 scripts/mcp/purlin/markers.py`) takes the form
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" ...`.
6. **Split by claim and one case per proof** (C11): candidates RULE-16, 17, 19.
7. **`references/formats/marker_format.md`, Q24 and decision 94** (no Format-Version bump: no
   field or structure changes):
   - "Comments that are nearly a marker" (line 206 onward), Q24 (decision 94): the paragraph
     that says when a comment is a near miss says that a suggestion names only an id a comment
     may name; that a comment one character from a rule with exactly one proof is offered that
     proof, with the `why` of C3.9 (**PENDING OQ18**; with its third option no suggestion is
     made for a comment one character from a rule id, and the section says so); and that one
     character from a rule with two or more proofs is not a near miss. The field table stays.
   - Line 106, "With no entry left, the run runs nothing and suggests one": it suggests one
     for each test tool it recognises (decision 94, C3.7 R4; **PENDING OQ5**; with OQ5's third
     option the line stays).

**You consume** P1's move. **You produce** C3.9's near misses, read by `purlin:build`.


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
cd /Users/richlabarca/LocalCode/purlin-wt/reports
.venv/bin/python -m pytest dev/test_reports.py -q      # your own files, whole
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

- Commit on `lane/reports` only, with the prefixes of `references/commit_conventions.md`, ending
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
