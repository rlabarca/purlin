# Generating Specs from Code

## What You Need to Know

```
purlin:spec-from-code
```

One command scans your codebase, detects existing specs in any format, and generates or migrates them to the current compliant format. It handles everything: `features/` directories from older Purlin versions, specs with unnumbered rules, missing metadata, or outdated formatting.

You review and approve at each step. Existing rules and descriptions are preserved.

---

## When to Use

- **New to Purlin.** You have code but no specs.
- **Migrating existing specs.** You have specs in `features/` (pre-0.9.0) or in `specs/` that are missing required fields, unnumbered rules, or outdated formatting. The skill reads them and produces compliant specs with minimal loss of fidelity.
- **Starting fresh.** After a major refactor where old specs no longer reflect the code.

## The Simplest Way

```
purlin:spec-from-code
```

Claude scans the codebase, detects existing specs, proposes a feature taxonomy, generates or migrates specs, and commits them. You review and refine at each step.

## What It Does (4 phases)

### Phase 1: Codebase Survey

The skill launches up to 3 parallel exploration agents:

- **Structure agent** — directory tree, entry points, routes, CLI commands
- **Domain agent** — frameworks, module boundaries, public APIs, tech stack
- **Comments agent** — TODOs, FIXMEs, architectural decisions, inline docs

It also scans for **existing specs to migrate**:
- `features/` directory (pre-0.9.0 Given/When/Then format)
- Non-compliant specs in `specs/` (missing `> Description:`, unnumbered rules, missing sections)
- Compliant specs are left untouched

Results are synthesized into a complete inventory of the codebase and any migration candidates.

### Phase 2: Taxonomy Review

The skill proposes feature categories. Existing specs seed the taxonomy — their category names and feature names are reused. Each feature is annotated:

```
Proposed category: auth/ (3 features)
  login (migrating) — email/password authentication
  session (migrating) — session management and refresh tokens
  rate_limit (new) — brute force protection

Approve? Rename? Merge with another category?
```

You confirm, rename, merge, or split categories. The skill also identifies cross-cutting concerns and proposes them as anchors.

### Phase 3: Spec Generation

For each approved category:

1. Reads the source files
2. If a migration candidate exists for a feature, uses it as the **primary input** — preserving the original rules, descriptions, and intent. Compares against current code and flags any discrepancies.
3. Writes or overwrites the spec in the current compliant format
4. Asks you to confirm each category before proceeding

Specs migrated from `features/` are written to `specs/`. Non-compliant specs in `specs/` are updated in place.

### Phase 4: Finalize

- Offers to remove old `features/` directory (if migration was from there)
- Runs `purlin:status` to show the initial coverage state
- Cleans up temporary files
- Prints next steps

## Resuming an Interrupted Run

State is preserved in `.purlin/cache/sfc_state.json`. Resume with:

```
purlin:spec-from-code --resume
```

Completed categories are skipped. Questions already answered are not re-asked.

## After Generation

Generated specs are a starting point. Review them, then start the build/test loop:

```
purlin:status          — see what needs tests
test <feature_name>    — write tests and iterate until VERIFIED
purlin:verify          — lock in verification receipts
```
