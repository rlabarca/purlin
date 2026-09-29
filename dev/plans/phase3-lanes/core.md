# Lane `core`

You are lane `core` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/core`, branch `lane/core`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/core -b lane/core main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-core`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q1, Q2, Q7, Q9, Q20, Q22, Q37, Q65, Q72 and report questions 1, 2, 7, 9, 20, 22,
   37, 65, 71, 72; the report's "Gaps left" for `group_states`.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/purlin/states.py`, `payload.py`, `status.py`, `summary.py`, `board.py`, `gate.py`,
  `console.py`
- `specs/mcp/states.md`, `specs/mcp/summary.md`
- `dev/test_states.py`, `dev/test_summary.py`, `dev/test_backing_tests.py`, `dev/test_failing.py`
- `skills/status/SKILL.md` (100 of 100 lines), `specs/skills/skill_status.md`,
  `dev/test_skill_status.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q2.** States RULE-5 folds into RULE-4: RULE-4 takes RULE-5's clauses (committed or not, the
   passed cell reads `passed` with the source named, `counts` true and no reason, at every gate;
   test reports under `.purlin/runtime/reports/` are not read). RULE-5's line goes and its number
   is never reused. PROOF-6, PROOF-7 and PROOF-152 are re-pointed to `(RULE-4)`, ids unchanged.
2. **Q1** (decision 71): each proof whose test loops over the gates becomes one proof per gate,
   each with its own test: PROOF-5 (gate and folder: six proofs), 6, 73, 106, 107, 66, 83, 174,
   76, 109, 110. PROOF-47 goes with item 11 instead.
3. **Q7, the cell** (contracts C4.1, second bullet): the passed cell reads `partial` only where
   two systems that each have a current section disagree. A system a proof is tagged for with
   no current section leaves the cell `not run`, `missing_env` naming it, reason
   `<os>: no run yet`, so `summary.rule_kind` gives `to_test_remote`. RULE-44 says "where two
   systems that each have a current section disagree". New states proof: "A Mac run passes
   PROOF-1's test; PROOF-2 is tagged `@env(windows)` and its test is skipped here; the passed
   cell reads `not run` with the reason `windows: no run yet`." New summary proof under RULE-8:
   such a rule ends the status on `  1 rule to test on Windows: purlin:test --remote`.
4. **Q20, the cell** (C4.1, third bullet): after the failure check and before the pass check,
   where a proof that is not `@manual` has no marker tied to a test and no test listed in any
   current section, the cell reads `no test` with the reason
   `no test for <PROOF-N>[, <PROOF-M>]` (**PENDING OQ4**). RULE-8 says "a rule some of whose
   proofs no test backs reads `no test`". PROOF-151 (RULE-3) keeps its case: mark PROOF-3 in its
   fixture so the rule still reads `not run`. New proof for the mixed case (PROOF-1 passing,
   PROOF-2 tied to no test: `no test`, reason `no test for PROOF-2`) and a summary proof that it
   counts `  1 rule to write a test for: purlin:build`.
5. **Decision 95, a section answers for the proofs it lists** (C4.1, first bullet): a proof
   absent from a section's `proofs` is neither passed, failed nor `not run` there
   (`_word_from_statuses`, `_failing_where`, `_section_passes`, `proof_result`). New proof: "A
   Windows `ci` section lists only PROOF-2, tagged `@env(windows)`, and passes it; the Mac's
   local section passes PROOF-1; the passed cell reads `passed`."
6. **Q22** (C2 row 2; **PENDING OQ3**, its place and what it counts): `to_correct` joins `summary.KINDS` second, `('to_correct', 'test comment
   to correct', 'test comments to correct', 'purlin:build')`, carried by the project like
   `to_tag`. The payload counts `markers.marker_problems(scan, features)` (moved there by P1)
   with `scan = markers.scan(project_root, suites)` and the suites of
   `markers.read_suites(project_root, config)`, counting both the lines for a comment naming
   something no spec has and those for a comment naming a rule that has proofs (with OQ3's
   second option only the first); `left` gets the item through `summary._words` as every kind
   does, so its `text` is `"1 test comment to correct"` for one and
   `"<n> test comments to correct"` otherwise:
   `{"kind": "to_correct", "count": 1, "text": "1 test comment to correct", "command": "purlin:build"}`;
   `to_tag` needs kinds 1 to 12 at zero. Summary RULE-4 (the kinds)
   and RULE-5 (their order) name it; new summary proofs: one comment naming nothing ends on
   `  1 test comment to correct: purlin:build`; at the gate `signed` with only that left,
   `the version to tag` is not listed. States RULE-27 (the `left` kinds) names it. The status
   skill's closing table gets a row for `test comments to correct` directing
   `→ Run: purlin:build`, cutting a line elsewhere (100 lines). `kind_row_problems()` in
   `dev/test_skill_status.py` learns the phrase `test comments`.
7. **Q37, the strong cell** (C4.2): with `mutation_engine` not `none`, where the feature's
   `audit.mutation.score` is null and `audit.mutation.missing` is not empty, the strong cell
   reads `weak`, reason `strength not measured: <missing>` after any findings. States RULE-13 is
   reworded to the case with no engine or an engine that cannot run here; a new rule says the
   missing-or-timed-out case reads weak with the reason. `to_measure` (C2 row 9,
   **PENDING OQ9**) joins `KINDS` just before `to_strengthen`,
   `('to_measure', 'rule to measure', 'rules to measure', 'purlin:audit')`, for a rule weak only
   for that reason; summary proof `  1 rule to measure: purlin:audit`; the status skill gets its
   row. Build the tests by writing the evidence JSON by hand with
   `"audit": {"mutation": {"engine": "mutmut", "score": null, "missing": "mutmut is not installed: run \"pip install mutmut\"", "at": ..., "commit": ...}}`
   and `mutation_engine: auto` in the settings: no other lane's code is needed.
7b. **Decision 94, nothing measured when the spec names no code files** (C4.2, C2 `no_scope`;
   **PENDING OQ10**): with OQ10's option 1, where `mutation_engine` is not `none` and the gate is
   `strong` or `signed`, a rule whose feature spec names no code files (the payload's
   `incomplete` for its owner, from `fingerprint.incomplete_reason`; an anchor is never such a
   spec) reads `weak` with the reason
   `strength not measured: the spec names no code files: run purlin:spec <feature>`, and
   `summary.rule_kind` counts it under `no_scope` (at `strong` as well as `signed`) rather than
   `to_measure` or `to_strengthen`. With option 2 the reason is the same and it counts under
   `to_measure`; with options 3 and 4 nothing here is built. States gains one rule with one proof
   per gate; summary gains one proof that at `strong` the line reads
   `  1 rule to tie to its files: purlin:spec`. The status skill's row for
   `rules to tie to their files` stays; if it says "at the gate signed", it says "at strong
   and signed when the code is broken on purpose" instead.
8. **Q65, the status** (C1.9, C3.4; **PENDING OQ1**): `status.sync_status` returns
   `config_engine.config_problem(project_root)`'s sentence alone when it answers. New rule and
   proof: the settings file holds `{"gate": "strong",` and the status prints exactly
   `.purlin/config.json cannot be read: Expecting property name enclosed in double quotes at line 1. Fix the file by hand; nothing ran and nothing was saved.`
   (take the JSON reader's own message from the code P2 landed).
9. **Q72.** Skill_status PROOF-21 (the printed lines and the dashboard data carry one answer)
   moves into `specs/mcp/states.md` as a new proof of RULE-27 with the same text; its test moves
   from `dev/test_skill_status.py` (around line 158, with `dashboard_data()`) into
   `dev/test_states.py`. `specs/skills/skill_status.md`: `> Scope:` becomes
   `skills/status/SKILL.md` alone, the Description says the spec covers the skill's
   instructions, RULE-2 drops "those lines and the data the dashboard reads come from one
   computation". PROOF-24, the table check, stays.
10. **Summary RULE-10, the three-name join** (gaps left): `summary.systems_text` keeps only the
    ` and ` join of at most two names; the `, ` path and its docstring mention go.
11. **Q9:** states RULE-40 and PROOF-47 go, with PROOF-47's test (around line 2071). The one rule
    is lane `instructions`'s (C10).
12. **Decision 94, instruction rules:** skill_status's rules say what the skill tells the agent
    (RULE-5: "tells the agent what to print for `purlin:status <name>` and what to do when
    several specs or none match").
13. **Q40's reason, applied** (C11, **PENDING OQ13**): skill_status's damaged-copy proofs (about
    22) leave the spec; each damaged copy stays as a second assertion in the test of the proof
    it guards. With OQ13's second or third option they stay as they are.
14. **Split by claim** (C11) across states, summary and skill_status. Candidates the survey
    named: states RULE-25, 27, 28, 36, 74; summary RULE-4, 8; each skill_status RULE-1.

**You produce** for other lanes: the kind names `to_correct` and `to_measure`, the `left` item
shape above, and the cells of C4.1 and C4.2. **You consume** `markers.marker_problems` (P1),
`config_engine.config_problem` (P2) and the evidence keys of C4 (written by lane `run`; build
your tests by writing evidence by hand).


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
cd /Users/richlabarca/LocalCode/purlin-wt/core
.venv/bin/python -m pytest dev/test_states.py dev/test_summary.py dev/test_backing_tests.py dev/test_failing.py dev/test_skill_status.py -q      # your own files, whole
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

- Commit on `lane/core` only, with the prefixes of `references/commit_conventions.md`, ending
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
