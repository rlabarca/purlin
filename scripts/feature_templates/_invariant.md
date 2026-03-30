# <Type>: <Name>

> Label: "<Category>: <Name>"
> Category: "<Category>"
> Format-Version: 1.1
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: what constraints this invariant enforces and why they exist.>

## <Domain> Invariants

### <Invariant Group Name>

- <Invariant statement>

## FORBIDDEN Patterns

*   <Description of violation>.
    *   **Pattern:** `<regex>`
    *   **Scope:** `<glob pattern for target files>`
    *   **Exemption:** <When the pattern is acceptable, if ever>

## Verification Scenarios

Scenario: <Scenario Name>
  Given <precondition>
  When <action>
  Then <expected outcome that demonstrates invariant compliance>
