# Invariants Guide

Invariants are read-only specs from external sources. Your project must conform to them — you can't change them locally.

## Where They Live

```
specs/_invariants/
  i_design_brand.md          # Design system tokens
  i_api_v3_contract.md       # API contract from another team
  i_security_owasp.md        # Security requirements
```

All invariant files use the `i_` prefix followed by a type prefix.

## Invariant Types

| Type | Prefix | Example |
|------|--------|---------|
| Design | `i_design_` | Colors, typography, spacing from Figma |
| API | `i_api_` | Endpoint contracts, request/response shapes |
| Security | `i_security_` | OWASP rules, encryption requirements |
| Brand | `i_brand_` | Voice, naming conventions, forbidden terms |
| Platform | `i_platform_` | App Store rules, WCAG accessibility |
| Schema | `i_schema_` | Database fields, data types, constraints |
| Legal | `i_legal_` | GDPR, data retention, consent rules |
| Product Brief | `i_prodbrief_` | User stories, UX requirements |

## Format

Same 3-section format as regular specs, plus source metadata:

```markdown
# Invariant: i_design_brand

> Type: design
> Source: git@github.com:acme/design-system.git
> Path: tokens/colors.md
> Pinned: a1b2c3d4

## What it does
Color tokens from the design system.

## Rules
- RULE-1: Primary color is #1a73e8
- RULE-2: Error color is #d93025

## Proof
- PROOF-1 (RULE-1): CSS variable --color-primary equals #1a73e8
- PROOF-2 (RULE-2): CSS variable --color-error equals #d93025
```

- **`> Source:`** — git repo URL or Figma URL
- **`> Path:`** — file path within the source repo
- **`> Pinned:`** — commit SHA (git) or lastModified timestamp (Figma). This is the version.

Full format: `references/formats/invariant_format.md`

## Write Protection

The gate hook blocks all writes to `specs/_invariants/i_*`. If you try:

```
BLOCKED: Invariant files are read-only. Use purlin:invariant sync to update from the external source.
```

This is the **only** hard write block in Purlin.

## Syncing from External Sources

### Git-sourced (all types)

```
purlin:invariant sync i_api_v3_contract
```

Compares `> Pinned:` SHA to remote HEAD. If different, pulls the updated file and updates the SHA.

### Figma-sourced (design type)

```
purlin:invariant sync figma figma.com/design/abc123/Brand-System
```

Reads the Figma file via MCP, extracts design constraints as rules, writes the invariant file. `> Pinned:` is the Figma `lastModified` timestamp.

### CI staleness check

```
purlin:invariant sync --check-only
```

Compares all invariants' `> Pinned:` to their remote sources without pulling. Fails if any are stale. Use in CI before `purlin:verify --audit`.

## Using Invariants in Feature Specs

Reference invariants in `> Requires:`:

```markdown
# Feature: color_picker

> Requires: i_design_brand
> Scope: src/components/ColorPicker.js
```

`sync_status` includes the invariant's rules in the feature's coverage report. Your tests must prove both the feature's own rules and the required invariant's rules.

## Anchors vs Invariants

Both have rules that other features can require. The difference:

| | Anchor | Invariant |
|-|--------|-----------|
| Location | `specs/<category>/<prefix>_name.md` | `specs/_invariants/i_<prefix>_name.md` |
| Editable? | Yes | No (gate-protected) |
| Source | Local project | External (git repo, Figma) |
| Prefixes | `design_`, `api_`, `security_`, `brand_`, `platform_`, `schema_`, `legal_`, `prodbrief_` | Same, with `i_` prefix |

Anchors are just regular specs that other features can require. Anyone can create and edit them.

## Build Time vs Test Time (Figma)

During `purlin:build`, the agent reads Figma directly via MCP for full visual context (screenshots, layout, tokens). During `purlin:verify`, the system just runs tests against the extracted rules — never touches Figma. Build time is creative; test time is mechanical.
