**Purlin mode: PM (arch_* targets activate Engineer mode)**

Purlin agent: This skill activates PM mode for design_*/policy_* anchors. For arch_* anchors, it activates Engineer mode instead.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Required Reading

Before creating or updating any anchor node, read `instructions/references/spec_authoring_guide.md` — specifically Section 3 (Anchor Node Classification Guide) — for detailed domain classification, boundary-case heuristics, and sizing guidance.

---

Given the topic provided as an argument, create or update an anchor node file in `features/`:

## Anchor Node Types

| Prefix | Domain | When to Use |
|--------|--------|-------------|
| `arch_*.md` | Technical | System architecture, API contracts, data access patterns, module boundaries, dependency rules, coding conventions |
| `design_*.md` | Design | Visual language, color systems, typography, spacing, interaction patterns, accessibility |
| `policy_*.md` | Governance | Security baselines, compliance, process protocols, coordination rules, quality gates, release criteria |

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

1. **Determine the correct prefix.** If the topic argument already starts with `arch_`, `design_`, or `policy_`, use that prefix. If it does NOT match any recognized prefix, prompt the user:
   ```
   What type of anchor?
     1. Technical (arch_<topic>)    — architecture, APIs, data patterns, conventions
     2. Design (design_<topic>)     — visual language, spacing, interaction patterns
     3. Policy (policy_<topic>)     — security, compliance, process rules, quality gates
   ```
   Wait for the user's choice before proceeding. Do not default to any type.
2. If **updating**: read the existing anchor node, identify the constraint to add or revise, apply the change, and identify all dependent features whose status will be reset to TODO.
3. If **creating**: scaffold using the template above. Replace `Policy:` with `Architecture:` or `Design:` as appropriate.
4. **Cascade awareness:** Editing an anchor node resets ALL dependent features to TODO. This triggers re-validation across the entire domain. Verify this is intended.
5. After editing, commit the change and run `${TOOLS_ROOT}/cdd/scan.sh`. The scan resets dependents and surfaces them as Engineer action items.
