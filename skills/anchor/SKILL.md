---
name: anchor
description: This skill activates PM mode for design_*/policy_* anchors. For arch_* anchors, it activates Engineer mode instead
---

**Purlin mode: PM (arch_* targets activate Engineer mode)**

Purlin agent: This skill activates PM mode for design_*/policy_* anchors. For arch_* anchors, it activates Engineer mode instead.

---

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.

---

## Required Reading

Before creating or updating any anchor node, read `${CLAUDE_PLUGIN_ROOT}/references/spec_authoring_guide.md` — specifically Section 3 (Anchor Node Classification Guide) — for detailed domain classification, boundary-case heuristics, and sizing guidance.

---

Given the topic provided as an argument, create or update an anchor node file in `features/`:

## Anchor Node Types

| Prefix | Domain | When to Use | Mode |
|--------|--------|-------------|------|
| `arch_*.md` | Technical | System architecture, API contracts, data access patterns, module boundaries, dependency rules, coding conventions | Engineer |
| `design_*.md` | Design | Visual language, color systems, typography, spacing, interaction patterns, accessibility | PM |
| `policy_*.md` | Governance | Security baselines, compliance, process protocols, coordination rules, quality gates, release criteria | PM |
| `ops_*.md` | Operational | CI/CD, deployment, monitoring, infrastructure mandates, operational integration | PM |
| `prodbrief_*.md` | Product | Product goals, user stories, outcomes, KPIs, success criteria | PM |

### Invariant Anchors (`i_*` prefix)

Any anchor type can exist as an **invariant** by prepending `i_` to the filename: `i_arch_*`, `i_design_*`, `i_policy_*`, `i_ops_*`, `i_prodbrief_*`.

**Invariants are externally-sourced and locally immutable.** No mode (Engineer, PM, QA) can write to `features/i_*.md` files. Changes come ONLY via `purlin:invariant add`, `purlin:invariant add-figma`, or `purlin:invariant sync`.

If the user requests creating an anchor with the `i_` prefix, redirect:
```
Invariant files are imported from external sources, not created locally.
Use purlin:invariant add <repo-url> to import, or create a local anchor without the i_ prefix.
```

## Anchor Node Template

```markdown
# Policy: <Name>

> Label: "<Category>: <Name>"
> Category: "<Category>"

## Purpose

<One paragraph: what invariants or constraints this anchor node enforces and why.>

## <Domain> Invariants

### <Invariant Group Name>

- <Invariant statement>

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
```

**Required section headings** (scan checks): `purpose` and `invariants` (case-insensitive substring).
Note: `## 1. Overview` does NOT satisfy the `purpose` check.

## Protocol

1. **Determine the correct prefix.** If the topic argument starts with `i_`, redirect to `purlin:invariant` (see Invariant Anchors above). If the topic already starts with `arch_`, `design_`, `policy_`, `ops_`, or `prodbrief_`, use that prefix. If it does NOT match any recognized prefix, prompt the user:
   ```
   What type of anchor?
     1. Technical (arch_<topic>)      — architecture, APIs, data patterns, conventions
     2. Design (design_<topic>)       — visual language, spacing, interaction patterns
     3. Policy (policy_<topic>)       — security, compliance, process rules, quality gates
     4. Operational (ops_<topic>)     — CI/CD, deployment, monitoring, infrastructure
     5. Product Brief (prodbrief_<topic>) — product goals, user stories, KPIs
   ```
   Wait for the user's choice before proceeding. Do not default to any type.
2. If **updating**: read the existing anchor node, identify the constraint to add or revise, apply the change, and identify all dependent features whose status will be reset to TODO.
3. If **creating**: scaffold using the template above. Replace `Policy:` with `Architecture:`, `Design:`, `Operational:`, or `Product Brief:` as appropriate. For `prodbrief_*` anchors, use `## User Stories` and `## Success Criteria` instead of `## <Domain> Invariants`.
4. **Cascade awareness:** Editing an anchor node resets ALL dependent features to TODO. This triggers re-validation across the entire domain. Verify this is intended.
5. After editing, commit the change and run `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh`. The scan resets dependents and surfaces them as Engineer action items.
