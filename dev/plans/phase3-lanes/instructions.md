# Lane `instructions`

You are lane `instructions` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/instructions`, branch `lane/instructions`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/instructions -b lane/instructions main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-instructions`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q9, Q40, Q57, Q58, Q74 and report questions 9, 40, 56, 57, 58, 74; "Gaps left" for
   `purlin_agent` and `purlin_version`.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `agents/purlin.md` (135 of 135 lines)
- `specs/instructions/purlin_agent.md`, `specs/instructions/purlin_version.md`,
  `specs/instructions/purlin_output.md` (new)
- `dev/test_purlin_agent.py`, `dev/test_purlin_version.py`, `dev/test_purlin_output.py` (new)
- `dev/bump_version.sh`, `.github/workflows/version-check.yml` (P1 changed both for Q75)

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q9, the one rule on emoji** (C10): write `specs/instructions/purlin_output.md`:
   `# Feature: purlin_output`, `> Scope: scripts/**, templates/**`, a Description saying it holds
   the one check of what Purlin prints, one rule ("No file under `scripts/` or `templates/`
   carries an emoji or a pictograph other than `▶`"), and one proof ("Every tracked file under
   `scripts/` and `templates/` is read; none holds a character with the Unicode property
   `Extended_Pictographic`, or U+FE0F, other than `▶`"). `dev/test_purlin_output.py` carries the
   `Extended_Pictographic` ranges as a table (from Unicode's `emoji-data.txt`) and reads every
   tracked file under both folders. The tree passes today: `→ ▼ ▲ ─ · ←` are not pictographs.
   The other lanes delete their clauses (C10).
2. **Q57:** `agents/purlin.md` line 61's sentence "`no proof written` means no proof line names
   the rule." goes; purlin_agent RULE-5 drops that clause, PROOF-5 is reworded, PROOF-37 goes;
   `dev/test_purlin_agent.py` around lines 264 to 266 and 411 to 420.
3. **Decision 94, the agent's line** (**PENDING OQ5**; with OQ5's third option it stays):
   `agents/purlin.md` lines 49 to 50, "suggests the test
   command", becomes "suggests a command for each test tool it recognises"; no line is added.
4. **Decision 94, instruction rules:** purlin_agent RULE-1 to RULE-8 take "The agent definition"
   as their subject.
5. **Q40's reason, applied** (C11, **PENDING OQ13**; with OQ13's second or third option this item
   is left as it stands): purlin_agent's damaged-copy proofs (about 35) and
   purlin_version's proofs whose case is a damaged copy of a file the spec covers leave the
   specs, each kept as a second assertion in its guarded test. purlin_version's proofs about a
   bump-script input that is refused, or `VERSION`'s content, stay.
6. **Q74:** purlin_version RULE-7 reads "the bump script is the one command that sets a new
   number; anything else that writes a version field copies it from `VERSION`"; a new proof and a
   test that scans `scripts/` for a written `version` field whose value is not read from
   `VERSION` (`scripts/init/scaffold.py` and `scripts/init/update.py` read it today).
7. **Q58:** the ban on emoji stays inside the agent's fourth never.
8. **Split by claim and one case per proof** (C11): candidates purlin_version RULE-2 and RULE-7,
   purlin_agent RULE-5.


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
cd /Users/richlabarca/LocalCode/purlin-wt/instructions
.venv/bin/python -m pytest dev/test_purlin_agent.py dev/test_purlin_version.py dev/test_purlin_output.py -q      # your own files, whole
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

- Commit on `lane/instructions` only, with the prefixes of `references/commit_conventions.md`, ending
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
