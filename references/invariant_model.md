# Invariant Model Reference

> Referenced by `/pl-invariant`, `/pl-build`, `/pl-spec`, `/pl-spec-code-audit`, and PURLIN_BASE.md mode guard.

## What Is an Invariant?

An invariant is an externally-sourced, locally-immutable anchor node. It originates from an external git repo or Figma and cannot be modified by the project team. Changes come only from the external source via `/pl-invariant sync`.

Invariants extend the anchor node system. They participate in the dependency graph, trigger cascade resets, and are validated by the scan — just like regular anchors. The difference: regular anchors are locally authored and editable; invariants are externally governed and immutable.

## Identification

All invariant files use the `i_` prefix: `features/i_<type>_<name>.md`.

Valid type prefixes after `i_`: `arch_`, `design_`, `policy_`, `ops_`, `prodbrief_`.

Detection: `filename.startswith('i_')`. Strip `i_` to get the anchor type prefix.

## Scope: Global vs Scoped

Each invariant declares `> Scope: global` or `> Scope: scoped`.

**Global** invariants auto-apply to every non-anchor feature without requiring `> Prerequisite:` declarations. They appear in `dependency_graph.json` under the `global_invariants` key, not as graph edges.

**Scoped** invariants require explicit `> Prerequisite:` links from features, identical to regular anchors.

Tools that need the full constraint set for a feature combine: explicit prerequisites (direct + transitive) + all global invariants.

## Immutability

No agent mode (Engineer, PM, QA) can write to `features/i_*.md` files. The mode guard blocks all write attempts. Changes come only via `/pl-invariant add`, `/pl-invariant add-figma`, or `/pl-invariant sync`.

The scan detects tampered files via SHA-256 comparison against cached hashes.

## Cascade Behavior

Updating an invariant cascades dependent features to `[TODO]`, gated by semver:

| Version Bump | Cascade | Rationale |
|-------------|---------|-----------|
| MAJOR | Full — all dependents reset | Breaking constraint change |
| MINOR | Cascade with warning | New or strengthened constraints |
| PATCH | No cascade — informational only | Corrections and clarifications |

For global invariants, "all dependents" means every non-anchor feature in the project.

## Enforcement Points

| Where | What | Blocks? |
|-------|------|---------|
| `/pl-build` Step 0 | FORBIDDEN pattern grep (combined regex per scope glob) | Yes — build blocked |
| `/pl-build` Step 0 | Behavioral invariant reminders | No — advisory |
| `/pl-build` Step 3 | Design token/style comparison (colors strict, spacing warned) | Colors block, spacing warn |
| `/pl-spec` commit | Global invariant reminder, scoped prerequisite suggestions | No — advisory |
| `/pl-spec-code-audit` | Dimension 14: full invariant compliance check | No — audit finding |
| `purlin.invariant_audit` | Project-wide invariant adherence report | No — report |

## Design Invariant Tiers

| Tier | Source | File | Assets? |
|------|--------|------|---------|
| Git markdown | External git repo | `i_design_*.md` (full content) | No — markdown only |
| Figma | Figma document | `i_design_*.md` (thin pointer) | No — Figma is authority |
| Local | Project team | `design_*.md` (regular anchor) | Yes — images, PDFs, web URLs |

Only the first two tiers are invariants. Local design anchors with asset references are regular anchors.

## Figma Annotations

Annotations extracted from Figma are **advisory, not binding**. They are stored in the invariant pointer's `## Annotations` section and inform PM spec writing like user stories in a prodbrief. PM decides which to adopt, adapt, or skip.

## Design Enforcement Weight

| Aspect | Weight |
|--------|--------|
| Colors / design tokens | Strict — hardcoded hex treated as FORBIDDEN |
| Typography | Strict — measurable from brief.json |
| Spacing / layout | Moderate — warned, not blocked |
| Annotations | Advisory — informs spec only |

## Scan State

Invariant tamper detection hashes and validation results are stored within `.purlin/cache/scan.json` alongside other scan data. Invalidated by SHA-256 comparison — since invariant files only change via explicit sync, cache hit rate approaches 100%.

## Format Reference

See `references/invariant_format.md` for the canonical file format, templates, and versioning rules.
