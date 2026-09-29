# Lane `skills-author`

You are lane `skills-author` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/skills-author`, branch `lane/skills-author`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/skills-author -b lane/skills-author main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-skills-author`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q7, Q20, Q37, Q40, Q61, Q62, Q64 and report questions 59, 61, 62, 63, 64, 73, 77;
   the four skills whole; `references/commit_conventions.md` and
   `references/spec_quality_guide.md` whole.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `skills/spec/SKILL.md` (165 of 210), `skills/spec-from-code/SKILL.md` (108 of 130),
  `skills/build/SKILL.md` (130 of 130), `skills/anchor/SKILL.md` (98 of 160)
- `specs/skills/skill_spec.md`, `skill_spec_from_code.md`, `skill_build.md`, `skill_anchor.md`
- `dev/test_skill_spec.py`, `dev/test_skill_spec_from_code.py`, `dev/test_skill_build.py`,
  `dev/test_skill_anchor.py`
- `references/commit_conventions.md`, `references/spec_quality_guide.md`, `references/rule_examples.md`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q61:** a build commit's changeset opens with its heading line `Changeset:`, as `Decisions:`
   and `Review:` do. `references/commit_conventions.md` "The build commit body" example gains
   the `Changeset:` line before the mapped lines (the `RULE-N → file:line` lines stay
   unindented); `skills/build/SKILL.md` (around lines 109 to 115) says the three sections open
   with `Changeset:`, `Decisions:` and `Review:`, adding no line (130 of 130). skill_build RULE-5,
   PROOF-5 and PROOF-37 are reworded; `example_problems()` requires a `Changeset:` line before the
   mapped lines, and `commit_problems()` the heading word.
2. **Q62** (decision 76, L7): `skills/build/SKILL.md` line 125's `→ Run: git push` becomes
   `` `Nothing left to do.` `` for a finished project at `passed` and at `strong`. skill_build RULE-3
   says each outcome has its own `→` directive except `Nothing left to do.`; PROOF-3 follows.
3. **Q64:** skill_spec_from_code gains RULE-10 (RULE-5 is vacant and not reused): "The skill tells
   the agent to write no rule for a private helper, since rules describe behaviour someone
   outside the module can see." Its proof, from the next free id (PROOF-145 if nothing took it):
   the skill carries, across line breaks, `Do not write a rule for a private helper.` and
   `Rules describe behaviour someone outside the module can see` (around lines 92 to 93).
4. **`references/spec_quality_guide.md`** (CLAUDE.md "Format reference versioning" step 3):
   - "When a rule is stuck", Q7: the `partial` row says the rule's tests passed on one system and
     failed on another; the row for `not run, with <os>: no run yet` covers a system that has
     not run;
   - "When a rule is stuck", Q20: the `no test` row says one of the rule's proofs has no test
     carrying its marker comment (**PENDING OQ4** for the reason's words, `no test for <PROOF-N>`);
   - "When a rule is stuck", Q37 (**PENDING OQ9**): a new `strong` row, `weak`,
     `strength not measured: <reason>`: do what the reason names, then `purlin:audit`. The row
     says how to read the cell and what to do, and points at the S2 paragraph of
     `references/hard_gates.md` (C12) instead of restating when the cell reads so;
   - "The operating system" (lines 218 to 223), decision 95: the paragraph says to tag a proof
     `@env(<system>)` where what it checks could differ on that system because of files or the
     operating system (decision 95's opening sentence), not only where it "can only be observed
     on one operating system"; and that a rule that holds everywhere but could differ on Windows
     keeps its untagged proof and gains a second proof tagged `@env(windows)`, tied to the same
     test by a second marker comment. Which run proves a proof with no `@env`, and what a remote
     runner runs, it does not say: it points at the S1 paragraph of `references/hard_gates.md`,
     "Where a runner runs", in one clause (C12), and any sentence of the paragraph that says
     either today goes. The three examples and "at most one per proof" stay.
   - Q13's "a rule says what a caller sees" and Q40's "a proof is not about the test" are
     already said by "One claim, observable" (lines 13 to 22) and "Written before the test, and
     not about the test" (lines 149 to 157): add nothing for them.
4b. **The build skill's "Running them"** (lines 96 to 102; decision 94, Q7): line 98's "where no
   test command is set it suggests one and writes it once the person confirms" says it
   suggests one for each test tool it recognises and writes them once the person confirms
   (**PENDING OQ5**; with OQ5's third option it stays); lines 101 to 102, "the run says it
   `needs <os>`", say the run counts such proofs in one line per system that names
   `purlin:test --remote` (**PENDING OQ20**; with OQ20's second option they stay; with its
   third, the list of work left counts them as `rules to test on <System>`). No line is added
   (130 of 130); skill_build's proofs that quote these words follow.
5. **The interpreter lookup** (C9): `skills/build/SKILL.md` line 84 and `skills/anchor/SKILL.md`
   lines 42 and 65 read
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<path>" <args>`;
   skill_build PROOF-9 and its test (around line 467) follow.
6. **Decision 94, instruction rules:** skill_spec RULE-2, 3, 5, 6, 7; skill_spec_from_code RULE-2,
   3, 6 to 9; skill_anchor RULE-2 and 5, and every other rule of the four specs, say what the
   skill tells the agent.
7. **Q40's reason, applied** (C11, **PENDING OQ13**): the damaged-copy proofs of skill_anchor
   (about 21), skill_build (about 20), skill_spec_from_code (about 23) and skill_spec (about 26)
   leave the specs, each kept as a second assertion in its guarded test. With OQ13's second or
   third option they stay as they are.
8. **Split by claim** (C11): candidates skill_spec RULE-5 and 6, skill_anchor RULE-5, skill_build
   RULE-5, and each RULE-1.
9. Q77: the checks stand; nothing to do.


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
cd /Users/richlabarca/LocalCode/purlin-wt/skills-author
.venv/bin/python -m pytest dev/test_skill_spec.py dev/test_skill_spec_from_code.py dev/test_skill_build.py dev/test_skill_anchor.py -q      # your own files, whole
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

- Commit on `lane/skills-author` only, with the prefixes of `references/commit_conventions.md`, ending
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
