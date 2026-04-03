# Feature: static_checks

> Scope: scripts/audit/static_checks.py

## What it does

Deterministic pre-filter that catches structural test problems without any LLM. Uses Python's `ast` module for Python tests and regex for Shell/Jest tests. Runs before the LLM audit pass so that structural issues like `assert True` are always caught regardless of which LLM performs the semantic evaluation.

## Rules

- RULE-1: Detects assert True / tautological assertions in Python test functions
- RULE-2: Detects test functions with no assertion statements
- RULE-3: Detects bare except:pass around code under test
- RULE-4: Detects logic mirroring (expected value from same function as SUT)
- RULE-5: Detects mock target matching the function being tested (requires --spec-path)
- RULE-6: Returns JSON with proof_id, rule_id, test_name, status, reason for each proof
- RULE-7: Exit code 0 when all pass, exit code 1 when any fail

## Proof

- PROOF-1 (RULE-1): Run static_checks on a file with assert True; verify status=fail check=assert_true
- PROOF-2 (RULE-2): Run static_checks on a file with no assertions; verify status=fail check=no_assertions
- PROOF-3 (RULE-3): Run static_checks on a file with except Exception: pass; verify status=fail check=bare_except
- PROOF-4 (RULE-4): Run static_checks on a file with logic mirroring; verify status=fail check=logic_mirroring
- PROOF-5 (RULE-5): Run static_checks with --spec-path on a file mocking the rule's function; verify status=fail check=mock_target_match
- PROOF-6 (RULE-6): Run static_checks on any file; verify JSON output has proofs array with required fields
- PROOF-7 (RULE-7): Run static_checks on a clean file and verify exit 0; run on flawed file and verify exit 1
