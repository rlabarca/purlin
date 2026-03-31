# Design Invariant Spec (`i_design_*`)

> Canonical definition for `i_design_*.md` invariant files.
> Spec-Version: 1.0

## Purpose

Design invariants enforce visual standards from an external authority — a Figma design system or a design team's git repo. Colors, typography, spacing, and component rules are defined externally and enforced locally. The project cannot edit them.

## When to Use

- Org-wide design system in Figma (brand colors, typography scale, component library)
- Shared design standards in a git repo (style guide, icon specifications)
- Any visual standard that originates outside your project

If the design is locally authored by your project team, use a `design_*.md` anchor instead. See the [Figma Guide](../docs/figma-guide.md) for the Figma-specific workflow.

## Source Tiers

| Tier | Source | File Content | Assets |
|------|--------|-------------|--------|
| Figma | Figma document | Thin pointer (metadata, variables, annotations) | No — Figma is authority |
| Git | External git repo | Full markdown content | No — markdown only |

## Required Sections

### Figma-sourced (`> Source: figma`)

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | What design system this defines |
| `## Figma Source` | Yes | Declaration that Figma governs this invariant |
| `## Design Variables` | Optional | Variable names/types from `get_variable_defs` (omit if none) |
| `## Code Connect` | Optional | Presence indicator (omit if not configured) |
| `## Annotations` | Yes | Behavioral notes from `get_design_context` (advisory) |

### Git-sourced (`> Source: <repo-url>`)

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | What visual standards this defines |
| `## <Domain> Invariants` | Yes | Numbered invariant statements |
| `## FORBIDDEN Patterns` | Optional | Regex patterns blocking hardcoded values |
| `## Verification Scenarios` | Optional | Given/When/Then for compliance |

## Required Metadata

### Figma-sourced

```markdown
> Format-Version: 1.1
> Invariant: true
> Version: <figma-version-id>
> Source: figma
> Figma-URL: <figma-file-url>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>
```

### Git-sourced

```markdown
> Format-Version: 1.1
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>
```

## Enforcement

| Aspect | Weight | What happens |
|--------|--------|--------------|
| Colors / design tokens | Strict | Hardcoded hex values treated as FORBIDDEN |
| Typography | Strict | Wrong font/weight/size flagged in audit |
| Spacing / layout | Moderate | Warned, not blocked |
| Annotations | Advisory | Informs PM spec writing only |

| Where | What | Blocks? |
|-------|------|---------|
| `purlin:build` Step 0 | FORBIDDEN pattern grep (git-sourced) | Yes |
| `purlin:build` Step 3 | Design token/style comparison | Colors block, spacing warn |
| `purlin:design-audit` | Staleness, token conflicts, visual drift | No — audit finding |
| `purlin:spec-code-audit` | Dimension 14 compliance check | No — audit finding |

## Example (Figma-sourced)

```markdown
# Design: Brand System

> Label: "Design: Brand System"
> Category: "Design"
> Format-Version: 1.1
> Invariant: true
> Version: 5234567
> Source: figma
> Figma-URL: https://figma.com/file/abc123/Brand-System
> Synced-At: 2026-03-28T12:00:00Z
> Scope: global

## Purpose

Defines ACME's brand design system — colors, typography, spacing, and component specifications. Maintained by the Design Systems team in Figma.

## Figma Source

This invariant is governed by the Figma document linked above.
Design tokens, constraints, and visual standards are defined in Figma
and cached locally in per-feature `brief.json` files during spec authoring.

## Design Variables

- **Colors:** `primary`, `secondary`, `surface`, `on-surface`, `error` (COLOR)
- **Spacing:** `spacing-xs`, `spacing-sm`, `spacing-md`, `spacing-lg` (FLOAT)
- **Typography:** `heading-lg`, `heading-md`, `body`, `caption` (STRING)

## Annotations

- Cards use 8px border radius consistently
- Primary action buttons are always `primary` color, never `secondary`
- Error states use `error` token with 0.1 opacity background
```

## Scope Guidance

Use `global` for org-wide design systems that apply to every feature with a UI. Use `scoped` for domain-specific designs (e.g., a Figma mockup for one specific screen).
