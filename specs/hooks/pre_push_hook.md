# Feature: pre_push_hook

> Requires: security_no_dangerous_patterns
> Scope: scripts/hooks/pre-push.sh
> Stack: shell/bash, python3 (sync_status invocation, config parsing)

## What it does

Layer 1 enforcement hook that runs before `git push`. Executes unit-tier tests and checks sync_status for proof coverage. Two modes: warn (default) blocks on FAIL only, allows passing and partial; strict blocks on anything not READY (requires verification receipt). Allows silently when no specs exist.

## Rules

- RULE-1: Blocks push with exit 1 when any proof has status FAIL in sync_status output
- RULE-2: Allows push with exit 0 and prints a warning when proofs are partial (NO PROOF rules exist but none are FAIL)
- RULE-3: Allows push with exit 0 silently when no specs directory exists or specs directory contains no .md files
- RULE-4: Allows push with exit 0 when all proofs pass (passing or READY status, no FAIL, no NO PROOF)
- RULE-5: Detects test framework from `.purlin/config.json` `test_framework` field, falling back to auto-detection (pytest if conftest.py or pyproject.toml [tool.pytest] exists, jest if package.json contains jest, shell otherwise)
- RULE-6: Runs only unit-tier tests (pytest excludes `not integration`, jest uses `--testPathPattern=unit`, shell runs `*.test.sh`)
- RULE-7: Produces output showing which features passed, which have partial coverage, and which are blocked with FAIL proofs
- RULE-8: In strict mode (`"pre_push": "strict"` in config), blocks push with exit 1 when any feature is not READY — this includes "passing" features that lack a verification receipt; allows push only when all features are READY
- RULE-9: After `purlin:init`, `.git/hooks/pre-push` exists, is executable, and runs `scripts/hooks/pre-push.sh`

## Proof

- PROOF-1 (RULE-1): Set up temp project with .purlin/ and specs/; create a spec with 3 rules; create proof file with one FAIL entry; run pre-push.sh; verify exit code is 1 and stdout contains "PUSH BLOCKED" @integration
- PROOF-2 (RULE-2): Set up temp project with .purlin/ and specs/; create proof file with one NO PROOF entry and no FAIL entries; run pre-push.sh; verify exit code is 0 and stdout contains "partial coverage" @integration
- PROOF-3 (RULE-3): Set up temp project with .purlin/ but no specs/ directory; run pre-push.sh; verify exit code is 0 and stdout is empty @integration
- PROOF-4 (RULE-4): Set up temp project with .purlin/ and specs/; create proof file with all PASS entries (READY status); run pre-push.sh; verify exit code is 0 @integration
- PROOF-5 (RULE-5): Set up temp project with `.purlin/config.json` containing `{"test_framework": "pytest"}`; verify pre-push.sh selects pytest; repeat with `{"test_framework": "jest"}` and verify jest is selected @integration
- PROOF-6 (RULE-6): Set up temp project with conftest.py and two test files (one unit, one @integration); run pre-push.sh; verify the unit test ran (sentinel file created) and the integration test was skipped (no sentinel) @integration
- PROOF-7 (RULE-7): Set up temp project with specs containing PASS, FAIL, and NO PROOF entries; run pre-push.sh; verify stdout contains "passing features", "partial coverage", and "PUSH BLOCKED" sections @integration
- PROOF-8 (RULE-1): Full lifecycle test: create temp git repo with .purlin/ and specs/; create spec with 3 rules; create proof file with 1 PASS, 1 FAIL, 1 NO PROOF; run hook and verify exit 1 (blocked by FAIL); fix FAIL to PASS; run hook and verify exit 0 with warning (NO PROOF remains); add missing proof as PASS; run hook and verify exit 0 silently (all READY) @e2e
- PROOF-9 (RULE-8): Set strict mode in config; create proofs for 2 of 3 rules (no FAIL, but not READY); run hook; verify exit 1 and output contains "strict mode" @integration
- PROOF-10 (RULE-8): Set strict mode in config; create proofs for all rules (READY); run hook; verify exit 0 @integration
- PROOF-11 (RULE-9): Run purlin:init on a fresh git repo; verify .git/hooks/pre-push exists, is executable, and a git push with failing proofs is intercepted and blocked @e2e
