> Format-Version: 3

# Anchor Spec Format

Anchors define cross-cutting constraints that other features reference via `> Requires:`. They live in `specs/_anchors/` and use the standard 3-section format.

Anchors may optionally have an external reference (`> Source:`), which links them to a git repo, Figma file, or URL. The external reference is authoritative context — the anchor file itself is always editable.

## Location

```
specs/_anchors/<name>.md
```

Users name anchors freely. No enforced prefixes.

## Template — Local Anchor

```markdown
# Anchor: <name>

> Scope: <file patterns this anchor governs>
> Type: <optional: design, api, security, brand, platform, schema, legal, prodbrief>

## What it does

<What cross-cutting concern this anchor defines.>

## Rules

- RULE-1: <Constraint that applies to all features requiring this anchor>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <How to verify compliance>
- PROOF-2 (RULE-2): <How to verify compliance>
```

## Template — Externally-Referenced Anchor (Git)

```markdown
# Anchor: <name>

> Source: git@github.com:org/repo.git
> Path: docs/spec.md
> Pinned: abc1234def5678
> Type: api

## What it does

<What this anchor defines, sourced from an external repo.>

## Rules

- RULE-1: <Rule from external source>
- RULE-2: <Rule added locally>

## Proof

- PROOF-1 (RULE-1): <Verification>
- PROOF-2 (RULE-2): <Verification>
```

## Template — Externally-Referenced Anchor (Figma)

```markdown
# Anchor: <name>

> Source: https://www.figma.com/design/ABC123/Design-System
> Pinned: 2026-03-31T12:00:00Z
> Visual-Reference: figma://ABC123/1:234
> Type: design

## What it does

Visual design constraints sourced from Figma.

## Rules

- RULE-1: Implementation must visually match the Figma design at the referenced node

## Proof

- PROOF-1 (RULE-1): Render component at same viewport size as Figma frame, capture screenshot, compare against Figma screenshot; verify visual match at design fidelity @e2e
```

## Metadata Fields

These fields are available on ANY spec (features, anchors). None are enforced by code.

| Field | Required | Description |
|-------|----------|-------------|
| `> Scope:` | No | File patterns this spec governs. Used for manual proof staleness detection. |
| `> Stack:` | No | Language/framework. |
| `> Requires:` | No | Comma-separated list of anchor names whose rules also apply. |
| `> Type:` | No | Suggested types: `design`, `api`, `security`, `brand`, `platform`, `schema`, `legal`, `prodbrief`. Not enforced. |
| `> Source:` | No | External reference: git repo URL, Figma URL, or HTTP URL. When present, `purlin:build` MUST read the source for full context. |
| `> Path:` | No | For git-sourced anchors: path within the repo to the source file. |
| `> Pinned:` | No | Git commit SHA (git-sourced) or ISO 8601 timestamp (Figma-sourced). Updated by `purlin:anchor sync`. |
| `> Global:` | No | When `true`, this anchor's rules auto-apply to ALL feature specs without needing `> Requires:`. |
| `> Visual-Reference:` | No | Pointer to visual source: `figma://fileKey/nodeId`, `./path.png`, `./path.html`, `https://url`. |
| `> Visual-Hash:` | No | SHA-256 hash of visual reference image for staleness detection. |

## Sync Behavior

`purlin:anchor sync <name>` compares `> Pinned:` to the upstream source:

- **Git:** `git ls-remote` to get HEAD SHA. If different, pull new content and update `> Pinned:`.
- **Figma:** `get_metadata` MCP call to get `lastModified`. If different, fetch new data and update.

If the anchor has local rules and the external source changed, `purlin:drift` surfaces this as a PM action item.

## Global Anchors

An anchor with `> Global: true` has its rules auto-applied to every non-anchor feature spec. Features don't need `> Requires:` — the rules are included automatically. In `sync_status`, global anchor rules appear with a `(global)` label.
