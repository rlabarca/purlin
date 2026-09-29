# Lane `dashboard`

You are lane `dashboard` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/dashboard`, branch `lane/dashboard`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/dashboard -b lane/dashboard main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-dashboard`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Report questions 3 to 6 and 22; decisions 85 to 93 in `three-levels.md` (lines 774 to 830);
   `design/readme.md`.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/report/src/**` (`page.html`, `styles.css`, `theme.js`, `filters.js`, `board.js`,
  `rule.js`, `app.js`), `scripts/mcp/purlin/report_data.py`, `dev/build_report.py`,
  `dev/capture_doc_screenshots.py`
- `specs/dashboard/purlin_report.md`
- `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`, `dev/test_report_refresh.py`
- `dev/fixtures/report/*.json`

## Where `main` stands

Commit `b172b3c1c` (after this plan was first written) changed `scripts/report/src/rule.js`,
`scripts/report/src/styles.css`, `specs/dashboard/purlin_report.md`, `dev/test_purlin_report.py`
and `docs/dashboard.md`: on the dashboard each test line, under a proof or under a rule's own
tests, starts with a dot drawn in its result's colour, the result's word is the dot's hover, and
the line carries no badge. RULE-46 says so; PROOF-180 shows it; PROOF-65, PROOF-152, PROOF-155
and PROOF-158 read the line that way. In `specs/dashboard/purlin_report.md` the highest ids on
`main` are RULE-56 and PROOF-180; take a new id as one more than the highest the file has held
since it was last written whole (C11), which is no lower than RULE-57 and PROOF-181. Every
assertion you write or change about a test line reads the dot, its colour and its hover, and
never a `PASSED` or `FAILED` badge on the line: badges stay on a rule's row and on a proof's own
result, as decision 85 has them. `docs/dashboard.md` is lane `words`'s.

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q22, the `To correct` button** (C2 row 2; **PENDING OQ3**, with whose removal option there
   is no button): `to_correct` joins `VERSION_KINDS` in
   `filters.js`: no rule carries it, and choosing it names `purlin:build` and leaves every rule
   showing, as `To tag` does. RULE-13 and RULE-14 name `To correct` beside `To tag`; one proof,
   built from a payload whose `left` holds
   `{"kind": "to_correct", "count": 1, "text": "1 test comment to correct", "command": "purlin:build"}`.
   `to_measure` (**PENDING OQ9**) is a rule kind: its button is named from its text like any
   other; check it reads `To measure` and add no code for it unless it does not.
2. **Q9:** RULE-4 keeps "no shadow, no gradient" and drops "no emoji"; PROOF-4 drops "no
   character of it is an emoji" and the check behind it (C10 holds the one rule).
3. **Decision 94, one share per feature:** PROOF-146 ("login `RULE-2`'s test strength removed")
   is reworded to the feature's strength, which is what the page shows; its test follows. A rule
   listed under another feature keeps its owner's share (plan section 7, call 52: the rule is
   counted under the feature that owns it).
4. Q3, Q4, Q5 and Q6 stand as built.
5. Look at the page with playwright from the `.venv`, headless, at 1500, 1280, 1024, 768 and 390
   pixels in both themes, with a `To correct` line present and one rule unfolded, so its test
   lines show their dots; a value never breaks inside itself.
   Build the page locally to test it; stage neither built page.
6. **Split by claim and one case per proof** (C11) where a rule you touch meets the test.


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
cd /Users/richlabarca/LocalCode/purlin-wt/dashboard
.venv/bin/python -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py -q      # your own files, whole
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

- Commit on `lane/dashboard` only, with the prefixes of `references/commit_conventions.md`, ending
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
