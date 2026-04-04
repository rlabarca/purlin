# Feature: report_data

> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json

## What it does

When `"report": true` is set in `.purlin/config.json`, `sync_status` writes a JS data file (`.purlin/report-data.js`) containing structured coverage, rule, and verification data for the HTML dashboard.

## Rules

- RULE-1: When config has `"report": true`, sync_status writes `.purlin/report-data.js`
- RULE-2: When config lacks `"report"` or it is false, no report file is written
- RULE-3: Report file contains `const PURLIN_DATA = {...};` that parses as valid JavaScript
- RULE-4: PURLIN_DATA.summary counts match the feature list (verified + passing + partial + failing + untested == total_features)
- RULE-5: Every feature entry has fields: name, type, is_global, proved, total, deferred, status, structural_checks, vhash, receipt, rules, audit
- RULE-6: Features with all proofs passing (status "PASSING" or "VERIFIED") have a non-null vhash; others have null vhash
- RULE-7: Features with receipt files include commit, timestamp, and stale fields in receipt
- RULE-8: Each rule entry has fields: id, description, label, source, is_deferred, is_assumed, status, proofs (array of proof objects where each proof has id, description, test_file, test_name, tier, status, audit)
- RULE-9: Rule status is one of PASS, FAIL, NO_PROOF, CHECK, CHECK_FAIL, or DEFERRED
- RULE-10: Rule label is one of own, required, or global
- RULE-11: docs_url is dynamically derived from the Purlin plugin git remote
- RULE-12: Anchor features have type "anchor" and include source_url when `> Source:` is present in spec
- RULE-13: anchors_summary.total matches the count of features with type "anchor"
- RULE-14: sync_status output includes dashboard file URL when purlin-report.html exists at project root
- RULE-15: report-data.js includes an audit_summary object with integrity percentage, assessment counts, last audit timestamp, relative time, and stale boolean; null when no audit cache exists
- RULE-16: Per-feature audit data is populated from the audit cache when entries exist for that feature
- RULE-17: Feature proved count excludes structural checks — only behavioral proofs count toward the coverage fraction
- RULE-18: Features with partial behavioral coverage have status "PARTIAL" in report data, not "PASSING", even if all existing proofs pass — PASSING requires every behavioral rule to have a passing proof
- RULE-19: Every feature entry includes a `category` field derived from the spec's parent directory under `specs/` (e.g., `specs/skills/skill_build.md` has category `skills`)

## Proof

- PROOF-1 (RULE-1): Set report=true in config, call sync_status, verify .purlin/report-data.js exists @integration
- PROOF-2 (RULE-2): Call sync_status without report config, verify no report-data.js written @integration
- PROOF-3 (RULE-3): Read report-data.js, strip JS wrapper, verify JSON parses successfully
- PROOF-4 (RULE-4): Parse report data, verify summary counts sum correctly
- PROOF-5 (RULE-5): Parse report data, verify every feature has all required fields
- PROOF-6 (RULE-6): Parse report data, verify PASSING/VERIFIED features have vhash and others don't
- PROOF-7 (RULE-7): Create a receipt file, regenerate report, verify receipt fields present
- PROOF-8 (RULE-8): Parse report data, verify every rule entry has all required fields
- PROOF-9 (RULE-9): Parse report data, verify all rule statuses are valid enum values
- PROOF-10 (RULE-10): Parse report data, verify all rule labels are valid enum values
- PROOF-11 (RULE-11): Call _get_plugin_docs_url, verify it returns a URL derived from git remote
- PROOF-12 (RULE-12): Create an anchor spec with > Source:, regenerate report, verify source_url in output
- PROOF-17 (RULE-17): Create a feature with 3 rules (2 behavioral, 1 structural grep-based); write passing proofs for all 3; build report data; verify proved==2 (not 3) and structural_checks==1 @integration
- PROOF-13 (RULE-13): Parse report data, count anchor features, verify matches anchors_summary.total
- PROOF-14 (RULE-14): Place purlin-report.html at root, call sync_status with report=true, verify output contains file:// URL
- PROOF-15 (RULE-15): Create an audit cache with STRONG/WEAK entries and timestamps, regenerate report, verify audit_summary fields; delete cache, regenerate, verify audit_summary is null @integration
- PROOF-16 (RULE-16): Create an audit cache with entries for a specific feature, regenerate report, verify that feature's audit field is populated with correct integrity and findings @integration
- PROOF-18 (RULE-18): Create a feature with 3 behavioral rules; write passing proofs for only 2 of them; build report data; verify feature status is "PARTIAL" not "PASSING" @integration
