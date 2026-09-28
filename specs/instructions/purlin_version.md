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

- PROOF-1 (RULE-1): Read the `VERSION` file; verify it exists, is not empty, and that its stripped content matches `^\d+\.\d+\.\d+$`
- PROOF-2 (RULE-2): Copy `scripts/mcp` under a temporary root whose `VERSION` file reads `9.8.7`, import the copied `purlin` package and its server in a fresh interpreter, and verify `PURLIN_VERSION` and the server's reported version both read exactly `9.8.7`; then import the package in this checkout and verify `PURLIN_VERSION` equals the stripped content of the `VERSION` file
- PROOF-3 (RULE-3): Read the `VERSION` file and parse `templates/config.json`; verify the file carries a `version` key and that its value is exactly the `VERSION` string
- PROOF-4 (RULE-4): Read every `.py` file of `scripts/mcp/purlin/`, drop the full-line comments, and grep the rest for a quoted `X.Y.Z` literal; verify the only match allowed is the sentinel `0.0.0` the reader returns when the `VERSION` file cannot be read, so a release number such as `0.10.0` written into any module fails naming it
- PROOF-5 (RULE-5): Read the `VERSION` file and parse `.claude-plugin/plugin.json`; verify the manifest carries a `version` key and that its value is exactly the `VERSION` string
- PROOF-6 (RULE-6): Read the `VERSION` file and parse this repository's own `.purlin/config.json`; verify it carries a `version` key equal to the `VERSION` string, so a stamp left at `0.9.2` while the file reads `0.10.0` fails naming both
- PROOF-7 (RULE-7): Build a temporary project holding a `VERSION` file and all three derived JSON files at `1.2.3`, plus a copy of the script; run it with `9.8.7` and verify the `VERSION` file and each JSON file read `9.8.7`; run `--check` and verify exit 0; hand-edit `.purlin/config.json` back to `1.2.3` and verify `--check` exits 1, printing `DRIFT` and naming `.purlin/config.json` while still listing `templates/config.json` and `.claude-plugin/plugin.json`. Then run the script with `not-a-version` and verify exit 2 with the `VERSION` file still reading `1.2.3`; delete `.purlin/config.json`, verify a bump exits 0 and still writes `templates/config.json`, and that `--check` exits 0 reporting that location as `absent`
- PROOF-8 (RULE-8): Read `references/drift_criteria.md`, take every table row whose first cell is `version`, and verify at least one exists, that none carries a quoted semver literal, and that each names the `VERSION` file. Then read every `.md` file under `skills/` and `references/` other than that one and verify none carries such a row, so restoring a `version` row at `0.9.0` to `skills/init/SKILL.md` fails naming that file
