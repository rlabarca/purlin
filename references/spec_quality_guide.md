# Spec Quality Guide

How to write good specs. For spec **syntax** (section names, ID format, metadata fields), see `references/formats/spec_format.md`. This guide covers **judgment** — what makes a spec useful for rebuilding, testing, and verifying code.

## Writing Rules

Aim for **5–10 rules per feature**. A spec with 2–3 rules loses too much detail for rebuild scenarios. Specifically extract:

- **Error handling paths** — each distinct error response is a rule. "Return 400 when email is missing" and "Return 409 when email already exists" are two separate rules, not one "handle errors" rule.
- **Configuration behavior** — defaults, overrides, env var fallbacks. "Default timeout is 30s" and "PURLIN_TIMEOUT env var overrides the default" are both rules.
- **Boundary conditions** — max lengths, timeouts, retry limits. "Reject passwords shorter than 8 characters" is a rule.
- **Data flow** — what goes in, what comes out, what gets cached, what gets logged. "Log a warning when retry count exceeds 3" is a rule.

Rules describe **behavior, not implementation**:
- Bad: "Use bcrypt.compare for password verification"
- Good: "Return 401 when password does not match stored hash"

## Writing Proof Descriptions

Proof descriptions must be **observable assertions with concrete inputs and expected outputs**. The description should tell the agent exactly what to do and what to assert — it should be copy-pasteable into a test without interpretation.

Bad:
```
- PROOF-1 (RULE-1): Test the login
- PROOF-1 (RULE-1): Verify authentication works
- PROOF-1 (RULE-1): Check error handling
```

Good:
```
- PROOF-1 (RULE-1): POST {"user": "alice", "pass": "wrong"} to /login; verify 401 with {error: "invalid_credentials"}
- PROOF-2 (RULE-2): Call resolve_config() with only config.json present; verify returned dict matches config.json contents
- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches
```

Include test setup context when architecture matters:
```
- PROOF-4 (RULE-4): With PURLIN_PROJECT_ROOT set to /tmp/test, call find_project_root(); verify it returns /tmp/test without climbing directories
```

## Tier Assignment

Assign a tier tag based on what the proof requires to execute. Proofs without a tag are `default` tier.

| Heuristic | Tier | Example |
|-----------|------|---------|
| Pure logic, no I/O, no external dependencies | default (no tag) | Validate input format, compute hash, parse config |
| Needs database, network, filesystem, or external service | `@slow` | API roundtrip, database query, file system operations |
| Needs browser, full app stack, or UI rendering | `@e2e` | Playwright login flow, screenshot comparison, full page render |
| Requires human judgment — visual, UX, brand voice | `@manual` | Review copy against brand guide, verify layout feels balanced |

Append the tier tag to the end of the proof description line:

```
- PROOF-1 (RULE-1): Parse config file and return default values
- PROOF-2 (RULE-2): POST to /api/users with mock database; verify 201 response @slow
- PROOF-3 (RULE-3): Load checkout page in browser; verify 3-click flow @e2e
- PROOF-4 (RULE-4): Review error messages against brand voice guide @manual
```

**Manual proof detection heuristics:** Source files in `views/`, `pages/`, `templates/`, `layouts/` directories, React/Vue/Svelte components with layout/styling logic, CSS/SCSS files in scope, or code producing HTML output → proofs are likely `@e2e` or `@manual`. Don't write automated proof descriptions for things that can't actually be automated.

## When to Create Anchors

Anchors capture **cross-cutting constraints shared across features**. If 3+ features would have the same rule, it belongs in an anchor.

- Architecture choices shared across features → `api_` or `schema_` anchor
- Security patterns applied everywhere → `security_` anchor (always include FORBIDDEN rules)
- Design system tokens used by multiple components → `design_` anchor

**Anchor type detection heuristics:**

| Prefix | Detection heuristics |
|--------|---------------------|
| `api_` | Shared route patterns, middleware chains, response envelope formats, error response shapes, pagination conventions. Look for: express Router, Flask blueprints, API versioning |
| `security_` | Auth middleware, password hashing, token validation, input sanitization, CORS, rate limiting. Look for: bcrypt, JWT, helmet, csrf, rate-limit imports |
| `design_` | Shared UI component libraries, CSS token files, theme configs, layout patterns. Look for: styled-components, tailwind config, design tokens, shared component dirs |
| `schema_` | Database models, ORM definitions, migration files, validation schemas, shared types. Look for: sequelize/prisma/sqlalchemy models, zod/joi schemas, shared TypeScript interfaces |
| `platform_` | Browser compat configs, polyfills, platform-specific code paths, accessibility. Look for: browserslist, babel config, a11y utilities |
| `brand_` | Copy constants, i18n files, terminology glossaries, tone-of-voice docs. Look for: locales/, i18n imports, string constant files |
| `prodbrief_` | User flow definitions, feature flags, A/B test configs, analytics events. Look for: feature flag configs, analytics track calls |
| `legal_` | Cookie consent, privacy policy refs, data retention configs, GDPR helpers. Look for: consent managers, data deletion utilities, PII handling |

**Architecture choices should be anchors.** If the codebase uses a specific pattern consistently across multiple features (middleware auth, write-through caching, event-driven architecture), that pattern should become an anchor — not be buried in individual feature specs.

## Tier Tags on Proofs

Every proof description must be tagged with the appropriate tier. Don't leave it to the test writer to guess.

| Heuristic | Tag | Examples |
|-----------|-----|----------|
| Pure logic, in-memory assertions, grep on local files | (none — default) | Parse a config, validate format, check string output |
| Shells out to git, calls external APIs, needs database/filesystem setup | `@slow` | git log comparison, API roundtrip, database query |
| Requires browser, full app rendering, UI interaction | `@e2e` | Playwright flow, screenshot comparison, full page render |
| Requires human judgment — visual, UX, brand voice | `@manual` | Review copy against brand guide, verify layout feels balanced |

**When in doubt, tag `@slow`.** A fast test with a `@slow` tag is harmless. A slow test with no tag blocks the default tier.

### Mandatory Tier Review

Tier tags are not optional metadata — they control which tests run in which CI stage. Every skill that writes proof descriptions (`purlin:spec`, `purlin:spec-from-code`, `purlin:build`) MUST review tier tags before committing. An untagged proof that shells out to `subprocess` or hits a database will block the default tier and slow down every developer's iteration loop. Review every proof against the heuristics above and tag it before the tests run.

## FORBIDDEN Grep Precision

FORBIDDEN proofs use grep to assert absence. The grep pattern must be precise enough to avoid false positives.

**Common false positives:**
- Comments and docstrings mentioning the keyword (`# never use eval`)
- Variable names containing the keyword (`password_hash`, `token_expiry`)
- Test files with intentional mock values

Bad:
```
grep -ri "password\|secret" scripts/
```

Good:
```
grep -rn "password\s*=\s*[\"'][^\"']*[\"']" scripts/ --include="*.py" | grep -v test_ | grep -v "# "
```

Target the **assignment pattern** (`keyword = "literal string"`), not the keyword alone. Exclude test files and comments.

## Edge Case Proof Specificity

Proofs for boundary conditions and edge cases must include the **specific test input that triggers the edge case** — not just the expected output.

Bad:
```
- PROOF-4 (RULE-4): Verify IDs are sequential with no gaps
- PROOF-5 (RULE-5): Check that invalid input is rejected
```

Good:
```
- PROOF-4 (RULE-4): Create a spec with RULE-1 and RULE-3 (skipping RULE-2); verify sync_status reports a warning about non-sequential IDs
- PROOF-5 (RULE-5): Call update_config() with key="" (empty string); verify it raises ValueError
```

Always ask: **"What exact input triggers this edge case?"** and include it in the proof description.

## FORBIDDEN Patterns

FORBIDDEN rules use standard rule/proof syntax — no special format. They are just rules with **negative proofs** (grep-based assertions that verify dangerous patterns don't exist).

```
- RULE-1: No eval() or exec() calls in scripts/
- PROOF-1 (RULE-1): Grep scripts/ for eval( and exec(; verify zero matches
```

Guidelines:
- Always create at least one `security_` anchor with FORBIDDEN rules, even if the codebase is clean — proving the absence of dangerous patterns is itself valuable.
- Test the attack, not the defense. Assert that the bad pattern doesn't exist rather than asserting that "security is good."
- Common FORBIDDEN patterns: `eval()`, `exec()`, `os.system()`, `subprocess` with `shell=True`, hardcoded credentials/secrets.

## `> Stack:` Metadata

Captures the technology choices for a feature so an agent can rebuild from the spec alone.

Format: `> Stack: <language>/<framework>, <key libraries>, <patterns>`

Examples:
- `> Stack: python/stdlib, subprocess (list-only), json, hashlib`
- `> Stack: node/express, axios, redis (cache), JWT auth`
- `> Stack: shell/bash, jq, curl`

Populate from the **actual imports/dependencies in the feature's source files**, not the project-level tech stack. Two features in the same project may have different stacks.

## `> Requires:` Guidance

- Reference anchors when the feature must follow shared rules.
- Reference invariants when external constraints apply.
- **Don't reference specs that are just related** — only specs whose rules MUST be proved by this feature's tests. `> Requires:` means "my tests must also prove these rules."
- Verify each reference exists (or is queued for generation) before writing it. Broken references produce silent gaps in coverage.

## `> Scope:` Guidance

- List the source files this feature touches — for humans and the staleness detection system.
- Verify each file path exists on disk before listing it.
- Used by `sync_status` to detect manual proof staleness (newer commits to scope files invalidate manual stamps).
- Not used for verification hashing — purely informational for navigation and staleness.

## Spec Categories

Where different types of specs belong. Both `purlin:spec` and `purlin:spec-from-code` use this to determine the output directory.

| Category dir | What goes here | Tier expectations | Example |
|-------------|---------------|-------------------|---------|
| Component dirs (`hooks/`, `mcp/`, `proof/`) | Behavioral specs for executable code | Default tier for unit-level proofs | `specs/hooks/gate-hook.md` |
| `schema/` | Anchors defining formats, contracts, and cross-cutting standards | Default tier | `specs/schema/schema_spec_format.md` |
| `integration/` | E2E flows testing the full system working together | All proofs tagged `@e2e` | `specs/integration/e2e_purlin_lifecycle.md` |
| `instructions/` | Structural specs for agent instructions — reference docs, skill definitions, agent definitions | Default tier (grep-based structural checks) | `specs/instructions/purlin_references.md` |

### Guidelines

- **Executable code** (scripts, hooks, MCP server) → spec category matches the source directory.
- **Cross-cutting contracts** (file formats, schemas, security rules) → `schema/`.
- **AI instructions** (`references/`, `skills/`, `agents/`) → `instructions/`. Rules verify sections exist and contain required content. Proofs are grep-based. These catch accidental deletions and structural drift.
- **Full lifecycle flows** → `integration/`. Rules describe end-to-end behavior. All proofs are `@e2e`. These run in CI nightly, not on every push.
- **Don't mix levels.** A spec in `mcp/` tests the MCP server code. A spec in `integration/` tests the MCP server as part of the full lifecycle. Different specs, different tiers.

## Audience-Appropriate Language

Specs, changelogs, and reports serve different audiences. Match the language to the reader:

| Artifact | Audience | Language |
|----------|----------|----------|
| Spec rules and proofs | Engineers and agents | Precise, technical — status codes, function names, exact inputs |
| Changelog CHANGED BEHAVIOR | PMs and QA | User-visible impact — "login is faster", "error message changed" |
| Changelog NO IMPACT | Engineers | Implementation details — "refactored middleware", "updated dependency" |
| Verification reports | Engineers and CI | Concise, structured — feature names, rule counts, directives |

**The test for good changelog language:** Could a PM read this line and understand whether it affects users? If not, rephrase or move it to NO IMPACT. "Fixed N+1 query in user list resolver" → "User list page loads faster" (CHANGED BEHAVIOR) + "Optimized database query in user list resolver" (NO IMPACT).

## When Tests Fail: Fix the Code, Not the Test

When a proof-marked test fails, the agent must diagnose before fixing. There are three possibilities:

| Diagnosis | What's wrong | Action |
|-----------|-------------|--------|
| Code bug | The test asserts the correct behavior but the code doesn't implement it | Fix the code. The test is right. |
| Test bug | The test asserts the wrong thing (wrong status code, wrong field name, bad mock setup) | Fix the test. The code is right. |
| Spec drift | The rule no longer matches the intended behavior | Update the spec rule first, then update code and test to match. |

**The default assumption is: the code is wrong, not the test.** The test was written to prove a rule from the spec. If the test fails, the code probably doesn't satisfy the rule yet.

Never:
- Weaken an assertion to make a test pass (`assert status == 200` → `assert status in [200, 401]`)
- Remove an assertion that was testing the right thing
- Change the expected value to match the actual value without understanding why they differ
- Delete a failing test

If the spec itself is wrong (the rule describes behavior that shouldn't exist), update the spec first — change the rule, update the proof description, THEN update the test and code. The spec is the source of truth.

### Assertion Integrity

If you change WHAT a test asserts (not just HOW — e.g., changing `assert status == 401` to `assert status == 400`), the proof description in the spec may be wrong. This is a signal, not a bug:

1. Re-read the original proof description from the spec's `## Proof` section
2. If the new assertion contradicts the proof description, the spec likely needs updating
3. Flag the change explicitly — in the commit message, in a WARNING to the user, or both
4. The spec, proof description, test assertion, and code must all agree. If any one disagrees, find out which is wrong before proceeding

Silently changing an assertion to match actual behavior — without checking whether the spec intended that behavior — is the most common way agents introduce correctness bugs.
