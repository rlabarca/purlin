> Format-Version: 2

# Proof File Format

Proof files are JSON files emitted by test runners with proof markers. They live next to the spec they cover.

## File Naming

```
<feature>.proofs-<tier>.json
```

Examples:
- `specs/auth/login.proofs-unit.json`
- `specs/auth/login.proofs-integration.json`
- `specs/webhooks/webhook_delivery.proofs-unit.json`

## Location

Proof files live in the same directory as their spec. The proof plugins resolve this automatically by scanning `specs/**/*.md` for matching feature names.

## Schema

```json
{
  "tier": "unit",
  "proofs": [
    {
      "feature": "login",
      "id": "PROOF-1",
      "rule": "RULE-1",
      "test_file": "tests/test_login.py",
      "test_name": "test_validates_credentials",
      "status": "pass",
      "tier": "unit"
    },
    {
      "feature": "login",
      "id": "PROOF-2",
      "rule": "RULE-2",
      "test_file": "tests/test_login.py",
      "test_name": "test_rejects_expired_token",
      "status": "fail",
      "tier": "unit"
    }
  ]
}
```

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `tier` | string | Test tier: `"unit"`, `"integration"`, `"e2e"`, etc. |
| `proofs[].feature` | string | Feature name (matches spec filename stem) |
| `proofs[].id` | string | Proof ID matching `## Proof` section: `PROOF-1`, `PROOF-2`, etc. |
| `proofs[].rule` | string | Rule ID this proof covers: `RULE-1`, `RULE-2`, etc. |
| `proofs[].test_file` | string | Relative path to the test file |
| `proofs[].test_name` | string | Test function/case name |
| `proofs[].status` | string | `"pass"` or `"fail"` |
| `proofs[].tier` | string | Tier this proof belongs to |

## Merge Behavior (Feature-Scoped Overwrite)

When proof plugins write a proof file, they:

1. Load the existing file (if any).
2. Remove all entries where `feature` matches the feature being tested.
3. Append the new entries from the current test run.
4. Write the merged result.

This means each test run replaces only its own feature's entries, preserving proofs from other features that share the same tier file. This is the "feature-scoped overwrite" pattern.

## Proof Markers by Framework

### pytest

```python
@pytest.mark.proof("feature_name", "PROOF-1", "RULE-1")
def test_something():
    assert actual == expected

@pytest.mark.proof("feature_name", "PROOF-2", "RULE-2", tier="integration")
def test_integration_thing():
    assert actual == expected
```

Plugin: `scripts/proof/pytest_purlin.py` (scaffolded to `.purlin/plugins/pytest_purlin.py` by `purlin:init`).

### Jest

```javascript
it("does something [proof:feature_name:PROOF-1:RULE-1:unit]", () => {
  expect(actual).toBe(expected);
});

it("does integration thing [proof:feature_name:PROOF-2:RULE-2:integration]", () => {
  expect(actual).toBe(expected);
});
```

Reporter: `scripts/proof/jest_purlin.js` (scaffolded to `.purlin/plugins/jest_purlin.js` by `purlin:init`).

### Shell

```bash
source scripts/proof/shell_purlin.sh  # or .purlin/plugins/purlin-proof.sh

purlin_proof "feature_name" "PROOF-1" "RULE-1" pass "test description"
purlin_proof "feature_name" "PROOF-2" "RULE-2" fail "test description"
purlin_proof_finish  # writes proof files
```

## Manual Proofs

For rules that cannot be tested automatically, proofs are stamped directly in the spec's `## Proof` section:

```markdown
- PROOF-3 (RULE-3): Visual layout matches design @manual(dev@example.com, 2026-03-31, a1b2c3d)
```

### Manual Stamp Format

```
@manual(<email>, <date>, <commit_sha>)
```

| Field | Source |
|-------|--------|
| `email` | `git config user.email` |
| `date` | Current date (YYYY-MM-DD) |
| `commit_sha` | `git rev-parse HEAD` (abbreviated) |

Manual stamps are applied by `purlin:verify --manual <feature> <PROOF-N>`. They become stale when files in the spec's `> Scope:` are modified after the stamp's commit SHA. `sync_status` detects staleness and issues a re-verify directive.

## Proof Quality Guidance

- **Assert behavior, not implementation.** Test what the code does, not how it's structured.
- **Test the attack, not the defense.** Send invalid input and assert the error response.
- **Never assert True.** Every assertion must check a specific expected value.
- **Use realistic inputs.** Test with data shapes that match production, not empty/trivial cases.
- **No self-mocking.** Mock external dependencies, but call the code under test for real.

## Git Behavior

Proof files are always committed to git. They are part of the project record, not ephemeral build artifacts.
