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

### pytest

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="slow")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
```

The marker args: `(feature_name, proof_id, rule_id)`. Optional: `tier="slow"` for tests that hit APIs, databases, or external services.

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

| Framework | Plugin file | Marker syntax |
|-----------|------------|---------------|
| **pytest** | `scripts/proof/pytest_purlin.py` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | `scripts/proof/jest_purlin.js` | `[proof:feature:PROOF-1:RULE-1:default]` in test title |
| **Shell** | `scripts/proof/shell_purlin.sh` | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

`purlin:init` detects your framework and copies the right plugin to `.purlin/plugins/`.

### Which plugin is active?

Check `.purlin/plugins/` — that's where your project's proof plugin lives. It was scaffolded by `purlin:init` based on your test framework.

### Adding support for another framework

If your project uses Go, Rust, C, or any framework without a built-in plugin, you can write one. A proof plugin does one thing: read test metadata, write a JSON file. See [Writing a Custom Proof Plugin](#writing-a-custom-proof-plugin) below for the schema, requirements, and a minimal example.

No registration is needed — `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`. If your plugin writes files in that pattern, it works automatically.

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

## Manual Proofs

Some rules can't be automated ("brand voice must be playful", "checkout is intuitive"). Mark them `@manual` in the spec:

```markdown
## Proof
- PROOF-3 (RULE-3): Review error copy against brand guide @manual
```

After verifying by hand:

```
purlin:verify --manual auth_login PROOF-3
```

Auto-stamps: `@manual(alice@company.com, 2026-04-01, f8e9d0c)` — who, when, at what commit. If code changes after the stamp, `sync_status` flags it stale.

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
