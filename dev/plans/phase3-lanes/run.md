# Lane `run`

You are lane `run` of phase 3 of Purlin 0.10.0 (decisions 94 to 97). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/run`, branch `lane/run`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/run -b lane/run main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-run`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 988 (decisions 94 to 97; decision 97 holds the
   owner's answers); a later decision amends an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q7, Q9, Q10, Q19, Q20, Q21, Q37 and report questions 7, 9, 10, 19, 20, 21, 37;
   the fault list items for `run_script` and `evidence_writer` (report lines 48 and 49); "Gaps
   left" for `run_script`, `evidence_writer` and `update`.
6. `references/formats/evidence_format.md` and `references/formats/marker_format.md` whole.

This is the largest lane. Build in the order of the items; each item is committed on its own.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/mcp/purlin/frameworks.py`
- `specs/run/run_script.md`, `specs/run/evidence_writer.md`
- `dev/test_run_script.py`, `dev/test_evidence_writer.py`
- `references/formats/evidence_format.md`, `references/supported_frameworks.md`

## The work

Each item names its source and the change. The owner's answers are written in (decision 97);
build every item.

1. **Decision 95, a remote run runs only the tests tied to proofs tagged for its system.**
   - `--ci`, with or without `--all` or a feature named, selects in each feature the proofs whose
     `@env` names this runner's system (around lines 788 to 803); a feature with none is not run.
   - `{files}` holds the test files carrying those proofs' markers; a suite with no such file is
     not started.
   - Only those markers count for missing evidence and for the exit code (around lines 836 to
     857). OQ21: a file holding tagged and untagged tests is started whole; results of tests tied to no selected proof are neither written nor counted; a suite
     whose command takes no `{files}` runs whole under the same rule.
   - The `ci` section lists only the selected proofs and the rules they prove (C4.3); `_ci`'s
     `merge_for_host` gets only those rules.
   - A runner prints no `needs <System>` line.
   - A tag run (`signed/*`) selects the same way.
   - Specs: run_script RULE-59 (`--ci` with no feature named runs every feature that has a proof
     tagged for this runner's system), RULE-12, RULE-47 and RULE-8 are reworded; evidence_writer
     RULE-2 and RULE-3 gain the `ci` clause.
   - Every `--ci` proof's fixture tags its proof `@env(<this machine's system>)` (from
     `host_os()`): PROOF-12, 15, 59, 68, 102, 116 to 121, 171, 174, 175 and 194.
   - New proofs: a `--ci` run over a feature whose PROOF-1 is untagged and PROOF-2 tagged for
     this system writes a `ci` section listing PROOF-2 alone; a feature with no tagged proof
     gets no `ci` file; an untagged test that fails in the same file as a tagged test that
     passes leaves the job's exit 0 (OQ21).
2. **Decision 95, the foreign result** (C4.4): `evidence.build_section` writes `not run` for a
   proof tagged for another system whatever its tied test did here; evidence_writer RULE-3 says
   so; new proof: one test carries a Mac proof's marker and a Windows proof's marker and passes
   on the Mac; the local section reads the Mac proof `pass` and the Windows proof `not run`.
3. **Q7** and fault `run_script` (C4.5): `rule_word` gives `no test` for a rule with a proof,
   tagged for another system or not, that no test is tied to; such a proof gets no `needs`
   line. OQ20: the per-proof `FOREIGN_PROOF` line becomes one line per system (R3):
   `1 proof needs <System>; this machine is <System>. Run purlin:test --remote.` /
   `<n> proofs need <System>; this machine is <System>. Run purlin:test --remote.`; RULE-10 and
   its proofs follow. PROOF-10's fixture today gives the foreign `PROOF-2` no marked test, which
   after this item makes the rule `no test` with no needs line: give `PROOF-2` a marked test that
   is skipped here (as PROOF-114's fixture does), so PROOF-10 still shows the needs line. The local section's word for "all that could run here passed, a foreign
   proof waits" stays `not run` (RULE-2 already says so). New run_script proof: a foreign proof
   with no test prints `<feature> <RULE-N> has no test. Run purlin:build <feature>.` (or R1 if
   the rule has another proof with a test). The ending lines (`Left to do`) are lane `core`'s
   proofs; do not assert them here.
4. **Q20** and fault `evidence_writer` (C4.5, C3.7 R1; OQ4): `rule_word` gives
   `no test` where any proof that is not `@manual` has no test tied to it, after `failed`;
   `rule_problems` prints `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`
   for a rule some of whose proofs have a test, and R2 unchanged for one where none has. New
   evidence_writer proof under RULE-2 ("PROOF-1's test passes and PROOF-2 is tied to no test:
   the rule reads `no test`") and new run_script proof under RULE-67 for the printed line.
5. **Q21** (C4.1): `build_sections` passes `hostname` only for `--ci`; `build_section` leaves the
   key out when it is None. Evidence_writer RULE-1 and PROOF-1 lose `hostname` from the local
   key list; RULE-16 and PROOF-41, RULE-17 and PROOF-44 keep the hostname case for `ci` alone;
   tests around lines 121 to 123, 200 and 263 to 266. A local section on disk keeps its old
   `hostname` until a write changes the section (plan call 6). `local_machine()` and its
   `or 'unknown'` stay as they are: evidence_writer RULE-16 promises `unknown` where the host
   reports none (plan call 64).
6. **Q37, the run's side** (C1.2, C3.2, C4.2): `_audit` writes `missing` into
   `audit.mutation` when `features[f].get('missing')` is not empty
   (`{"engine", "score", "at", "commit", "missing"}`); `_run_breaks` prints `purlin: <reason>`
   for any non-empty `reason`, installed or not, and `purlin: <missing>` once per distinct
   sentence not already printed; `evidence.merge_audit` treats two entries differing in
   `missing` alone as different. New run_script proof under RULE-45 with the engine stood in by
   monkeypatching `mutation.run_breaks` to answer a feature `missing`
   `mutmut is not installed: run "pip install mutmut"`: the evidence carries that `missing` and
   the run prints `purlin: mutmut is not installed: run "pip install mutmut"`. Do not assert the
   strong cell: that is lane `core`'s.
7. **Q10:** the run's early print of `cfg.warnings` (around lines 767 to 770) goes; the status
   prints them beside the table. RULE-51 says "beside the status table"; PROOF-177 and 179 to
   182 ("opens with") change.
8. **Q19:** `set_up_by_095(project_root)` moves into `purlin_run.py` with the same checks
   (`.purlin/config.json` lacks `tests`; carries `test_framework`, `spec_dir`, `pre_push`,
   `report` or `digest`; a `*.proofs-*.json` or `*.receipt.json` exists under `specs/`) and the
   run stops calling `update.set_up_by_095` (lane `update` deletes it). RULE-66 reads: "A
   project set up by Purlin 0.9.5 and not upgraded stops the run: it prints `This project was
   set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.`,
   writes nothing and exits 1". One proof per sign, eight in all (PROOF-138 is one; the five
   keys are five), each a real run that stops, built with `dev/run_project.py`'s `_project` and
   `_spec` in `dev/test_run_script.py`.
9. **Decision 94, the first test run suggests a command for every test tool it recognises**
   (C3.7 R4; OQ5, OQ6): `frameworks.suggest(project_root)` returns the
   list of entries of every tool found, in the order pytest, vitest, jest, dotnet, go, sql,
   shell (empty when none); `no_test_command_lines` prints `No test command is set in .purlin/config.json, so nothing ran.`,
   then per tool `Suggested for <name>: <run>` and that tool's needs line where it has one, then
   `Suggested tests setting: <the entries as one JSON array on one line>`. On Windows the pytest
   entry's `run` starts `py -3 -m pytest` in place of `python3 -m pytest`. RULE-61 and RULE-63
   ("the first tool found") are reworded; PROOF-129 (a project with a conftest and vitest gets
   both), 126 and 136 change; tests around lines 2354 to 2512. `references/supported_frameworks.md`
   lines 7 to 14 and "A project that carries several frameworks is suggested the first" say
   every recognised tool is suggested, and give the Windows form. Keep `ENTRIES`, `entry_for`,
   `entries_for` and `detect_frameworks`: other lanes' code and tests use them.
10. **Decision 94, a spec mistake seen in a run** (after P2; OQ2): one run_script
    proof: a test run over a spec whose `> Scope:` names `src/gone.py`, which is not in git,
    prints `login: > Scope: names src/gone.py, which finds no file in git. Run purlin:spec login.`
    and runs its tests, exiting 0 when they pass.
11. **Run_script RULE-12 at `signed`** (gaps left): new proof, `--all --ci` at the gate `signed`
    hands the git host one path and prints `Evidence committed.`, through the existing
    `self._ci(..., gate='signed')` helper, its proof tagged per item 1.
12. **Q65, the run** (C1.9, C3.4; OQ1): `settings_stop` returns
    `config_engine.config_problem(project_root)`'s sentence as its third case; the run prints it,
    writes nothing and exits 1; new proof with a settings file holding a trailing comma.
13. **Q9:** run_script RULE-22 and PROOF-22 go with the test (C10).
14. **Evidence format 5** (C4): `references/formats/evidence_format.md` goes to
    `> Format-Version: 5` in the commit of the first item that changes emission, and says each of
    C4's five points (including line 99's `hostname`, line 110's `no test`, line 139's
    `audit.mutation`). One bump for all.
15. **Split by claim and one case per proof** (C11): candidates run_script RULE-11, 12, 45, 51,
    52, 56; evidence_writer RULE-8, 10, 12.

**You consume** P1's three-argument `run_breaks`, the engine answer of C1.2 (read
`features[f].get('missing') or ''`), P2's `config_problem` and P2's warnings. **You produce**
evidence format 5 (C4), the run's lines of C3.7, and the `--ci` behaviour of C7.


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
cd /Users/richlabarca/LocalCode/purlin-wt/run
.venv/bin/python -m pytest dev/test_run_script.py dev/test_evidence_writer.py -q      # your own files, whole
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

- Commit on `lane/run` only, with the prefixes of `references/commit_conventions.md`, ending
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
