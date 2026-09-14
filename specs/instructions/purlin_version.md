# Feature: purlin_version

> Description: The version string lives in one file, `VERSION` at the project
>   root. Everything else either reads it at run time or is written from it by
>   `dev/bump_version.sh`, and `bash dev/bump_version.sh --check` is the check
>   that fails when a derived location disagrees. Nobody edits a version
>   literal by hand, and a document that describes the version field names the
>   file rather than restating a number, so no table can go stale. The one
>   count a release also states, the test totals in the notes, is held against
>   the sweep's own record of what ran.
> Scope: VERSION, templates/config.json, .claude-plugin/plugin.json, .purlin/config.json, scripts/mcp/purlin/__init__.py, scripts/mcp/purlin/server.py, dev/bump_version.sh, references/drift_criteria.md, skills/init/SKILL.md, RELEASE_NOTES.md
> Stack: python/stdlib for the reader, bash for the propagation script, json for the derived locations

## Rules

- RULE-1: A `VERSION` file at the project root holds one semver string and nothing else [risk: medium] [origin: eng]
- RULE-2: The `purlin` package reads the version out of the `VERSION` file at import time and assigns it to `PURLIN_VERSION`, and the server reports that value rather than a literal of its own [risk: medium] [origin: eng]
- RULE-3: The `version` field of `templates/config.json`, which `purlin:init` stamps into a new project, equals the `VERSION` file [risk: medium] [origin: eng]
- RULE-4: No module of the `purlin` package carries a release version literal outside its comments [risk: medium] [origin: eng]
- RULE-5: The `version` field of `.claude-plugin/plugin.json`, which is what the plugin loader reports and what a consumer installs against, equals the `VERSION` file [risk: high] [origin: eng]
- RULE-6: Where `.purlin/config.json` exists, because the repository is itself a Purlin project, its `version` field equals the `VERSION` file: the project's own stamp never lags the framework it ships [risk: low] [origin: eng]
- RULE-7: `dev/bump_version.sh <semver>` is the one propagation entry point: it writes the `VERSION` file and sets the version field in every derived location, it refuses an argument that is not semver before writing anything, and `dev/bump_version.sh --check` exits non-zero naming each location that disagrees while still reporting the ones that match [risk: high] [origin: eng]
- RULE-8: The one table that describes the config `version` field, in `references/drift_criteria.md`, states the `VERSION` file as its source rather than restating a release number, and no second copy of that row lives anywhere under `skills/` or `references/` [risk: low] [origin: eng]
- RULE-9: The `## Unreleased` section of `RELEASE_NOTES.md` states the counts of the run it describes once, as `N passed, M skipped`, and those two numbers equal `passed` and `skipped` in `.purlin/runtime/last_sweep.json`, the sweep's own whole record of itself rather than the shared marker each proof plugin rewrites as it finishes. That record is runtime state, so a checkout that has never run the sweep has nothing to compare and the proof reports that instead of failing [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read the `VERSION` file; verify it exists, is not empty, and that its stripped content matches `^\d+\.\d+\.\d+$` @unit
- PROOF-2 (RULE-2): Import the `purlin` package and read `scripts/mcp/purlin/__init__.py` as text; verify the package defines a callable version reader, that the source assigns `PURLIN_VERSION = _read_version()` rather than a literal, that `scripts/mcp/purlin/server.py` gives `SERVER_INFO` its `"version"` from `PURLIN_VERSION`, and that the imported `PURLIN_VERSION` equals the stripped content of the `VERSION` file @unit
- PROOF-3 (RULE-3): Read the `VERSION` file and parse `templates/config.json`; verify the file carries a `version` key and that its value is exactly the `VERSION` string @unit
- PROOF-4 (RULE-4): Read every `.py` file of `scripts/mcp/purlin/`, drop the full-line comments, and grep the rest for a quoted `X.Y.Z` literal; verify the only match allowed is the sentinel `0.0.0` the reader returns when the `VERSION` file cannot be read, so a release number such as `0.10.0` written into any module fails naming it @unit
- PROOF-5 (RULE-5): Read the `VERSION` file and parse `.claude-plugin/plugin.json`; verify the manifest carries a `version` key and that its value is exactly the `VERSION` string @unit
- PROOF-6 (RULE-6): Read the `VERSION` file and parse this repository's own `.purlin/config.json`; verify it carries a `version` key equal to the `VERSION` string, so a stamp left at `0.9.2` while the file reads `0.10.0` fails naming both @unit
- PROOF-7 (RULE-7): Build a temporary project holding a `VERSION` file and all three derived JSON files at `1.2.3`, plus a copy of the script; run it with `9.8.7` and verify the `VERSION` file and each JSON file read `9.8.7`; run `--check` and verify exit 0; hand-edit `.purlin/config.json` back to `1.2.3` and verify `--check` exits 1, printing `DRIFT` and naming `.purlin/config.json` while still listing `templates/config.json` and `.claude-plugin/plugin.json`. Then run the script with `not-a-version` and verify exit 2 with the `VERSION` file still reading `1.2.3`; delete `.purlin/config.json`, verify a bump exits 0 and still writes `templates/config.json`, and that `--check` exits 0 reporting that location as `absent` @integration
- PROOF-8 (RULE-8): Read `references/drift_criteria.md`, take every table row whose first cell is `version`, and verify at least one exists, that none carries a quoted semver literal, and that each names the `VERSION` file. Then read every `.md` file under `skills/` and `references/` other than that one and verify none carries such a row, so restoring a `version` row at `0.9.0` to `skills/init/SKILL.md` fails naming that file @unit
- PROOF-9 (RULE-9): Four legs. Leg (a): cut the marker-writing function out of `dev/run_tests.sh`, run that text in a shell whose working directory is a temporary repository, with the counts `PASS=2`, `FAIL=0`, `PYTEST_PASSED=11`, `PYTEST_FAILED=0`, `PYTEST_SKIPPED=3` and the two suite names `Proof Plugins (Shell)` and `All Pytest Tests`; verify it exits 0 and writes `last_sweep.json` beside `test_run.json`, that the record reads `passed` 12, `failed` 0, `skipped` 3, `ok` true, those two suite names, the temporary repository's own head sha, a timestamp, and no `runs` key, while the shared marker written by the same call names the sweep and does carry `runs`. Leg (b): read the text between `## Unreleased` and the next heading in `RELEASE_NOTES.md` and verify it holds exactly one line matching `N passed, M skipped`. Leg (c): given a record whose `passed` is one higher than the notes, verify the comparison raises naming both numbers, and given a path with no file, verify it returns a reason naming that path and `bash dev/run_tests.sh` and asserts nothing. Leg (d): run the same comparison against the real `.purlin/runtime/last_sweep.json`, skipping with that reason when it is absent @integration
