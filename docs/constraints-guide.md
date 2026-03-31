# Constraints Guide

How anchors and invariants flow through the build process, and how Purlin enforces them.

---

## What Are Constraints?

Constraints are cross-cutting rules that govern features. They live in `features/` and are detected by filename prefix, not folder.

| Type | Source | Prefix | Location | Editable? |
|------|--------|--------|----------|-----------|
| **Anchor** | Your team | `arch_*`, `design_*`, `policy_*`, `ops_*`, `prodbrief_*` | `features/<category>/` | Yes, via `purlin:anchor` |
| **Invariant** | External (git repo, Figma) | `i_arch_*`, `i_design_*`, `i_policy_*`, etc. | `features/_invariants/` | No — sync only via `purlin:invariant sync` |

Both kinds define rules in `## Purpose` and `## <Domain> Invariants` sections. Both can declare `## FORBIDDEN Patterns` that block builds. Both cascade status resets to dependent features when edited.

For the full comparison, see [Invariants Guide](invariants-guide.md#anchors-vs-invariants).

---

## How Features Connect to Constraints

Features declare dependencies via `> Prerequisite:` metadata:

```markdown
> Prerequisite: design_visual_standards.md
> Prerequisite: arch_data_model.md
```

Prerequisites form a **directed acyclic graph (DAG)** stored in `.purlin/cache/dependency_graph.json`. The graph engine builds this during `purlin_scan`.

### Transitive Closure

If Feature A requires Anchor B, and Anchor B requires Anchor C, then Feature A is governed by **both** B and C. Purlin walks the full chain — not just direct prerequisites.

### Global Invariants

Invariants with `> Scope: global` apply to **every non-anchor feature** automatically, without prerequisite links. They appear in the dependency graph under the `global_invariants` key.

---

## The `purlin_constraints` Tool

The `purlin_constraints` MCP tool resolves all applicable constraints for a feature in a single call:

```
purlin_constraints { "feature": "my_feature" }
```

Returns:

| Field | Contents |
|-------|----------|
| `ancestors` | All prerequisite specs (transitive) |
| `anchors` | Ancestor anchors (`arch_*`, `design_*`, `policy_*`, `ops_*`, `prodbrief_*`) |
| `scoped_invariants` | Ancestor invariants (`i_*` files reached via prerequisites) |
| `global_invariants` | All global-scope invariants (apply regardless of prerequisites) |

CLI equivalent: `python3 scripts/mcp/graph_engine.py constraints <feature_stem>`

---

## Enforcement During Build

`purlin:build` Step 0 enforces constraints before any code is written:

1. **Collect** — Call `purlin_constraints` for the feature.
2. **Read** — Read every anchor, invariant, and ancestor spec returned. Ancestors in `[TODO]` status get special attention (unstable contracts).
3. **FORBIDDEN pre-scan** — Extract `## FORBIDDEN Patterns` from all constraint files. Grep feature code for violations. **Block the build** on any match.
4. **Behavioral reminders** — Surface non-FORBIDDEN constraint statements as binding guidance (not blockers).
5. **Missing links** — If an anchor's domain intersects the feature but isn't in the prerequisite tree, log `[DISCOVERY]` in the companion file.

### FORBIDDEN Pattern Example

An anchor or invariant declares:

```markdown
## FORBIDDEN Patterns

- No eval() in user-facing code (INV-3)
  - **Pattern:** `eval\(`
  - **Scope:** `tools/auth/*.py`
```

If a violation is found, the build stops:

```
INVARIANT VIOLATION -- build blocked
i_policy_security.md (INV-3): No eval() in user-facing code
Pattern: eval\(
Found: tools/auth/handler.py:42
Fix: Replace eval() with ast.literal_eval() or json.loads()
```

---

## Enforcement Across Skills

Constraints aren't just a build concern. Multiple skills interact with them:

| Skill | When | What |
|-------|------|------|
| `purlin:build` | Step 0 pre-flight | FORBIDDEN blocks build; other constraints are binding guidance |
| `purlin:spec` | Pre-commit advisory | Surfaces global invariants; suggests scoped prerequisites |
| `purlin:spec-code-audit` | Post-hoc audit | Dimension 10 (anchor drift) + Dimension 14 (invariant compliance) |
| `purlin:invariant audit` | On-demand | Full compliance report with violations, staleness, conflicts |
| `purlin:design-audit` | On-demand | Design constraint compliance, Token Map validation, brief staleness |
| `purlin:verify` | Verification | Delegates to sub-skills that check constraints in their domains |

---

## Cascade Behavior

When an anchor or invariant is updated, all dependent features reset to `[TODO]`:

- **Anchor edit** — All features with direct or transitive prerequisites reset immediately.
- **Invariant sync** — Cascade scope follows semver:
  - **MAJOR** bump (breaking) — full cascade, all dependents reset.
  - **MINOR** bump (new constraints) — cascade with warning.
  - **PATCH** bump (corrections) — no cascade, informational only.
- **Global invariant update** — All non-anchor features reset (MAJOR/MINOR).

---

## Companion File References

When implementation addresses a specific constraint, companion entries should reference it:

```markdown
**[IMPL]** Implemented correlation ID header per i_arch_api_standards.md INV-2
```

Invariant deviations escalate as **invariant conflict** (harder than spec deviation — the invariant is immutable and externally-sourced).

---

## Related Guides

- [Invariants Guide](invariants-guide.md) — Full invariant lifecycle: import, sync, audit, Figma integration.
- [Features Folder Guide](features-folder-guide.md) — How feature files and constraints are organized.
- [Spec-Code Sync Guide](spec-code-sync-guide.md) — How sync tracking detects drift.
- [File Format Specs](../references/formats/) — Canonical formats for anchors (`anchor_format.md`) and invariants (`invariant_format.md`).
