# Policy: Test Quality Standards

> Label: "Policy: Test Quality Standards"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

## 1. Purpose

Codifies test quality standards to prevent shallow tests that pass structural validation (tests.json schema, keyword traceability) but do not verify behavioral outcomes. The Critic validates that tests exist and trace to scenarios; this policy defines what those tests must actually do to be meaningful.

## 2. Test Quality Invariants

### 2.1 The Deletion Invariant

If the implementation under test were deleted, at least one test per automated scenario MUST fail. This is the minimum bar for test quality. A test that passes without the implementation is not a test -- it is a checkbox.

### 2.2 Anti-Pattern Taxonomy

Five named anti-patterns the Builder MUST check against during the self-audit. Each includes a concrete BAD/GOOD example.

**AP-1: Prose Inspection**
Test reads a documentation, markdown, or instruction file and asserts string presence instead of importing and calling the implementation code.

- BAD: `content = open('features/my_feature.md').read(); assert 'retry logic' in content`
- GOOD: `result = retry_operation(failing_func, max_retries=3); assertEqual(result.attempts, 3)`

**AP-2: Structural Presence**
Test checks that a key, section, or element exists without verifying its value or correctness.

- BAD: `assertIn('status', result)`
- GOOD: `assertEqual(result['status'], 'PASS')`

**AP-3: Mock-Dominated**
Test mocks the implementation under test then asserts the mock was called, verifying wiring rather than behavior. Mocks of external dependencies (network, filesystem, clock) are acceptable; mocks of the code path being tested are not.

- BAD: `mock_process = Mock(return_value={'ok': True}); result = run(mock_process); mock_process.assert_called_once()`
- GOOD: `result = process_real_input(sample_data); assertEqual(result['status'], 'ok')`

**AP-4: Tautological Assertion**
Asserts something that is always true regardless of whether the implementation is correct. Type checks on functions with typed signatures, None checks on required return values, and isinstance checks when the constructor guarantees the type.

- BAD: `assertIsInstance(result, dict)` (when the function signature guarantees dict)
- GOOD: `assertEqual(result['computed_value'], expected_value)`

**AP-5: Representative Input Neglect**
Tests use toy data (empty strings, single-element lists, trivially small inputs) that do not resemble real inputs, missing failure modes that occur with actual data shapes. A test that exercises the mechanism with synthetic data while the real input (CLI output, API response, complex config) goes untested is verifying plumbing, not behavior.

- BAD: `result = parse_config('{}'); assertIsNotNone(result)`
- GOOD: `result = parse_config(SAMPLE_REAL_CONFIG); assertEqual(result['database']['host'], 'localhost'); assertEqual(len(result['features']), 5)`

### 2.3 Test Classification by Feature Type

What constitutes behavioral testing depends on the feature category:

| Feature Type | Behavioral Test Approach |
|---|---|
| Python tool features | Import and call the implementation functions. Assert return values, side effects, and error conditions against expected outcomes. |
| Claude skill/command features | Test the infrastructure the skill depends on (parsers, validators, state management), not string presence in the command markdown file. |
| Shell script features | Execute the script with controlled arguments. Assert exit codes, stdout content, and filesystem side effects. |
| Web UI features | Interact with rendered DOM or API endpoints. Assert response content, status codes, and state changes. |

### 2.4 Minimum Assertion Depth

Each test function MUST include at least one value-verifying assertion -- an assertion that checks a specific expected value, not merely presence or type.

Value-verifying assertions (count toward minimum):
- `assertEqual(result, expected)`
- `assert result['key'] == 'specific_value'`
- `assertEqual(exit_code, 0)`

Presence-only assertions (do NOT count alone):
- `assertIn('key', result)` without verifying `result['key']`
- `assertTrue(os.path.exists(path))` without verifying file contents
- `assertIsNotNone(result)` without verifying result value

A test MAY use presence-only assertions alongside value-verifying assertions. The mandate is that presence-only assertions alone are insufficient.

### 2.5 Test Tier Decision Matrix

Defines what the Builder runs during Step 3 versus what defers to the Regression tier (see `arch_automated_feedback_tests.md` Execution Tiers).

| Feature Type | Step 3 Testing | Regression Tier |
|---|---|---|
| Python tool | Unit tests (pytest): import and call functions, assert values | AFT:Agent if applicable |
| Shell script | Execute with args, assert exit codes and output | AFT:Agent if applicable |
| Web UI with `> AFT Web:` | Unit tests + AFT:Web spot check (visual verification) | Full AFT:Web regression |
| Web UI without `> AFT Web:` | Unit tests only | N/A |
| Claude skill/command | Test infrastructure (parsers, validators, state) | AFT:Agent for interaction flow |

**Builder rule:** Run AFT:Web during Step 3 ONLY for features with `> AFT Web:` metadata AND a Visual Specification section. All other features: unit tests only.

### 2.6 Subagent Test Quality Evaluation

After writing tests and before committing, the Builder MUST spawn Haiku subagents to independently evaluate test quality. This replaces the manual "audit against AP-1 through AP-5" with actual enforcement.

**Protocol:**

1. For each automated scenario, identify the corresponding test function(s).
2. Spawn subagents **in parallel** (one per scenario-test pair, Haiku model).
3. Each subagent receives:
   - The Gherkin scenario text (Given/When/Then)
   - The test function body
   - The evaluation criteria (deletion invariant, AP-1 through AP-5, minimum assertion depth)
4. Each subagent returns:
   - Verdict: `ALIGNED` | `PARTIAL` | `DIVERGENT`
   - Reasoning: brief explanation
   - Fix suggestion: specific improvement if not ALIGNED
5. Builder reads all verdicts:
   - **DIVERGENT:** MUST fix the test before committing (mandatory).
   - **PARTIAL:** SHOULD improve (recommended, not blocking).
   - **ALIGNED:** Pass.
6. Record verdicts in the companion file (`features/<name>.impl.md`) under a `### Test Quality Audit` heading:
   ```
   ### Test Quality Audit
   Evaluated via Haiku subagent (2026-03-18)
   - Scenario: Single-turn test produces structured output -> test_single_turn -> ALIGNED
   - Scenario: Multi-turn test resumes session -> test_multi_turn -> ALIGNED
   - Scenario: Fixture tag missing causes skip -> test_fixture_skip -> PARTIAL (uses empty string instead of realistic tag)
   ```
7. Skip entirely if the feature has zero automated scenarios (no cost).

**Efficiency guarantees:**

- All subagents run in parallel -- wall clock approximately 2-3 seconds total regardless of count.
- Haiku model only (cheapest, fastest).
- Focused prompt (scenario + test body only, no codebase exploration needed).
- No Critic slowdown -- evaluation happens at build time, not audit time.

**Why subagents instead of manual self-audit:**

- Independent evaluator (addresses trust model -- not the same "brain" that wrote the test).
- Catches AP-1 through AP-4 programmatically, not advisorily.
- Immediate feedback with fix suggestions -- Builder fixes in-context, not after the fact.
- Auditable record in companion file.
- Backstop: `policy_critic.md` Section 2.17 generates a LOW-priority Builder action item when the `### Test Quality Audit` section is missing from the companion file.

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
