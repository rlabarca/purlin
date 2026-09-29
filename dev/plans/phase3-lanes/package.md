# Lane `package`

You are lane `package` of phase 3 of Purlin 0.10.0 (decisions 94 to 97). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/package`, branch `lane/package`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/package -b lane/package main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-package`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 988 (decisions 94 to 97; decision 97 holds the
   owner's answers); a later decision amends an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Report questions 34 and 35; "Gaps left" for `package`; `references/formats/package_format.md` whole.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/export/package.py`
- `specs/export/package.md`, `dev/test_export.py`
- `references/formats/package_format.md`

## The work

Each item names its source and the change. The owner's answers are written in (decision 97);
build every item.

1. **Decision 94, split by claim, package RULE-6** (Q35): read each proof, then split into:
   RULE-6 (its words, the one kind of work, its proofs, its tests: PROOF-9, 18); a new rule for
   each result with its system, source, time, commit, runner and machine (PROOF-25); a new rule
   for what the audit found with the model and the fingerprint of its instructions (PROOF-26);
   a new rule for each current signature with its fields and the hashes it locked (PROOF-27, 28);
   a new rule for one status per step up to the gate (PROOF-20, 29); a new rule for "nothing
   names who last changed a test" (PROOF-11; Q34 keeps it). New ids from the next free. Proofs
   move unchanged; if a proof shows two of these claims, it stays under RULE-6 and you report it.
2. **Package format 4** (C5): `references/formats/package_format.md` goes to
   `> Format-Version: 4` and its table of `left` kinds gains two rows, in C2's places (the
   `to_correct` row right after `no_proof`, the `to_measure` row right before `to_strengthen`),
   word for word in the table's own form:

   ```
   | `to_correct` | `1 test comment to correct`, `<n> test comments to correct` | `purlin:build` |
   | `to_measure` | `1 rule to measure`, `<n> rules to measure` | `purlin:audit` |
   ```

   The two rows are OQ3's and OQ9's. The sentence above the table, "Each rule is counted under
   one kind, the first that applies, and a kind at zero has no line:", reads, word for word
   (`phase3-plan.md` section 12, item 4):

   ```
   Each rule is counted under one kind, the first that applies, and a kind at zero has no line. `to_correct` counts test comments, not rules, and is carried by the project:
   ``` `package.py` copies `left` as today;
   no code change for them. RULE-4 does not list kinds and stays.
3. **Split by claim and one case per proof** (C11) for the other rules: candidate RULE-1.
4. The package's `warnings` carry the spec mistakes as they carry every payload warning; nothing
   to build.
5. **Q65, `purlin:export`** (C1.9, C3.4; OQ1): `package.py` `main`, after the
   command line is read and before anything else is read or written (`--check` included),
   prints `config_engine.config_problem(project_root)`'s sentence when it answers, writes
   nothing and exits 1. One new rule, or one proof under an existing rule that already says what
   the export does when it cannot start, with a test whose `.purlin/config.json` holds a
   trailing comma. The module docstring's exit paragraph names it, as C6's
   `scripts/export/package.py` row does.


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
cd /Users/richlabarca/LocalCode/purlin-wt/package
.venv/bin/python -m pytest dev/test_export.py -q      # your own files, whole
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

- Commit on `lane/package` only, with the prefixes of `references/commit_conventions.md`, ending
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
