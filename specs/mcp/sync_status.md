# Feature: sync_status

> Requires: schema_spec_format, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json, glob, re, hashlib

## What it does

Rule coverage reporting tool. Scans specs and proof files, computes per-feature coverage including own, required, and global anchor rules. Reports actionable directives and computes verification hashes.

## Rules

- RULE-1: Scans `specs/**/*.md` for RULE-N lines, reads `*.proofs-*.json`, and reports per-feature coverage including own rules, required rules (from `> Requires:`), and global anchor rules, with actionable directives
- RULE-2: Reports "PASSING" with vhash when all rules have passing behavioral proofs but no current receipt. Reports "VERIFIED" only when all proofs pass AND a non-stale verification receipt exists. Features with only structural checks get no vhash
- RULE-3: Warns about unnumbered lines under `## Rules` and missing `## Rules` sections
- RULE-4: Required rules from `> Requires:` specs count toward a feature's coverage total (X/total) with `(required)` label; proofs are looked up under the source spec's feature name
- RULE-5: Detects manual proof staleness by checking if scope files have commits newer than the stamp's commit SHA
- RULE-6: `vhash` is computed as `sha256(sorted rule IDs including prefixed required/global keys + "|" + sorted proof ID:status pairs for all relevant proofs)[:8]`
- RULE-7: Classifies proofs as structural (grep/existence checks) or behavioral (observable outcomes). Structural proofs are reported as "checks" and excluded from the proved/total count and VERIFIED determination. Only behavioral proofs count toward coverage
- RULE-8: Detects `> Global: true` metadata on anchor specs and sets the `is_global` flag
- RULE-9: Global anchor rules auto-apply to all non-anchor feature specs without needing `> Requires:`; they appear in coverage with `(global)` label
- RULE-10: Displays rule labels: `(own)` for the feature's own rules, `(required)` for `> Requires:` rules, `(global)` for global anchor rules
- RULE-11: Shows a scope overlap advisory when an anchor's `> Scope:` overlaps a feature's scope but is not in `> Requires:`
- RULE-12: Warns when a `> Requires:` target does not match any known spec name
- RULE-13: Warns when a spec has manual proofs but no `> Scope:` metadata
- RULE-14: Prefers proof files adjacent to their spec over proof files in the specs/ root directory
- RULE-15: Explains receipt staleness cause: distinguishes own rule changes from required/global anchor rule changes
- RULE-16: Warns when `specs/` contains uncommitted changes to `.md` or `.proofs-*.json` files, listing the affected files and recommending a commit before drift or verify
- RULE-17: Displays structural checks separately from behavioral proofs, with a note that they are not counted toward coverage
- RULE-18: sync_status output begins with a summary table showing feature name, coverage fraction, and status (VERIFIED/PASSING/FAIL/PARTIAL/—) for all features, sorted by status priority (FAIL, PARTIAL, PASSING, VERIFIED, —)
- RULE-19: sync_status appends an integrity summary after the features VERIFIED line showing the integrity percentage and relative time since last purlin:audit, sourced from the audit cache; when no cache exists, shows a prompt to run purlin:audit

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
