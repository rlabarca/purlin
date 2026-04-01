# Testing Workflow Guide

Write tests with proof markers. Run them. `sync_status` shows what's proved.

## Step 1: Write Tests with Proof Markers

### pytest

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200

@pytest.mark.proof("login", "PROOF-2", "RULE-2", tier="slow")
def test_rate_limiting():
    for i in range(6):
        client.post("/login", json={"user": "alice", "pass": "wrong"})
    assert client.post("/login", json={"user": "alice", "pass": "wrong"}).status_code == 429
```

### Jest

```javascript
it("returns 200 on valid login [proof:login:PROOF-1:RULE-1:default]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

### Shell

```bash
source .purlin/plugins/purlin-proof.sh
purlin_proof "login" "PROOF-1" "RULE-1" pass "valid login returns 200"
purlin_proof_finish
```

## Step 2: Run Tests

```
purlin:unit-test
```

The proof plugin collects results and writes proof files next to the spec:

```
specs/auth/login.proofs-default.json
specs/auth/login.proofs-slow.json
```

**Feature-scoped overwrite:** The plugin updates proofs for features tested in this run. Other features' proofs are untouched. No global wipe during development.

## Step 3: Check Coverage

```
purlin:status
```

Shows which rules are proved, which are failing, which have no proof. Follow the `→` directives.

## Step 4: Verify and Ship

```
purlin:verify
```

Runs ALL tests, issues verification receipts for every feature with 100% coverage. One receipt commit for the whole project.

## Test Tiers

Not all tests are fast. Use tiers to separate them:

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")                    # default — runs always
@pytest.mark.proof("login", "PROOF-5", "RULE-5", tier="slow")       # CI only
@pytest.mark.proof("login", "PROOF-8", "RULE-8", tier="nightly")    # scheduled
```

| Command | What runs |
|---------|-----------|
| `purlin:unit-test` | Default tier only |
| `purlin:unit-test --all` | All tiers |
| `purlin:verify` | All tiers |

## Manual Proofs

Some rules can't be automated. Mark them `@manual` in the spec:

```markdown
## Proof
- PROOF-3 (RULE-3): Review error copy against brand guide @manual
```

After verifying by hand:

```
purlin:verify --manual login PROOF-3
```

This auto-stamps: `@manual(alice@company.com, 2026-04-01, f8e9d0c)` — who, when, at what commit. If code changes after the stamp, `sync_status` flags it stale.

## Proof Quality

Tests must actually test the rule, not just exist. Key principles:

- **Assert behavior, not implementation.** `assert response.status == 429` not `assert rate_limiter.count == 5`
- **Never `assert True`.** Every proof needs a real check against actual output.
- **Test the negative case.** Prove bad input is rejected, not just that good input works.
- **Don't mock what you're testing.** If the rule is about encryption, don't mock the crypto layer.
- **Security proofs test the attack.** Inject `<script>alert(1)</script>`, don't just check that `sanitize()` exists.

Full format: `references/formats/proofs_format.md`
