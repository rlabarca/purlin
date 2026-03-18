**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-anchor instead." and stop.

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

**Required section headings** (Critic checks): `purpose` and `invariants` (case-insensitive substring).
Note: `## 1. Overview` does NOT satisfy the `purpose` check.

## Protocol

1. Determine the correct prefix from the table above.
2. If **updating**: read the existing anchor node, identify the constraint to add or revise, apply the change, and identify all dependent features whose status will be reset to TODO.
3. If **creating**: scaffold using the template above. Replace `Policy:` with `Architecture:` or `Design:` as appropriate.
4. **Cascade awareness:** Editing an anchor node resets ALL dependent features to TODO. This triggers re-validation across the entire domain. Verify this is intended.
5. After editing, commit the change and run `tools/cdd/status.sh`. The status run resets dependents and surfaces them as Builder action items.
