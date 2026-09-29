# Lane `update`

You are lane `update` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/update`, branch `lane/update`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/update -b lane/update main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-update`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q9, Q17, Q18, Q19, Q37, Q65 and report questions 17, 18, 19; "Gaps left" for
   `update`.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/init/update.py`
- `specs/init/update.md`, `dev/test_init_update.py`
- `dev/fixtures/upgrade-0.9.5/**`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q17:** RULE-11 goes; PROOF-11 and PROOF-44 are re-pointed to RULE-10, text unchanged.
2. **Q18** (L3): `_ask_gate` (around lines 391 to 404) prints `scaffold.NOT_A_GATE % (answer, gate)`
   (P1, C1.7), naming the gate it used, the project's own default; an empty answer prints
   nothing. RULE-12 is reworded; PROOF-47 is reworded or a new proof added (test around line 526).
3. **Q19, the upgrade's side:** RULE-32, PROOF-59 to PROOF-66 and their tests (around lines 1668
   to 1745) go, and so does `set_up_by_095` (lane `run` moved it into the run); the Description
   loses its last sentence.
4. **Decision 94 and Q37, a tool that cannot run here counts as none** (C1.3): `_ask_mutation`
   asks `mutation.runs_here(engine)`; on Windows a pytest project is not asked the breaking
   question and prints `init.NO_ENGINE_HERE` (landed by P2, C1.11; **PENDING OQ12**) in place of
   `init.NO_ENGINE`; with OQ12's removal option it prints no mutation line. New proof with the
   system given as Windows.
5. **Q9:** RULE-20 drops "What the run prints carries no emoji," and PROOF-20 goes (test around
   line 1630).
6. **Q65, the upgrade** (C1.9, C3.4; **PENDING OQ1**): `_config` stops answering `{}` for a file
   that cannot be read; the upgrade prints `config_problem`'s sentence, writes nothing and exits
   1. New rule and proof.
7. **Line endings:** `_read` and `_write` open with `newline=''`, so a rewrite of spec lines keeps
   each line's own ending byte for byte (update RULE-13, 23 and 24 are on the Windows list for
   this). Existing tests hold.
8. **Split by claim and one case per proof** (C11): candidates RULE-8, 15, 16, 26, 29.
9. The file-link test (PROOF-31) is left as it stands: its `@env(macos)` tag is wave W's (plan
   section 6), after the owner reads the Windows list and answers OQ24.
10. P1 set the unknown-host line PROOF-51 quotes; leave it.

**You consume** P1's `NOT_A_GATE` and `runs_here`, P2's `config_problem`. Lane `run` must stop
calling `update.set_up_by_095`; it merges before you.


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
cd /Users/richlabarca/LocalCode/purlin-wt/update
.venv/bin/python -m pytest dev/test_init_update.py -q      # your own files, whole
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

- Commit on `lane/update` only, with the prefixes of `references/commit_conventions.md`, ending
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
