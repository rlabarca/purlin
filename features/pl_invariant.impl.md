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
