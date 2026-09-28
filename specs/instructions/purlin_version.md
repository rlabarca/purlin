# Feature: purlin_version

> Description: The version string lives in one file, `VERSION` at the project
>   root. Everything else either reads it at run time or is written from it by
>   `dev/bump_version.sh`, and `bash dev/bump_version.sh --check` is the check
>   that fails when a derived location disagrees. Nobody edits a version
>   literal by hand, and a document that describes the version field names the
>   file rather than restating a number, so no table can go stale.
> Scope: VERSION, templates/config.json, .claude-plugin/plugin.json, .purlin/config.json, scripts/mcp/purlin/__init__.py, scripts/mcp/purlin/server.py, dev/bump_version.sh, references/drift_criteria.md, skills/init/SKILL.md
> Stack: python/stdlib for the reader, bash for the propagation script, json for the derived locations

## Rules

- RULE-1: A `VERSION` file at the project root holds one semver string and nothing else
- RULE-2: The `purlin` package reads the version out of the `VERSION` file at import time and assigns it to `PURLIN_VERSION`, and the server reports that value rather than a literal of its own
- RULE-3: The `version` field of `templates/config.json`, which `purlin:init` stamps into a new project, equals the `VERSION` file
- RULE-4: No module of the `purlin` package carries a release version literal outside its comments
- RULE-5: The `version` field of `.claude-plugin/plugin.json`, which is what the plugin loader reports and what a consumer installs against, equals the `VERSION` file
- RULE-6: Where `.purlin/config.json` exists, because the repository is itself a Purlin project, its `version` field equals the `VERSION` file: the project's own stamp never lags the framework it ships [level: passed]
- RULE-7: `dev/bump_version.sh <semver>` is the one propagation entry point: it writes the `VERSION` file and sets the version field in every derived location, it refuses an argument that is not semver before writing anything, and `dev/bump_version.sh --check` exits non-zero naming each location that disagrees while still reporting the ones that match
- RULE-8: The one table that describes the config `version` field, in `references/drift_criteria.md`, states the `VERSION` file as its source rather than restating a release number, and no second copy of that row lives anywhere under `skills/` or `references/` [level: passed]

## Proof

- PROOF-1 (RULE-1): The `VERSION` file at the project root is read; it exists and, leading and trailing whitespace aside, holds exactly three whole numbers joined by dots, such as `0.10.0`, and nothing else. An empty file, `0.10`, `v0.10.0`, or a version followed by a second line would fail the check
- PROOF-2 (RULE-2): A copy of the package is placed in a temporary project whose `VERSION` file reads `9.8.7`, and the package and its server are loaded there in a fresh process; the version the package reports and the version the server reports both read exactly `9.8.7`, where a number written into either would read this checkout's release instead. In this checkout, the version the package reports is exactly what the `VERSION` file reads
- PROOF-3 (RULE-3): The settings template a new project is stamped from, `templates/config.json`, carries a `version` key whose value is exactly what the `VERSION` file reads; a template with no `version` key fails, and a template left at `0.9.2` while the file reads `0.10.0` fails naming both numbers
- PROOF-4 (RULE-4): Every Python module of the `purlin` package is read with its whole-line comments set aside; what remains holds no quoted version of three whole numbers joined by dots except `0.0.0`, the placeholder the package reports when the `VERSION` file cannot be read. A quoted `'0.10.0'` written into any module fails, and the failure lists `0.10.0`
- PROOF-5 (RULE-5): The plugin manifest a consumer installs against, `.claude-plugin/plugin.json`, carries a `version` key whose value is exactly what the `VERSION` file reads; a manifest with no `version` key fails, and a manifest left at `0.9.2` while the file reads `0.10.0` fails naming both numbers
- PROOF-6 (RULE-6): Read the `VERSION` file and parse this repository's own `.purlin/config.json`; verify it carries a `version` key equal to the `VERSION` string, so a stamp left at `0.9.2` while the file reads `0.10.0` fails naming both
- PROOF-7 (RULE-7): A temporary project holds its own copy of the bump script, a `VERSION` file, `templates/config.json`, `.claude-plugin/plugin.json` and `.purlin/config.json`, all at `1.2.3`. The script run with `9.8.7` exits 0 and leaves the `VERSION` file and all three JSON files reading `9.8.7`, and `--check` then exits 0. With `.purlin/config.json` set back to `1.2.3`, `--check` exits 1, and its output carries `DRIFT`, names `.purlin/config.json`, and still names `templates/config.json` and `.claude-plugin/plugin.json`. In a fresh project at `1.2.3`, the script run with `not-a-version` exits 2 and the `VERSION` file still reads `1.2.3`. With `.purlin/config.json` then deleted, the script run with `2.0.0` exits 0 and `templates/config.json` reads `2.0.0`, and `--check` exits 0 with `absent` in its output
- PROOF-8 (RULE-8): Read `references/drift_criteria.md`, take every table row whose first cell is `version`, and verify at least one exists, that none carries a quoted semver literal, and that each names the `VERSION` file. Then read every `.md` file under `skills/` and `references/` other than that one and verify none carries such a row, so restoring a `version` row at `0.9.0` to `skills/init/SKILL.md` fails naming that file
