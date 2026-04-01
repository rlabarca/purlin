# Testing Workflow Guide

Purlin's testing workflow connects spec rules to test results through **proof markers**. Tests emit proof files, and `sync_status` diffs them against spec rules to show coverage.

## The Flow

```
Spec (RULE-1, RULE-2)  -->  Tests (@proof markers)  -->  Proof files (.proofs-*.json)  -->  sync_status report
```

## Step 1: Write Proof Markers

Add proof markers to your tests to link them to spec rules.

### pytest

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200

@pytest.mark.proof("auth_login", "PROOF-2", "RULE-2", tier="slow")
def test_rate_limiting():
    # tier="slow" writes to a separate proof file
    ...
```

### Jest

```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:default]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

The marker is embedded in the test title: `[proof:feature:PROOF-ID:RULE-ID:tier]`.

### Shell

```bash
source .purlin/plugins/purlin-proof.sh

purlin_proof "auth_login" "PROOF-1" "RULE-1" pass "valid login returns 200"
purlin_proof "auth_login" "PROOF-2" "RULE-2" pass "invalid login returns 401"
purlin_proof_finish  # writes proof files
```

## Step 2: Run Tests

```
purlin:unit-test
```

This runs your test suite. The proof plugin collects marked tests and writes proof JSON files next to the corresponding spec:

```
specs/auth/auth_login.proofs-default.json
specs/auth/auth_login.proofs-slow.json
```

Each proof file contains:
```json
{
  "tier": "default",
  "proofs": [
    {
      "feature": "auth_login",
      "id": "PROOF-1",
      "rule": "RULE-1",
      "test_file": "tests/test_login.py",
      "test_name": "test_valid_login",
      "status": "pass",
      "tier": "default"
    }
  ]
}
```

## Step 3: Check Coverage

```
purlin:status
```

The `sync_status` MCP tool reads specs and proof files, then reports:

```
auth_login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in tests/test_login.py)
  RULE-2: PASS (PROOF-2 in tests/test_login.py)
  RULE-3: NO PROOF
  --> Fix: write a test with @pytest.mark.proof("auth_login", "PROOF-3", "RULE-3")
  --> Run: purlin:unit-test
```

When all rules are proved:

```
auth_login: READY
  3/3 rules proved
  vhash=a1b2c3d4
  --> No action needed.
```

## Step 4: Verify

```
purlin:verify
```

Runs ALL tests and issues verification receipts for features with 100% rule coverage. A receipt is the proof that every rule has been tested and passed.

## Manual Proofs

Some rules can't be tested automatically (visual checks, UX flows). Use manual proof stamps in the spec's `## Proof` section:

```markdown
## Proof
- PROOF-1 (RULE-1): @manual(user@example.com, 2026-03-15, abc1234)
```

The stamp includes who verified, when, and which commit SHA was current. If scope files change after the stamp's commit, `sync_status` reports the proof as **STALE**.

## Tiers

Proof markers support a `tier` parameter (default: `"default"`). Tiers let you separate fast unit tests from slow integration tests:

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="integration")
```

Each tier writes to a separate file: `feature.proofs-integration.json`. The `sync_status` tool reads all tiers.
