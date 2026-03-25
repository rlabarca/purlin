# Knowledge Colocation

> Referenced by PURLIN_BASE.md Section 7 and by build/verify skills.

## Principle

We do not use a global implementation log. Tribal knowledge, technical "gotchas," and lessons learned are stored alongside each feature specification in companion files.

## Anchor Node Taxonomy

The dependency graph uses three types of anchor nodes, distinguished by filename prefix. All three function identically in the dependency system — they cascade status resets to dependent features. The distinction is semantic.

| Prefix | Domain | Owner |
|--------|--------|-------|
| `arch_*.md` | Technical constraints — architecture, data flow, dependency rules, code patterns | Engineer |
| `design_*.md` | Design constraints — visual language, typography, spacing, interaction patterns | PM |
| `policy_*.md` | Governance rules — process policies, security baselines, compliance requirements | PM |

Every feature MUST anchor to relevant node(s) via `> Prerequisite:` links.

## Cross-Cutting Standards Pattern

When a project has cross-cutting standards that constrain multiple features, use a three-tier structure:

1. **Anchor Node** — Defines the constraints and invariants for the domain.
2. **Foundation Feature** — Implements the shared infrastructure that enforces the anchor's constraints. Has a `> Prerequisite:` link to its anchor node.
3. **Consumer Features** — Declare `> Prerequisite:` links to both the anchor node and the foundation feature.

Editing an anchor node file resets all dependent features to `[TODO]`, triggering re-validation across the entire domain.

## Companion Files

Implementation knowledge in `features/<name>.impl.md`. Separate from feature specs.

- **Standalone:** Companion files are standalone — feature files do NOT reference or link to them. The naming convention provides discoverability.
- **Not a feature file:** Companion files do not appear in the dependency graph and are not tracked by the CDD lifecycle.
- **Status reset exemption:** Edits to `<name>.impl.md` do NOT reset the parent feature's lifecycle status.
- **Owner:** Engineer (see `references/file_classification.md`)

For the Active Deviations table format and decision hierarchy, see `references/active_deviations.md`.

## Discovery Sidecars

User testing discoveries in `features/<name>.discoveries.md`. QA owns lifecycle. Any mode can record new OPEN entries.

- **Not a feature file:** Same exclusion rules as companion files.
- **Status reset exemption:** Edits to `<name>.discoveries.md` do NOT reset lifecycle status.
- **Queue hygiene:** An empty or absent file means the feature has no open discoveries.

### Discovery Types

| Type | Meaning |
|------|---------|
| `[BUG]` | Behavior contradicts an existing scenario |
| `[DISCOVERY]` | Behavior exists but no scenario covers it |
| `[INTENT_DRIFT]` | Behavior matches spec literally but misses actual intent |
| `[SPEC_DISPUTE]` | User disagrees with a scenario's expected behavior |

### Discovery Lifecycle

`OPEN → SPEC_UPDATED → RESOLVED → PRUNED`

Use `/pl-discovery` for the full recording and lifecycle protocol.
