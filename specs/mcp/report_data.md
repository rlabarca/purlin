# Feature: report_data

> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json
> Description: When `"report": true` is set in `.purlin/config.json`, `sync_status` writes a JS data file (`.purlin/report-data.js`) containing structured coverage, rule, and verification data for the HTML dashboard.

## Rules

- RULE-1: When config has `"report": true`, sync_status writes `.purlin/report-data.js`
- RULE-2: When config lacks `"report"` or it is false, no report file is written
- RULE-3: Report file contains `const PURLIN_DATA = {...};` that parses as valid JavaScript
- RULE-4: PURLIN_DATA.summary counts match the feature list (verified + passing + partial + failing + untested == total_features)
- RULE-5: Every feature entry has fields: name, type, is_global, proved, total, deferred, status, vhash, receipt, rules, audit, design
- RULE-6: Features with all proofs passing (status "PASSING" or "VERIFIED") have a non-null vhash; others have null vhash
- RULE-7: Features with receipt files include commit, timestamp, and stale fields in receipt
- RULE-8: Each rule entry has fields: id, description, label, source, is_deferred, is_assumed, status, proofs (array of proof objects where each proof has id, description, test_file, test_name, tier, status, audit). The proofs array contains executed proofs plus planned proofs — spec `PROOF-N` entries from the rule's source `## Proof` section with no executed result — distinguished by status "planned" with empty test_file, test_name, and audit, and tier parsed from the proof description's @tag (default unit); a proof id with an executed result for a rule is never also emitted as planned for that rule
- RULE-9: Rule status is one of PASS, FAIL, NONE, or DEFERRED
- RULE-10: Rule label is one of own, required, or global
- RULE-11: docs_url is dynamically derived from the Purlin plugin git remote
- RULE-12: Anchor features have type "anchor" and include source_url when `> Source:` is present in spec
- RULE-13: anchors_summary.total matches the count of features with type "anchor"
- RULE-14: sync_status output includes dashboard file URL when purlin-report.html exists at project root
- RULE-15: report-data.js includes an audit_summary object with integrity percentage, assessment counts, last audit timestamp, relative time, and stale boolean; null when no audit cache exists
- RULE-16: Per-feature audit data is populated from the audit cache when entries exist for that feature
- RULE-17: All proved rules count toward the coverage fraction (proved/total) regardless of proof type — grep-based and behavioral proofs are treated equally. Proof quality is assessed by the auditor (STRONG/WEAK/HOLLOW), not the coverage system
- RULE-18: Features with partial behavioral coverage have status "PARTIAL" in report data, not "PASSING", even if all existing proofs pass — PASSING requires every behavioral rule to have a passing proof
- RULE-19: Every feature entry includes a `category` field derived from the spec's parent directory under `specs/` (e.g., `specs/skills/skill_build.md` has category `skills`)
- RULE-20: Coverage invariant — for every feature in report data, status PASSING or VERIFIED implies proved == total (100% coverage fraction). No feature may show PASSING or VERIFIED with proved < total
- RULE-21: Every feature entry includes a `description` field containing the text of the spec's `> Description:` metadata field (with multi-line continuations joined), or null if the field is absent
- RULE-22: Planned proofs do not affect coverage — proved/total counts, vhash, and feature status are computed from executed proofs only; a rule whose only proofs are planned has status NONE
- RULE-23: report-data.js carries a `design_summary` object with the Proof Design percentage and per-level counts, or null when no design cache exists, so the dashboard can render the gauge alongside integrity
- RULE-24: Every entry point that writes `.purlin/report-data.js` populates BOTH gauges. `sync_status` and `generate_digest` (the pre-commit digest path) each read the audit cache and the design cache, so a digest refresh never blanks a gauge the other path had populated
- RULE-25: Per-feature design data is populated from the design cache when entries exist for that feature, computed as PROVABLE / (PROVABLE + LOOSE + UNPROVABLE) with STRUCTURAL excluded from both numerator and denominator
- RULE-26: A feature's `audit` and `design` are always objects, never null, each carrying a `state` of `measured`, `excluded` or `unmeasured`, so no quality cell can render blank. `measured` means a percentage is present. `excluded` means the feature has cached assessments but none are gradeable, so the denominator is zero: EXCLUDED proofs on the Integrity side, STRUCTURAL descriptions on the Design side. `unmeasured` means the cache holds no entries for that feature at all. Collapsing `excluded` and `unmeasured` into one null made a fully assessed feature indistinguishable from a never-audited one
- RULE-27: `audit_summary` and `design_summary` each carry a `coverage` object of `measured`, `total` and `complete`, where `total` is the project-wide population the gauge could measure: executed proofs for Integrity, declared proof descriptions for Design. A percentage is therefore never readable without its denominator, so a score over a small measured subset cannot be mistaken for a project-wide one

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
- PROOF-17 (RULE-17): Create a feature with 3 rules (2 behavioral, 1 grep-based); write passing proofs for all 3; build report data; verify proved==3, total==3, and status==PASSING — all proofs count equally @integration
- PROOF-13 (RULE-13): Parse report data, count anchor features, verify matches anchors_summary.total
- PROOF-14 (RULE-14): Place purlin-report.html at root, call sync_status with report=true, verify output contains file:// URL
- PROOF-15 (RULE-15): Create an audit cache with STRONG/WEAK entries and timestamps, regenerate report, verify audit_summary fields; delete cache, regenerate, verify audit_summary is null @integration
- PROOF-16 (RULE-16): Seed an audit cache holding 2 STRONG and 1 WEAK entry for feature `login` and nothing for feature `payments`; regenerate report data; verify `login.audit.integrity` is 67, `login.audit.strong` is 2, `login.audit.weak` is 1, and that `login.audit.findings` holds exactly one entry naming the WEAK proof id; verify `payments.audit.integrity` is null @integration
- PROOF-18 (RULE-18): Create a feature with 3 behavioral rules; write passing proofs for only 2 of them; build report data; verify feature status is "PARTIAL" not "PASSING" @integration
- PROOF-20 (RULE-20): Create multiple features — one PASSING (behavioral-only), one PASSING (mixed behavioral+structural), one VERIFIED with receipt, one PARTIAL; build report data; assert every PASSING/VERIFIED feature has proved == total and every PARTIAL feature has proved < total @integration
- PROOF-21 (RULE-21): Create a spec with `> Description: Handles user login.`; build report data; verify feature description equals "Handles user login."; create a spec with no `> Description:` field; verify description is null
- PROOF-22 (RULE-8): Create a spec whose `## Proof` section declares PROOF-1 (RULE-1) and PROOF-2 (RULE-1) `@integration`; write an executed proof result for PROOF-1 only; build report data; verify RULE-1's proofs array contains PROOF-1 with status pass and PROOF-2 with status "planned", empty test_file/test_name/audit, and tier "integration"; verify PROOF-1 does not also appear as planned @integration
- PROOF-23 (RULE-22): Create a feature with one rule whose only proof is planned (no executed result); build report data; verify proved==0, feature status is UNTESTED, vhash is null, and the rule status is NONE @integration
- PROOF-24 (RULE-23): Seed a design cache, regenerate report data, and verify `design_summary.design` matches the computed percentage and the per-level counts are present. Delete the design cache, regenerate, and verify `design_summary` is null
- PROOF-25 (RULE-24): Seed both an audit cache and a design cache in a temp project; call `generate_digest` directly (not `sync_status`); parse the written report-data.js and verify `design_summary.design` equals the computed percentage and `audit_summary.integrity` is non-null. Then call `sync_status` on the same project and verify both objects are populated there too, so neither entry point can drop a gauge on its own @e2e
- PROOF-26 (RULE-25): Seed a design cache holding 2 PROVABLE, 1 LOOSE and 3 STRUCTURAL entries for feature `login` and nothing for feature `payments`; build report data; verify `login.design.design` is 67, `login.design.provable` is 2, `login.design.loose` is 1 and `login.design.structural` is 3, proving STRUCTURAL is excluded from the denominator; verify `payments.design.design` is null @integration
- PROOF-27 (RULE-26): Build report data for three features: one with PROVABLE design entries and STRONG audit entries, one whose only entries are STRUCTURAL (design) and EXCLUDED (audit), and one with no cache entries at all; verify every feature has a non-null `audit` object and a non-null `design` object, and that their `state` values are `measured`, `excluded` and `unmeasured` respectively; assert no feature in the payload has `audit` or `design` equal to null @integration
- PROOF-28 (RULE-27): Build a project with 4 declared proof descriptions and 4 executed proofs; seed a design cache covering 2 of the descriptions and an audit cache covering 1 of the executed proofs; verify `design_summary.coverage` equals `{measured: 2, total: 4, complete: false}` and `audit_summary.coverage` equals `{measured: 1, total: 4, complete: false}`; seed the remaining entries and verify both report `measured == total` and `complete: true` @integration
