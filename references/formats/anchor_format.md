> Format-Version: 4

# Anchor Spec Format

Anchors define cross-cutting constraints that other features reference via `> Requires:`. They use the standard 3-section format (Rules, Proof, What it does).

This document has two parts:

1. **Authoring format** — what you write when creating an anchor (either locally or in a remote repo for others to consume)
2. **Consumer tracking fields** — metadata that Purlin tooling adds when a project pulls an anchor from an external source. You do NOT write these yourself.

## Part 1: Authoring Format

This is the format to use when writing an anchor — whether it lives locally in `specs/_anchors/` or in a remote repo that other projects will pull from.

### Template

```markdown
# Anchor: <name>

> Description: <What cross-cutting concern this anchor defines>
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

### Location

When authoring a local anchor, place it in:

```
specs/_anchors/<name>.md
```

Users name anchors freely. No enforced prefixes.

When authoring a remote anchor (in an external repo for others to consume), place it wherever makes sense in that repo. The consuming project will reference it by repo URL + path.

### Metadata Fields (author-controlled)

These fields are written by the anchor author. All are optional.

| Field | Description |
|-------|-------------|
| `> Description:` | Plain-language description. Displayed in the Purlin dashboard. Supports multi-line via `>` continuation lines. |
| `> Scope:` | File patterns this anchor governs. Used for manual proof staleness detection. |
| `> Stack:` | Language/framework. |
| `> Type:` | Suggested types: `design`, `api`, `security`, `brand`, `platform`, `schema`, `legal`, `prodbrief`. Not enforced. |
| `> Global:` | When `true`, this anchor's rules auto-apply to ALL feature specs without needing `> Requires:`. |
| `> Visual-Reference:` | Pointer to visual source: `figma://fileKey/nodeId`, `./path.png`, `./path.html`, `https://url`. |

## Part 2: Consumer Tracking Fields (added by Purlin tooling)

When a project pulls an anchor from an external source (a git repo, Figma file, or URL), Purlin adds tracking metadata to the local copy in `specs/_anchors/`. **These fields are NOT written by the anchor author** — they are added and maintained by `purlin:anchor sync` in the consuming project.

### Tracking fields

| Field | Description |
|-------|-------------|
| `> Source:` | External reference: git repo URL, Figma URL, or HTTP URL. Tells Purlin where to pull updates from. |
| `> Path:` | For git-sourced anchors: path within the repo to the source file. |
| `> Pinned:` | Git commit SHA (git-sourced) or ISO 8601 timestamp (Figma-sourced). Updated by `purlin:anchor sync`. |
| `> Visual-Hash:` | SHA-256 hash of visual reference image for staleness detection. |

### Example: what a consumer's local copy looks like

The consuming project's `specs/_anchors/security_no_eval.md` might look like this after pulling from a remote repo:

```markdown
# Anchor: security_no_eval

> Description: No eval() calls in production code
> Source: git@github.com:acme/security-policies.git
> Path: specs/no_eval.md
> Pinned: abc1234def5678
> Type: security

## What it does

No eval() calls in production code.

## Rules

- RULE-1: No eval() in source files
- RULE-2: No exec() in source files

## Proof

- PROOF-1 (RULE-1): grep -r "eval(" src/ returns zero matches
- PROOF-2 (RULE-2): grep -r "exec(" src/ returns zero matches
```

The `> Source:`, `> Path:`, and `> Pinned:` lines were added by Purlin tooling — the original author's file in `acme/security-policies` does NOT contain them.

### Example: Figma-sourced anchor (consumer copy)

```markdown
# Anchor: checkout_design

> Description: Visual design constraints sourced from Figma.
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

## Requires Field (on feature specs)

Feature specs reference anchors via `> Requires:`:

```markdown
# Feature: checkout

> Requires: security_no_eval, checkout_design
```

This pulls in all rules from the named anchors. The feature's tests must prove compliance with both its own rules and the anchor rules.

## Sync Behavior

`purlin:anchor sync <name>` compares `> Pinned:` to the upstream source:

- **Git:** `git ls-remote` to get HEAD SHA. If different, pull new content and update `> Pinned:`.
- **Figma:** `get_metadata` MCP call to get `lastModified`. If different, fetch new data and update.

If the anchor has local rules and the external source changed, `purlin:drift` surfaces this as a PM action item.

## Global Anchors

An anchor with `> Global: true` has its rules auto-applied to every non-anchor feature spec. Features don't need `> Requires:` — the rules are included automatically. In `sync_status`, global anchor rules appear with a `(global)` label.
