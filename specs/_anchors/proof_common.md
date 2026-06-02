# Anchor: proof_common

> Type: schema
> Scope: scripts/proof/, skills/init/SKILL.md
> Description: The behavior every Purlin proof plugin implements regardless of language —
>   spec-directory resolution, proof-file naming, fallback, feature-scoped overwrite, the
>   7 required fields, pass/fail status, the no-marker no-op, glob-based discovery, the
>   fallback stderr warning, and purge-on-rerun. Each per-language proof plugin spec
>   (proof_plugins_pytest, proof_plugins_jest, proof_plugins_shell, proof_plugins_c,
>   proof_plugins_php, proof_plugins_sql, proof_plugins_vitest, proof_plugins_xunit)
>   requires this anchor and adds only its framework-specific rules.

## What it does

Defines the cross-cutting contract shared by all proof collection plugins. A plugin spec
that declares `> Requires: proof_common` inherits these rules, so per-language specs only
restate the marker syntax and status mapping unique to their framework. Keeping the shared
behavior in one place means a change to the proof-file contract is made and proved once,
not copied across eight specs.

## Rules

- RULE-1: Each plugin resolves the spec directory by scanning `specs/**/*.md` and matching the feature name to the spec filename stem
- RULE-2: Proof files are written to the spec's directory as `<feature>.proofs-<tier>.json`
- RULE-3: When the spec directory for a feature is not found, the plugin falls back to writing to `specs/`
- RULE-4: Feature-scoped overwrite: existing entries for other features are preserved; only the current feature's entries are replaced
- RULE-5: Each proof entry contains all 7 required fields: `feature`, `id`, `rule`, `test_file`, `test_name`, `status`, `tier`
- RULE-6: `status` is `"pass"` when the test passes and `"fail"` when it fails — no other values
- RULE-7: If no proof markers are collected during a test run, no proof files are written (no-op)
- RULE-8: Custom/community proof plugins installed to `.purlin/plugins/` require no registration — `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`, so any plugin that writes files in that pattern works automatically
- RULE-9: When spec directory lookup falls back to specs/ root, the plugin emits a warning to stderr naming the missing spec and suggesting purlin:spec <feature>
- RULE-10: When a test is removed from a re-run, the old proof entry is purged and not carried over from the previous proof file

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
- PROOF-12 (RULE-10): e2e: Write proof file with only 1 of 2 proofs (test deletion); verify coverage shows 1/2 not 2/2 @e2e
- PROOF-13 (RULE-10): Write a proof file with 2 proofs, then re-run with only 1; verify the removed entry is purged and not carried over @integration
