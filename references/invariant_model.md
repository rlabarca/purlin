# Invariant Model Reference

> Referenced by `purlin:invariant`, `purlin:build`, `purlin:spec`, `purlin:spec-code-audit`, and PURLIN_BASE.md mode guard.

## What Is an Invariant?

An invariant is an externally-sourced, locally-immutable anchor node. It originates from an external git repo or Figma and cannot be modified by the project team. Changes come only from the external source via `purlin:invariant sync`.

Invariants extend the anchor node system. They participate in the dependency graph, trigger cascade resets, and are validated by the scan — just like regular anchors. The difference: regular anchors are locally authored and editable; invariants are externally governed and immutable.

## Identification

All invariant files use the `i_` prefix: `features/_invariants/i_<type>_<name>.md`.

Valid type prefixes after `i_`: `arch_`, `design_`, `policy_`, `ops_`, `prodbrief_`.

Detection: `filename.startswith('i_')`. Strip `i_` to get the anchor type prefix.

## Scope: Global vs Scoped

Each invariant declares `> Scope: global` or `> Scope: scoped`.

**Global** invariants auto-apply to every non-anchor feature without requiring `> Prerequisite:` declarations. They appear in `dependency_graph.json` under the `global_invariants` key, not as graph edges.

**Scoped** invariants require explicit `> Prerequisite:` links from features, identical to regular anchors.

Tools that need the full constraint set for a feature combine: explicit prerequisites (direct + transitive) + all global invariants.

## Immutability

No agent mode (Engineer, PM, QA) can write to `features/_invariants/i_*.md` files. The mode guard blocks all write attempts. Changes come only via `purlin:invariant add`, `purlin:invariant add-figma`, or `purlin:invariant sync`.

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
| `purlin:build` Step 0 | FORBIDDEN pattern grep (combined regex per scope glob) | Yes — build blocked |
| `purlin:build` Step 0 | Behavioral invariant reminders | No — advisory |
| `purlin:build` Step 3 | Design token/style comparison (colors strict, spacing warned) | Colors block, spacing warn |
| `purlin:spec` commit | Global invariant reminder, scoped prerequisite suggestions | No — advisory |
| `purlin:spec-code-audit` | Dimension 14: full invariant compliance check | No — audit finding |
| `purlin:invariant audit` | Project-wide invariant adherence report | No — report |

## Design Invariant Tiers

| Tier | Source | File | Assets? |
|------|--------|------|---------|
| Git markdown | External git repo | `i_design_*.md` (full content) | No — markdown only |
| Figma | Figma document | `i_design_*.md` (thin pointer) | No — Figma is authority |
| Local | Project team | `design_*.md` (regular anchor) | Yes — images, PDFs, web URLs |

Only the first two tiers are invariants. Local design anchors with asset references are regular anchors.

## Figma Design Data

Figma invariant pointers capture three categories of data from Figma MCP during `add-figma` and `sync`:

- **Design Variables** (from `get_variable_defs`) — variable names and types grouped by collection. Stored in `## Design Variables`. This is the token vocabulary the design system defines. Used by `purlin:spec` for Token Map auto-seeding and by `purlin:design-audit` for drift detection.
- **Code Connect** (from `get_design_context`, optional) — presence indicator for component-to-code mappings. Stored in `## Code Connect` when Code Connect is configured in the Figma org. Used by `purlin:spec` to auto-populate the `code_connect` key in `brief.json`.
- **Annotations** (from `get_design_context`) — behavioral notes, interaction descriptions, edge cases. Stored in `## Annotations`. **Advisory, not binding** — they inform PM spec writing like user stories in a prodbrief. PM decides which to adopt, adapt, or skip.

## Design Enforcement Weight

| Aspect | Weight |
|--------|--------|
| Colors / design tokens | Strict — hardcoded hex treated as FORBIDDEN |
| Typography | Strict — measurable from brief.json |
| Spacing / layout | Moderate — warned, not blocked |
| Annotations | Advisory — informs spec only |

## Scan State

Invariant tamper detection hashes and validation results are stored within `.purlin/cache/scan.json` alongside other scan data. Invalidated by SHA-256 comparison — since invariant files only change via explicit sync, cache hit rate approaches 100%.

## Per-Type Specifications

Each invariant type has a canonical spec defining its purpose, required sections, enforcement, and examples:

| Type | Spec | Use case |
|------|------|----------|
| `i_arch_*` | [Architecture Invariant Spec](invariant_type_arch.md) | API standards, coding patterns, service boundaries |
| `i_design_*` | [Design Invariant Spec](invariant_type_design.md) | Figma design systems, visual standards |
| `i_policy_*` | [Policy Invariant Spec](invariant_type_policy.md) | Security, compliance, governance rules |
| `i_ops_*` | [Operational Invariant Spec](invariant_type_ops.md) | Observability, deployment, infrastructure |
| `i_prodbrief_*` | [Product Brief Invariant Spec](invariant_type_prodbrief.md) | Product goals, user stories, KPIs |

## Format Reference

See [Invariant Format Reference](invariant_format.md) for the shared file format, metadata fields, templates, and versioning rules.
