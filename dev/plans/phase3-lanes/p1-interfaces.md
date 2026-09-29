# Lane `p1-interfaces`

You are lane `p1-interfaces` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p1-interfaces`, branch `lane/p1-interfaces`, created from
  `main` (P2 starts after P1 merged): `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/p1-interfaces -b lane/p1-interfaces main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-p1-interfaces`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q18, Q50, Q75 and report questions 18, 50, 75; decision 96.

You run alone, before the fan-out, while the owner answers the questions of plan section 8.
Nothing you do depends on those answers. Every item keeps behaviour as it is unless it names a
change, and every commit leaves `--fast` green.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

You run alone, so you may write any file an item below names, and no other:
- `scripts/run/mutation/__init__.py`, `scripts/run/purlin_run.py`, `scripts/run/reports.py`,
  `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/specs.py`, `scripts/mcp/purlin/payload.py`,
  `scripts/run/workflow.py`, `scripts/init/scaffold.py`
- `templates/config.json`, `dev/bump_version.sh`, `.github/workflows/version-check.yml`, `CLAUDE.md`
- `specs/run/run_script.md`, `specs/init/scaffold.md`, `specs/init/update.md`,
  `specs/instructions/purlin_version.md`
- `dev/test_run_script.py`, `dev/test_init_scaffold.py`, `dev/test_init_update.py`,
  `dev/test_host.py`, `dev/test_purlin_version.py`, `dev/test_consumer_ci.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **The breaks, called with the scope alone** (decision 94, contracts C1.1):
   `run_breaks(project_root, engine, scope_by_feature, tests_by_rule=None)`; `purlin_run.py` calls
   it with three arguments and deletes `tests_by_rule()`; run_script RULE-16 reads
   `The breaks are asked for each feature's scope files`; PROOF-16 is reworded to that one case;
   PROOF-160 and its test go; the stub near `dev/test_run_script.py:615` takes three arguments,
   and its answer drops its `rules` entry and with it `'attribution': 'per_scope'` (line 623),
   so it holds what C1.2 says the engine's answer holds (the run reads only `scope_score`).
2. **`mutation.runs_here(engine, os_name=None) -> bool`** (C1.3): false only for `mutmut` on
   Windows (`os_name == 'windows'`, or `os.name == 'nt'` when none is given). No caller yet.
3. **One program start** (Q50, C1.4): `execute` starts `subprocess.Popen([*command], ...)`.
4. **`marker_problems` moves** (C1.5): `marker_problems`, `NAMES_NOTHING` and `RULE_HAS_PROOFS`
   move from `scripts/run/reports.py` to `scripts/mcp/purlin/markers.py` unchanged;
   `reports.py` imports the three names, so `reports.marker_problems` still answers.
5. **`specs.spec_mistakes(project_root, features)`** returning `[]` (C1.6), and in
   `payload.build_payload` the loop that appends each line it returns to `warnings`, after the
   unnumbered-rule lines.
6. **Decision 96's second line** (C1.7, L1), `workflow.UNKNOWN_HOST` set to:

   ```
   UNKNOWN_HOST = 'This git host cannot run tests remotely. Everything on this machine works.'
   ```

   and every test and proof quoting the old words (setup still prints it where it does today;
   lane `scaffold` moves it, OQ7): `dev/test_init_scaffold.py` (around lines 809, 976 to 978, 1011 to 1031),
   `dev/test_init_update.py` (around line 1411), `specs/init/scaffold.md` RULE-14, PROOF-44, 69
   and 70, `specs/init/update.md` PROOF-51, and any line of `dev/test_host.py` quoting it (grep
   `neither GitHub nor Azure DevOps`).
7. **`scaffold.NOT_A_GATE = 'purlin: "%s" is not a gate; reading it as %s.'`** (C1.7), used by
   setup's `main` in place of its inline string.
8. **Q75, the template's version goes** (C1.8): `templates/config.json` holds `gate`,
   `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`; `scaffold.write_config`
   writes `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci` in
   that order, `version` from the plugin's `VERSION` file; `dev/bump_version.sh` drops the template
   from `DERIVED`, its header comment and its usage; `.github/workflows/version-check.yml` drops it
   from both `paths` lists; `specs/instructions/purlin_version.md`: the Scope drops the template,
   RULE-3 keeps "a project `purlin:init` sets up is stamped with `VERSION`", PROOF-3, 19 and 20
   and their tests go, PROOF-7 and 28 to 33 say two JSON files; `dev/test_purlin_version.py`
   (`CONFIG_TEMPLATE`, the paths near line 335, `TEMPLATE_REL`); `specs/init/scaffold.md` RULE-5
   and PROOF-54 (reworded to "the template carries exactly six keys, in this order: `gate`,
   `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`", which says what it holds
   and nothing about what it lacks, decision 44 and the writing style) and its test near line
   392, which compares the template's key list with that list;
   host PROOF-84's test in `dev/test_consumer_ci.py` compares the fixture's keys with
   `['version'] + list(template)`; `CLAUDE.md`, "Releasing a new version", names two derived
   locations and says the spec "covers all three locations".


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
cd /Users/richlabarca/LocalCode/purlin-wt/p1-interfaces
.venv/bin/python -m pytest dev/test_run_script.py dev/test_mutation_adapters.py dev/test_reports.py dev/test_states.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_host.py dev/test_purlin_version.py dev/test_consumer_ci.py dev/test_security.py -q      # your own files, whole
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

- Commit on `lane/p1-interfaces` only, with the prefixes of `references/commit_conventions.md`, ending
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
