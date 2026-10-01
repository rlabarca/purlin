# Feature: purlin_version

> Description: The version string lives in one file, `VERSION` at the project
>   root. Everything else either reads it at run time or is written from it by
>   `dev/bump_version.sh`, and `bash dev/bump_version.sh --check` is the check
>   that fails when a derived location disagrees, so the version a user installs
>   and the one Purlin reports are the same.
> Scope: VERSION, .claude-plugin/plugin.json, .claude-plugin/marketplace.json, .purlin/config.json, scripts/mcp/purlin/__init__.py, scripts/mcp/purlin/server.py, dev/bump_version.sh, scripts/init/scaffold.py
> Stack: python/stdlib for the reader, bash for the propagation script, json for the derived locations
> Highest-Rule: 16
> Highest-Proof: 38

## Rules

- RULE-1: A `VERSION` file at the project root holds one semver string and nothing else
- RULE-2: The `purlin` package reads the version out of the `VERSION` file at import time and assigns it to `PURLIN_VERSION`, and the server reports that value rather than a literal of its own
- RULE-3: A project `purlin:init` sets up is stamped with `VERSION`
- RULE-5: The `version` field of `.claude-plugin/plugin.json`, which is what the plugin loader reports and what a consumer installs against, equals the `VERSION` file
- RULE-6: Where `.purlin/config.json` exists, because the repository is itself a Purlin project, its `version` field equals the `VERSION` file: the project's own stamp never lags the framework it ships
- RULE-11: With no `VERSION` file, the `purlin` package and its server both read `0.0.0`
- RULE-12: `dev/bump_version.sh <semver>` writes the `VERSION` file and sets the version field in every derived location
- RULE-13: `dev/bump_version.sh` refuses an argument that is not semver before writing anything
- RULE-14: `dev/bump_version.sh --check` exits non-zero naming each location that disagrees while still reporting the ones that match
- RULE-16: The plugin's marketplace manifest, `.claude-plugin/marketplace.json`, is named `purlin` and lists one plugin, `purlin`, whose source is the repository root

## Proof

- PROOF-1 (RULE-1): The `VERSION` file at the project root is read; with whitespace at either end set aside, it holds exactly three whole numbers joined by dots, such as `0.10.0`, and nothing else
- PROOF-11 (RULE-1): Read the same way, a `VERSION` file holding `0.10.0` with two spaces before it and a line ending after it passes: the whitespace at either end is set aside
- PROOF-12 (RULE-1): Read the same way, an empty `VERSION` file fails: it holds no version
- PROOF-13 (RULE-1): Read the same way, a `VERSION` file holding `0.10` fails: two numbers are not a version
- PROOF-14 (RULE-1): Read the same way, a `VERSION` file holding `v0.10.0` fails: the letter before the numbers is not part of a version
- PROOF-15 (RULE-1): Read the same way, a `VERSION` file holding `0.10.0` on its first line and `0.11.0` on a second fails: it holds two versions
- PROOF-2 (RULE-2): A copy of the package sits in a temporary project whose `VERSION` file reads `9.8.7`. Loaded there in a fresh process, the package reports `9.8.7` and its server reports `9.8.7`, where a number written into either would read this checkout's release instead
- PROOF-16 (RULE-2): A client starts the server of a copied package beside a `VERSION` file reading `9.8.7` and sends the opening handshake; the answer names the server `purlin` at version `9.8.7`
- PROOF-17 (RULE-11): A copy of the package sits in a temporary project with no `VERSION` file. Loaded there in a fresh process, the package reports `0.0.0` and its server reports `0.0.0`
- PROOF-18 (RULE-2): In this checkout, the version the package reports is exactly what the `VERSION` file reads, whitespace at either end aside
- PROOF-21 (RULE-3): Setup, `purlin:init`, is run with `--yes` in a new git repository holding no files; it exits 0, and the new project's `.purlin/config.json` carries a `version` key reading exactly what this checkout's `VERSION` file reads
- PROOF-5 (RULE-5): The plugin manifest a consumer installs against, `.claude-plugin/plugin.json`, carries a `version` key whose value is exactly what the `VERSION` file reads
- PROOF-6 (RULE-6): This repository's own settings file, `.purlin/config.json`, carries a `version` key whose value is exactly what the `VERSION` file reads
- PROOF-7 (RULE-12): A temporary project holds its own copy of the bump script, a `VERSION` file, `.claude-plugin/plugin.json` and `.purlin/config.json`, all at `1.2.3`. The script run with `9.8.7` exits 0, and the `VERSION` file and both JSON files then read `9.8.7`
- PROOF-28 (RULE-14): In a temporary project with its own copy of the bump script and its `VERSION` file and two JSON files all at `9.8.7`, the script run with `--check` exits 0, and its lines for the two JSON files each read `ok 9.8.7`
- PROOF-29 (RULE-14): In a temporary project with its own copy of the bump script, its `VERSION` file at `9.8.7` and `.purlin/config.json` at `1.2.3`, `--check` exits 1; its line for `.purlin/config.json` reads `DRIFT 1.2.3 (expected 9.8.7)`, and its line for `.claude-plugin/plugin.json` reads `ok 9.8.7`
- PROOF-30 (RULE-14): In a temporary project with its own copy of the bump script, its files at `9.8.7` and the `version` key removed from `.claude-plugin/plugin.json`, `--check` exits 1, and its line for `.claude-plugin/plugin.json` reads `FAIL no "version" key`
- PROOF-31 (RULE-13): In a temporary project with its own copy of the bump script and its `VERSION` file and two JSON files all at `1.2.3`, the script run with `not-a-version` exits 2, and all three files still read `1.2.3`
- PROOF-32 (RULE-12): In a temporary project with its own copy of the bump script, its files at `1.2.3` and no `.purlin/config.json`, the script run with `2.0.0` exits 0; the `VERSION` file and `.claude-plugin/plugin.json` read `2.0.0`, and `.purlin/config.json` is not created
- PROOF-33 (RULE-14): In a temporary project with its own copy of the bump script, its files at `2.0.0` and no `.purlin/config.json`, `--check` exits 0; its line for `.purlin/config.json` reads `absent`, and its line for `.claude-plugin/plugin.json` reads `ok 2.0.0`
- PROOF-38 (RULE-16): The plugin's marketplace manifest reads the name `purlin` and holds one plugin entry, named `purlin`, whose source is `./`, the repository root
