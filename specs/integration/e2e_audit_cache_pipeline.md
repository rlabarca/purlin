# Feature: e2e_audit_cache_pipeline

> Scope: scripts/audit/static_checks.py, scripts/mcp/purlin_server.py, .claude/agents/purlin-auditor.md
> Stack: shell/bash, python3

## What it does

End-to-end test of the audit → cache → status → dashboard pipeline. Verifies that audit results are written to the cache with all required fields, that sync_status reads the cache to produce the integrity summary line, that the dashboard report-data.js includes audit_summary and per-feature audit data, and that the cache correctly invalidates stale entries.

## Rules

- RULE-1: write_audit_cache writes .purlin/cache/audit_cache.json with entries keyed by proof hash
- RULE-2: Each cache entry contains all required fields: assessment, criterion, why, fix, feature, proof_id, rule_id, priority, cached_at
- RULE-3: sync_status reads the audit cache and appends an integrity summary line with percentage and relative time after the features READY line
- RULE-4: sync_status shows "No audit data — run purlin:audit" when the cache does not exist
- RULE-5: sync_status shows "consider re-auditing" when the cache is older than 24 hours
- RULE-6: report-data.js includes audit_summary with integrity, assessment counts, last_audit, last_audit_relative, and stale fields when cache exists
- RULE-7: report-data.js audit_summary is null when no cache exists
- RULE-8: report-data.js per-feature audit data is populated from cache entries matching the feature name, with correct integrity calculation and findings
- RULE-9: Cache entries without a feature field are excluded from per-feature audit data but still counted in the project-wide summary
- RULE-10: Deleting the cache file causes sync_status and report-data.js to revert to the no-audit state
- RULE-11: Per-feature integrity penalizes own behavioral rules with NO_PROOF — they count in the denominator but contribute 0 to the numerator
- RULE-12: Per-feature integrity does NOT penalize required anchor rules — only own rules with NO_PROOF affect the denominator
- RULE-13: Global integrity (project-wide) includes NO_PROOF penalties from all features combined
- RULE-14: Read-side dedup keeps only the latest cache entry per (feature, proof_id) — stale entries from prior test code do not inflate the integrity denominator
- RULE-15: Write-side pruning removes duplicate (feature, proof_id) entries on write, keeping only the entry with the latest cached_at timestamp

## Proof

- PROOF-1 (RULE-1): Create temp project with .purlin/cache/; call write_audit_cache with 3 entries; verify .purlin/cache/audit_cache.json exists and contains exactly 3 keys @e2e
- PROOF-2 (RULE-2): Write cache with entries; read back; verify every entry has assessment, criterion, why, fix, feature, proof_id, rule_id, priority, cached_at fields; verify cached_at is valid ISO 8601 @e2e
- PROOF-3 (RULE-3): Create temp git repo with spec and passing proofs; write audit cache with 2 STRONG and 1 WEAK entry with timestamps from 5 minutes ago; run sync_status; verify output contains "Integrity: 67%" and "last purlin:audit:" and "minutes ago" @e2e
- PROOF-4 (RULE-4): Create temp git repo with spec and proofs but NO audit cache; run sync_status; verify output contains "No audit data" and "purlin:audit" @e2e
- PROOF-5 (RULE-5): Create temp git repo with spec; write audit cache with cached_at timestamps from 3 days ago; run sync_status; verify output contains "consider re-auditing" @e2e
- PROOF-6 (RULE-6): Create temp project with spec, proofs, and audit cache (2 STRONG, 1 WEAK, timestamps); set report=true; run sync_status; parse report-data.js; verify audit_summary.integrity==67, audit_summary.strong==2, audit_summary.weak==1, audit_summary.stale==false, audit_summary.last_audit is not null @e2e
- PROOF-7 (RULE-7): Create temp project with spec and proofs but no audit cache; set report=true; run sync_status; parse report-data.js; verify audit_summary is null @e2e
- PROOF-8 (RULE-8): Write audit cache with 2 STRONG entries for feature "login" and 1 WEAK for feature "login"; run _build_report_data; find the "login" feature; verify audit.integrity==67, audit.strong==2, audit.weak==1, audit.findings has 1 entry with level "WEAK" @e2e
- PROOF-9 (RULE-9): Write audit cache with one entry having feature="login" and one entry missing the feature field; run _build_report_data; verify "login" feature has audit with 1 proof; verify _read_audit_summary counts both entries in the project-wide summary @e2e
- PROOF-10 (RULE-10): Create project with audit cache; run sync_status; verify integrity line present; delete the cache file; run sync_status again; verify "No audit data" and report-data.js audit_summary is null @e2e
- PROOF-11 (RULE-11): Create feature with 5 behavioral rules; write audit cache for only 3 (2 STRONG, 1 WEAK); run _build_report_data; verify per-feature integrity = 2/(3+2) = 40% where 2 is the NO_PROOF count @e2e
- PROOF-12 (RULE-12): Create feature requiring an anchor with 3 rules; feature has 2 own rules with 2 STRONG proofs; anchor rules have no proofs under the feature; verify integrity = 2/2 = 100% (anchor rules excluded from NO_PROOF penalty) @e2e
- PROOF-13 (RULE-13): Create two features: A with 1 NO_PROOF rule, B with 1 NO_PROOF rule; write cache with 2 STRONG for each; run sync_status; verify global integrity = 4/(4+2) = 67% @e2e
- PROOF-14 (RULE-14): Write cache with 3 entries for same (feature, proof_id) with different hashes and timestamps; call _read_audit_cache_by_feature; verify only 1 entry returned (the latest); call _read_audit_summary; verify behavioral_total==1 (not 3); verify _build_feature_audit computes integrity from deduped count @e2e
- PROOF-15 (RULE-15): Write cache with 2 entries for same (feature, proof_id) — one HOLLOW (older), one STRONG (newer); call write_audit_cache; read back; verify only 1 entry exists (the STRONG one); verify the HOLLOW entry's hash key is gone @e2e
