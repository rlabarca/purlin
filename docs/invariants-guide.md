# Invariants Guide

Invariants are externally-sourced rules that your project must follow. They come from outside your project — an architecture team's git repo, a CISO's security standards, or a Figma design system — and they're enforced automatically across all your features.

The key idea: **invariants can't be edited locally.** You import them, you sync them when the source changes, and Purlin enforces them. If you disagree with a constraint, you talk to whoever owns the source.

---

## When to Use Invariants

- Your org has a shared API standard or coding guidelines in a separate repo
- A design system in Figma defines your colors, typography, and component rules
- Security or compliance mandates need to be enforced across all features
- Product briefs set goals that every feature should contribute toward

If you just need local project standards, use regular [anchor nodes](pm-agent-guide.md) (`design_*.md`, `arch_*.md`, `policy_*.md`) instead. Invariants are for rules that come from *outside* the project.

---

## Anchors vs Invariants

Anchors and invariants serve the same role — they define constraints that features must follow. The difference is the source:

| | Anchor | Invariant |
|---|---|---|
| Source | Locally authored by your team | Externally sourced (git repo, Figma) |
| Editable | Yes (by mode owner) | No (sync only via `purlin:invariant sync`) |
| Prefix | `design_*`, `arch_*`, `policy_*`, `ops_*`, `prodbrief_*` | `i_design_*`, `i_arch_*`, `i_policy_*`, etc. |
| Storage | `features/<category>/` | `features/_invariants/` |

**Never have both for the same concern.** If your design system comes from Figma, use `i_design_system.md` — don't also create a `design_system.md` anchor. If your API standards are locally authored, use `arch_api_standards.md` — don't import them as an invariant.

**When you'd have both in the same domain:** Only when they cover *different* concerns. For example:
- `design_visual_standards.md` — locally authored CSS tokens and typography (anchor)
- `i_design_feedback_form.md` — Figma mockup for one feature (scoped invariant)

These aren't duplicates. One is a project-wide standard authored by your team, the other is an imported design for a specific UI. A feature might prerequisite both:

```markdown
> Prerequisite: design_visual_standards.md
> Prerequisite: features/_invariants/i_design_feedback_form.md
```

### Decision guide

| Situation | Use |
|---|---|
| Your team writes the standard | Anchor (`design_*`, `arch_*`, `policy_*`) |
| Standard comes from an external repo | Invariant (`i_arch_*`, `i_policy_*`) |
| Design comes from Figma | Invariant (`i_design_*`) |
| Product brief from leadership | Invariant (`i_prodbrief_*`) |
| Local coding conventions | Anchor (`arch_*`) |
| Compliance rules from legal/security | Invariant (`i_policy_*`) |

---

## Quick Start

### Import from a Git Repo

In PM mode:

```
purlin:invariant add https://github.com/your-org/standards features/arch_api_standards.md
```

This clones the repo, copies the file into `features/_invariants/` with an `i_` prefix (e.g., `i_arch_api_standards.md`), injects sync metadata, and integrates it into the dependency graph.

### Import from Figma

**Prerequisites:**
1. Add the Figma MCP server: `claude mcp add --transport http figma https://mcp.figma.com/mcp`
2. Restart the session
3. Authenticate: run `/mcp`, select Figma, and complete OAuth in the browser

In PM mode:

```
purlin:invariant add-figma https://figma.com/file/abc123/Design-System
```

This creates a thin pointer file (e.g., `features/_invariants/i_design_system.md`) that references the Figma document. Purlin calls `get_metadata` (version tracking), `get_design_context` (annotations, Code Connect detection), and `get_variable_defs` (design variable vocabulary). Actual design data stays in Figma — the pointer stores only metadata, variable names/types, and advisory annotations.

---

## Global vs Scoped

| Type | Applies to | How to set up |
|------|-----------|---------------|
| **Global** | Every feature in the project | Set `> Scope: global` in the invariant — no prerequisites needed |
| **Scoped** | Only features that declare it as a prerequisite | Features must add `> Prerequisite: features/i_<name>.md` |

Global invariants are good for org-wide standards (API conventions, security rules). Scoped invariants work for domain-specific constraints (design system only applies to UI features).

---

## FORBIDDEN Patterns

Invariants can declare patterns that **block builds** if violated:

```markdown
## FORBIDDEN Patterns

- No eval() in user-facing code (INV-3)
  - **Pattern:** `eval\(`
  - **Scope:** `tools/auth/*.py`
  - **Exemption:** Only in test fixtures
```

When `purlin:build` runs, it scans your code for these patterns before starting. If a violation is found, the build stops with file and line evidence. Fix the code, then try again.

---

## How Enforcement Works

Invariants are checked at multiple points:

| When | What happens |
|------|-------------|
| `purlin:build` (Step 0) | FORBIDDEN patterns block the build. Behavioral invariants show as reminders. |
| `purlin:spec` | PM sees applicable invariants as advisory context while writing specs. |
| `purlin:spec-code-audit` | Dimension 14 checks invariant compliance — violations, coverage gaps, staleness. |
| `purlin:toolbox run invariant audit` | Full audit report: status, compliance, violations with severity and fix guidance. |

---

## Keeping Invariants Current

External sources change. To pull the latest version:

```
purlin:invariant sync i_arch_api_standards.md
```

Or sync everything at once:

```
purlin:invariant sync --all
```

**What happens on sync:**

- **MAJOR version bump** (breaking change): All dependent features reset to `[TODO]` — engineers must re-implement against new constraints.
- **MINOR version bump** (new constraints): Features reset with a warning.
- **PATCH bump** (corrections): No cascade — just updates the local file.

For Figma-sourced invariants, sync fetches the current version via `get_metadata`, compares against the stored version ID, and if changed: re-extracts annotations via `get_design_context`, re-extracts variable definitions via `get_variable_defs`, and updates Code Connect availability.

### Check Without Syncing

To see if updates are available without pulling them:

```
purlin:invariant check-updates
```

---

## Other Commands

| Command | What it does |
|---------|-------------|
| `purlin:invariant list` | Show all invariants with sync status |
| `purlin:invariant validate` | Check all invariant files for format errors |
| `purlin:invariant check-feature <name>` | Check one feature's compliance with its invariants |
| `purlin:invariant check-conflicts` | Detect contradictions between invariants |
| `purlin:invariant remove <file>` | Remove an invariant and clean up prerequisites |

All read-only commands work in any mode. Write commands (`add`, `add-figma`, `sync`, `remove`) require PM mode.

---

## Invariant File Format

Invariant files live in `features/_invariants/` with an `i_` prefix:

- `i_arch_*.md` — Architecture standards
- `i_design_*.md` — Design system rules
- `i_policy_*.md` — Security/compliance policies
- `i_ops_*.md` — Operational directives
- `i_prodbrief_*.md` — Product goals

Every invariant includes metadata at the top:

```markdown
> Format-Version: 1.1
> Invariant: true
> Version: 2.1.0
> Source: https://github.com/your-org/standards
> Source-SHA: abc123
> Synced-At: 2026-03-28T12:00:00Z
> Scope: global
```

---

## Running the Full Audit

For a comprehensive compliance report across the entire project:

```
purlin:toolbox run invariant audit
```

This produces a structured report with:
1. **Invariant Status** — Is each invariant synced or stale?
2. **Feature Compliance** — Per-feature check against all applicable invariants.
3. **Violations** — Numbered findings with severity (HIGH/MEDIUM/LOW), evidence, fix instructions, and which mode owns the fix.

---

## Canonical Specifications

### Per-Type Specs

Each invariant type has a canonical spec defining its purpose, required sections, enforcement behavior, and examples:

| Type | Spec |
|------|------|
| `i_arch_*` | [Architecture Invariant Spec](../references/invariant_type_arch.md) |
| `i_design_*` | [Design Invariant Spec](../references/invariant_type_design.md) |
| `i_policy_*` | [Policy Invariant Spec](../references/invariant_type_policy.md) |
| `i_ops_*` | [Operational Invariant Spec](../references/invariant_type_ops.md) |
| `i_prodbrief_*` | [Product Brief Invariant Spec](../references/invariant_type_prodbrief.md) |

### System References

| Document | What it defines |
|----------|----------------|
| [Invariant Model](../references/invariant_model.md) | Conceptual model — tiers, scope, cascade behavior, enforcement points |
| [Invariant Format](../references/invariant_format.md) | Shared file format — metadata fields, templates, versioning rules |
| [Invariant Template](../scripts/feature_templates/_invariant.md) | Starter template for new invariant files |

---

## Tips

- **Start with scoped invariants** if you're unsure. Global invariants reset *every* feature on a major version bump.
- **Check updates regularly** — stale invariants mean your enforcement is out of date.
- **FORBIDDEN patterns are your friend** — they catch problems before code review.
- **Invariant deviations are harder than spec deviations** — you can't change the invariant locally, so escalate to the source owner.
