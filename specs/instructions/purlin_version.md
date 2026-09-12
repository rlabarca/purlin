# Feature: purlin_version

> Scope: VERSION, templates/config.json, .claude-plugin/plugin.json, .purlin/config.json, scripts/mcp/purlin_server.py, dev/bump_version.sh, skills/init/SKILL.md, references/drift_criteria.md, RELEASE_NOTES.md
> Description: Ensures the Purlin version string is defined in exactly one place (the VERSION file) and every other location either reads from that file at runtime or is derived from it by `dev/bump_version.sh`. A human edits no version literal by hand: `bash dev/bump_version.sh <semver>` writes VERSION and propagates it, and `bash dev/bump_version.sh --check` is the CI gate that fails on drift. Prevents version drift when releasing new versions.

## Rules

- RULE-1: A VERSION file exists at the project root containing a single semver string
- RULE-2: purlin_server.py reads the version from the VERSION file via _read_version(), not a hardcoded string
- RULE-3: templates/config.json version field matches the VERSION file
- RULE-4: No hardcoded version strings in purlin_server.py (no literal "0.9.0" or similar version patterns)
- RULE-5: The .claude-plugin/plugin.json version field matches the VERSION file
- RULE-6: When `.purlin/config.json` exists (the repo is itself a Purlin project), its version field matches the VERSION file. The project's own stamp must not lag the framework it ships
- RULE-7: `dev/bump_version.sh <semver>` is the single propagation entry point: it writes the VERSION file and sets the version field in every derived location, and `dev/bump_version.sh --check` exits non-zero naming each location that disagrees with VERSION
- RULE-8: Documentation that describes the config `version` field states its source as the VERSION file rather than restating a release number, so no doc table can carry a stale version literal
- RULE-9: The `## Unreleased` section of `RELEASE_NOTES.md` states the test counts of the run it describes, on a line of the form `N passed, M skipped`, and those two numbers equal `passed` and `skipped` in `.purlin/runtime/test_run.json`. Release notes are written from memory at the end of a long branch and a count typed from the last sweep but one is the easiest number in the repository to get wrong; the run marker is the only record of what actually ran, so the notes are checked against it rather than against a person. The marker is gitignored runtime state, so a checkout that has never run the sweep has nothing to compare and the proof reports that rather than failing: a missing marker is an absent observation, not a contradiction

## Proof

- PROOF-1 (RULE-1): Read VERSION file; verify it exists and contains a valid semver string (X.Y.Z)
- PROOF-2 (RULE-2): Grep purlin_server.py for _read_version; verify it's called to set PURLIN_VERSION; verify SERVER_INFO uses PURLIN_VERSION
- PROOF-3 (RULE-3): Read VERSION file and templates/config.json; verify the version field in the template matches the VERSION file content
- PROOF-4 (RULE-4): Grep purlin_server.py for hardcoded version patterns like "0.9.0" or "0.10.0"; verify zero matches outside of comments
- PROOF-5 (RULE-5): Read VERSION file and .claude-plugin/plugin.json; verify the version field in the manifest matches the VERSION file content
- PROOF-6 (RULE-6): Read VERSION file and this repo's `.purlin/config.json`; verify its version field equals the VERSION file content exactly (e.g. both `0.10.0`, not `0.9.2` against `0.10.0`)
- PROOF-7 (RULE-7): Build a temp project root holding VERSION plus all three derived JSON files set to `1.2.3`; run `dev/bump_version.sh 9.8.7` against it and verify the VERSION file reads `9.8.7` and each JSON file reports `"version": "9.8.7"`; verify `--check` then exits 0; hand-edit `.purlin/config.json` back to `1.2.3` and verify `--check` exits 1 with stdout containing `DRIFT` and naming `.purlin/config.json` while still listing the two matching files. Separately verify `bump_version.sh not-a-version` exits 2 leaving VERSION at `1.2.3`, and that with `.purlin/config.json` deleted a bump exits 0 and `--check` exits 0 reporting that location as `absent`
- PROOF-8 (RULE-8): Grep `skills/init/SKILL.md` and `references/drift_criteria.md` for a quoted semver literal on the line describing the config `version` field; verify zero matches and that both lines instead reference the `VERSION` file by name
- PROOF-9 (RULE-9): Read `RELEASE_NOTES.md`, take the text between `## Unreleased` and the next `## ` heading, and parse the single line matching `(\d+) passed, (\d+) skipped`; verify exactly one such line exists in that section. Read `.purlin/runtime/test_run.json`; when it is absent, skip with a message naming the file and `bash dev/run_tests.sh`. When it is present, verify the parsed passed count equals the marker's `passed` and the parsed skipped count equals its `skipped`, failing with both numbers side by side. Editing the notes to say one test more than the marker records fails the proof naming both values
