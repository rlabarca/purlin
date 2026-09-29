# Feature: purlin_version

> Description: The version string lives in one file, `VERSION` at the project
>   root. Everything else either reads it at run time or is written from it by
>   `dev/bump_version.sh`, and `bash dev/bump_version.sh --check` is the check
>   that fails when a derived location disagrees. Nobody edits a version
>   literal by hand, and a document that describes the version field names the
>   file rather than restating a number, so no table can go stale.
> Scope: VERSION, templates/config.json, .claude-plugin/plugin.json, .purlin/config.json, scripts/mcp/purlin/__init__.py, scripts/mcp/purlin/server.py, dev/bump_version.sh, references/drift_criteria.md, skills/init/SKILL.md, scripts/init/scaffold.py
> Stack: python/stdlib for the reader, bash for the propagation script, json for the derived locations

## Rules

- RULE-1: A `VERSION` file at the project root holds one semver string and nothing else
- RULE-2: The `purlin` package reads the version out of the `VERSION` file at import time and assigns it to `PURLIN_VERSION`, and the server reports that value rather than a literal of its own; with no `VERSION` file, both read `0.0.0`
- RULE-3: The `version` field of `templates/config.json`, the settings template `purlin:init` copies into a new project, equals the `VERSION` file, and a project `purlin:init` sets up is stamped with that same version
- RULE-4: No module of the `purlin` package carries a quoted release version, three whole numbers joined by dots, on a line that is not wholly a comment; the one exception is `0.0.0`, which the package reports when the `VERSION` file cannot be read
- RULE-5: The `version` field of `.claude-plugin/plugin.json`, which is what the plugin loader reports and what a consumer installs against, equals the `VERSION` file
- RULE-6: Where `.purlin/config.json` exists, because the repository is itself a Purlin project, its `version` field equals the `VERSION` file: the project's own stamp never lags the framework it ships
- RULE-7: `dev/bump_version.sh <semver>` is the one propagation entry point: it writes the `VERSION` file and sets the version field in every derived location, it refuses an argument that is not semver before writing anything, and `dev/bump_version.sh --check` exits non-zero naming each location that disagrees while still reporting the ones that match
- RULE-8: The one table that describes the config `version` field, in `references/drift_criteria.md`, states the `VERSION` file as its source rather than restating a release number, and no second copy of that row lives anywhere under `skills/` or `references/`

## Proof

- PROOF-1 (RULE-1): The `VERSION` file at the project root is read; with whitespace at either end set aside, it holds exactly three whole numbers joined by dots, such as `0.10.0`, and nothing else
- PROOF-11 (RULE-1): Read the same way, a `VERSION` file holding `0.10.0` with two spaces before it and a line ending after it passes: the whitespace at either end is set aside
- PROOF-12 (RULE-1): Read the same way, an empty `VERSION` file fails: it holds no version
- PROOF-13 (RULE-1): Read the same way, a `VERSION` file holding `0.10` fails: two numbers are not a version
- PROOF-14 (RULE-1): Read the same way, a `VERSION` file holding `v0.10.0` fails: the letter before the numbers is not part of a version
- PROOF-15 (RULE-1): Read the same way, a `VERSION` file holding `0.10.0` on its first line and `0.11.0` on a second fails: it holds two versions
- PROOF-2 (RULE-2): A copy of the package sits in a temporary project whose `VERSION` file reads `9.8.7`. Loaded there in a fresh process, the package reports `9.8.7` and its server reports `9.8.7`, where a number written into either would read this checkout's release instead
- PROOF-16 (RULE-2): A client starts the server of a copied package beside a `VERSION` file reading `9.8.7` and sends the opening handshake; the answer names the server `purlin` at version `9.8.7`
- PROOF-17 (RULE-2): A copy of the package sits in a temporary project with no `VERSION` file. Loaded there in a fresh process, the package reports `0.0.0` and its server reports `0.0.0`
- PROOF-18 (RULE-2): In this checkout, the version the package reports is exactly what the `VERSION` file reads, whitespace at either end aside
- PROOF-3 (RULE-3): The settings template a new project is made from, `templates/config.json`, carries a `version` key whose value is exactly what the `VERSION` file reads
- PROOF-19 (RULE-3): Checked the same way, a copy of the template with its `version` key removed fails, and the failure reads `templates/config.json has no 'version' field`
- PROOF-20 (RULE-3): Checked the same way, a copy of the template left at `0.9.2` while the `VERSION` file reads `0.10.0` fails, and the failure names both numbers
- PROOF-21 (RULE-3): Setup, `purlin:init`, is run at the gate `passed` with nothing asked, in a new git repository holding no files; it exits 0, and the new project's `.purlin/config.json` carries a `version` key reading exactly what this checkout's `VERSION` file reads
- PROOF-4 (RULE-4): Every Python module of the `purlin` package is read with its whole-line comments set aside; what remains holds no quoted version of three whole numbers joined by dots other than `0.0.0`
- PROOF-22 (RULE-4): In a copy of the package, a line `RELEASE = '0.10.0'` added to one module is found, and the failure lists `0.10.0` beside the name of that module and nothing else
- PROOF-23 (RULE-4): In a copy of the package, a whole-line comment `# the release was '0.9.0'` added to one module is not found, and nothing is listed
- PROOF-5 (RULE-5): The plugin manifest a consumer installs against, `.claude-plugin/plugin.json`, carries a `version` key whose value is exactly what the `VERSION` file reads
- PROOF-24 (RULE-5): Checked the same way, a copy of the manifest with its `version` key removed fails, and the failure reads `.claude-plugin/plugin.json has no 'version' field`
- PROOF-25 (RULE-5): Checked the same way, a copy of the manifest left at `0.9.2` while the `VERSION` file reads `0.10.0` fails, and the failure names both numbers
- PROOF-6 (RULE-6): This repository's own settings file, `.purlin/config.json`, carries a `version` key whose value is exactly what the `VERSION` file reads
- PROOF-26 (RULE-6): Checked the same way, a copy of that settings file with its `version` key removed fails, and the failure reads `.purlin/config.json has no 'version' field`
- PROOF-27 (RULE-6): Checked the same way, a copy of that settings file left at `0.9.2` while the `VERSION` file reads `0.10.0` fails, and the failure names both numbers
- PROOF-7 (RULE-7): A temporary project holds its own copy of the bump script, a `VERSION` file, `templates/config.json`, `.claude-plugin/plugin.json` and `.purlin/config.json`, all at `1.2.3`. The script run with `9.8.7` exits 0, and the `VERSION` file and all three JSON files then read `9.8.7`
- PROOF-28 (RULE-7): In a temporary project with its own copy of the bump script and its `VERSION` file and three JSON files all at `9.8.7`, the script run with `--check` exits 0, and its lines for the three JSON files each read `ok 9.8.7`
- PROOF-29 (RULE-7): In a temporary project with its own copy of the bump script, its `VERSION` file at `9.8.7` and `.purlin/config.json` at `1.2.3`, `--check` exits 1; its line for `.purlin/config.json` reads `DRIFT 1.2.3 (expected 9.8.7)`, and its lines for `templates/config.json` and `.claude-plugin/plugin.json` each read `ok 9.8.7`
- PROOF-30 (RULE-7): In a temporary project with its own copy of the bump script, its files at `9.8.7` and the `version` key removed from `templates/config.json`, `--check` exits 1, and its line for `templates/config.json` reads `FAIL no "version" key`
- PROOF-31 (RULE-7): In a temporary project with its own copy of the bump script and its `VERSION` file and three JSON files all at `1.2.3`, the script run with `not-a-version` exits 2, and all four files still read `1.2.3`
- PROOF-32 (RULE-7): In a temporary project with its own copy of the bump script, its files at `1.2.3` and no `.purlin/config.json`, the script run with `2.0.0` exits 0; the `VERSION` file, `templates/config.json` and `.claude-plugin/plugin.json` read `2.0.0`, and `.purlin/config.json` is not created
- PROOF-33 (RULE-7): In a temporary project with its own copy of the bump script, its files at `2.0.0` and no `.purlin/config.json`, `--check` exits 0; its line for `.purlin/config.json` reads `absent`, and its lines for the other two JSON files read `ok 2.0.0`
- PROOF-8 (RULE-8): In `references/drift_criteria.md` at least one table row has `version` as its first cell, and every such row names the `VERSION` file and holds no version of three whole numbers joined by dots
- PROOF-34 (RULE-8): No Markdown file under `skills/` or `references/` other than `references/drift_criteria.md` holds a table row whose first cell is `version`
- PROOF-35 (RULE-8): In a copy of `skills/` and `references/`, a table row with `version` as its first cell and `0.9.0` as its second, added to `skills/init/SKILL.md`, is found as a second copy, and the failure names that file and no other
- PROOF-36 (RULE-8): In a copy of `references/drift_criteria.md` whose `version` row reads `0.9.0` where it named the `VERSION` file, that row is found both to restate a number and to not name the `VERSION` file
