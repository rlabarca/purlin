# Lane `mutation`

You are lane `mutation` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/mutation`, branch `lane/mutation`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/mutation -b lane/mutation main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-mutation`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q37, Q38, Q39, Windows Q4 and report questions 36, 37, 38, 39; the fault list item
   for `mutation` (report line 53); "Gaps left" for `mutation`; the report's rows for mutation
   RULE-5, 7, 13, 14, 18, 22 (around line 2984).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/mutation/__init__.py`, `stryker.py`, `stryker_net.py`, `mutmut.py`, `none.py`
- `specs/run/mutation.md`
- `dev/test_mutation_adapters.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Decision 94, test strength is one share per feature** (clears the fault that matched a
   test by the end of its path): the per-rule working goes.
   - `stryker.py`: `_clean_name`, `_same_file`, `_same_test`, `test_ids_by_rule` and the per-rule
     part of `parse_report`.
   - `__init__.py`: `rule_entry`, `rules_by_feature`, `feature_tests`, the `rules` part of
     `empty_features`, `timed_out_feature` and `normalise`, the `attribution` docstring, and the
     fourth parameter of `run_breaks` (C1.1: final signature
     `run_breaks(project_root, engine, scope_by_feature)`).
   - `stryker_net.py`, `mutmut.py`, `none.py`: their rule entries.
   - `specs/run/mutation.md`: RULE-4, 9, 10 and 11 go; RULE-17, 19, 20 and 22 lose their rule and
     attribution clauses; the Description says one share per feature; proofs 4, 9, 10, 11, 40 to
     45, 62 and 63 go or are reworded to the feature's share; the attribution parts of proofs 17
     to 20, 22, 38, 60, 65 and 66 go.
2. **Q37 and Windows Q4, the engine's answer** (C1.2, C3.2): the answer keeps
   `features[f]['scope_score']` and gains `features[f]['missing']`.
   - Not installed: `engine` names the selected engine, `available` false, `reason` its
     not-installed sentence (the three kept word for word), every feature's `missing` the same.
     **PENDING OQ11** for .NET itself missing:
     `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`.
   - Timed out: that feature's `missing` is **PENDING OQ11**
     `the engine timed out after <seconds> s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`
     (the first `<seconds>` filled with `ARM_TIMEOUT`, the second literal). OQ11's other
     options are in C3.2: the second ends `measure nothing: run purlin:audit again`, the third
     keeps today's words for both reasons.
   - Wrote no report (RULE-12): **PENDING OQ10** (options 1 and 2), that feature's `missing` is
     `<engine> ran and wrote no report: run purlin:audit again`
     (`mutmut`, `stryker` or `dotnet stryker`). With OQ10's options 3 and 4 it stays `''`.
   - A feature whose spec names no code files: nothing changes here. It is not handed to the
     engine, as today, and gets no `missing`; lane `core` reads that case from the spec (C4.2).
   - mutmut on Windows: `mutmut.run` asks `runs_here('mutmut')` (P1, C1.3); when false it answers
     `engine: none`, `available: false`, `reason` **PENDING OQ12**
     `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`
     (OQ12's second option: `mutmut does not run on Windows`; its removal option: `''`),
     every `missing` `''`. RULE-18 gains the Windows clause; a new proof with the system given as
     Windows (monkeypatch `os.name` or pass the system) reads that answer.
   - New proofs: not installed gives each feature that `missing`; timed out gives it to the
     feature that ran out.
3. **Q38, mutmut's breaks matched by file:** each module name `a.b` becomes `a/b.py` or
   `a/b/__init__.py`, tried at the project root and then under `src/`, the root winning when
   both exist (plan call 30); the break counts for every feature whose scope reaches that file,
   through `fingerprint.expand_scope` (tracked files); a module that maps to no tracked file
   counts for none. `_segments`, `_overlap`, `_glob_covers`, `source_file` and `group_by_file`
   are replaced. RULE-17 and RULE-21 are reworded (RULE-21 folds into RULE-17 if they always pass
   together); PROOF-17, 57, 58, 21 and 59 reworked; new proofs: a scope of `src/` gets the breaks
   of `src/login/session.py`; a scope naming `pkg/__init__.py` does not get `pkg/other.py`'s
   breaks. These tests build a git repository.
4. **Q39:** `stryker_net.find_report` (around lines 56 to 73) returns only `mutation-report.json`;
   new proof under RULE-13: with only `other.json` in the output folder nothing is measured and
   the log reads `login: dotnet stryker exited 0 and wrote no report`.
5. **Decision 95, fault 2, Stryker's project copy on Windows:** `stryker.binary` tries
   `node_modules/.bin/stryker.cmd` on Windows before the search path. `install_program` in
   `dev/test_mutation_adapters.py` (around lines 149 to 158) writes a `.cmd` wrapper on Windows
   for stryker, dotnet and mutmut, and the same shebang script with the exec bit elsewhere. The
   Windows proof waits for wave W.
6. **Q50:** P1 made `execute` start `subprocess.Popen([*command], ...)`; keep that form.
7. **One case per proof** (Q8): PROOF-1 (four frameworks), PROOF-23 (three), PROOF-30 (two tools)
   become one proof each. **Split by claim** (C11): candidate RULE-22.

**You consume** P1's `runs_here` and `fingerprint.expand_scope` (read-only). **You produce**
C1.2's answer, which lane `run` reads with `.get('missing') or ''`.


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
cd /Users/richlabarca/LocalCode/purlin-wt/mutation
.venv/bin/python -m pytest dev/test_mutation_adapters.py -q      # your own files, whole
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

- Commit on `lane/mutation` only, with the prefixes of `references/commit_conventions.md`, ending
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
