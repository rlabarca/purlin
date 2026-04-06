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
- RULE-17: Each audit cache entry contains all required fields: assessment, criterion, why, fix, feature, proof_id, rule_id, priority, cached_at
- RULE-18: clear_audit_cache atomically replaces the cache file with an empty dict {}
- RULE-19: write_audit_cache stamps every entry with the real current UTC time, overwriting any caller-provided cached_at
- RULE-20: check_spec_coverage classifies proof descriptions as structural or behavioral using the same `_classify_description` function as rule classification, returning proof_desc_count, structural_proof_desc_count, behavioral_proof_desc_count
- RULE-21: load_criteria returns built-in criteria always, appends cached additional criteria from `.purlin/cache/additional_criteria.md` if present, appends extra path if provided; no other function in static_checks.py assembles criteria text
- RULE-22: prune_audit_cache removes all cache entries whose hash key is not in the provided live_keys set, preserving entries whose key IS in live_keys with all fields intact
- RULE-23: prune_audit_cache with an empty live_keys set on a non-empty cache produces an empty cache (full sweep), and with all keys live produces an identical cache (no false pruning)
- RULE-24: write_audit_cache merges new entries into the existing cache on disk — entries from prior writes for different features are preserved, not overwritten. Entries for the same (feature, proof_id) are deduplicated by keeping the latest cached_at
- RULE-25: `_classify_description` strips backtick-enclosed content before regex matching so that code patterns like `create.*commit` do not trigger behavioral verb detection
- RULE-26: `_classify_description` checks structural patterns before behavioral patterns and defaults to behavioral when neither matches — structural false positives (exclusion) are safer than behavioral false positives (score inflation)
- RULE-27: `check_spec_coverage` returns `structural_proof_ids` and `behavioral_proof_ids` mapping each PROOF-N to its classification, enabling per-proof filtering in mixed specs
- RULE-28: `_classify_description` correctly classifies expanded structural patterns including "has...frontmatter", "contains a...section" (with intervening words), "extract...verify", "includes...instruction", and "field in frontmatter"

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
- PROOF-17 (RULE-1): e2e: Create test with assert True and a valid test; verify assert_true detected on first, pass on second @e2e
- PROOF-18 (RULE-2): e2e: Create test with no assertions; verify no_assertions detected @e2e
- PROOF-19 (RULE-4): e2e: Create test with logic mirroring (expected from same function as SUT); verify logic_mirroring detected @e2e
- PROOF-20 (RULE-7): e2e: Create structurally valid but semantically weak test; verify passes structural checks @e2e
- PROOF-21 (RULE-7): e2e: Create 3 strong tests; verify all pass structural checks with exit 0 @e2e
- PROOF-22 (RULE-6): e2e: Parse JSON output; verify proofs array has proof_id, rule_id, test_name, status, reason fields @e2e
- PROOF-23 (RULE-7): e2e: Run on clean and flawed files; verify exit 0 for both; verify flawed has status=fail in JSON @e2e
- PROOF-24 (RULE-5): e2e: Create test mocking bcrypt on rule about bcrypt; verify mock_target_match detected @e2e
- PROOF-25 (RULE-3): e2e: Create test with bare except:pass; verify bare_except detected @e2e
- PROOF-26 (RULE-8): e2e: Create structural-only and behavioral specs; verify structural_only_spec=true/false classification @e2e
- PROOF-27 (RULE-13): e2e: Create shell test with if/else purlin_proof pair; verify pass; verify bare hardcoded pass still caught @e2e
- PROOF-28 (RULE-12): e2e: Call write_audit_cache with 3 entries; verify audit_cache.json created with 3 keys @e2e
- PROOF-29 (RULE-17): e2e: Write cache; verify every entry has all required fields and cached_at is valid ISO 8601 @e2e
- PROOF-30 (RULE-11): e2e: Write cache with 3 entries for same (feature, proof_id); call _read_audit_cache_by_feature; verify dedup to 1 entry @e2e
- PROOF-31 (RULE-12): e2e: Write cache with 2 entries for same (feature, proof_id) — HOLLOW older, STRONG newer; verify only STRONG entry kept @e2e
- PROOF-32 (RULE-18): e2e: Write cache with entries; call clear_audit_cache; read back; verify empty dict @e2e
- PROOF-33 (RULE-19): e2e: Write cache with stale cached_at (midnight UTC); read back; verify cached_at is within 5 seconds of real current time @e2e
- PROOF-34 (RULE-20): Create spec with behavioral rule but structural proof description "Verify file exists"; verify structural_proof_desc_count=1. Create spec with behavioral proof "POST to /login; verify 401"; verify behavioral_proof_desc_count=1
- PROOF-35 (RULE-21): Call load_criteria with no config; verify only built-in content. Save additional file to cache; call again; verify built-in + separator + additional. Pass extra_path; verify all three present
- PROOF-36 (RULE-22): Write cache with 3 entries (keys "aaa", "bbb", "ccc"); call prune_audit_cache with live_keys={"aaa","ccc"}; read back; verify "bbb" removed, "aaa" and "ccc" preserved with all original fields intact
- PROOF-37 (RULE-23): Write cache with 3 entries; call prune_audit_cache with live_keys=set(); read back; verify empty dict. Write cache with 3 entries; call prune_audit_cache with all 3 keys as live; read back; verify all 3 entries preserved with identical content
- PROOF-38 (RULE-22): e2e: Write 5 cache entries via write_audit_cache; write 3 live keys to a temp file; call --prune-cache --live-keys-file; verify JSON output shows pruned=2, kept=3; read cache back and confirm exactly 3 entries remain @e2e
- PROOF-39 (RULE-24): Write 3 entries for feature_a via write_audit_cache; then write 2 entries for feature_b via a second call; read cache back; verify all 5 entries are present. Then write 1 updated entry for feature_a (same proof_id, newer assessment); read back; verify feature_b entries are untouched and feature_a has the updated entry
- PROOF-40 (RULE-25): Create description with behavioral verb inside backticks (`create.*commit` in grep context); call _classify_description; verify returns 'structural'. Create description with behavioral verb outside backticks; verify returns 'behavioral'
- PROOF-41 (RULE-26): Call _classify_description on description matching both structural and behavioral patterns (e.g. "Grep for patterns that trigger failures"); verify returns 'structural'. Call on description matching neither; verify returns 'behavioral'
- PROOF-42 (RULE-27): Create mixed spec with structural + behavioral proofs; call check_spec_coverage; verify structural_proof_ids contains structural PROOF-Ns and behavioral_proof_ids contains behavioral PROOF-Ns. Verify with exact skill_anchor spec as regression test
- PROOF-43 (RULE-28): Call _classify_description on each expanded pattern variant ("has YAML frontmatter", "contains a...section", "Extract...verify", "includes...instruction", "field in frontmatter"); verify all return 'structural'. Verify 10+ behavioral descriptions return 'behavioral' (no false positives)
