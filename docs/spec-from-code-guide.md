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

You choose which directories to scan before the agents launch. Results are synthesized into a complete inventory of the codebase and any migration candidates. Phase 1 also writes a `project_environment` anchor capturing the runtime, key dependencies, build config, and environment variables.

### Phase 2: Taxonomy Review

The skill proposes feature categories. Existing specs seed the taxonomy — their category names and feature names are reused. Each feature is annotated:

```
Proposed category: auth/ (3 features)
  login (migrating) — email/password authentication
  session (migrating) — session management and refresh tokens
  rate_limit (new) — brute force protection

Approve? Rename? Merge with another category?
```

You confirm, rename, merge, or split categories. The skill also identifies cross-cutting concerns and proposes them as anchors — always including at least one `security_` anchor (dangerous-pattern checks, proposed even when the codebase is clean).

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

## After Generation: Proving the Specs

Generated specs start UNTESTED — the code exists, but nothing proves it satisfies the rules. This is the reverse of the normal lifecycle: because the code was **not** built by `purlin:build`, the build loop's job here is to write the proof-marked tests, not to write code.

Run the build loop with the existing code as the source of truth:

```
build <feature> — the code already exists and is the source of truth.
Don't modify it; only write tests with proof markers.
```

Two things matter in this mode:

- **Don't let the build change the code.** Say so explicitly, as above. The rules were extracted *from* the code, so the code already satisfies them — the only missing artifact is tests.
- **A failing test means the generated rule is probably wrong**, not the code. In a normal build, a failing test means "fix the code." Here it usually means spec-from-code extracted a rule inaccurately — review it with `purlin:spec <feature>` and correct the rule, then re-test. Only fix the code if the rule is right and you've found a genuine bug.

The full loop:

```
purlin:status          — see what needs tests (everything, initially)
build <feature>        — tests only, code is source of truth (see above)
purlin:verify          — lock in verification receipts
```
