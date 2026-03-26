**Purlin mode: Engineer (QA cross-mode: verify-only)**

Purlin agent: This skill activates Engineer mode. If QA mode is active, runs in verify-only cross-mode (can run tests and read results but cannot modify application code).

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.
> **Companion files:** See `instructions/references/active_deviations.md` for deviation format and PM review protocol.
> **Test infrastructure:** See `instructions/references/test_infrastructure.md` for result schemas, harness types, status interpretation, and smoke tier rules.

---

## Scope

If an argument was provided, run the testing protocol for `features/<arg>.md`.
If no argument was provided, run the testing protocol for the feature currently being implemented (from the active `/pl-build` session context).

Read the feature spec to determine the feature type (Python tool, shell script, Claude skill, web UI). Load the companion file (`features/<name>.impl.md`) if it exists.

---

## Section 1 -- The Cardinal Rule

**Grepping or reading source code to verify its presence is NOT testing.**

Engineer mode MUST NEVER verify a feature by opening source files and checking whether code exists, patterns match, or strings are present. That validates structure, not behavior. A test MUST import, call, or execute the implementation and assert on its outputs.

If your test file contains `open('features/...')` or `open('instructions/...')` and reads file contents as part of the assertion, STOP. You are writing an AP-1 test (see Section 3).

---

## Section 2 -- Test Requirements by Feature Type

What constitutes behavioral testing depends on the feature category:

| Feature Type | Behavioral Test Approach |
|---|---|
| Python tool features | Import and call the implementation functions. Assert return values, side effects, and error conditions against expected outcomes. |
| Claude skill/command features | Test the infrastructure the skill depends on (parsers, validators, state management), not string presence in the command markdown file. |
| Shell script features | Execute the script with controlled arguments. Assert exit codes, stdout content, and filesystem side effects. |
| Web UI features | Interact with rendered DOM or API endpoints. Assert response content, status codes, and state changes. Unit tests + `/pl-web-test` for visual features. |

### Test Tier Decision Matrix

Defines what Engineer mode runs during Step 3 versus what defers to the Regression tier (see `arch_testing.md` Execution Tiers).

| Feature Type | Step 3 Testing | Regression Tier |
|---|---|---|
| Python tool | Unit tests (pytest): import and call functions, assert values | Regression harness if applicable |
| Shell script | Execute with args, assert exit codes and output | Regression harness if applicable |
| Web UI with `> Web Test:` | Unit tests + web test spot check (visual verification) | Full web test regression |
| Web UI without `> Web Test:` | Unit tests only | N/A |
| Claude skill/command | Test infrastructure (parsers, validators, state) | Regression harness for interaction flow |

**Engineer rule:** Run `/pl-web-test` during Step 3 ONLY for features with `> Web Test:` metadata AND a Visual Specification section. All other features: unit tests only.

### Fixture Exclusion

Fixture-based testing (checkout fixture state, run harness against snapshot) is regression-tier work owned by QA. Do not set up fixtures during `/pl-unit-test`. If a scenario requires fixture state, log `[DISCOVERY: scenario requires fixture -- defer to regression tier]` in the companion file.

---

## Section 3 -- Anti-Pattern Checklist

Five named anti-patterns Engineer mode MUST check against during the self-audit. Each includes a concrete BAD/GOOD example.

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

### Assertion Quality Cross-Reference

The assertion quality invariants (positive/negative test pairing, assertion tightening tiers) are defined in `arch_testing.md` Section "Assertion Quality Invariant." The anti-patterns above complement those invariants: the anti-patterns describe what bad tests look like (pattern recognition), while the assertion quality invariant describes how to verify that tests are meaningful (structural guarantee). Both MUST be satisfied.

---

## Section 4 -- Quality Rubric Gate

Hard gate -- all 6 checks MUST pass before `tests.json` is written. If any item fails: fix tests, re-run, re-audit. No `tests.json` until clean.

1. **DELETION TEST**: If the implementation under test were deleted, would at least one test fail? A test that passes without the implementation is not a test -- it is a checkbox.
2. **BEHAVIORAL VERIFICATION**: Does every test import, call, or execute the implementation and assert on output? No tests that only read source files.
3. **VALUE ASSERTIONS**: Does every test contain at least one value-verifying assertion (`assertEqual`, `assert x == expected`)? Presence-only assertions alone do not count. (See Minimum Assertion Depth below.)
4. **ANTI-PATTERN FREE**: Every test passes all 5 AP checks from Section 3.
5. **REPRESENTATIVE INPUTS**: Tests use realistic data shapes, not empty/trivial inputs.
6. **NO SELF-MOCKING**: Mocks limited to external deps (network, filesystem, clock). Code under test called for real.

### Minimum Assertion Depth

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

---

## Section 5 -- Result Reporting

*   **`tests.json` MUST be produced by an actual test runner** -- never hand-written.
*   **Required fields:** `status`, `passed`, `failed`, `total`. `total` MUST be > 0.
*   **Output location:** `tests/<feature_name>/tests.json` at the project root, where `<feature_name>` matches the feature file stem from `features/`.
*   **Inline harness pattern:** Test files that use the inline harness pattern (`record()` / `write_results()`) MUST be executed directly (`python3 <path>/test_file.py`), not via pytest -- only direct execution triggers `write_results()`.
*   **Self-validation:** After writing `tests.json`, verify: required fields present, `total > 0`, `passed + failed == total`, `status` matches (`PASS` if `failed == 0`, `FAIL` otherwise).

---

## Section 6 -- Companion File Audit Record

After the rubric passes, record in `features/<name>.impl.md` under `### Test Quality Audit`:

```
### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: N total, N passed
- AP scan: clean
- Date: YYYY-MM-DD
```
