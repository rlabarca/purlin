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

## Quick Start

### Import from a Git Repo

In PM mode:

```
purlin:invariant add https://github.com/your-org/standards features/arch_api_standards.md
```

This clones the repo, copies the file into your `features/` folder with an `i_` prefix (e.g., `i_arch_api_standards.md`), injects sync metadata, and integrates it into the dependency graph.

### Import from Figma

In PM mode (requires Figma MCP):

```
purlin:invariant add-figma https://figma.com/file/abc123/Design-System
```

This creates a thin pointer file (e.g., `i_design_system.md`) that references the Figma document. Actual design data stays in Figma — Purlin reads it via MCP when needed.

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

For Figma-sourced invariants, sync compares the Figma version ID and re-extracts annotations if the design changed.

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

Invariant files live in `features/` with an `i_` prefix. The prefix tells Purlin it's an invariant:

- `i_arch_*.md` — Architecture standards
- `i_design_*.md` — Design system rules
- `i_policy_*.md` — Security/compliance policies
- `i_ops_*.md` — Operational directives
- `i_prodbrief_*.md` — Product goals

Every invariant includes metadata at the top:

```markdown
> Format-Version: 1.0
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

## Tips

- **Start with scoped invariants** if you're unsure. Global invariants reset *every* feature on a major version bump.
- **Check updates regularly** — stale invariants mean your enforcement is out of date.
- **FORBIDDEN patterns are your friend** — they catch problems before code review.
- **Invariant deviations are harder than spec deviations** — you can't change the invariant locally, so escalate to the source owner.
