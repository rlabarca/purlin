# Implementation Notes: Release Process

*   This policy governs the release checklist tooling behavior -- it describes buildable constraints, not process rules, and is therefore valid under the Feature Scope Restriction mandate.
*   The `purlin.` namespace reservation mirrors the existing `purlin-` prefix convention used for CSS custom properties in `design_visual_standards.md`.
*   Auto-discovery (Invariant 2.5) eliminates the "config migration" problem that plagues many structured configuration systems. Consumer projects never need to manually update their config when Purlin ships new steps.
