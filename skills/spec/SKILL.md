---
name: spec
description: Scaffold or edit feature specs in 3-section format
---

Scaffold a new spec or edit an existing one. Writes to `specs/<category>/<name>.md`.

For **syntax** (section names, ID format), see `references/formats/spec_format.md`.
For **quality** (how to write good rules, proofs, tiers, anchors), see `references/spec_quality_guide.md`.

## Usage

```
purlin:spec <name>              Create or edit a spec
purlin:spec <name> --anchor     Create an anchor spec (design_, api_, etc.)
purlin:spec <name> --invariant  Create an invariant spec (i_<prefix>_<name>)
```

## Step 1 — Find or Create

Search `specs/**/<name>.md` for an existing spec.

- **Found:** Read the spec. Show current rules and proof coverage (call `sync_status`). Ask the user what to change.
- **Not found:** Ask the user for:
  - Category name
  - Tech stack and key dependencies (for `> Stack:` metadata)
  - Whether any existing anchors should be referenced (check `specs/**/{api_,security_,design_,schema_,platform_,brand_,legal_,prodbrief_}*.md`)

## Step 2 — Write the Spec

Use the 3-section format from `references/formats/spec_format.md` with quality standards from `references/spec_quality_guide.md`.

### Template

```markdown
# Feature: <name>

> Requires: <comma-separated spec names or invariant names, if any>
> Scope: <comma-separated file paths this feature touches>
> Stack: <language>/<framework>, <key libraries>, <patterns>

## What it does

<One paragraph: what this feature is and why it exists.>

## Rules

- RULE-1: <Constraint the code must satisfy>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion with concrete inputs and expected outputs>
- PROOF-2 (RULE-2): <Observable assertion with concrete inputs and expected outputs>
```

### Quality Checklist (from spec_quality_guide.md)

- **5–10 rules** per feature. Extract error handling, config behavior, boundary conditions, data flow.
- **Observable proof descriptions** with concrete inputs/outputs. Bad: "Test the login." Good: "POST {user: alice, pass: wrong} to /login; verify 401."
- **Tier tags** on proofs: no tag = default, `@slow` for I/O, `@e2e` for browser, `@manual` for human judgment.
- **`> Requires:`** only references specs whose rules MUST be proved by this feature's tests. Verify each reference exists.
- **`> Scope:`** only lists files that exist on disk.
- **`> Stack:`** populated from actual imports in the feature's source files.

### Anchor Specs

Anchors are regular specs with type-prefixed names. Use `--anchor` flag.
Type prefixes: `design_`, `api_`, `security_`, `brand_`, `platform_`, `schema_`, `legal_`, `prodbrief_`.
See `references/formats/anchor_format.md` for format, `references/spec_quality_guide.md` for when to create anchors and FORBIDDEN pattern guidance.

### Invariant Specs

Invariants live in `specs/_invariants/i_<prefix>_<name>.md`. Use `--invariant` flag.
See `references/formats/invariant_format.md` for the invariant format with `> Source:` and `> Pinned:` metadata.

## Step 3 — Update an Existing Spec

When updating a spec after code changes:

1. Call the `changelog` MCP tool to understand what changed since the last verification.
2. Read the current spec and the changed source files.
3. Propose rule additions/modifications based on the diff — new error paths, new config options, changed boundaries.
4. Update proof descriptions to match the new rules.

## Step 4 — Validate Before Commit

Before committing, verify the spec:
- `## What it does` has at least one full sentence
- `## Rules` has at least one `RULE-N:` line, all numbered sequentially
- `## Proof` has at least one `PROOF-N (RULE-N):` line, each mapping to a rule
- Proof descriptions are observable assertions, not vague instructions
- All `> Requires:` references point to existing specs
- All `> Scope:` file paths exist on disk

## Step 5 — Commit

```
git commit -m "spec(<name>): <description of change>"
```
