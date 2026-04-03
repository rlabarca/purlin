# Feature: e2e_hybrid_audit

> Scope: scripts/audit/static_checks.py, skills/audit/SKILL.md

## What it does

End-to-end test for the two-pass hybrid audit architecture. Creates temp projects with deliberately flawed and valid Python tests, runs the deterministic static checker, and verifies that structural defects are caught without any LLM and that structurally valid tests pass through to the semantic pass.

## Rules

- RULE-1: assert True is detected as HOLLOW by static_checks.py (deterministic, no LLM)
- RULE-2: Tests with no assertion statements are detected as HOLLOW
- RULE-3: Logic mirroring (expected value from same function as SUT) is detected as HOLLOW
- RULE-4: Structurally valid but semantically weak tests pass Pass 1 (not flagged by static checker)
- RULE-5: Strong tests with real assertions pass structural checks with exit code 0
- RULE-6: JSON output contains proofs array with proof_id, rule_id, test_name, status, reason fields
- RULE-7: Exit code 0 when all proofs pass, exit code 1 when any fail
- RULE-8: Mock target matching the rule's described function is detected as HOLLOW
- RULE-9: Bare except:pass around code under test is detected as HOLLOW

## Proof

- PROOF-1 (RULE-1): Create test with assert True; run static_checks; verify fail/assert_true @e2e
- PROOF-2 (RULE-2): Create test with no assertions; run static_checks; verify fail/no_assertions @e2e
- PROOF-3 (RULE-3): Create test with logic mirroring; run static_checks; verify fail/logic_mirroring @e2e
- PROOF-4 (RULE-4): Create test checking status code only; run static_checks; verify pass @e2e
- PROOF-5 (RULE-5): Create 3 strong tests; run static_checks; verify all pass with exit 0 @e2e
- PROOF-6 (RULE-6): Parse JSON output; verify proofs array has required fields @e2e
- PROOF-7 (RULE-7): Verify exit 0 on clean file and exit 1 on flawed file @e2e
- PROOF-8 (RULE-8): Create test mocking bcrypt on rule about bcrypt; run static_checks; verify fail/mock_target_match @e2e
- PROOF-9 (RULE-9): Create test with except Exception: pass; run static_checks; verify fail/bare_except @e2e
