# Lane `skills-sign`

You are lane `skills-sign` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/skills-sign`, branch `lane/skills-sign`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/skills-sign -b lane/skills-sign main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-skills-sign`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q11, Q12, Q40, Q52 and report questions 11, 12, 40, 52; `skills/sign/SKILL.md` and
   `skills/export/SKILL.md` whole.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `skills/sign/SKILL.md` (174 of 185), `skills/export/SKILL.md` (83 of 90)
- `specs/skills/skill_sign.md`, `specs/skills/skill_export.md`
- `dev/test_skill_sign.py`, `dev/test_skill_export.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q40:** skill_sign's damaged-copy proofs leave the spec: PROOF-9, 10, 11, 12, 13, 15, 16, 17,
   18, 20, 22, 24, 25, 26, 27, 28, 29, 32, 33, 34, 35, 36, 37 and 39, with their marker lines. Each
   damaged copy stays as a second assertion inside the test of the proof it guards:

   | Kept proof | Damaged copies it now also checks |
   |---|---|
   | PROOF-1 | 24 to 28 |
   | PROOF-23 | 29 |
   | PROOF-2 | 10 |
   | PROOF-31 | 9, 11 |
   | PROOF-3 | 32 to 35 |
   | PROOF-4 | 36, 37 |
   | PROOF-5 | 12, 39 |
   | PROOF-38 | 13 |
   | PROOF-7 | 15, 16 |
   | PROOF-40 | 17 |
   | PROOF-41 | 18 |
   | PROOF-43 | 20 |
   | PROOF-21 | 22 |

   Read each pair before moving it; where a copy guards another proof than the table says, follow
   the proof and report it.
2. **Q52** (L6): the export skill's closing row for a package that fails its fingerprint (around
   line 83) directs
   `→ Run: git show signed/<version>:.purlin/evidence/package/<version>.json`. skill_export
   PROOF-29 and PROOF-12's wording follow; tests around lines 234 and 359.
3. **Q12** (C3.6, **PENDING OQ15**): the sign skill's closing table gets a row for
   `` `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` ``
   (C3.6, word for word) directing `→ Run: purlin:status <feature>`. With OQ15's third option
   the row quotes `` `<feature> <RULE-N> is not a rule any spec has.` ``.
4. **Q11** (C6): one clause in the sign skill's Step 6: the command exits 1 when the tag was
   refused for a reason to fix (uncommitted work or results, no version, a package not
   committed, git failing to write the tag), and 0 when the tag already exists.
5. **The interpreter lookup** (C9): sign skill lines 73, 85 and 100 and export skill lines 32 and
   69 read `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<path>" <args>`.
   skill_export PROOF-21 ("begins with `python3 …`") says it begins with
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"`; its test around line 290.
6. **Decision 94, instruction rules:** skill_sign RULE-2 ("tells the agent to read what waits from
   `sync_status`") and every other rule of both specs say what the skill tells the agent.
7. **Q40's reason, applied to skill_export** (about 20 damaged-copy proofs), as item 1
   (**PENDING OQ13**; with OQ13's second or third option they stay as they are). Item 1, for
   skill_sign, is the approved reading itself; with OQ13's third option it is left as it stands
   too.
8. **Split by claim** (C11): candidates skill_sign RULE-5 and RULE-8, and each RULE-1.


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
cd /Users/richlabarca/LocalCode/purlin-wt/skills-sign
.venv/bin/python -m pytest dev/test_skill_sign.py dev/test_skill_export.py -q      # your own files, whole
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

- Commit on `lane/skills-sign` only, with the prefixes of `references/commit_conventions.md`, ending
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
