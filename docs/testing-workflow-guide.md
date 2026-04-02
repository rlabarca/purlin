# Testing Workflow Guide

## Why Proofs, Not Just Tests

A test tells you code works. A proof tells you code satisfies a specific rule in a spec.

The difference matters because:

- **Tests can be tautological.** `assert True` passes. A proof must reference a real rule — if the rule says "passwords are hashed with bcrypt," the proof must actually check for bcrypt, not just assert something passed.
- **Tests can drift from intent.** A test might check the wrong thing and still pass. A proof is linked to a rule, so `sync_status` shows you exactly which constraints are verified and which aren't.
- **Tests can be orphaned.** A test for deleted functionality keeps passing. Proofs linked to deleted rules show up as orphaned — `sync_status` tells you to clean them up.

### What makes a good proof?

A good proof tests the **behavior described in the rule**, not the implementation:

| Rule | Bad proof | Good proof |
|------|-----------|------------|
| Passwords hashed with bcrypt | `assert hasher is not None` | `assert bcrypt.checkpw(password, stored_hash)` |
| Rate limit at 5 per minute | `assert rate_limiter.count == 5` | Submit 6 requests; assert the 6th returns 429 |
| Input sanitized against XSS | `assert sanitize in source_code` | Inject `<script>alert(1)</script>`; assert it's escaped in output |

The pattern: **test the attack, not the defense.** Prove bad input is rejected, not just that good input works. Assert observable output, not internal state.

### Why should you be confident proofs pass?

Because `purlin:verify` runs all tests from scratch in a clean state. The verification receipt (`vhash`) proves the rules had these exact test outcomes. CI `--audit` mode re-runs everything independently — if a developer's local environment was rigged, CI catches it.

For comprehensive guidance on writing rules, proofs, tiers, and anchors, see the [Spec Quality Guide](../references/spec_quality_guide.md).

## The Simplest Workflow

Ask Claude:

```
test auth_login
```

Claude reads the spec, writes tests with proof markers, runs them, iterates until all rules pass. You don't need to understand proof markers to use Purlin — the agent handles it.

When you want more control, read on.

---

## How Proof Markers Work

A proof marker is metadata on a test that says: "this test proves RULE-N for feature X."

The marker is framework-specific — it uses whatever metadata mechanism the test framework already has. The proof plugin reads the metadata during test execution and writes a structured JSON file (`<feature>.proofs-<tier>.json`) next to the spec. `sync_status` reads these files to compute coverage.

```
Test code                     Proof plugin              sync_status
@pytest.mark.proof(...)  -->  collects markers     -->  reads JSON
                              writes proofs JSON        diffs against rules
```

**The chain:** test framework marker → proof plugin → JSON file → `sync_status`. No regex parsing. No source code scanning. The plugin reads framework metadata at runtime.

### pytest (Python)

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="slow")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
```

The marker args: `(feature_name, proof_id, rule_id)`. Optional: `tier="slow"` for tests that hit APIs, databases, or external services.

### Jest (JavaScript / TypeScript)

```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:slow]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

The marker is embedded in the test title: `[proof:feature:PROOF-ID:RULE-ID:tier]`.

### Shell (Bash)

```bash
source .purlin/plugins/purlin-proof.sh
purlin_proof "auth_login" "PROOF-1" "RULE-1" pass "valid login returns 200"
purlin_proof_finish
```

Call `purlin_proof` after each assertion. `purlin_proof_finish` writes the JSON file.

---

## Running Tests

```
purlin:unit-test
```

Runs your test suite with the proof plugin active. The plugin:

1. Collects proof markers from tests that ran
2. For each feature tested: purges that feature's old entries from the proof file (kills ghosts from deleted tests)
3. Appends fresh entries for that feature
4. Leaves other features' entries untouched

This is **feature-scoped overwrite** — running `pytest tests/login/` only updates login's proofs without wiping checkout or payments.

## Proof Plugins

A proof plugin is the bridge between your test framework and Purlin. It reads proof markers from your tests, collects pass/fail results, and writes `.proofs-*.json` files that `sync_status` reads.

### Built-in plugins

Purlin ships with plugins for three frameworks:

| Framework | Language | Plugin file | Marker syntax |
|-----------|----------|------------|---------------|
| **pytest** | Python | `scripts/proof/pytest_purlin.py` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | JavaScript / TypeScript | `scripts/proof/jest_purlin.js` | `[proof:feature:PROOF-1:RULE-1:default]` in test title |
| **Shell** | Bash | `scripts/proof/shell_purlin.sh` | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

`purlin:init` detects your framework and copies the right plugin to `.purlin/plugins/`.

### Which plugin is active?

Check `.purlin/plugins/` — that's where your project's proof plugin lives. It was scaffolded by `purlin:init` based on your test framework.

### Adding support for another framework

Install a community proof plugin or your own:

```
purlin:init --add-plugin ./my-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-go-proof.git
```

This copies the plugin to `.purlin/plugins/`. No registration needed — `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`. If your plugin writes files in that pattern, it works automatically.

To see what's installed:

```
purlin:init --list-plugins
```

To write your own plugin, see [Writing a Custom Proof Plugin](#writing-a-custom-proof-plugin) below.

## Checking Coverage

```
purlin:status
```

Shows which rules are proved, failing, or missing. Every problem has a `→` directive:

```
auth_login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in test_login.py)
  RULE-2: PASS (PROOF-2 in test_login.py)
  RULE-3: NO PROOF
  → Fix: write a test with @pytest.mark.proof("auth_login", "PROOF-3", "RULE-3")
  → Run: purlin:unit-test
```

## Verifying and Shipping

```
purlin:verify
```

Runs ALL tests (every feature, every tier), issues verification receipts for every feature with 100% coverage. This is the only time a global sweep happens — all proof files are deleted and regenerated from scratch.

---

## Test Tiers

Not all tests are fast. Tiers separate them:

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")                    # default — always
@pytest.mark.proof("login", "PROOF-5", "RULE-5", tier="slow")       # CI only
@pytest.mark.proof("login", "PROOF-8", "RULE-8", tier="nightly")    # scheduled
```

Each tier writes to a separate file: `login.proofs-default.json`, `login.proofs-slow.json`. `sync_status` merges all tiers.

| Command | What runs |
|---------|-----------|
| `purlin:unit-test` | Default tier only |
| `purlin:unit-test --all` | All tiers |
| `purlin:verify` | All tiers |

## Proof Levels

AI tends to write Level 2 proofs — isolated unit tests with mocked dependencies. These prove code logic is correct but don't prove the feature actually works. Understanding proof levels helps you get the coverage that matters.

### The three levels

| Level | What it proves | Example | Who writes the rule |
|-------|---------------|---------|-------------------|
| **Level 1** | A value exists or has the right type | `assert config.timeout is not None` | Nobody should — these are hollow |
| **Level 2** | Code behavior with controlled inputs | `POST invalid password → 401` (mocked DB) | Engineer or AI |
| **Level 3** | End-to-end behavior through the real system | `Open browser, enter wrong password, see "Invalid credentials" on screen` | PM (in prodbrief or spec) |

### Why AI defaults to Level 2

Level 2 proofs are fast, deterministic, and easy to write. The AI can mock everything, assert a return value, and get a green proof. But Level 2 can be green while the feature is broken — the mock says the API returns 200, but the real API is misconfigured. The test proves the code logic, not the user experience.

### How PMs drive Level 3 proofs

**The PM controls the proof level by how they write rules.** This is the key insight — you don't need to know about proof levels. Just describe what you want to see happen:

- "Passwords are hashed with bcrypt" → Level 2 (engineer writes a unit test)
- "User enters wrong password and sees 'Invalid credentials' on screen" → Level 3 (engineer must write an E2E test — there's no way to mock this)

When a rule describes a **user-visible outcome**, the only way to prove it is to run the real system and check the real output. The rule forces Level 3.

### Prodbrief invariants: the PM's enforcement tool

A PM who wants to guarantee user-facing behavior writes a `prodbrief_` invariant with rules that describe user journeys:

```markdown
# Invariant: i_prodbrief_checkout

> Type: prodbrief
> Source: git@bitbucket.org:acme/product-briefs.git
> Path: briefs/checkout-v2.md
> Pinned: a1b2c3d4

## What it does
Core checkout flow requirements from the product brief.

## Rules
- RULE-1: User adds item to cart, proceeds to checkout, enters payment, sees confirmation page
- RULE-2: If payment fails, user sees an error and can retry without losing cart contents
- RULE-3: Order confirmation email arrives within 60 seconds of successful payment

## Proof
- PROOF-1 (RULE-1): Open browser → add item → click checkout → enter test card → verify confirmation page shows order number @e2e
- PROOF-2 (RULE-2): Open browser → add item → checkout with declined card → verify error message → verify cart still has item → retry with valid card → verify confirmation @e2e
- PROOF-3 (RULE-3): Complete checkout → poll inbox for 60 seconds → verify email contains order number @e2e
```

Every feature that `> Requires: i_prodbrief_checkout` must prove these rules. The engineer can't satisfy them with mocked tests — RULE-1 says "sees confirmation page," which means rendering real HTML in a real browser.

### When to write Level 3 rules

Write Level 3 rules when:
- **The user experience matters, not just the code logic.** "User sees error message" vs "API returns 400."
- **Multiple systems must work together.** "Confirmation email arrives" requires API + email service + template rendering.
- **You've been burned by mocks.** A Level 2 test passed but the feature was broken in production. Write a Level 3 rule for that exact scenario.
- **Regulatory or contractual requirements.** "User can export their data within 30 days" — prove it end-to-end.

### When Level 2 is fine

Level 2 is the right level for most rules. Internal logic, data transformations, error handling, input validation — these don't need a browser or a running server. Don't force Level 3 where Level 2 is sufficient. The cost of E2E tests (slow, flaky, infrastructure-dependent) means you should use them selectively for high-value user flows.

### Level 3 and tiers

Level 3 proofs are tagged `@e2e` and don't run on every build:

| When | What runs |
|------|-----------|
| Every build | Default tier (Level 2 proofs) |
| On check-in / PR | Default + `@slow` tiers |
| On release / nightly | All tiers including `@e2e` (Level 3) |
| `purlin:verify` | All tiers |

See the [Spec Quality Guide](../references/spec_quality_guide.md) for detailed guidance on writing rules and proofs at each level.

## Manual Proofs

Some rules can't be automated ("error message is clear to non-technical users", "login page matches the design"). Mark them `@manual` in the spec:

```markdown
## Proof
- PROOF-5 (RULE-5): Verify login error messages are clear and non-technical @manual
```

After verifying by hand:

```
verify login PROOF-5 manually
```

Auto-stamps: `@manual(alice@company.com, 2026-04-01, f8e9d0c)` — who, when, at what commit. If code changes after the stamp, `sync_status` flags it stale.

---

## Real-World Loop: Test, Fix, Validate

Here's what a typical session looks like. One prompt does the whole loop:

```
test login — iterate until all rules pass and verify
```

Claude runs through the full cycle:

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
  → READY for verification (manual proof pending)

Running purlin:verify...
  Receipt issued: login vhash=a3f7c912

Done. 4/4 auto proofs pass. 1 manual proof pending (PROOF-5).
```

The agent reads the spec, writes tests, runs them, diagnoses the failure (code bug, not test bug), fixes the code, re-runs, confirms coverage, and issues the receipt. One prompt.

---

## Writing a Custom Proof Plugin

The built-in plugins cover pytest, Jest, and shell. If your test framework isn't supported, writing a plugin is straightforward.

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
2. **Feature-scoped overwrite.** On write, load the existing file, purge entries for features tested in this run, append fresh entries. This prevents ghost proofs from deleted tests while preserving other features' data.
3. **Write the file next to the spec.** Find the spec file `specs/**/<feature>.md` and write `<feature>.proofs-<tier>.json` in the same directory.
4. **Handle parameterized tests.** If a proof marker is on a parameterized test, aggregate: one entry per proof, status = "pass" only if ALL variants pass.

### Example: minimal custom plugin

```python
# For any Python test runner — adapt the collection mechanism
def write_proofs(results, tier="default"):
    """results: list of (feature, proof_id, rule_id, test_file, test_name, passed)"""
    import json, os, glob

    # Find spec directories
    spec_dirs = {}
    for spec in glob.glob("specs/**/*.md", recursive=True):
        stem = os.path.splitext(os.path.basename(spec))[0]
        spec_dirs[stem] = os.path.dirname(spec)

    # Group by feature
    by_feature = {}
    for feature, proof_id, rule_id, test_file, test_name, passed in results:
        by_feature.setdefault(feature, []).append({
            "feature": feature, "id": proof_id, "rule": rule_id,
            "test_file": test_file, "test_name": test_name,
            "status": "pass" if passed else "fail", "tier": tier
        })

    # Feature-scoped overwrite
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

To scaffold your plugin during `purlin:init`, place it in `scripts/proof/` alongside the built-in plugins. `purlin:init` copies the appropriate one to `.purlin/plugins/` based on the `test_framework` setting in `.purlin/config.json`. Add your framework to the detection logic in `skills/init/SKILL.md`.

Full format reference: [references/formats/proofs_format.md](../references/formats/proofs_format.md)
