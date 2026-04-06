> Criteria-Version: 14

# Proof Audit Criteria

This document defines how `purlin:audit` evaluates whether test code actually proves what the proof description claims. The audit pipeline has three stages: a pre-filter (Pass 0) excludes structural checks, deterministic static analysis (Pass 1) catches structural test defects like `assert True` and logic mirroring, and LLM semantic evaluation (Pass 2) checks whether tests actually prove their rules. The first two are fast and always run. The LLM stage runs only for proofs that survive the first two. To use custom criteria, set `audit_criteria` in `.purlin/config.json` (see below).

## Assessment Levels

| Level | Symbol | Meaning | Determined by |
|-------|--------|---------|---------------|
| STRONG | ✓ | Test meaningfully proves the rule — assertions match proof description, tests real behavior | Pass 2 (LLM) |
| WEAK | ~ | Test partially proves the rule — missing assertions, only happy path, looser than described | Pass 2 (LLM) |
| HOLLOW | ✗ | Test passes but doesn't prove the rule — structural defect caught deterministically | Pass 1 (static) |
| MANUAL | ● | Human-verified via @manual stamp — assess staleness only | Either pass |

## Pre-filter: Structural Check Exclusion (Pass 0 — deterministic)

Before evaluating individual proofs, classify each proof description as structural or behavioral.

**Structural** — proof describes file/string presence checks: grep for pattern, file exists, section exists, field present, contains string/line. These verify document content, not system behavior.

**Behavioral** — proof describes observable outcomes: returns, rejects, blocks, sends, creates, renders, computes, detects. These verify the system does what the rule claims.

Structural proofs are **excluded from the audit**. They are not assessed, not scored, and not included in the integrity score. They still run as checks in the test suite, but they are not proofs.

Classification uses `_classify_description` in `static_checks.py`: backtick-enclosed content is stripped before matching (to prevent code patterns like `create.*commit` from triggering behavioral verbs), structural patterns are checked before behavioral patterns, and unmatched descriptions default to behavioral (safer to audit than to exclude).

### Per-proof filtering in mixed specs

When a spec has both structural and behavioral proofs, `check_spec_coverage` returns `structural_proof_ids` listing which specific PROOF-N identifiers are structural. The auditor uses this list to exclude individual proofs rather than only excluding entire structural-only specs. This ensures mixed specs have their structural proofs excluded while behavioral proofs are still audited.

Only behavioral proofs proceed to Pass 1 (static analysis) and Pass 2 (LLM evaluation).

## Pass 1 — Deterministic Checks (static_checks.py)

These are caught by static analysis (`scripts/audit/static_checks.py`). No LLM involved. A proof that fails any deterministic check is HOLLOW — no override possible.

### HOLLOW (always caught)

- **Tautological assertions** — `assert True`, `assert result is not None`, `assert len(x) >= 0`, `self.assertTrue(True)`. These are true regardless of code behavior
- **No assertion statements** — test function body contains zero assertion statements (`assert`, `self.assert*`, `pytest.raises`, `expect`). Test runs code but checks nothing
- **Bare `except: pass`** — `except:` or `except Exception:` followed by `pass` around the code being tested. Failures are silently swallowed
- **Logic mirroring** — the expected value is computed by the same function as the system under test. Example: `expected = hash_func(input); assert result == expected` where `hash_func` is the same code being tested. If the function has a bug, the test confirms the bug. Expected values must be literal constants or derived from an independent source
- **Mock target match** — a `@patch` or `mock.patch` target contains the exact function name that the rule describes. Example: `@patch("auth.bcrypt.checkpw")` on a test proving a rule about bcrypt. The mock replaces the very behavior the rule requires

### Shell-specific checks

- **Hardcoded pass** — `purlin_proof ... pass` with no preceding test logic (the result is hardcoded, not based on a check). Note: if/else pairs where the same proof ID appears in both branches (one pass, one fail) are recognized as conditional proofs — the if-condition is the assertion, and they are NOT flagged
- **No assertion commands** — no `test`, `[`, `grep`, `diff`, or `||` patterns between proof markers

### JavaScript/TypeScript-specific checks

- **`expect(true).toBe(true)`** — tautological, same as `assert True`
- **No `expect()` calls** — test function body contains no assertions

### Proof-file structural checks (Pass 0.5 — language-agnostic)

These checks operate on proof JSON files, not source code. They work for any language that emits proof files.

- **Proof ID collision** — the same PROOF-N identifier appears in the proof file targeting different RULE-N values. This confuses proof tracking: one test's coverage may shadow another's, and the proof system cannot distinguish which test proves which rule. The test with the colliding ID must be reassigned a unique proof ID, or the extra marker must be removed
- **Proof rule orphan** — a proof entry targets a RULE-N that does not exist in the spec file. This typically means the rule was removed or renumbered, but the test's proof marker was not updated. The proof claims to cover a non-existent rule

## Pass 2 — Semantic Alignment (LLM)

The LLM evaluates whether the test semantically matches the rule. It does NOT check structural issues — those are handled by Pass 1. The LLM can only return STRONG or WEAK (or EXCLUDED for the structural guard below).

### Structural proof guard (LLM backup)

If a proof reaches Pass 2 despite Pass 0 filtering and describes file/string presence checks rather than system behavior (e.g. reads a file and checks for string patterns, section headings, field existence — without exercising any production code), respond with `ASSESSMENT: EXCLUDED` and `CRITERION: structural presence check — not a behavioral proof`. This catches proofs that slipped past Pass 0's regex classification. The pipeline excludes these from the integrity score rather than marking them STRONG.

### WEAK (LLM judgment)

- Proof description says "verify X AND Y" but test only checks X
- Test checks status code but not response body when proof mentions both
- Test only covers the happy path when the rule implies error handling
- Assertion is looser than the proof description ("greater than 0" when proof says "exactly 3")
- For API tests: checks status code but not the response shape or content
- **Deep mocking** — for critical paths (auth, payments, data integrity), the test mocks the data-persistence layer entirely (database connector, file system, external API) rather than using an ephemeral real version (in-memory database, temp directory, test server). The test exercises application logic but the state is artificial — a real database constraint violation or network timeout would not be caught
- **Assertion farming** — multiple assertions on the same object that test individual properties redundantly (`assert user.email is not None`, `assert "@" in user.email`, `assert len(user.email) > 5`) instead of one meaningful check (`assert user.email == "alice@example.com"` or schema validation)
- **Missing negative test for constraint rules** — when the rule describes rejection or constraint behavior ("reject passwords under 8 characters", "block after 5 failed attempts"), the test only checks the happy path (valid password accepted). STRONG requires at least one negative test proving the constraint rejects what it should
- **Catch-all assertions** — `assert resp.json()` (truthy check) instead of checking specific fields
- **String containment instead of equality** — `assert "error" in resp.text` when the proof says "verify error message is 'invalid_credentials'"
- **Time-dependent tests without mocked clock** — `assert elapsed < 1.0` depends on machine speed, not code correctness
- **Tautological escape hatch** — the assertion contains an OR/||/or branch that always evaluates to True, typically a comparison between test constants, fixture data, or literal values that makes the assertion pass regardless of what the code under test returns. Examples: Python `assert func() > 0 or CONSTANT not in OTHER_CONSTANT`, JavaScript `expect(result > 0 || FIXTURE === FIXTURE).toBe(true)`, Go `if result > 0 || expectedConst != "" { t.Log("ok") }`. The escape hatch may not be obvious — look for OR branches where both operands are defined in test setup rather than derived from code-under-test output
- **Assertion validates test data, not code output** — the test's primary assertions check properties of the test's own setup data (constants, fixtures, mock return values) rather than output from the system under test. The test proves the test is correctly set up, not that the code works
- **Name/value drift** — the test function name makes a numeric or behavioral claim (e.g. "fourteen_entries", "rejects_invalid") that contradicts the actual assertion values or logic (asserts 12, or doesn't test rejection). This suggests the code changed and the test was patched to pass without updating the name
- **Fragile string parsing in assertions** — the assertion uses string splitting, slicing, or indexing to extract a value for comparison where a simpler direct check would be more robust. Example: `result.split('WARNING')[0]` to isolate a feature's output — this breaks with multiple features or reordered output

### STRONG (LLM judgment)

A proof is STRONG when ALL of these are true:

- Every assertion in the test corresponds to a claim in the proof description
- Test exercises real code paths (not mocked abstractions of the thing being tested)
- Test inputs match or are equivalent to the inputs described in the proof
- Expected outputs match the proof description's expected outcomes
- For negative tests: actually attempts the bad input and verifies rejection
- For FORBIDDEN proofs: greps the real codebase, not a test fixture

### Quality factors that strengthen STRONG

- Test uses `pytest.raises` or equivalent for expected exceptions
- Test has explicit setup and teardown (fixtures, context managers)
- Test asserts specific values, not just types or truthiness
- Test exercises exactly one code path per assertion
- Test name describes the scenario, not the implementation

For test writing guidelines (assert behavior not implementation, realistic data, no self-mocking), see `references/spec_quality_guide.md` § Test Quality Rules.

## Scoring

Integrity score = (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) × 100%

The denominator includes only proofs that have been audited (STRONG + WEAK + HOLLOW + MANUAL). Rules with no proof at all (NONE) are excluded from both numerator and denominator — integrity measures proof quality only, while coverage (proved/total rules) is reported separately by purlin:status. Structural checks are excluded from both numerator and denominator. WEAK proofs count as 0 (they need strengthening). HOLLOW proofs count as 0 (they need rewriting).

## Finding Priority

Audit findings are grouped by the value of fixing them — how much real coverage the fix adds.

| Tier | What it catches | Fix value |
|------|----------------|-----------|
| CRITICAL | Test proves nothing (no assertions, bare except, literal assert True) | Highest — the test is functionally absent |
| HIGH | Real coverage gap (missing assertions, happy-path only, no negative test) | High — real behavior is untested |
| MEDIUM | Self-confirming test (logic mirroring, mock target match) | Medium — test passes but could confirm bugs |
| LOW | Weak assertion form (heuristic assert_true, assertion farming) | Low — test works but assertions are imprecise |

When reporting, group findings by tier. When fixing (manually or via builder), work top-down: CRITICAL first, then HIGH, MEDIUM, LOW. This ensures the highest-value fixes happen first, regardless of how many low-value findings exist.

**Pass 1 (deterministic) tier mapping by check name:**

- CRITICAL: `assert_true` (when `literal: true`), `no_assertions`, `bare_except`
- MEDIUM: `logic_mirroring`, `mock_target_match`
- LOW: `assert_true` (when `literal: false` — heuristic patterns like `assert x is not None`)

**Pass 2 (LLM) tier mapping by criterion:**

- HIGH: any WEAK with "missing" in criterion, "only happy path", "only checks", deep mocking, missing negative test for constraint rules
- LOW: assertion farming, catch-all assertions, string containment instead of equality, time-dependent tests

## Audit Caching

To avoid redundant LLM calls, audit results are cached in `.purlin/cache/audit_cache.json`.

### Cache key

The cache key is `sha256(rule_text + "\0" + proof_description + "\0" + test_function_code)[:16]`. The null-byte separator prevents input-shifting collisions (e.g. a `|` in rule text causing two different inputs to hash identically). If any of these three inputs change, the cache is invalidated for that proof and Pass 2 re-runs.

### Cache behavior

- Cache hits skip Pass 2 entirely — the cached STRONG/WEAK assessment is reused
- Pass 0 (structural-only) and Pass 1 (deterministic) ALWAYS run — they are not cached. A test that was STRONG last time could have been edited to `assert True` — Pass 1 must catch this.
- Cache misses go through Pass 2 normally, and the result is stored in the cache
- The cache file is gitignored (per-machine, not shared)

### Cache invalidation

The cache self-invalidates per-proof when:
- The spec rule text changes (rule was reworded)
- The proof description changes (proof was rewritten)
- The test function code changes (test was modified)

No manual invalidation is needed. To force a full re-audit, delete `.purlin/cache/audit_cache.json`.

## Design Anchor Proofs

Design anchors (`design_*` specs) use a thin visual-match model: one rule per viewport saying "match the design," one screenshot comparison proof per rule. Behavioral proofs belong in the feature spec, not the anchor.

### What a design anchor proof must do

- Render the real component (not mock DOM, not stylesheet inspection)
- Capture a screenshot at the same viewport size as the Figma frame
- Compare against the original source (Figma screenshot or reference image)
- Be tagged `@e2e`

### Automatic HOLLOW

- **Stylesheet inspection without rendering** — test reads CSS/style values directly instead of rendering the component and comparing screenshots. The component might not render at all and the test would still pass
- **Mocked DOM** — test creates a fake DOM structure instead of rendering the real component. Proves the mock, not the code

### Automatic WEAK

- **Missing screenshot comparison proof** — anchor has `> Visual-Reference:` but no screenshot comparison proof. Without it, visual drift from the reference is not caught
- **Wrong viewport size** — Figma frame is 428px wide but test renders at 1024px. The comparison must use the same viewport size as the design
- **Missing `@e2e` tag** — all design proofs require rendering and must be tagged `@e2e`
- **Behavioral proofs in anchor** — behavioral proofs (click, type, select) belong in the feature spec that requires the anchor, not in the anchor itself

## Anchor Rules

When auditing proofs for rules that come from anchors (via `> Requires:` or `> Global: true`), the audit cannot recommend changing the rule — anchor files are read-only and externally owned.

For HOLLOW or WEAK proofs on anchor rules:
- Recommend strengthening the TEST to fully satisfy the rule as written
- If the rule itself seems wrong or unclear, output a separate "Recommendations for Anchor Author" section with the suggested change and the anchor source (`> Source:` URL)
- Format: `→ Recommend to anchor author (<source>): RULE-N could be clearer — suggest: <proposed rewording>`

The anchor rule is the contract. The test must satisfy it. If the contract is bad, flag it — but don't change it.

## External LLM Auditing

When Purlin is configured with an external audit LLM (`audit_llm` in config), the full contents of this criteria document are included in the prompt sent to the external LLM. The external LLM evaluates tests against these exact criteria.

This eliminates shared-model bias: the builder (Claude) and auditor (e.g., Gemini) use different model weights, different training data, and different biases. If Claude writes a subtly flawed test, the external LLM evaluates it independently.

The audit criteria must be self-contained and unambiguous — the external LLM has no other context about Purlin. Every assessment level, every detection heuristic, and every quality check must be fully described in this document.

## Additional Team Criteria

Teams can add additional criteria that are **appended** to these built-in defaults. Built-in criteria always apply and cannot be weakened — additional criteria only add stricter checks.

```json
// .purlin/config.json
{
  "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "a1b2c3d4"
}
```

When `audit_criteria` is set, `purlin:init --sync-audit-criteria` caches the external file locally. The `load_criteria()` function in `scripts/audit/static_checks.py` assembles the combined criteria (built-in + additional) — this is the single source for criteria loading logic. The `audit_criteria_pinned` SHA ensures reproducible audits.

To sync: `purlin:init --sync-audit-criteria` pulls the latest version, saves to `.purlin/cache/additional_criteria.md`, and updates the pinned SHA.
