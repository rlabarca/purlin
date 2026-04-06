# Feature: sync_status

> Requires: schema_spec_format, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json, glob, re, hashlib
> Description: Rule coverage reporting tool. Scans specs and proof files, computes per-feature coverage including own, required, and global anchor rules. Reports actionable directives and computes verification hashes.

## Rules

- RULE-1: Scans `specs/**/*.md` for RULE-N lines, reads `*.proofs-*.json`, and reports per-feature coverage including own rules, required rules (from `> Requires:`), and global anchor rules, with actionable directives
- RULE-2: Status is determined by proof coverage: VERIFIED (all rules proved + passing + non-stale receipt exists), PASSING (all rules proved + passing + no current receipt), PARTIAL (some but not all rules proved, none failing), FAILING (any proof has status FAIL), UNTESTED (zero proofs). Partial coverage never earns PASSING — every rule must have a passing proof
- RULE-3: Warns about unnumbered lines under `## Rules` and missing `## Rules` sections
- RULE-4: Required rules from `> Requires:` specs count toward a feature's coverage total (X/total) with `(required)` label; proofs are looked up under the source spec's feature name
- RULE-5: Detects manual proof staleness by checking if scope files have commits newer than the stamp's commit SHA
- RULE-6: `vhash` is computed as `sha256(sorted rule IDs including prefixed required/global keys + "|" + sorted proof ID:status pairs for all relevant proofs)[:8]`
- RULE-7: All proofs count equally toward coverage regardless of proof type (grep-based, behavioral, etc.). Proof quality (STRONG/WEAK/HOLLOW) is assessed by the auditor, not the coverage system
- RULE-8: Detects `> Global: true` metadata on anchor specs and sets the `is_global` flag
- RULE-9: Global anchor rules auto-apply to all non-anchor feature specs without needing `> Requires:`; they appear in coverage with `(global)` label
- RULE-10: Displays rule labels: `(own)` for the feature's own rules, `(required)` for `> Requires:` rules, `(global)` for global anchor rules
- RULE-11: Shows a scope overlap advisory when an anchor's `> Scope:` overlaps a feature's scope but is not in `> Requires:`
- RULE-12: Warns when a `> Requires:` target does not match any known spec name
- RULE-13: Warns when a spec has manual proofs but no `> Scope:` metadata
- RULE-14: Prefers proof files adjacent to their spec over proof files in the specs/ root directory
- RULE-15: Explains receipt staleness cause: distinguishes own rule changes from required/global anchor rule changes
- RULE-16: Warns when `specs/` contains uncommitted changes to `.md` or `.proofs-*.json` files, listing the affected files and recommending a commit before drift or verify
- RULE-17: All proofs are displayed uniformly — grep-based and behavioral proofs both show PASS/FAIL status with no visual distinction in coverage reporting
- RULE-18: sync_status output begins with a summary table showing feature name, coverage fraction, and status (VERIFIED/PASSING/FAILING/PARTIAL/UNTESTED) for all features, sorted by status priority (FAILING, PARTIAL, PASSING, VERIFIED, UNTESTED)
- RULE-19: sync_status appends an integrity summary after the features VERIFIED line showing the integrity percentage and relative time since last purlin:audit, sourced from the audit cache; when no cache exists, shows a prompt to run purlin:audit
- RULE-20: Reports UNTESTED when a feature has zero behavioral proofs — this replaces the em-dash display for features with no proofs
- RULE-21: Reports PARTIAL (not PASSING) when a feature has some rules proved and passing but not all rules are covered — partial coverage never earns PASSING status
- RULE-22: Anchor detail shows Source URL, Path (if present), and Pinned value (SHA truncated to 7 chars) for anchors with `> Source:` metadata
- RULE-23: Shows unpinned warning for anchors with `> Source:` but no `> Pinned:`
- RULE-24: report-data.js feature entries include `pinned` and `source_path` fields when the anchor spec has `> Pinned:` and `> Path:` metadata
- RULE-25: Shows "consider re-auditing" when the audit cache is older than 24 hours
- RULE-26: report-data.js includes audit_summary with integrity, assessment counts, last_audit, last_audit_relative, and stale fields when cache exists; audit_summary is null when no cache exists
- RULE-27: report-data.js per-feature audit data is populated from cache entries matching the feature name
- RULE-28: Cache entries without a feature field are excluded from per-feature audit data but counted in project-wide summary
- RULE-29: Per-feature integrity = (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) — measures proof quality only; NO_PROOF rules do not affect the integrity denominator
- RULE-30: Per-feature integrity counts only proofs cached under that feature name — required/global anchor proofs are counted under the anchor's own feature, not the consuming feature
- RULE-31: Global integrity (project-wide) = (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) across all features — NO_PROOF rules do not affect the denominator
- RULE-32: sync_status CLI integrity percentage matches the audit_summary.integrity value in report-data.js
- RULE-33: The integrity formula `(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)` is consistent across `references/audit_criteria.md`, `skills/audit/SKILL.md`, and this spec; none of these files include NO_PROOF in the integrity formula denominator
- RULE-34: Integrity is computed by exactly one function (`_compute_integrity`) — both `_read_audit_summary` and `_build_feature_audit` delegate to it; no other function in purlin_server.py contains the integrity formula
- RULE-35: Feature status is determined by exactly one function (`_determine_status`) — all call sites in purlin_server.py delegate to it; no other function contains the status determination logic
- RULE-36: `_scan_specs` parses `> Stack:` metadata from spec files and includes it in feature info; report-data.js includes `stack` field when present
- RULE-37: Warns when a non-anchor, non-instruction feature has fewer than 5 or more than 10 own rules (advisory only — does not block PASSING/VERIFIED status)

## Proof

- PROOF-1 (RULE-1): Create a spec with rules plus a required anchor; run sync_status; verify coverage includes own and required rules with directives @integration
- PROOF-2 (RULE-2): Create a spec with all behavioral rules proved but no receipt; verify "PASSING" and vhash in output @integration
- PROOF-3 (RULE-3): Create a spec with unnumbered rule; verify WARNING in output @integration
- PROOF-4 (RULE-4): Create spec A with RULE-1 and spec B requiring A; verify B's total includes A's rule with (required) label @integration
- PROOF-5 (RULE-5): Create a spec with manual stamp at old SHA and modified scope file; verify MANUAL PROOF STALE @integration
- PROOF-6 (RULE-6): Compute vhash with prefixed required key; verify it includes the prefix and differs from hash without it
- PROOF-7 (RULE-7): Create a spec with all grep-based proofs; verify structural checks are reported separately and feature is not VERIFIED @integration
- PROOF-8 (RULE-8): Create an anchor with `> Global: true`; verify is_global flag in scan result @integration
- PROOF-9 (RULE-9): Create a global anchor and a feature with no Requires; verify global rule appears with (global) label @integration
- PROOF-10 (RULE-10): Create a feature requiring an anchor; verify (own) and (required) labels @integration
- PROOF-11 (RULE-11): Create an anchor with overlapping scope but no Requires; verify scope overlap advisory @integration
- PROOF-12 (RULE-12): Create a feature spec with `> Requires: does_not_exist`; run sync_status; verify warning about unresolved requires target @integration
- PROOF-13 (RULE-13): Create a spec with manual proof but no `> Scope:`; verify warning about staleness detection; create another with `> Scope:` and verify no warning @integration
- PROOF-14 (RULE-14): Create a proof file at specs/ root and a matching proof in a subdirectory next to its spec; run sync_status; verify the subdirectory proof is used @integration
- PROOF-15 (RULE-15): Create a feature requiring an anchor; verify and write receipt; add a rule to the anchor; run sync_status; verify output explains staleness is from the anchor change @integration
- PROOF-16 (RULE-16): Create a temp git repo with a committed spec; modify the spec without committing; run sync_status; verify warning appears with filename; commit the change; run sync_status again; verify no warning @integration
- PROOF-17 (RULE-17): Create a spec with structural-only proofs; verify output shows structural checks with "not counted" label and summary line @integration
- PROOF-18 (RULE-18): Create 3 features (one VERIFIED, one PARTIAL, one with no proofs); run sync_status; verify output starts with summary table, correct ready count, and detail follows @integration
- PROOF-19 (RULE-19): Create a temp project with an audit cache containing STRONG and WEAK entries with timestamps; run sync_status; verify output contains "Integrity: NN%" and "last purlin:audit:" with relative time; delete the cache; run sync_status; verify output contains "No audit data" @integration
- PROOF-20 (RULE-20): Create a spec with 2 behavioral rules but zero proof entries; run sync_status; verify status is "UNTESTED" in the summary table @integration
- PROOF-21 (RULE-21): Create a spec with 3 behavioral rules; write proof file with 2 passing proofs covering RULE-1 and RULE-2 only; run sync_status; verify status is "PARTIAL" not "PASSING" despite both proofs passing @integration
- PROOF-22 (RULE-4): e2e: Create anchor (2 rules), global anchor (1 rule), feature (2 own + Requires); run sync_status; verify 0/5 total @e2e
- PROOF-23 (RULE-10): e2e: Run sync_status on feature with required and global rules; verify (own), (required), (global) labels on rule lines @e2e
- PROOF-24 (RULE-21): e2e: Add proofs for feature's 2 own rules only; run sync_status; verify 2/5 and not VERIFIED @e2e
- PROOF-25 (RULE-2): e2e: Add proofs for all 5 rules (own + required + global); run sync_status; verify 5/5 and PASSING @e2e
- PROOF-26 (RULE-5): e2e: Create spec with @manual stamp at current HEAD; verify PASS with verified date @e2e
- PROOF-27 (RULE-5): e2e: Edit scope file and commit; verify MANUAL PROOF STALE with re-verify directive @e2e
- PROOF-28 (RULE-5): e2e: Re-stamp with new HEAD SHA; verify PASS again @e2e
- PROOF-29 (RULE-6): e2e: Compute vhash and write receipt; verify receipt has correct vhash, commit, rules, proofs @e2e
- PROOF-30 (RULE-6): e2e: Recompute vhash with no changes; verify matches receipt on disk @e2e
- PROOF-31 (RULE-15): e2e: Add rule to spec; recompute vhash; verify mismatch with stale receipt @e2e
- PROOF-32 (RULE-6): e2e: Add proof for new rule; write new receipt; verify different vhash and audit matches @e2e
- PROOF-33 (RULE-2): e2e: Create behavioral and structural-only specs with proofs; verify both PASSING and check_spec_coverage classification @e2e
- PROOF-34 (RULE-1): e2e: Create anchor with Source/Pinned/Path metadata; run _scan_specs; verify pinned and source_path extracted @e2e
- PROOF-35 (RULE-22): e2e: Create external anchor; run sync_status; verify Source, Path, and Pinned lines in output @e2e
- PROOF-36 (RULE-23): e2e: Create anchor with Source but no Pinned; run sync_status; verify unpinned warning @e2e
- PROOF-37 (RULE-24): e2e: Create external anchor with report=true; verify report-data.js has pinned and source_path fields @e2e
- PROOF-38 (RULE-4): e2e: Create 1 external anchor (2 rules) + feature (1 own); verify coverage 0/3 @e2e
- PROOF-39 (RULE-4): e2e: Create 2 external anchors + feature; verify coverage 0/5 @e2e
- PROOF-40 (RULE-4): e2e: Create 1 external + 1 local anchor + feature; verify coverage 0/4 @e2e
- PROOF-41 (RULE-9): e2e: Create global external anchor; verify auto-applies to all features @e2e
- PROOF-42 (RULE-2): e2e: Coverage progression UNTESTED to PARTIAL to PASSING with external anchor rules @e2e
- PROOF-43 (RULE-19): e2e: Write audit cache with STRONG/WEAK entries; run sync_status; verify Integrity percentage and relative time @e2e
- PROOF-44 (RULE-19): e2e: No audit cache; run sync_status; verify "No audit data" message @e2e
- PROOF-45 (RULE-25): e2e: Write cache with timestamps from 3 days ago; verify "consider re-auditing" @e2e
- PROOF-46 (RULE-26): e2e: Write cache with report=true; parse report-data.js; verify audit_summary fields @e2e
- PROOF-47 (RULE-26): e2e: No cache with report=true; verify report-data.js audit_summary is null @e2e
- PROOF-48 (RULE-27): e2e: Write cache for feature login; verify per-feature audit data with correct integrity and findings @e2e
- PROOF-49 (RULE-28): e2e: Write cache with/without feature field; verify per-feature excludes no-feature entries; verify project-wide counts both @e2e
- PROOF-50 (RULE-19): e2e: Write cache then delete; verify sync_status reverts to no-audit state @e2e
- PROOF-51 (RULE-29): e2e: Feature with 5 rules, 3 proved (2 STRONG, 1 WEAK); verify integrity = 2/3 = 67% (quality only, NO_PROOF excluded) @e2e
- PROOF-52 (RULE-30): e2e: Feature with 2 own STRONG rules requiring anchor with 3 rules; verify integrity = 2/2 = 100% (anchor proofs counted under anchor) @e2e
- PROOF-53 (RULE-31): e2e: Two features each with 1 NO_PROOF rule; write 2 STRONG each; verify global integrity = 4/4 = 100% (NO_PROOF excluded) @e2e
- PROOF-54 (RULE-29): e2e: Feature with 4 rules, 2 STRONG proofs + 2 NO_PROOF; verify integrity = 100% not 50% @e2e
- PROOF-55 (RULE-32): e2e: Write cache; run sync_status with report=true; verify CLI integrity percentage matches report-data.js audit_summary.integrity @e2e
- PROOF-56 (RULE-33): Grep `references/audit_criteria.md`, `skills/audit/SKILL.md`, and `specs/mcp/sync_status.md` for the integrity formula; verify all three contain `(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)` and none include NO_PROOF in the integrity denominator
- PROOF-57 (RULE-32): e2e: Create isolated project with 5-rule feature, 3 proved (1 STRONG, 1 WEAK, 1 HOLLOW) + 2 NO_PROOF; run sync_status with report=true; verify CLI, dashboard, and computed integrity all equal 33% (NO_PROOF excluded from denominator) @e2e
- PROOF-58 (RULE-34): Grep purlin_server.py for the integrity computation pattern; verify `_compute_integrity` is the only function containing the formula and that both `_read_audit_summary` and `_build_feature_audit` call it
- PROOF-59 (RULE-35): Grep purlin_server.py for the status determination pattern; verify `_determine_status` is the only function containing the if/elif chain and that all three call sites delegate to it
- PROOF-60 (RULE-34): e2e: Create isolated project with 2 features, each with different audit mixes; run sync_status with report=true; verify per-feature and global integrity in CLI output match report-data.js per-feature audit.integrity and audit_summary.integrity @e2e
- PROOF-61 (RULE-35): e2e: Create isolated project with features in every status (VERIFIED, PASSING, PARTIAL, FAILING, UNTESTED); verify CLI summary table status matches report-data.js per-feature status for all five @e2e
- PROOF-62 (RULE-36): Create spec with `> Stack: python/stdlib, json`; run `_scan_specs`; verify features dict has `stack == "python/stdlib, json"`. Create spec without Stack; verify `stack is None` @integration
- PROOF-63 (RULE-37): Create feature with 3 rules; verify warning. Create feature with 12 rules; verify warning. Create anchor with 2 rules; verify NO warning. Create instruction spec with 3 rules; verify NO warning @integration
