> Format-Version: 3

# Invariant Spec Format

Invariants are read-only constraint specs sourced from external systems (git repos, Figma files). They live in `specs/_invariants/` and are protected by the gate hook.

## Location

```
specs/_invariants/i_<prefix>_<name>.md
```

## Type Prefixes

Same as anchors but with `i_` prefix:

| Prefix | Domain |
|--------|--------|
| `i_design_` | Design tokens, visual standards |
| `i_api_` | External API contracts |
| `i_security_` | Security policies |
| `i_brand_` | Brand guidelines |
| `i_platform_` | Platform requirements |
| `i_schema_` | External data schemas |
| `i_legal_` | Legal/compliance requirements |
| `i_prodbrief_` | Product brief requirements |

## Template — Git-sourced

```markdown
# Invariant: i_design_tokens

> Type: design
> Source: git@github.com:org/design-system.git
> Path: docs/tokens.md
> Pinned: abc1234def5678

## What it does

Design token constraints imported from the shared design system repository.

## Rules

- RULE-1: All colors must reference CSS custom properties from the token set
- RULE-2: Font sizes must use rem units defined in the token scale

## Proof

- PROOF-1 (RULE-1): CSS files contain no raw hex colors outside token definitions
- PROOF-2 (RULE-2): Font-size declarations use only rem values from the scale
```

## Template — Figma-sourced

```markdown
# Invariant: i_design_navigation

> Type: design
> Source: https://www.figma.com/design/ABC123/Navigation
> Pinned: 2026-03-31T12:00:00Z
> Visual-Reference: figma://ABC123/1:234

## What it does

Navigation layout and spacing constraints from the Figma design source.

## Rules

- RULE-1: Navigation bar height is 64px on desktop, 56px on mobile
- RULE-2: Menu items use 16px horizontal padding

## Proof

- PROOF-1 (RULE-1): Rendered nav element height matches spec per breakpoint
- PROOF-2 (RULE-2): Menu item padding matches design tokens
- PROOF-3 (RULE-1, RULE-2): Render component, capture screenshot, compare against specs/_invariants/screenshots/i_design_navigation.png; verify <5% pixel difference @e2e
```

## Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `> Type:` | No | Invariant type: `design`, `api`, `security`, `brand`, `platform`, `schema`, `legal`, `prodbrief` |
| `> Source:` | Yes | Git repo URL, or Figma URL |
| `> Path:` | Git only | Path within the repo to the source file |
| `> Pinned:` | Yes | Git commit SHA (git-sourced) or ISO 8601 timestamp (Figma-sourced) |
| `> Global:` | No | When `true`, this invariant's rules auto-apply to ALL non-anchor, non-invariant feature specs without needing `> Requires:`. Use for project-wide constraints like `i_security_no_eval`. |
| `> Visual-Reference:` | No | Direct pointer to the visual source for build-time reference. Figma: `figma://fileKey/nodeId`. Image: `./designs/modal.png`. HTML: `./designs/modal.html`. URL: `https://staging.app.com/modal`. |

## Sync Behavior

`purlin:invariant sync` compares `> Pinned:` to the upstream source:

- **Git:** `git ls-remote` to get HEAD SHA. If different, pull new content and update `> Pinned:`.
- **Figma:** `get_metadata` MCP call to get `lastModified`. If different, `get_design_context` to fetch new data and update `> Pinned:`.

## Write Protection

All files matching `specs/_invariants/i_*` are protected by `scripts/gate.sh`. Only `purlin:invariant sync` can write to these files by creating a temporary bypass lock at `.purlin/runtime/invariant_write_lock`.
