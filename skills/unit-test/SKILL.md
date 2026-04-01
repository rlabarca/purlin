---
name: unit-test
description: Run tests and emit proof files with coverage report
---

Run tests (default tier unless `--all`), emit proof files via feature-scoped overwrite, and report coverage per feature.

## Usage

```
purlin:unit-test [feature]      Run tests for a specific feature (default tier)
purlin:unit-test                Run all default-tier tests
purlin:unit-test --all          Run all tests across all tiers
```

## Step 1 — Detect Test Framework

Read `.purlin/config.json` for `test_framework`. If `"auto"`, detect from project files:
- `conftest.py` or `pyproject.toml` with `[tool.pytest]` → pytest
- `package.json` with `jest` in devDependencies → jest
- `*.test.sh` files → shell

## Step 2 — Run Tests

```bash
# pytest (default tier)
pytest -m "not slow"

# pytest (all tiers with --all)
pytest

# jest (default tier)
npx jest --testPathPattern="default"

# jest (all tiers with --all)
npx jest
```

The proof plugins (`scripts/proof/pytest_purlin.py`, `scripts/proof/jest_purlin.js`, `scripts/proof/shell_purlin.sh`) emit `<feature>.proofs-<tier>.json` next to the spec file. This is a **feature-scoped overwrite**: each run replaces all proof entries for the tested feature in that tier file, preserving entries from other features.

### Proof File Freshness Check

After tests run, before reporting results, verify that proof files (`*.proofs-*.json`) were modified AFTER the test command started. If proof files are older than the test run or don't exist, the proof plugin didn't emit — something went wrong. Report:

```
WARNING: Proof files were not updated by the test run. The proof plugin may not be loaded.
→ Check: is the proof plugin registered in conftest.py / jest.config.js?
→ Run: purlin:init --force to re-scaffold the proof plugin
```

Never write proof JSON files directly. Only the test framework plugin writes proof files.

## Step 3 — Report Coverage

Call `sync_status` after tests complete. Display the full result. **This is not optional** — without `sync_status`, the agent doesn't know if coverage is complete.

```
Test results:
  auth_login: 3/3 rules proved
  user_profile: 1/2 rules proved
    RULE-2: NO PROOF → write a test with @pytest.mark.proof("user_profile", "PROOF-2", "RULE-2")
  webhook_delivery: RULE-1 FAIL
    → Fix: test_webhook_basic is failing
```

## Step 4 — Commit Proof Files

Proof files are always committed to git.

```
git commit -m "test(<feature>): <passed>/<total> rules proved"
```

If no feature argument was given (ran all tests):
```
git commit -m "test: run default tier (<passed>/<total> features fully proved)"
```

## Writing Tests with Proof Markers

When tests are missing, write them with proof markers. See `references/formats/proofs_format.md` for the full proof format specification.

**pytest:**
```python
@pytest.mark.proof("feature_name", "PROOF-1", "RULE-1")
def test_validates_input():
    result = validate(bad_input)
    assert result.status == "error"
    assert result.code == 400
```

**Jest:**
```javascript
it("validates input [proof:feature_name:PROOF-1:RULE-1:default]", () => {
  const result = validate(badInput);
  expect(result.status).toBe("error");
  expect(result.code).toBe(400);
});
```

**Shell:**
```bash
source scripts/proof/shell_purlin.sh
result=$(validate_input "bad")
if [[ "$result" == *"error"* ]]; then
  purlin_proof "feature_name" "PROOF-1" "RULE-1" pass "validates input"
else
  purlin_proof "feature_name" "PROOF-1" "RULE-1" fail "validates input"
fi
purlin_proof_finish
```

### Test Quality Rules

- **Assert behavior, not implementation.** Test outputs and side effects, not whether code exists.
- **Test the attack, not the defense.** Send bad input and assert the error, don't assert that validation code is present.
- **Never assert True.** Every assertion must check a specific expected value.
- **Use realistic data.** No empty strings or single-element arrays as representative inputs.
- **No self-mocking.** Mock external dependencies (network, filesystem), not the code under test.

## Note

This skill does NOT issue verification receipts. That is `purlin:verify`'s job. This skill runs tests, emits proof files, and reports coverage.
