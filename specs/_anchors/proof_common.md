# Anchor: proof_common

> Type: schema
> Scope: scripts/proof/
> Description: The behavior every Purlin proof plugin implements regardless of language:
>   spec-directory resolution, proof-file naming, fallback, the write-scoped overwrite keyed
>   by (feature, tier, test_file), orphan reaping, the 7 required fields, pass/fail status,
>   the no-marker no-op, glob-based discovery, the fallback stderr warning, and
>   purge-on-rerun. Each per-language proof plugin spec
>   (proof_plugins_pytest, proof_plugins_jest, proof_plugins_shell, proof_plugins_c,
>   proof_plugins_php, proof_plugins_sql, proof_plugins_vitest, proof_plugins_xunit)
>   requires this anchor and adds only its framework-specific rules.

## What it does

Defines the cross-cutting contract shared by all proof collection plugins. A plugin spec
that declares `> Requires: proof_common` inherits these rules, so per-language specs only
restate the marker syntax and status mapping unique to their framework. Keeping the shared
behavior in one place means a change to the proof-file contract is made and proved once,
not copied across eight specs.

The merge key is `(feature, tier, test_file)`. Two test files can cover the same feature at
the same tier and be run in any order, in separate processes, without destroying each
other's entries. That is what lets a platform-gated tier be proven on a remote runner and a
large suite be split across files. The cost of the narrower key is that a run only reaps
what it can see: RULE-11 reaps entries whose test file is gone, and RULE-12 states the
bounded case that survives.

A proof file is only evidence while something regenerates it. RULE-14 closes that gap for this
repository's own proofs: a committed entry whose test file no sweep runs would stay green no
matter what the code did, so every proof-named test file is either in `dev/run_tests.sh` or in
an explicit exception list that names the runner it needs, and the proof of that rule fails in
both directions, so an exception cannot outlive its reason.

## Rules

- RULE-1: Each plugin resolves the spec directory by scanning `specs/**/*.md` and matching the feature name to the spec filename stem
- RULE-2: Proof files are written to the spec's directory as `<feature>.proofs-<tier>.json`
- RULE-3: When the spec directory for a feature is not found, the plugin falls back to writing to `specs/`
- RULE-4: Write-scoped overwrite keyed by `(feature, tier, test_file)`: within the tier file being written, an existing entry is replaced only if it matches the current feature AND its `test_file` was executed in the current run. Entries belonging to other features, and the current feature's entries from test files this run did not execute, are preserved, so two test files covering the same `(feature, tier)` can run in any order without clobbering each other
- RULE-5: Each proof entry contains all 7 required fields: `feature`, `id`, `rule`, `test_file`, `test_name`, `status`, `tier`
- RULE-6: `status` is `"pass"` when the test passes and `"fail"` when it fails, no other values
- RULE-7: If no proof markers are collected during a test run, no proof files are written (no-op)
- RULE-8: Custom/community proof plugins installed to `.purlin/plugins/` require no registration: `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`, so any plugin that writes files in that pattern works automatically
- RULE-9: When spec directory lookup falls back to specs/ root, the plugin emits a warning to stderr naming the missing spec and suggesting purlin:spec <feature>
- RULE-10: When a test is removed from a test file and that file is re-run, the old proof entry is purged and not carried over from the previous proof file
- RULE-11: Orphan reaping: when writing a tier file, the current feature's entries whose `test_file` no longer resolves to a file in the working tree are dropped, not preserved. A renamed or deleted test file's entries are therefore reaped on the next run of that `(feature, tier)`
- RULE-12: A test file's entries are reaped only by a run that executes that `(feature, tier)`. Removing a proof marker from a test file that the run did not execute leaves that entry in place until that file runs again
- RULE-13: `status` records execution, never availability. A test that did not run on this host emits no proof entry at all: `"fail"` means the test ran and its assertion failed, and `"pass"` means it ran and passed. Writing `"fail"` for a skipped test is forbidden, because a reader and every gate downstream cannot tell a broken build from a missing tool. Emitting nothing is safe under the RULE-4 merge key: whatever a capable host last proved for those ids stays committed and untouched, so the skip neither falsifies nor destroys it
- RULE-14: Every test file named by a committed proof entry is either executed by `dev/run_tests.sh` or listed with its runner in this rule's exception list: `dev/test_windows_native.py` (Windows runner), `dev/test_e2e_figma_web.py` (Figma MCP, `PURLIN_E2E_FIGMA=1`), `dev/test_e2e_build_agent.py` (claude CLI, `PURLIN_E2E_AGENT=1`). A test file outside both sets is a proof nothing regenerates. The list is exact: a listed file the sweep runs, or that no committed proof names, is a stale exception and is removed

## Proof

- PROOF-1 (RULE-1): Create `specs/hooks/gate_hook.md` and run a proof plugin with feature `gate_hook`; verify the proof file is written to `specs/hooks/` @integration
- PROOF-2 (RULE-2): Run a proof plugin for feature `gate_hook` tier `unit`; verify output file is named `gate_hook.proofs-unit.json` @integration
- PROOF-3 (RULE-3): Run a proof plugin for feature `nonexistent_feature` (no matching spec); verify proof file is written to `specs/` @integration
- PROOF-4 (RULE-4): Create a proof file with entries for features A and B; run the plugin for feature A only; verify feature B entries are preserved and feature A entries are replaced @integration
- PROOF-5 (RULE-5): Run a proof plugin and read the output JSON; verify each entry in `proofs` array contains all 7 fields: `feature`, `id`, `rule`, `test_file`, `test_name`, `status`, `tier` @integration
- PROOF-6 (RULE-6): Run a passing test and a failing test with proof markers; verify the passing test has `status: "pass"` and the failing test has `status: "fail"` @integration
- PROOF-7 (RULE-7): Run a test suite with no proof markers; verify no `*.proofs-*.json` files are created @integration
- PROOF-8 (RULE-8): Place a `.proofs-unit.json` file in a spec directory written by a non-built-in source; run `sync_status`; verify it reads the proofs @integration
- PROOF-9 (RULE-9): Run a proof plugin for a feature with no matching spec; verify stderr contains a warning naming the feature and suggesting purlin:spec @integration
- PROOF-10 (RULE-4): e2e: Create 2 specs; write proofs for each separately; verify both PASSING and no cross-contamination @e2e
- PROOF-11 (RULE-4): e2e: Overwrite one feature's proofs via shell harness; verify target feature updated, other feature untouched @e2e
- PROOF-12 (RULE-10): e2e: Run a shell test file emitting PROOF-1 and PROOF-2 for one feature, then re-run the same file emitting only PROOF-1; verify coverage drops to 1/2 because the PROOF-2 entry was purged, not carried over @e2e
- PROOF-13 (RULE-10): Write a proof file with 2 proofs, then re-run the same test file with only 1; verify the removed entry is purged and not carried over @integration
- PROOF-14 (RULE-4): Run the real pytest plugin for one feature from test file A, then from test file B, both at tier `unit`; verify the merged file holds both entries. Repeat with the order reversed; verify the merged file again holds both @integration
- PROOF-15 (RULE-11): Run the real pytest plugin for one feature from test files A and B, delete A, then run the same feature from test file C; verify A's entry is absent from the merged file while B's entry, whose file still exists and was not re-run, is still present @integration
- PROOF-16 (RULE-12): Run the real pytest plugin for one feature from test files A and B, remove the proof marker from A, then re-run B only; verify A's entry is still present because A was not executed @integration
- PROOF-17 (RULE-13): Run a suite whose prerequisite is absent so it takes its skip path; verify it writes no proof file and leaves an existing one byte-identical, and that its output names the proof ids it did not execute. Scan every proof-emitting test script in the repo for a call that writes `fail` from inside a skip or unavailable-prerequisite branch; verify there are none @integration
- PROOF-18 (RULE-14): Parse `dev/run_tests.sh` for every `$SCRIPT_DIR/test_*` path it invokes; parse every git-tracked `specs/**/*.proofs-*.json` for `test_file`; read the exception list from RULE-14's own text. Verify the set of proof-named files the sweep does not invoke equals the exception list exactly: a proof-named file in neither set fails with its path, and a listed exception the sweep now runs or that no proof names fails with its path
