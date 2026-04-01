---
name: spec
description: Scaffold or edit feature specs in 3-section format
---

Scaffold a new spec or edit an existing one. Writes to `specs/<category>/<name>.md`.

## Usage

```
purlin:spec <name>              Create or edit a spec
purlin:spec <name> --anchor     Create an anchor spec (design_, api_, etc.)
purlin:spec <name> --invariant  Create an invariant spec (i_<prefix>_<name>)
```

## Step 1 — Find or Create

Search `specs/**/<name>.md` for an existing spec.

- **Found:** Read the spec. Show current rules and proof coverage (call `sync_status`). Ask the user what to change.
- **Not found:** Ask the user for a category. Create `specs/<category>/<name>.md` using the template below.

## Step 2 — Write the Spec

Use the 3-section format. See `references/formats/spec_format.md` for the full canonical format.

### Template

```markdown
# Feature: <name>

> Requires: <comma-separated spec names or invariant names, if any>
> Scope: <comma-separated file paths this feature touches>

## What it does

<One paragraph: what this feature is and why it exists.>

## Rules

- RULE-1: <Constraint the code must satisfy>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion description>
- PROOF-2 (RULE-2): <Observable assertion description>
```

### Rules Guidelines

- Each rule is a testable constraint, not a vague goal.
- Rules must be numbered: `RULE-1`, `RULE-2`, etc.
- Bad: "RULE-1: Handle errors properly" — Good: "RULE-1: Return HTTP 400 with error body when input validation fails"
- Every rule must have at least one corresponding PROOF.

### Proof Guidelines

- Each proof maps to a rule via `PROOF-N (RULE-N):`.
- Proofs describe **observable assertions**, not implementation steps.
- Bad: "PROOF-1 (RULE-1): Check that error handling code exists" — Good: "PROOF-1 (RULE-1): POST invalid input returns 400 with `{error: 'validation_failed'}`"
- For rules that cannot be tested automatically, add `@manual` after the description.

### Anchor Specs

Anchors are regular specs with type-prefixed names. Use `--anchor` flag.
Type prefixes: `design_`, `api_`, `security_`, `brand_`, `platform_`, `schema_`, `legal_`, `prodbrief_`.
See `references/formats/anchor_format.md` for the anchor-specific format.

### Invariant Specs

Invariants live in `specs/_invariants/i_<prefix>_<name>.md`. Use `--invariant` flag.
See `references/formats/invariant_format.md` for the invariant format with `> Source:` and `> Pinned:` metadata.

## Step 3 — Metadata

- `> Requires:` — List other spec names (or invariant names) whose rules also apply. `sync_status` merges required rules into coverage.
- `> Scope:` — List file paths this feature touches. Used by `sync_status` to detect manual proof staleness.

## Step 4 — Commit

```
git commit -m "spec(<name>): <description of change>"
```
