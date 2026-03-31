# Implementation Notes: Purlin Scan Engine

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (silent on per-feature timestamp filtering) | Exemption index stores (timestamp, message) tuples and filters per-feature by status_ts | DISCOVERY | ACKNOWLEDGED |
| `--only` sections skip computation | `run_scan(only=set)` conditionally calls each scan function; `smoke` implicitly computes features | DISCOVERY | ACKNOWLEDGED |
| Tombstones excluded by default | `_filter_tombstones()` applied to output; cache always includes tombstones | DISCOVERY | ACKNOWLEDGED |

## [DISCOVERY] [ACKNOWLEDGED] Per-feature exemption timestamp filtering (2026-03-25)

The exemption index (`_build_exemption_index`) originally stored only commit
messages and used `--since={min_ts}` where `min_ts` was the **global** earliest
status commit across all features. This meant the exemption check in
`_check_spec_modified_after_completion` saw commits that predated a specific
feature's completion — e.g., the original `arch: author feature specs` commit
appeared alongside the `[Spec-FMT]`-tagged recategorize commit, causing false
positives on 30 features.

**Fix:** The index now stores `(timestamp, message)` tuples. The check filters
entries to only those with `ts > status_ts` for the specific feature, so commits
before completion are correctly ignored.

## [DISCOVERY] [ACKNOWLEDGED] Smoke candidate detection added to scan output (2026-03-26)

The scan now includes a `smoke_candidates` field that surfaces completed features
with 3+ dependents that aren't already smoke-classified. Implementation reuses
`suggest_smoke_features()` from `scripts/smoke/smoke.py` and applies two additional
filters: lifecycle must be COMPLETE, and dependents must be >= 3. This is the
scan-level signal formerly described in purlin_smoke.md (retired; smoke management now in `purlin:regression promote/suggest`).

## [DISCOVERY] [ACKNOWLEDGED] Focused output and tombstone exclusion flags (2026-03-26)

**`--only <sections>`:** Accepts comma-separated section names mapped via
`SECTION_MAP` dict. `run_scan(only=set)` conditionally calls each scan function.
`smoke` implicitly triggers `scan_features()` internally since smoke detection
depends on the features list, but features are not included in output unless
explicitly requested. `--only` scans skip cache writes to avoid partial results
overwriting complete caches.

**`--tombstones`:** `_filter_tombstones()` removes tombstone entries from the
features array in output. Applied after both fresh scan and cache read paths.
Cache always stores full data including tombstones so `--cached --tombstones`
works without re-scanning. Argument parsing uses simple `sys.argv` scanning
(no argparse) to match existing style.

### Audit Finding -- 2026-03-29 (3 issues)

[DISCOVERY] Dependency graph stale: 3 features have prerequisites declared in spec headers but missing from dependency_graph.json. agent_launchers_common missing [models_configuration.md, config_layering.md]; models_configuration missing [instructions/PURLIN_BASE.md]; project_init missing [instructions/PURLIN_BASE.md].
**Source:** purlin:spec-code-audit
**Severity:** MEDIUM
**Details:** Graph generation does not capture all `> Prerequisite:` declarations. scan.json correctly reads these from spec headers but dependency_graph.json omits them. May be caused by graph generator filtering out certain prerequisite targets (e.g., instruction files).
**Suggested fix:** Engineer should fix graph_engine.py to include all prerequisite declarations, including references to instruction files.

[DISCOVERY] Section detection fails on numbered heading format: policy_spec_code_sync.md has `## 2. Requirements` (numbered) but scan reports `requirements: false`. The section parser likely only matches `## Requirements` (unnumbered).
**Source:** purlin:spec-code-audit
**Severity:** MEDIUM
**Details:** scan_engine.py section detection regex does not account for numbered section headings (`## N. SectionName`). This affects any spec using the numbered format.
**Suggested fix:** Engineer should update section detection regex to match both `## Requirements` and `## N. Requirements` patterns.

[DISCOVERY] Deviation acknowledgment detection false positives: scan reports 7 unacknowledged deviations but only 1 (policy_toolbox) is truly unacknowledged. The other 6 are ACKNOWLEDGED or RESOLVED in their companion files. toolbox_migration has 3 entries marked ACKNOWLEDGED in the companion but reported as unacknowledged by scan. plugin_migration has a RESOLVED discovery reported as unacknowledged. purlin_invariant has an [IMPL] entry misidentified as a discovery.
**Source:** purlin:spec-code-audit
**Severity:** MEDIUM
**Details:** The `scan_unacknowledged_deviations()` function does not check for [ACKNOWLEDGED] or [RESOLVED] markers adjacent to deviation tags. It may be doing line-level matching without context.
**Suggested fix:** Engineer should update acknowledgment detection to check for [ACKNOWLEDGED], [RESOLVED], or "Acknowledged" markers in the same entry block as the deviation tag.
