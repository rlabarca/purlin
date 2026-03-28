# Invariant Format Reference

> Format-Version: 1.0
> Referenced by `purlin:invariant validate` and external invariant authors.

This document defines the canonical format for Purlin invariant files. External teams authoring invariants for consumption by Purlin projects MUST conform to this format.

## Overview

An invariant is an externally-sourced, locally-immutable constraint document. It lives in a project's `features/` directory with an `i_` prefix (e.g., `i_policy_security.md`). The project cannot modify it — changes come only from the external source via `purlin:invariant sync`.

## Required Metadata

All invariant files MUST include these blockquote metadata lines:

| Field | Required | Description |
|-------|----------|-------------|
| `> Format-Version:` | Yes | Format spec version this file conforms to (e.g., `1.0`) |
| `> Invariant: true` | Yes | Marks this as an externally-sourced invariant |
| `> Version:` | Yes | Content version (semver: MAJOR.MINOR.PATCH). Defaults to `0.0.0` if absent |
| `> Source:` | Yes | Git repo URL (git-sourced) or `figma` (Figma-sourced) |
| `> Source-Path:` | Yes (git) | Original file path within the source repo |
| `> Source-SHA:` | Yes (git) | Git commit SHA the file was pulled from |
| `> Figma-URL:` | Yes (figma) | Figma file URL (Figma-sourced only) |
| `> Synced-At:` | Yes | ISO 8601 timestamp of last sync |
| `> Scope:` | Yes | `global` (applies to all features) or `scoped` (requires prerequisite link) |

Standard anchor metadata (`> Label:`, `> Category:`) is also expected.

## Required Sections by Type

| Section | arch_ / policy_ / ops_ | prodbrief_ | design_ (git) | design_ (figma) |
|---------|----------------------|------------|---------------|-----------------|
| `## Purpose` | Required | Required | Required | Required |
| `## <Domain> Invariants` | Required | — | Required | — |
| `## User Stories` | — | Required | — | — |
| `## Success Criteria` | — | Required | — | — |
| `## Figma Source` | — | — | — | Required |
| `## Annotations` | — | — | — | Required |
| `## FORBIDDEN Patterns` | Optional | — | Optional | — |
| `## Verification Scenarios` | Optional | — | Optional | — |
| `## Acceptance Scenarios` | — | Optional | — | — |

## Templates

### Base Template (arch_, policy_, ops_)

```markdown
# <Type>: <Name>

> Label: "<Category>: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: what constraints this invariant enforces and why they exist.
Must answer: What organizational authority mandates these constraints?>

## <Domain> Invariants

### <Invariant Group Name>

- <INV-1> <Invariant statement — specific, testable, unambiguous>
- <INV-2> <Invariant statement>

## FORBIDDEN Patterns

*   <Description of violation> (Invariant <INV-N>).
    *   **Pattern:** `<regex>`
    *   **Scope:** `<glob pattern for target files>`
    *   **Exemption:** <When the pattern is acceptable, if ever>

## Verification Scenarios

Scenario: <Scenario Name>
  Given <precondition>
  When <action>
  Then <expected outcome that demonstrates invariant compliance>
```

### Product Brief Template (prodbrief_)

```markdown
# Product Brief: <Name>

> Label: "Product: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: the product goal this brief defines.>

## User Stories

### <Epic or Theme Name>

- As a <role>, I want to <goal>, so that <benefit>

## Success Criteria

- <KPI-1> <Measurable outcome with target>

## Acceptance Scenarios

Scenario: <Scenario Name>
  Given <user context>
  When <user action>
  Then <expected product behavior>
```

### Figma Design Invariant (design_, Figma-sourced)

```markdown
# Design: <Name>

> Label: "Design: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <figma-version-id>
> Source: figma
> Figma-URL: <figma-file-url>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: what design system this Figma file defines.>

## Figma Source

This invariant is governed by the Figma document linked above.
Design tokens, constraints, and visual standards are defined in Figma
and cached locally in per-feature `brief.json` files during spec authoring.

## Annotations

- <Advisory behavioral note extracted from Figma>
```

## Source Repository Requirements

External invariant repos need only a `features/` directory containing markdown files in one of the formats above. No other directory structure, config files, or tooling is required.

## Versioning

- Use semantic versioning (MAJOR.MINOR.PATCH).
- **MAJOR** bumps indicate breaking constraint changes that require full re-validation.
- **MINOR** bumps add new constraints or strengthen existing ones.
- **PATCH** bumps are corrections, clarifications, or typo fixes.
- Purlin uses the version to control cascade scope: MAJOR = full cascade, MINOR = cascade with warning, PATCH = no cascade.
