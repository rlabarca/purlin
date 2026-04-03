> Criteria-Version: 5

# Proof Audit Criteria

This document defines how `purlin:audit` evaluates whether test code actually proves what the proof description claims. The audit skill reads this file at runtime. To use custom criteria, set `audit_criteria` in `.purlin/config.json` (see below).

## Assessment Levels

| Level | Symbol | Meaning |
|-------|--------|---------|
| STRONG | ✓ | Test meaningfully proves the rule — assertions match proof description, tests real behavior |
| WEAK | ~ | Test partially proves the rule — missing assertions, only happy path, looser than described |
| HOLLOW | ✗ | Test passes but doesn't prove the rule — mocks the thing being tested, tautological |
| MANUAL | ● | Human-verified via @manual stamp — assess staleness only |

## HOLLOW Detection (test proves nothing)

A proof is HOLLOW when ANY of these are true:

- Test contains `assert True`, `assert result is not None`, or `assert len(x) >= 0`
- Test mocks the exact function the rule is about (rule says "bcrypt hashing", test mocks bcrypt.checkpw)
- Test setup creates the expected output, then test asserts that same value back
- Test has no assertions (runs code but checks nothing)
- Test asserts a mock's return value (mock returns 200, test asserts 200)
- For FORBIDDEN proofs: test greps a mock filesystem instead of the real codebase
- **Logic mirroring** — the expected value is calculated at runtime using the same function or logic as the system under test. Example: `expected = hash_func(input); assert result == expected` where `hash_func` is the same code being tested. If the function has a bug, the test confirms the bug. Expected values must be literal constants or derived from an independent source

## WEAK Detection (test partially proves)

A proof is WEAK when ANY of these are true:

- Proof description says "verify X AND Y" but test only checks X
- Test checks status code but not response body when proof mentions both
- Test only covers the happy path when the rule implies error handling
- Assertion is looser than the proof description ("greater than 0" when proof says "exactly 3")
- Test uses hardcoded expected values that coincidentally match the mock, not real behavior
- For API tests: checks status code but not the response shape or content
- **Deep mocking** — for critical paths (auth, payments, data integrity), the test mocks the data-persistence layer entirely (database connector, file system, external API) rather than using an ephemeral real version (in-memory database, temp directory, test server). The test exercises application logic but the state is artificial — a real database constraint violation or network timeout would not be caught
- **Assertion farming** — multiple assertions on the same object that test individual properties redundantly (`assert user.email is not None`, `assert "@" in user.email`, `assert len(user.email) > 5`) instead of one meaningful check (`assert user.email == "alice@example.com"` or schema validation). Redundant property-level assertions create brittle tests that break on irrelevant formatting changes
- **Missing negative test for constraint rules** — when the rule describes rejection or constraint behavior ("reject passwords under 8 characters", "block after 5 failed attempts"), the test only checks the happy path (valid password accepted). STRONG requires at least one negative test proving the constraint rejects what it should

## STRONG Detection (test meaningfully proves)

A proof is STRONG when ALL of these are true:

- Every assertion in the test corresponds to a claim in the proof description
- Test exercises real code paths (not mocked abstractions of the thing being tested)
- Test inputs match or are equivalent to the inputs described in the proof
- Expected outputs match the proof description's expected outcomes
- For negative tests: actually attempts the bad input and verifies rejection
- For FORBIDDEN proofs: greps the real codebase, not a test fixture

## Test Code Quality (independent of proof description)

Beyond matching the proof description, the audit checks the test code itself for patterns that produce unreliable results:

### Automatic HOLLOW (regardless of proof match)

- **Bare `except: pass`** or `except Exception: pass` around the code being tested — failures are silently swallowed
- **No setup for the asserted value** — the variable being asserted was never assigned in the test (relies on leaked state from another test)
- **Assert on a literal** — `assert "login" == "login"` or `assert 200 == 200` without any code execution producing the value

### Automatic WEAK (regardless of proof match)

- **Catch-all assertions** — `assert resp.json()` (truthy check) instead of checking specific fields
- **String containment instead of equality** — `assert "error" in resp.text` when the proof says "verify error message is 'invalid_credentials'"
- **No negative assertion** — test only checks the happy path when the rule describes a constraint that should reject bad input
- **Setup and assertion in different scopes** — value assigned in a try block, asserted outside it without verifying the try succeeded
- **Time-dependent tests without mocked clock** — `assert elapsed < 1.0` depends on machine speed, not code correctness

### Quality factors that strengthen STRONG

- Test uses `pytest.raises` or equivalent for expected exceptions
- Test has explicit setup and teardown (fixtures, context managers)
- Test asserts specific values, not just types or truthiness
- Test exercises exactly one code path per assertion
- Test name describes the scenario, not the implementation

## Scoring

Integrity score = (STRONG count + MANUAL count) / total proofs x 100%

WEAK proofs count as 0 (they need strengthening). HOLLOW proofs count as 0 (they need rewriting).

## Figma Design Proofs

Design invariant proofs (from `i_design_*` specs) have additional criteria:

### Automatic HOLLOW

- **Stylesheet inspection without rendering** — test reads CSS/style values directly (parsing source files or stylesheets) instead of rendering the component and checking computed styles. The component might not render at all and the test would still pass
- **Mocked DOM** — test creates a fake DOM structure matching expected values instead of rendering the real component. Proves the mock, not the code

### Automatic WEAK

- **Visual-only coverage for behavioral rules** — the invariant has behavioral rules from annotations (interactions, validation, state changes) but all proofs only check CSS properties. Behavioral rules require interaction tests (click, type, select), not style checks
- **Missing `@e2e` tag** — all Figma proofs require rendering and must be tagged `@e2e`. Untagged Figma proofs will run in the default tier where they're likely to fail due to missing rendering infrastructure

See [references/figma_extraction_criteria.md](figma_extraction_criteria.md) for the full extraction criteria.

## Invariant Rules

When auditing proofs for rules that come from invariants (via `> Requires:` or `> Global: true`), the audit cannot recommend changing the rule — invariant files are read-only and externally owned.

For HOLLOW or WEAK proofs on invariant rules:
- Recommend strengthening the TEST to fully satisfy the rule as written
- If the rule itself seems wrong or unclear, output a separate "Recommendations for Invariant Author" section with the suggested change and the invariant source (`> Source:` URL)
- Format: `→ Recommend to invariant author (<source>): RULE-N could be clearer — suggest: <proposed rewording>`

The invariant rule is the contract. The test must satisfy it. If the contract is bad, flag it — but don't change it.

## Custom Criteria

Teams can override this file by pointing to an external version:

```json
// .purlin/config.json
{
  "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "a1b2c3d4"
}
```

When `audit_criteria` is set, the audit skill fetches and uses the external file instead of this one. The `audit_criteria_pinned` SHA ensures reproducible audits — the criteria don't change unless explicitly updated.

To sync: `purlin:init --sync-audit-criteria` pulls the latest version and updates the pinned SHA.
