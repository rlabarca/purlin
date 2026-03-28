# Companion: pl_invariant

## Phase 1: Foundation — Data Model & Detection

[IMPL] Created `tools/feature_templates/_invariant.md` — base invariant template with all required metadata fields and sections. Follows the same structure as `_anchor.md` but adds Format-Version, Invariant, Version, Source, Source-Path, Source-SHA, Synced-At, Scope metadata.

[IMPL] Created `instructions/references/invariant_format.md` — canonical format reference for external invariant authors. Documents all three template variants (base, prodbrief, Figma pointer), required metadata fields, required sections by type, and semver cascade rules. Carries `Format-Version: 1.0`.

[IMPL] Created `instructions/references/invariant_model.md` — model reference documenting identification (`i_` prefix), scope (global/scoped), immutability enforcement, cascade behavior (semver-gated), enforcement points, design invariant tiers, Figma annotation model, and constraint cache.

[IMPL] Updated `instructions/references/file_classification.md` — added INVARIANT classification section. No mode can write `i_*` files. Added INVARIANT row to the Quick Reference mode guard table.

[IMPL] Updated `instructions/references/knowledge_colocation.md` — extended Anchor Node Taxonomy table with `ops_*` and `prodbrief_*` prefixes. Added Invariant Anchor Nodes subsection explaining the `i_` prefix convention.

[IMPL] Updated `instructions/references/spec_authoring_guide.md` — added sections 3.5 (`ops_*`), 3.6 (`prodbrief_*`), and 3.7 (Invariant Anchors). Updated anchor authorship table with new types and `i_*` row. Renumbered existing 3.5 to 3.8.
