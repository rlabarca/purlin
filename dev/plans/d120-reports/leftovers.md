# Lane `leftovers`, decision 120

Branch `lane/d120-leftovers`. Tests run: `dev/test_run_script.py`, `dev/test_planted_bug.py`,
`dev/test_states.py`, `dev/test_config_engine.py`, `dev/test_purlin_version.py`: 177 passed and
1 skipped before, 177 passed and 1 skipped after. No test was added or removed. No rule or proof
number changed, and no `> Highest-*` line moved. No format file changed.

Each reworded proof's test was seen to fail once with the code broken on purpose, then the code
was restored.

## 1. `--ignore=mutants` leaves the suggested pytest command

- Code: `scripts/mcp/purlin/frameworks.py`, pytest's entry. `scripts/run/purlin_run.py` does not
  hold the command and is unchanged.
- Proofs reworded, same numbers, `specs/run/run_script.md`:
  - `PROOF-126 (RULE-102)`: In a project whose `tests` setting is empty and that holds a
    `conftest.py`, `--all --test` prints `No test command is set in .purlin/config.json, so
    nothing ran.`, then `Suggested for pytest: python3 -m pytest {files} --junitxml={report}`,
    then `Suggested tests setting: ` and a JSON array holding pytest's entry alone, writes
    nothing under `.purlin/`, and exits 1
  - `PROOF-221 (RULE-63)`: In a project with an empty `tests` setting holding only a
    `conftest.py`, on a machine whose system is Windows, the one entry suggested runs
    `py -3 -m pytest {files} --junitxml={report}`
  - `PROOF-262 (RULE-88)`: A project with an empty `tests` setting holding only
    `tests/test_cart.py` prints `Suggested for pytest: python3 -m pytest {files}
    --junitxml={report}`
- Tests changed: the three marked tests in `dev/test_run_script.py`.
- Line a person reads: `Suggested for pytest: python3 -m pytest {files} --junitxml={report}`.
- Quotes corrected: `README.md:63`, `docs/getting-started.md:99`,
  `docs/running-and-evidence.md:39` and `:40`, `references/supported_frameworks.md:13` and `:61`.
- Not mine, left as it is: `dev/run_project.py:40` gives this repository's test projects
  `suites.pytest_suite(extra='--ignore=mutants')`. Edit for its owner: drop the `extra`
  argument, if no test depends on it.

## 2. `while a bug was planted`

- Code: `scripts/review/targeted_break.py`, `STOPPED`.
- Reworded, same numbers, `specs/review/planted_bug.md`:
  - `RULE-6`: When a file of the project changes while a bug is planted, the audit stops, prints
    `The audit stopped: <path> changed while a bug was planted. Nothing in the project was
    written by the audit.` and exits 1
  - `PROOF-7 (RULE-6)`: The model's answer, as it is given, writes a line to `src/age.py` in the
    project; the audit prints `The audit stopped: src/age.py changed while a bug was planted.
    Nothing in the project was written by the audit.` and exits `1`
- Test changed: `dev/test_planted_bug.py`, the test of PROOF-7.
- Line a person reads: `The audit stopped: <path> changed while a bug was planted. Nothing in
  the project was written by the audit.`
- Quote corrected: `docs/running-and-evidence.md:360`.
- Not mine, needs this edit: `skills/audit/SKILL.md:89`, `changed while a break ran` becomes
  `changed while a bug was planted`.

## 3. `remote_url` leaves the dashboard's data

- Readers checked first: no file under `scripts/report/src/` names `remote_url`, nor does
  `scripts/mcp/purlin/report_data.py` or any other file under `scripts/`, `skills/`, `docs/`,
  `references/` or `agents/`. The key went; the schema number stays 14.
- Code: `scripts/mcp/purlin/payload.py` loses the key, its line in the docstring's sample and
  the function `_remote_url`.
- Reworded, same numbers, `specs/mcp/states.md`:
  - `RULE-27`: The payload carries schema version 14 and the top-level keys `generated_at`,
    `generated_by`, `project`, `version`, `branch`, `commit`, `dirty`, `summary`, `features`,
    `left`, `met`, `signoff`, `last_line`, `os_words`, `evidence`, `information` and `warnings`
  - `PROOF-31 (RULE-27)`: The payload reads `schema_version` 14 and carries exactly the
    seventeen top-level keys the rule names beside it, with `generated_at` ending in `Z`
- Test changed: `dev/test_states.py`, now
  `test_schema_fourteen_carries_exactly_the_seventeen_keys`.
- Fixtures: the key is out of `dev/fixtures/report/solo.json`, `team.json` and `regulated.json`.
- `references/formats/package_format.md` and `evidence_format.md` do not describe the key and
  are unchanged.

## 4. The upgrade names 0.9.5's settings alone

- Code: `scripts/mcp/config_engine.py`, `UPGRADE_KEYS` is `test_framework`, `spec_dir`,
  `pre_push`, `report`, `digest`, `audit_criteria`. `min_strength`, `gate`, `mutation_engine`,
  `audit_parallel`, `ci` and `project_name` are gone. A file that still holds one of them is now
  told `Remove it from .purlin/config.json.` (RULE-20, PROOF-51's case).
- Reworded, same number, `specs/mcp/config_engine.md`:
  - `PROOF-50 (RULE-20)`: A settings file holding `version`, `tests`, `pre_push` and `digest`,
    in that order, is read with exactly the one warning `.purlin/config.json carries pre_push,
    digest, which this version does not read. Run purlin:init --update.`
- Test changed: `dev/test_config_engine.py`, the test of PROOF-50.
- `scripts/init/update.py` names no such list: it removes every key but `version` and `tests`.
  No edit is needed there. `docs/upgrading.md` quotes only 0.9.5 keys and is unchanged.

## 5. The plugin's description

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`: the description reads
  `Rule-proof spec-driven development: specs define rules, proofs say how each rule is shown,
  tests prove it` (the marketplace's ends with a full stop, as before).
- The keyword `sync` is out of `plugin.json`.
- `python3 -m pytest dev/test_purlin_version.py -q` passes. Of `dev/test_install.py`, the one
  test that calls no real `claude` passes; the four that do were not run.

## 6. The tag `v0.10.0` in `docs/running-and-evidence.md`

Stays as it is, about line 510. Nothing added. The tag does not exist until the release.

## Left open

- `skills/audit/SKILL.md:89` (item 2) and `dev/run_project.py:40` (item 1), above.
- This repository's committed evidence for the reworded proofs stops counting until integration
  runs the tests again.
