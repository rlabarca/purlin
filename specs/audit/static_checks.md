# Feature: static_checks

> Scope: scripts/audit/static_checks.py
> Description: Deterministic pre-filter that catches structural test problems without any LLM. Uses Python's `ast` module for Python tests, regex for Shell/Jest tests, and language-agnostic proof-file checks (proof ID collisions, orphan rules) that operate on JSON regardless of source language. Runs before the LLM audit pass so that structural issues like `assert True` are always caught regardless of which LLM performs the semantic evaluation.

## Rules

- RULE-1: Detects assert True / tautological assertions in Python test functions
- RULE-2: Detects test functions with no assertion statements
- RULE-3: Detects bare except:pass around code under test
- RULE-4: Detects logic mirroring (expected value from same function as SUT)
- RULE-5: Detects mock target matching the function being tested (requires --spec-path)
- RULE-6: Returns JSON with proof_id, rule_id, test_name, status, reason for each proof
- RULE-7: Always exits 0 for completed analysis; defects are reported via JSON output status=fail, not exit codes. Non-zero exits (2) are reserved for real errors (bad args, missing files)
- RULE-8: check_spec_coverage returns structural_only_spec=true and per-rule structural/behavioral classification when all rules are structural presence checks
- RULE-9: check_spec_coverage returns structural_only_spec=false and per-rule structural/behavioral classification when at least one rule describes behavioral constraints
- RULE-10: compute_proof_hash returns a deterministic 16-char hex hash from (rule text, proof description, test code)
- RULE-11: read_audit_cache returns an empty dict when no cache file exists and parses valid JSON when it does
- RULE-12: write_audit_cache writes atomically via tmp + os.replace
- RULE-13: Shell if/else proof pairs (same proof_id and rule_id with one pass and one fail branch) are recognized as a single conditional proof where the if-condition is the assertion, not flagged as hardcoded pass
- RULE-14: Python assert_true results include a literal field (true for assert True/assertTrue(True), false for heuristic patterns like assert x is not None)
- RULE-15: Proof ID collisions within a feature are detected — same PROOF-N targeting different RULE-N values in a proof JSON file
- RULE-16: Proof entries referencing non-existent rules in the spec are flagged as orphans

## Proof

- PROOF-1 (RULE-1): Run static_checks on a file with assert True; verify status=fail check=assert_true
- PROOF-2 (RULE-2): Run static_checks on a file with no assertions; verify status=fail check=no_assertions
- PROOF-3 (RULE-3): Run static_checks on a file with except Exception: pass; verify status=fail check=bare_except
- PROOF-4 (RULE-4): Run static_checks on a file with logic mirroring; verify status=fail check=logic_mirroring
- PROOF-5 (RULE-5): Run static_checks with --spec-path on a file mocking the rule's function; verify status=fail check=mock_target_match
- PROOF-6 (RULE-6): Run static_checks on any file; verify JSON output has proofs array with required fields
- PROOF-7 (RULE-7): Run static_checks on a clean file and verify exit 0; run on a flawed file and verify exit 0 with status=fail in JSON output
- PROOF-8 (RULE-8): Create spec with only grep/existence rules; call check_spec_coverage; verify structural_only_spec is true and structural_proofs list contains all rules
- PROOF-9 (RULE-9): Create spec with behavioral rules (returns, rejects); call check_spec_coverage; verify structural_only_spec is false and behavioral_proofs list contains behavioral rules
- PROOF-10 (RULE-10): Call compute_proof_hash with same inputs twice and verify identical 16-char hex output; call with different inputs and verify different hash
- PROOF-11 (RULE-11): Call read_audit_cache on a nonexistent path and verify empty dict; write valid JSON to the cache path and verify it parses correctly
- PROOF-12 (RULE-12): Call write_audit_cache, then read the file back and verify contents match the written dict
- PROOF-13 (RULE-13): Create shell test with if/else purlin_proof pair; run static_checks; verify status=pass (not flagged). Also verify a bare hardcoded pass without if/else is still caught
- PROOF-14 (RULE-14): Run static_checks on file with assert True; verify literal=true. Run on file with assert x is not None; verify literal=false
- PROOF-15 (RULE-15): Create proof JSON with two entries sharing PROOF-1 but targeting RULE-1 and RULE-2; call check_proof_file; verify result contains check='proof_id_collision' with both rules listed. Test with proof JSON from multiple language contexts (Python pytest, JavaScript Jest, Shell, C, PHP, SQL, TypeScript) to verify language-agnostic detection
- PROOF-16 (RULE-16): Create proof JSON with entry targeting RULE-99 on a spec with only RULE-1 through RULE-3; call check_proof_file with spec_path; verify result contains check='proof_rule_orphan'. Test with proof JSON from multiple language contexts to verify language-agnostic detection
