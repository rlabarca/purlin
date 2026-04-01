# Generating Specs from Code

`purlin:spec-from-code` scans an existing codebase and generates specs in the 3-section format. Use it to onboard a project that already has code but no specs.

## When to Use

- **New to Purlin.** You have a codebase and want to start tracking rule coverage.
- **Upgrading from an older Purlin version.** After deleting old `features/` and running `purlin:init`.
- **Starting fresh.** After a major refactor where old specs no longer reflect the code.

## The Simplest Way

```
purlin:spec-from-code
```

Claude scans the codebase, proposes a feature taxonomy, generates specs, and commits them. You review and refine.

## What It Does (4 phases)

### Phase 1: Codebase Survey

The skill launches up to 3 parallel exploration agents:

- **Structure agent** — directory tree, entry points, routes, CLI commands
- **Domain agent** — frameworks, module boundaries, public APIs, tech stack
- **Comments agent** — TODOs, FIXMEs, architectural decisions, inline docs

Results are synthesized into `.purlin/cache/sfc_inventory.md` — a complete map of the codebase.

### Phase 2: Taxonomy Review

The skill proposes feature categories based on the survey. It presents them in batches for your review:

```
Proposed category: auth/ (3 features)
  login — email/password authentication
  session — session management and refresh tokens
  rate_limit — brute force protection

Approve? Rename? Merge with another category?
```

You confirm, rename, merge, or split categories. The validated taxonomy is saved to `.purlin/cache/sfc_taxonomy.md`.

The skill also identifies **cross-cutting concerns** (error handling, logging, config patterns) and proposes them as anchor specs with type prefixes (`api_`, `security_`, `design_`, etc.).

### Phase 3: Spec Generation

For each approved category (processed in dependency order — fewer anchor dependencies first):

1. Reads the source files (uses exploration agents for categories with 5+ files)
2. Extracts behavioral constraints — what the code does, not how
3. Writes a spec in the 3-section format:

```markdown
# Feature: login

> Requires: security_auth_standards
> Scope: src/auth/login.js, src/auth/middleware.js
> Stack: node/express, bcrypt, jsonwebtoken

## What it does
Authenticates users via email and password, issues JWT tokens.

## Rules
- RULE-1: Returns 200 with JWT token on valid credentials
- RULE-2: Returns 401 on invalid credentials
- RULE-3: Passwords are compared using bcrypt, never plaintext

## Proof
- PROOF-1 (RULE-1): POST valid credentials; verify 200 and JWT in response @slow
- PROOF-2 (RULE-2): POST invalid password; verify 401 @slow
- PROOF-3 (RULE-3): Store password; verify bcrypt hash in database @slow

## Implementation Notes
<!-- TODO from src/auth/login.js:42 — add OAuth2 support -->
<!-- FIXME from src/auth/middleware.js:15 — rate limit not applied to /api/v2 -->
```

4. Asks you to confirm each category before proceeding to the next
5. Commits each category batch separately

### Phase 4: Finalize

- Cleans up temporary files (`.purlin/cache/sfc_*.md`, `.purlin/cache/sfc_state.json`)
- Runs `sync_status` to show the initial coverage state (all 0% — no proofs yet)
- Prints next steps

## Resuming an Interrupted Run

If a run is interrupted (context limit, network error), state is preserved in `.purlin/cache/sfc_state.json`. Resume with:

```
purlin:spec-from-code --resume
```

Completed categories are skipped. Questions already answered are not re-asked.

## After Generation

Generated specs are a starting point, not a final product. Use the [Spec Quality Guide](../references/spec_quality_guide.md) as your review checklist. Key questions:

- **Are the rules correct?** Do they describe what the code actually does?
- **Are the proof descriptions observable?** Can you write a test that asserts the described outcome?
- **Are cross-cutting concerns captured as anchors?** Should any feature require them?
- **Is the `> Scope:` accurate?** Does it list the right source files?

Then start the build/test loop:

```
purlin:status          — see what needs tests
test <feature_name>    — write tests and iterate until READY
purlin:verify          — lock in verification receipts
```

## Guidelines

- **Extract behavior, not implementation.** "Returns 401 on invalid credentials" not "calls `bcrypt.compare()` in the auth middleware."
- **One feature per module boundary.** Don't spec internal helpers — spec the public interface.
- **2-5 rules per feature to start.** You can always add more via `purlin:spec`.
- **Proof descriptions should be observable assertions.** "POST invalid password; verify 401" not "test the auth module."
