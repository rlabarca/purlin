# Feature: e2e_feature_scoped_overwrite

> Scope: scripts/proof/shell_purlin.sh, scripts/proof/pytest_purlin.py
> Stack: shell/bash, python3 (proof plugin feature-scoped overwrite logic)
> Description: End-to-end test of the proof plugin's feature-scoped overwrite behavior. When proof files are written for one feature, entries for other features in separate proof files must not be affected. Verifies that re-running tests for a single feature replaces only that feature's entries, and that removing a test correctly purges the old proof.

## Rules

- RULE-1: Writing proofs for one feature does not affect proof files of other features
- RULE-2: Re-writing proofs for a feature replaces only that feature's entries in its proof file, leaving other features' proof files intact
- RULE-3: When a test is removed from a re-run, the old proof entry is purged and not carried over from the previous proof file

## Proof

- PROOF-1 (RULE-1): Create 2 specs (login, signup) with separate proof files; write login proofs; write signup proofs; run sync_status; verify both PASSING @e2e
- PROOF-2 (RULE-2): Overwrite login proof file with updated entries; run sync_status; verify login still PASSING and signup still PASSING with original entries @e2e
- PROOF-3 (RULE-3): Write login proof file with only 1 of 2 proofs (PROOF-2 removed); run sync_status; verify login shows 1/2 not 2/2 @e2e
