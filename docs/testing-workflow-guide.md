# Testing Workflow Guide

## What Makes Purlin Tests Different

A regular test tells you code works. A Purlin **proof** tells you code satisfies a specific rule in a spec.

The difference matters:

- **Tests can be hollow.** `assert True` passes. A proof must reference a real rule — if the rule says "passwords are hashed with bcrypt," the proof must actually check for bcrypt.
- **Tests can drift from intent.** A test might check the wrong thing and still pass. A proof is linked to a rule, so `sync_status` shows exactly which constraints are verified and which aren't.
- **Tests can be orphaned.** A test for deleted functionality keeps passing silently. Proofs linked to deleted rules are flagged by `sync_status`.

---

## The Quickest Path

```
test login
```

That's it. Claude reads the spec, writes tests with proof markers, runs them, diagnoses failures, fixes the code, and iterates until `sync_status` shows READY. You don't need to understand anything below this line to use Purlin testing.

When you want more control — or want to understand what's happening under the hood — read on.

---

## Proof Levels

Not all proofs are equal. Understanding the three levels helps you write rules that get the coverage you actually need.

| Level | What it proves | Example |
|-------|---------------|---------|
| **Level 1** | A value exists or has the right type | `assert config.timeout is not None` |
| **Level 2** | Code behavior with controlled inputs | `POST invalid password → 401` (mocked DB) |
| **Level 3** | End-to-end behavior through the real system | `Open browser, enter wrong password, see error on screen` |

### Level 1 is hollow — reject it

If a proof says "verify X exists" or "check Y is not null," it proves nothing. Always rewrite:

- Level 1: "Verify the login endpoint exists"
- Level 2: "POST to /login with valid credentials; verify 200 and JWT in response"
- Level 3: "Open browser, enter credentials, click login, verify dashboard loads"

### Level 2 is the AI default — and it's usually fine

AI writes Level 2 proofs because they're fast, deterministic, and mockable. For internal logic — data transformations, error handling, input validation, algorithms — Level 2 is the right level. Don't force Level 3 where Level 2 is sufficient.

But Level 2 can be green while the feature is broken. The mock says the API returns 200, but the real API is misconfigured. The test proves the code logic, not the real outcome.

### Level 3 is for when you need certainty

Write Level 3 rules when you need to prove the real system works, not just the code logic. **Anyone** can write Level 3 rules — not just PMs. The key is writing rules that describe real-world outcomes rather than function-level behavior:

**A PM** enforcing product requirements:
```
RULE: User adds item to cart, proceeds to checkout, enters payment, sees confirmation page
PROOF: Open browser → add item → checkout → enter test card → verify confirmation page @e2e
```

**A security engineer** enforcing compliance:
```
RULE: Authentication tokens expire and cannot be reused after 30 minutes
PROOF: Obtain a token → wait 31 minutes → use the token → verify 401 Unauthorized @e2e
```

**An architect** enforcing system behavior:
```
RULE: Service recovers from database connection failure within 5 seconds
PROOF: Kill DB connection → send request → verify 503 → restart DB → send request within 5s → verify 200 @e2e
```

**A QA engineer** codifying a regression:
```
RULE: Search results for "café" match results for "cafe" (accent-insensitive)
PROOF: Insert "café" record → search for "cafe" → verify the record appears @slow
```

The pattern: **when the rule describes a real-world outcome, the proof must exercise the real system.** The rule controls the proof level.

### Level 3 through invariants

Invariants are the strongest enforcement mechanism for Level 3. When a PM, security engineer, or architect writes an invariant, every feature that requires it must prove those rules. No shortcuts.

**PM — product brief:**
```markdown
# Invariant: i_prodbrief_checkout

> Type: prodbrief
> Source: git@bitbucket.org:acme/product-briefs.git
> Pinned: a1b2c3d4

## Rules
- RULE-1: User can complete checkout in under 3 clicks from cart
- RULE-2: Payment failure shows a retry option without clearing the cart
- RULE-3: Confirmation email arrives within 60 seconds

## Proof
- PROOF-1 (RULE-1): Open browser → add item → count clicks to confirmation page → verify ≤ 3 @e2e
- PROOF-2 (RULE-2): Checkout with declined card → verify retry button → verify cart intact @e2e
- PROOF-3 (RULE-3): Complete checkout → poll inbox 60s → verify email with order number @e2e
```

**Security — compliance requirements:**
```markdown
# Invariant: i_security_session_policy

> Type: security
> Source: git@bitbucket.org:acme/security-policies.git
> Pinned: b2c3d4e5

## Rules
- RULE-1: Sessions expire after 30 minutes of inactivity
- RULE-2: Concurrent sessions from different IPs are rejected
- RULE-3: Session tokens are invalidated on password change

## Proof
- PROOF-1 (RULE-1): Login → wait 31 minutes → request with session token → verify 401 @e2e
- PROOF-2 (RULE-2): Login from IP-A → login same user from IP-B → verify IP-A session rejected @e2e
- PROOF-3 (RULE-3): Login → change password → request with old session → verify 401 @e2e
```

Every feature that `> Requires:` these invariants must prove every rule. The engineer can't mock their way out — the rules describe observable system behavior.

### When to use each level

| Level | When | Examples |
|-------|------|---------|
| **Level 2** | Internal logic, data transforms, error codes, validation | Most rules — this is the default |
| **Level 3** | User-facing flows, multi-system integration, compliance, regressions from production bugs | Checkout flows, security policies, architecture guarantees, anything that's broken before |
| **@manual** | Human judgment required — visual quality, brand voice, UX feel | Design review, copy review, accessibility audit |

For detailed guidance on writing rules and proofs at each level, see the [Spec Quality Guide](../references/spec_quality_guide.md).

---

## Test Tiers

Tiers control which proofs run when. They map directly to proof levels:

| Tier | When it runs | Typical proof level |
|------|-------------|-------------------|
| default (no tag) | Every build | Level 2 — unit tests |
| `@slow` | On check-in / PR | Level 2 — tests needing I/O, DB, network |
| `@e2e` | On release / nightly | Level 3 — full system tests |
| `@manual` | Human-initiated | Manual verification |

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")                    # default — always
@pytest.mark.proof("login", "PROOF-5", "RULE-5", tier="slow")       # on PR
@pytest.mark.proof("login", "PROOF-8", "RULE-8", tier="e2e")        # nightly
```

Each tier writes to a separate file: `login.proofs-default.json`, `login.proofs-slow.json`. `sync_status` merges all tiers.

| Command | What runs |
|---------|-----------|
| `purlin:unit-test` | Default tier only |
| `purlin:unit-test --all` | All tiers |
| `purlin:verify` | All tiers |

---

## How Proof Markers Work

A proof marker is metadata on a test that says: "this test proves RULE-N for feature X."

```
Test code                     Proof plugin              sync_status
@pytest.mark.proof(...)  →  collects markers      →  reads JSON
                              writes proofs JSON        diffs against rules
```

The marker is framework-specific. The proof plugin reads it at runtime and writes a JSON file. `sync_status` reads the JSON. No source code scanning.

### pytest (Python)

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="slow")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
```

Args: `(feature_name, proof_id, rule_id)`. Optional: `tier="slow"`.

### Jest (JavaScript / TypeScript)

```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:slow]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

Marker embedded in test title: `[proof:feature:PROOF-ID:RULE-ID:tier]`.

### Shell (Bash)

```bash
source .purlin/plugins/purlin-proof.sh
purlin_proof "auth_login" "PROOF-1" "RULE-1" pass "valid login returns 200"
purlin_proof_finish
```

Call `purlin_proof` after each assertion. `purlin_proof_finish` writes the JSON.

---

## Proof Plugins

A proof plugin is the bridge between your test framework and Purlin. It reads proof markers, collects pass/fail results, and writes `.proofs-*.json` files.

### Built-in plugins

| Framework | Language | Plugin file | Marker syntax |
|-----------|----------|------------|---------------|
| **pytest** | Python | `scripts/proof/pytest_purlin.py` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | JavaScript / TypeScript | `scripts/proof/jest_purlin.js` | `[proof:feature:PROOF-1:RULE-1:default]` in test title |
| **Shell** | Bash | `scripts/proof/shell_purlin.sh` | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

`purlin:init` detects your framework and copies the right plugin to `.purlin/plugins/`.

### Which plugin is active?

Check `.purlin/plugins/` — that's your project's proof plugin, scaffolded by `purlin:init`.

### Adding support for another framework

```
purlin:init --add-plugin ./my-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-go-proof.git
```

Copies the plugin to `.purlin/plugins/`. No registration needed — `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`.

To see what's installed: `purlin:init --list-plugins`

To write your own plugin, see [Writing a Custom Proof Plugin](#writing-a-custom-proof-plugin) below.

---

## The Workflow: Check, Test, Fix, Verify

### Check coverage

```
purlin:status
```

```
login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in test_login.py)
  RULE-2: PASS (PROOF-2 in test_login.py)
  RULE-3: NO PROOF
  → Fix: write a test with @pytest.mark.proof("login", "PROOF-3", "RULE-3")
```

### Run tests

```
purlin:unit-test
```

The proof plugin collects markers and writes proof files using **feature-scoped overwrite** — only the tested feature's entries are replaced. Other features' proofs are untouched.

### Fix failures

When a test fails, **diagnose before fixing**. Is the code wrong, or is the test wrong?

- Test expects 401, code returns 200 → **fix the code** (the spec says 401)
- Test mocks the wrong endpoint → **fix the test** (test bug)
- The spec rule no longer matches intended behavior → **update the spec first**

Never weaken an assertion to make it pass. See the [Spec Quality Guide](../references/spec_quality_guide.md) for the full diagnostic framework.

### Verify and ship

```
purlin:verify
```

Runs ALL tests (every tier), issues verification receipts for features with 100% coverage. The receipt includes a `vhash` — a tamper-evident hash of rules + proof results.

### Manual proofs

Some rules need human verification. Mark them `@manual` in the spec:

```markdown
- PROOF-5 (RULE-5): Verify login error messages are clear and non-technical @manual
```

After verifying by hand:

```
verify login PROOF-5 manually
```

Auto-stamps with your email, date, and commit SHA. If code changes later, `sync_status` flags it stale.

---

## Real-World Loop

One prompt does the whole cycle:

```
test login — iterate until all rules pass and verify
```

```
Reading specs/auth/login.md... 5 rules found.

Writing tests with proof markers...
  PROOF-1 (RULE-1): POST valid credentials → 200 + JWT
  PROOF-2 (RULE-2): POST invalid password → 401
  PROOF-3 (RULE-3): bcrypt hash check
  PROOF-4 (RULE-4): Rate limit after 10 attempts → 429
  PROOF-5 (RULE-5): error messages @manual (skipping)

Running pytest...
  3 passed, 1 failed

  FAIL: test_rate_limiting — expected 429, got 200
  Diagnosis: code bug — rate_limit.py doesn't check attempt count
  Fixing src/auth/rate_limit.py...

Running pytest...
  4 passed

Calling sync_status...
  login: 4/5 rules proved (PROOF-5 is @manual)

Running purlin:verify...
  Receipt issued: login vhash=a3f7c912

Done. 4/4 auto proofs pass. 1 manual proof pending (PROOF-5).
```

---

## Writing a Custom Proof Plugin

### What a proof plugin does

One job: read test metadata during execution, write a JSON file after the run.

### The JSON schema

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

### Requirements

1. **Read proof metadata from tests.** Use whatever mechanism your framework provides — annotations, decorators, naming conventions, tags.
2. **Feature-scoped overwrite.** Load existing file, purge entries for features tested in this run, append fresh entries. Preserves other features' data.
3. **Write the file next to the spec.** Find `specs/**/<feature>.md` and write `<feature>.proofs-<tier>.json` in the same directory.
4. **Handle parameterized tests.** Aggregate: one entry per proof, status = "pass" only if ALL variants pass.

### Example: minimal custom plugin

```python
def write_proofs(results, tier="default"):
    """results: list of (feature, proof_id, rule_id, test_file, test_name, passed)"""
    import json, os, glob

    spec_dirs = {}
    for spec in glob.glob("specs/**/*.md", recursive=True):
        stem = os.path.splitext(os.path.basename(spec))[0]
        spec_dirs[stem] = os.path.dirname(spec)

    by_feature = {}
    for feature, proof_id, rule_id, test_file, test_name, passed in results:
        by_feature.setdefault(feature, []).append({
            "feature": feature, "id": proof_id, "rule": rule_id,
            "test_file": test_file, "test_name": test_name,
            "status": "pass" if passed else "fail", "tier": tier
        })

    for feature, new_entries in by_feature.items():
        spec_dir = spec_dirs.get(feature, "specs")
        path = os.path.join(spec_dir, f"{feature}.proofs-{tier}.json")
        existing = []
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f).get("proofs", [])
        kept = [e for e in existing if e["feature"] != feature]
        with open(path, "w") as f:
            json.dump({"tier": tier, "proofs": kept + new_entries}, f, indent=2)
```

### Registering with Purlin

No registration needed. `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`. If your plugin writes files in that pattern, it works automatically.

Full format reference: [references/formats/proofs_format.md](../references/formats/proofs_format.md)
