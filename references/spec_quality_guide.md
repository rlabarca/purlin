# Spec Quality Guide

How to write good specs. For spec **syntax** (section names, ID format, metadata fields), see [references/formats/spec_format.md](formats/spec_format.md). This guide covers **judgment** — what makes a spec useful for rebuilding, testing, and verifying code. For bad→good rule examples from real projects, see [references/rule_examples.md](rule_examples.md).

## Writing Rules

### The rebuild test

Every rule must pass one test: **"If an engineer rebuilt this feature from only this spec, would they get this wrong without this rule?"**

If the answer is "no, they'd figure it out" or "QA would catch it immediately" — it's not a rule. Cut it.

This question comes before everything else. Coverage dimensions, tier tags, proof descriptions — none of that matters if the rules themselves don't capture what an engineer would get wrong.

Rules describe **behavior, not implementation**:
- Bad: "Use bcrypt.compare for password verification"
- Good: "Return 401 when password does not match stored hash"

Three tests for every candidate rule:

1. **Rebuild test:** Would an engineer get this wrong without this rule?
2. **Behavior test:** Does this describe what the feature does, or how the code does it? If it names a library, hook, CSS value, or token — rewrite it as the observable behavior, or cut it.
3. **Overlap test:** Would this rule always pass or fail together with another rule? If yes — merge them.

### Rebuild risk tiers

Not all missing rules are equally dangerous. Prioritize by what would go wrong in a rebuild:

| Tier | Rebuild risk | Example | Spec priority |
|------|-------------|---------|---------------|
| **Wrong behavior** | Engineer builds the wrong thing — wrong data source, wrong conditional gate, wrong calculation | "Purchase flow uses `PurchasePriceOrPropertyValue`; refi uses `PropertyValue`" | Must be a rule. A rebuild without this produces wrong numbers. |
| **Broken functionality** | Feature works but degrades badly under real conditions — crashes on missing data, one section failure cascades | "Accordion sections render independently — one failing does not collapse others" | Must be a rule. An engineer would likely miss this. |
| **Wrong layout** | Feature works correctly but looks wrong in ways that affect usability — content overlaps, sections hidden | "Loan details and disclaimer do not overlap on any viewport" | Should be a rule with `@e2e` or `@manual` proof. |
| **Visual polish** | CSS spacing, exact pixel values, animation timing, icon sizing | "Info bar has 16px bottom margin" | Not a rule. QA catches this. |

### Signs of too few / too many rules

Signs of too few rules:
- Data source fields not specified — engineer might pull from wrong API field
- Conditional gates missing — engineer shows content to wrong user segment
- Graceful degradation absent — engineer's rebuild crashes on missing data
- Responsive behavior causes functional breakage (overlapping content, hidden controls)

Signs of too many rules:
- Rules describe implementation rather than behavior ("uses a `forEach` loop", "uses `rx={h/2}` for SVG elbow")
- Rules specify CSS values that are visual polish, not behavioral ("margin-top: -66px")
- Rules overlap — two rules that would always pass or fail together
- Rules for behavior that exists only in tests, not in the feature itself
- Implementation notes masquerading as rules (architecture decisions, library choices)

### Coverage dimensions

After applying the rebuild test, check that the spec covers each applicable **contract boundary**. Every feature has data crossing between systems or modules — the contracts at those boundaries are what an engineer would get wrong. The number of rules scales with the feature's complexity — there is no fixed target.

**Inbound contracts** — what data enters this feature and in what shape?
- API response fields the feature consumes (exact field names — this is the #1 rebuild risk)
- Config/env values the feature reads
- Props, parameters, or messages from other modules
- File contents, CLI arguments, webhook payloads

**Outbound contracts** — what data does this feature emit?
- Analytics events (event names, parameter shapes, when they fire)
- API calls to other services (endpoints, payloads, query params)
- Database writes, file outputs, log entries
- Callbacks, events, or messages to other modules

**Transformation rules** — what logic converts between inbound and outbound?
- Field mappings (API field → display field, with exact names on both sides)
- Calculations and formulas (the math that produces displayed or stored values)
- Formatting functions (URL builders, phone formatters, name concatenation)
- Filters, sorts, and aggregations applied to data

**State transitions** — what lifecycle does this feature have?
- Valid states and what triggers each transition
- What's forbidden (can't go from X to Y directly)
- Timeout/expiry behavior

**Access contracts** — who can see or do what?
- Role/permission gates
- Feature flag conditions
- Mode switches that change behavior (e.g., admin mode, loan officer mode)

**Project-level anchors** (check once per project, not per feature):

- **Environment contracts** — runtime version, key dependency versions, build command, env var inventory. Captured in a `project_environment` anchor with `> Global: true`. Every feature implicitly depends on the environment being correct.
- **API surface** — full endpoint inventory with paths, methods, and parameter shapes. Captured in an `api_surface` anchor. Feature specs reference it for their specific endpoints; the anchor is the single source of truth for base paths, auth patterns, and response envelope conventions.
- **Domain schemas** — critical field names for types that flow through multiple features. Captured in `schema_` anchors with field-level rules. Not the full interface — the fields that appear in transformations, display, or conditional gates. If an engineer uses the wrong field name, the feature produces wrong output.

**Supporting dimensions** (check after the above):
- Error handling paths — each distinct error response
- Boundary conditions — max lengths, timeouts, retry limits
- Performance constraints — load times, render budgets, query limits
- Graceful degradation — what happens when dependencies fail

## Rule Tags

Three tags can be added to rule lines:

### (assumed)

Added by `purlin:spec` when the AI translates vague input into a specific constraint. The tag includes what the user actually said so the PM can see the gap:

User: "search should be fast"
→ RULE-3: Search returns in under 500ms (assumed — user said "fast")

The AI picked 500ms. The user said "fast." The PM decides whether 500ms is right, changes it to 200ms, or confirms it.

**When to add:** only when `purlin:spec` invents a specific number, threshold, algorithm, or constraint that the user didn't explicitly state. NOT when the user was explicit ("must return in under 200ms" → no tag needed).

**When to remove:** PM either confirms the value (change to `(confirmed)`) or edits the value to what they actually want (and removes the tag).

### (confirmed)

Added by the PM to explicitly mark that this exact constraint was reviewed and approved. Optional — rules without any tag are implicitly accepted. Use `(confirmed)` when you want to signal "I specifically chose this value, don't second-guess it."

### (deferred)

Added by PM or engineer when a rule is accepted but not being built yet. Deferred rules are excluded from coverage — `sync_status` shows them as DEFERRED and they don't block VERIFIED status.

Use for: next-sprint features, nice-to-haves accepted into the spec but not yet prioritized, rules that depend on infrastructure not yet available.

Remove the tag when work begins. The rule immediately starts requiring proofs.

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

## Proof Levels

Rules and proofs operate at three levels of confidence. Understanding these levels helps PMs write rules that get the coverage they actually need.

| Level | What it proves | Example rule | Example proof |
|-------|---------------|-------------|--------------|
| **Level 1** | A value exists or has the right type | "Config has a timeout field" | `assert config.timeout is not None` |
| **Level 2** | Code behavior with controlled inputs | "Return 401 on invalid credentials" | `POST wrong password to mock endpoint; verify 401` |
| **Level 3** | End-to-end behavior through the real system | "User sees 'Invalid credentials' on screen" | `Open browser → enter wrong password → verify error message visible @e2e` |

### Why AI writes Level 2 by default

AI agents default to Level 2 because it's fast, deterministic, and easy to mock. Level 2 proofs are correct for most internal logic — but they can pass while the real feature is broken. The mock says the API returns 200, but the real API is misconfigured.

### How to drive Level 3

**Anyone controls the proof level by how they write rules.** Write a rule that describes a real-world outcome and the proof must exercise the real system — there's no way to mock it.

- "Passwords are hashed with bcrypt" → Level 2 (unit test)
- "User enters wrong password and sees 'Invalid credentials' on screen" → Level 3 (must render real UI)
- "Authentication tokens expire and cannot be reused after 30 minutes" → Level 3 (must test real session lifecycle)
- "Service recovers from database failure within 5 seconds" → Level 3 (must kill and restart real DB)

PMs write Level 3 rules for user flows. Security engineers write them for compliance. Architects write them for system guarantees. QA engineers write them for regressions. The pattern is the same: **describe the outcome you need to see, not the function you need to call.**

### Visual proof descriptions

For rules about UI rendering, write proofs that describe **what a person would see**, not DOM selectors or CSS classes. The agent picks the tool (Playwright, headless Chrome, MCP browser, screenshot + vision — whatever is available).

Bad (implementation-coupled):
```
- PROOF-4 (RULE-4): Count table rows with class "fr"; verify count is 8; take screenshot
- PROOF-5 (RULE-5): Click first element matching "tr.fr"; verify element with class "dr" becomes visible
```

Good (outcome-based):
```
- PROOF-4 (RULE-4): Load dashboard with 3 features (3/3 VERIFIED, 2/6 PARTIAL, 0/4 untested).
  Verify the table shows 3 rows. Verify coverage bars are filled proportionally — 3/3 full,
  2/6 roughly one-third, 0/4 empty. Verify status badges read "Verified", "Partial", "Untested".
  Take screenshot @e2e
- PROOF-5 (RULE-5): Load dashboard with features. Click a feature row. Verify a detail panel
  expands showing individual rules with descriptions and proof status. Take screenshot @e2e
```

The key differences: no CSS selectors, no class names, no `querySelector`. The proof says what the user sees — the agent decides how to verify it. This also makes proofs resilient to HTML refactors.

### Anchors for Level 3 enforcement

Anchors are the strongest mechanism for Level 3 enforcement. When anyone writes an anchor with outcome-based rules, every feature that requires it must prove those rules end-to-end:

```markdown
# Anchor: prodbrief_checkout

> Description: Checkout flow requirements from product brief.
> Type: prodbrief
> Source: git@bitbucket.org:acme/product-briefs.git
> Path: briefs/checkout-v2.md
> Pinned: a1b2c3d4

## Rules
- RULE-1: User adds item to cart, proceeds to checkout, enters payment, sees confirmation page
- RULE-2: If payment fails, user sees error and can retry without losing cart contents
- RULE-3: Order confirmation email arrives within 60 seconds

## Proof
- PROOF-1 (RULE-1): Open browser → add item → checkout → enter test card → verify confirmation page shows order number @e2e
- PROOF-2 (RULE-2): Open browser → checkout with declined card → verify error → verify cart intact → retry with valid card → verify confirmation @e2e
- PROOF-3 (RULE-3): Complete checkout → poll inbox for 60s → verify email contains order number @e2e
```

Every feature that `> Requires: prodbrief_checkout` must prove these rules. The engineer can't satisfy them with mocked tests — the rules describe what users see, not what functions return.

### When to write rules at each level

| Level | When to use | Who typically writes |
|-------|------------|---------------------|
| **Level 1** | Never. These are hollow. `assert X is not None` proves nothing. | Nobody |
| **Level 2** | Internal logic, data transformations, error codes, validation, algorithms | Engineer or AI |
| **Level 3** | User-facing flows, multi-system integration, regulatory requirements, things that have broken in production | PM (via prodbrief/spec rules) |

### Recognizing Level 1 proofs (and rejecting them)

If a proof description says "verify X exists", "check that Y is not null", or "assert Z is present" — it's Level 1. Rewrite it to test behavior:

- Level 1: "Verify the login endpoint exists"
- Level 2: "POST to /login with valid credentials; verify 200 and JWT token in response"
- Level 3: "Open browser, enter credentials, click login, verify dashboard loads"

## Tier Assignment

Assign a tier tag based on what the proof requires to execute. Proofs without a tag are `unit` tier.

| Heuristic | Tier | Example |
|-----------|------|---------|
| Pure logic, no I/O, no external dependencies | unit (no tag) | Validate input format, compute hash, parse config |
| Needs database, network, filesystem, or external service | `@integration` | API roundtrip, database query, file system operations |
| Needs browser, full app stack, or UI rendering | `@e2e` | Playwright login flow, screenshot comparison, full page render |
| Requires human judgment — visual, UX, brand voice | `@manual` | Review copy against brand guide, verify layout feels balanced |

**When in doubt, tag `@integration`.** A fast test with an `@integration` tag is harmless. A slow test with no tag blocks the unit tier.

Tier tags are not optional — they control which tests run in which CI stage. Every skill that writes proof descriptions (`purlin:spec`, `purlin:spec-from-code`, `purlin:build`) MUST review tier tags before committing.

Append the tier tag to the end of the proof description line:

```
- PROOF-1 (RULE-1): Parse config file and return default values
- PROOF-2 (RULE-2): POST to /api/users with mock database; verify 201 response @integration
- PROOF-3 (RULE-3): Load checkout page in browser; verify 3-click flow @e2e
- PROOF-4 (RULE-4): Review error messages against brand voice guide @manual
```

**Manual proof detection heuristics:** Source files in `views/`, `pages/`, `templates/`, `layouts/` directories, React/Vue/Svelte components with layout/styling logic, CSS/SCSS files in scope, or code producing HTML output → proofs are likely `@e2e` or `@manual`. Don't write automated proof descriptions for things that can't actually be automated.

## When to Create Anchors

Anchors capture **cross-cutting constraints shared across features**. If 3+ features would have the same rule, it belongs in an anchor.

- Architecture choices shared across features → `api_` or `schema_` prefix
- Security patterns applied everywhere → `security_` prefix (always include FORBIDDEN rules)
- Design system tokens used by multiple components → `design_` prefix

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

- Reference anchors when the feature must follow shared rules or when external constraints apply.
- **Don't reference specs that are just related** — only specs whose rules MUST be proved by this feature's tests. `> Requires:` means "my tests must also prove these rules."
- Verify each reference exists (or is queued for generation) before writing it. Broken references produce silent gaps in coverage.

## `> Scope:` Guidance

Scope lists the source files THIS feature implements. It serves two purposes:
1. **Manual proof staleness detection** — if scope files change after a manual stamp, the stamp goes stale
2. **Documentation** — helps developers find the code that implements a feature

### What to Include

- Files that implement THIS feature's behavior: `src/auth/login.js, src/auth/session.js`
- Test files for this feature: `tests/auth/test_login.py`
- Config files specific to this feature: `src/auth/auth.config.js`

### What NOT to Include

- **Shared utilities** (`utils/helpers.js`, `lib/common.py`) — these change frequently and would make manual proofs stale constantly. If a shared utility changes, your feature's behavior probably didn't change.
- **Framework files** (`package.json`, `tsconfig.json`) — these affect every feature. Including them would make every manual proof stale on every dependency update.
- **Generated files** (`dist/`, `build/`) — these are outputs, not source.
- **Broad directories** (`src/`) — too wide. Scope individual files or narrow directories.

### The Staleness Test

Ask: "If THIS file changes, does it mean my feature's behavior MIGHT have changed?" If yes, include it. If no, leave it out.

- `src/auth/login.js` changes → login behavior might have changed → **include**
- `utils/format-date.js` changes → login behavior didn't change → **exclude**
- `src/auth/auth.config.js` changes → login config might affect behavior → **include**
- `package.json` changes → probably just a dependency bump → **exclude**

### Tight Scope = Useful Staleness Detection

A feature with 3 files in scope gets meaningful staleness alerts. A feature with 50 files in scope gets constant false alarms and developers start ignoring the alerts.

### Existing Rules

- Verify each file path exists on disk before listing it.
- Not used for verification hashing — purely informational for navigation and staleness.

## Spec Categories

Where different types of specs belong. Both `purlin:spec` and `purlin:spec-from-code` use this to determine the output directory.

| Category dir | What goes here | Tier expectations | Example |
|-------------|---------------|-------------------|---------|
| Component dirs (`hooks/`, `mcp/`, `proof/`) | Behavioral specs for executable code | Unit tier for unit-level proofs | `specs/hooks/gate-hook.md` |
| `schema/` | Anchors defining formats, contracts, and cross-cutting standards | Unit tier | `specs/schema/schema_spec_format.md` |
| `integration/` | **Legacy — avoid creating new specs here.** E2E rules belong in the feature spec they validate, tagged `@e2e`. | All proofs tagged `@e2e` | *(migrate existing to feature specs)* |
| `instructions/` | Structural specs for agent instructions — reference docs, skill definitions, agent definitions | Unit tier (grep-based structural checks) | `specs/instructions/purlin_references.md` |

### Guidelines

- **Executable code** (scripts, hooks, MCP server) → spec category matches the source directory.
- **Cross-cutting contracts** (file formats, schemas, security rules) → `schema/`.
- **AI instructions** (`references/`, `skills/`, `agents/`) → `instructions/`. Rules verify sections exist and contain required content. Proofs are grep-based. These catch accidental deletions and structural drift.
- **E2E rules belong in the feature they validate.** If an e2e test proves that `sync_status` reads proofs from multiple tiers, that rule belongs in `specs/mcp/sync_status.md` tagged `@e2e` — not in a separate `e2e_multi_tier.md`. Test tier (`@unit`, `@e2e`) is a proof attribute, not a reason to create a separate spec.
- **Never create test-only specs.** A spec like `e2e_feature_scoped_overwrite` that exists solely to hold integration tests should not exist. Those tests prove `proof_plugins` RULE-4. Wire them there.

## Audience-Appropriate Language

Specs, drift reports, and other reports serve different audiences. Match the language to the reader:

| Artifact | Audience | Language |
|----------|----------|----------|
| Spec rules and proofs | Engineers and agents | Precise, technical — status codes, function names, exact inputs |
| Drift report CHANGED BEHAVIOR | PMs and QA | User-visible impact — "login is faster", "error message changed" |
| Drift report NO IMPACT | Engineers | Implementation details — "refactored middleware", "updated dependency" |
| Verification reports | Engineers and CI | Concise, structured — feature names, rule counts, directives |

**The test for good drift report language:** Could a PM read this line and understand whether it affects users? If not, rephrase or move it to NO IMPACT. "Fixed N+1 query in user list resolver" → "User list page loads faster" (CHANGED BEHAVIOR) + "Optimized database query in user list resolver" (NO IMPACT).

## Test Quality Rules

These rules apply when writing or reviewing any proof-marked test. Violating them produces HOLLOW or WEAK assessments during audit (see `references/audit_criteria.md` for assessment criteria):

- **Assert behavior, not implementation.** Test outputs and side effects, not whether code exists.
- **Test the attack, not the defense.** Send bad input and assert the error, don't assert that validation code is present.
- **Never assert True.** Every assertion must check a specific expected value.
- **Use realistic data.** No empty strings or single-element arrays as representative inputs.
- **No self-mocking.** Mock external dependencies (network, filesystem), not the code under test.

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
