# Companion: pl_invariant

## Phase 1: Foundation — Data Model & Detection

[IMPL] Created `tools/feature_templates/_invariant.md` — base invariant template with all required metadata fields and sections. Follows the same structure as `_anchor.md` but adds Format-Version, Invariant, Version, Source, Source-Path, Source-SHA, Synced-At, Scope metadata.

[IMPL] Created `instructions/references/invariant_format.md` — canonical format reference for external invariant authors. Documents all three template variants (base, prodbrief, Figma pointer), required metadata fields, required sections by type, and semver cascade rules. Carries `Format-Version: 1.0`.

[IMPL] Created `instructions/references/invariant_model.md` — model reference documenting identification (`i_` prefix), scope (global/scoped), immutability enforcement, cascade behavior (semver-gated), enforcement points, design invariant tiers, Figma annotation model, and constraint cache.

[IMPL] Updated `instructions/references/file_classification.md` — added INVARIANT classification section. No mode can write `i_*` files. Added INVARIANT row to the Quick Reference mode guard table.

[IMPL] Updated `instructions/references/knowledge_colocation.md` — extended Anchor Node Taxonomy table with `ops_*` and `prodbrief_*` prefixes. Added Invariant Anchor Nodes subsection explaining the `i_` prefix convention.

[IMPL] Updated `instructions/references/spec_authoring_guide.md` — added sections 3.5 (`ops_*`), 3.6 (`prodbrief_*`), and 3.7 (Invariant Anchors). Updated anchor authorship table with new types and `i_*` row. Renumbered existing 3.5 to 3.8.

## Phase 2: Scanner & Graph Integration

[IMPL] Created `tools/cdd/invariant.py` — core operations module. Provides `is_invariant_node()`, `strip_invariant_prefix()`, `get_anchor_type()`, `is_anchor_node()`, `extract_metadata()` (early-termination regex), `compute_content_hash()` (SHA-256), and `validate_invariant()` (metadata + section checks per anchor type including prodbrief). Filters out companion/discovery suffixes from invariant detection.

[IMPL] Updated `tools/cdd/scan.py` — extended `_ANCHOR_PREFIXES` to include `ops_` and `prodbrief_`. Added `_is_invariant_node()` and updated `_is_anchor_node()` to delegate to `invariant.py` for full prefix coverage. Added `invariant: true` flag to feature entries for `i_*` files. Updated `_check_sections()` with prodbrief-specific section detection (`User Stories`, `Success Criteria`). Updated `scan_companion_debt()` to skip all anchor types (including `ops_`, `prodbrief_`, `i_*`) using the unified `_is_anchor_node()`. Added `scan_invariant_integrity()` — computes SHA-256 per invariant, compares against cached hashes, checks for `invariant-sync(...)` commit tags for tamper detection, runs `validate_invariant()`. Added `invariants` section to `SECTION_MAP` and `run_scan()`.

[IMPL] Updated `tools/cdd/graph.py` — `parse_features()` now parses `> Scope:` and `> Invariant:` metadata, sets `invariant: true` flag (also detected by `i_` prefix). `build_features_json()` emits `invariant` and `scope` fields when present. `generate_dependency_graph()` collects global invariants (scope == "global") into a new top-level `global_invariants` key in the JSON output.

[IMPL] Created `tools/cdd/test_invariant.py` — 26 unit tests covering: invariant detection for all 5 anchor type prefixes and their `i_*` variants, prefix stripping, anchor type extraction, metadata extraction with early termination, content hash consistency and differentiation, format validation (valid arch, missing metadata, invalid scope, format version too new, prodbrief with/without required sections, Figma-sourced, non-invariant rejection).

[IMPL] Updated `tools/collab/extract_whats_different.py` — `categorize_file()` now recognizes `i_*` prefix as `anchor_node`, and added `ops_` and `prodbrief_` to anchor detection.

[IMPL] Updated `tools/test_support/harness_runner.py` — `scan_fixture_features()` skip tuple extended with `ops_`, `prodbrief_`, and `i_` prefixes.

[IMPL] Updated `tools/smoke/smoke.py` — `suggest_smoke_features()` anchor detection extended with `ops_` and `i_` prefixes for foundational constraint reasoning.

## Phase 3: Command & Enforcement

[IMPL] Created `.claude/commands/pl-invariant.md` — full skill file with all 9 subcommands: `add` (git import), `add-figma` (Figma-sourced design invariant), `sync` (pull latest from source with semver-gated cascade), `check-updates` (fast remote check via `git ls-remote`), `check-conflicts` (semantic contradiction analysis), `check-feature` (per-feature adherence with FORBIDDEN grep and coverage check), `validate` (format/metadata/section validation), `list` (tabular summary), `remove` (delete with prerequisite cleanup). Mode enforcement: write subcommands require PM mode, read-only subcommands run in any mode. Includes P1/P5 performance notes for combined regex and inverted iteration.

[IMPL] Updated `.claude/commands/pl-build.md` — extended Step 0 Pre-Flight with Invariant Preflight subsection. Collects global invariants from `dependency_graph.json` -> `global_invariants` and scoped invariants from transitive prerequisites. Runs FORBIDDEN pre-scan that greps feature code files for pattern violations and blocks the build with actionable messages (file:line evidence + fix suggestion). Surfaces behavioral invariant statements as non-blocking awareness reminders. Checks Figma brief staleness for design invariants.

[IMPL] Updated `.claude/commands/pl-spec.md` — added Invariant Advisory (Pre-Commit) section. Before committing a spec, shows applicable global invariants and suggests scoped invariant prerequisites based on domain overlap. Added `ops_*`/`i_ops_*` and `prodbrief_*`/`i_prodbrief_*` rows to the Prerequisite Checklist table. Advisory only — does not block spec commit.

[IMPL] Updated `.claude/commands/pl-anchor.md` — extended Anchor Node Types table with `ops_*.md` (Operational) and `prodbrief_*.md` (Product) prefixes including mode ownership column. Added Invariant Anchors subsection explaining `i_*` prefix immutability with redirect message for local creation attempts. Updated prefix prompt to include all 5 types. Updated scaffold instruction for prodbrief-specific sections (`## User Stories`, `## Success Criteria`). Added `i_*` prefix detection to redirect to `/pl-invariant`.

[IMPL] Updated `instructions/PURLIN_BASE.md` — added `/pl-invariant` (write subcommands) and `/pl-anchor ops_*`, `/pl-anchor prodbrief_*` to PM mode's "Activated by" list (§3.2). Added invariant immutability rule to Mode Guard (§4.3): no mode can write `features/i_*.md` files, with redirect message to `/pl-invariant sync`. Applies even in PM mode — only the `/pl-invariant` skill's add/add-figma/sync code paths write invariant files.

[IMPL] Updated `.claude/commands/pl-build.md` Step 2 — added Invariant References in Companion Entries guidance. Companion entries SHOULD reference invariant constraint IDs (e.g., `per i_arch_api_standards.md INV-2`). Invariant deviations escalate as "invariant conflict" rather than "spec deviation" since invariants are immutable and externally-sourced. Per plan Section 5.5.

## Phase 4: Figma & Design Integration

[IMPL] Updated `.claude/commands/pl-design-ingest.md` — retired per plan Section 6.1. Replaced full workflow with retirement notice showing responsibility split table (Figma -> `/pl-invariant add-figma`, briefs -> `/pl-spec`, Token Maps -> `/pl-spec`, local assets -> manual + `/pl-anchor`, staleness -> `/pl-invariant sync`, Dev Resources -> dropped). Added redirect logic that detects user intent (Figma URL, local file, reprocess keyword, no arg) and routes to the correct new command. Includes three-tier design model reference table.

[IMPL] Updated `.claude/commands/pl-design-audit.md` — extended inventory scan (step 1) to glob `features/i_design_*.md` invariant pointers and read their metadata. Added step 3.2 (invariant pointer sync status) checking Figma version via MCP and git SHA via `ls-remote`, with cascade impact reporting and brief-vs-pointer version comparison. Added step 4.1 (invariant-governed design compliance) enforcing the three-tier weight model: colors/typography strict (HIGH), spacing moderate (MEDIUM), plus FORBIDDEN pattern grep for invariant violations. Updated report table with Invariant column (CURRENT, STALE_INVARIANT, STALE_BRIEF, INVARIANT_VIOLATION, N/A). Added step 7.1 (invariant status summary table). Updated remediation (step 8) to route STALE_INVARIANT to `/pl-invariant sync` and STALE_BRIEF to `/pl-spec`.

[IMPL] Verified `/pl-invariant` Figma workflows (add-figma, sync Figma-sourced) against plan Section 6: end-to-end Figma flow (6.3), annotation model (6.4 — advisory not binding, stored in `## Annotations`), enforcement weight (6.5 — colors strict, typography strict, spacing moderate, annotations advisory), staleness detection (6.6 — covered in pl-build Step 0 and pl-design-audit step 3.2), briefs as mutable caches (6.7 — created during `/pl-spec`, not invariants). No gaps found.
