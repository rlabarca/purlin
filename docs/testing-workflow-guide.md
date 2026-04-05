# Testing Workflow Guide

## What You Need to Know

A Purlin **proof** links a test to a specific rule in a spec. Regular tests tell you code works; proofs tell you code satisfies a specific constraint.

**The quickest path:**

```
test <feature>
```

Claude reads the spec, writes tests with proof markers, runs them, fixes failures, and iterates until all rules are proved. That's the whole workflow.

**Key commands:**

| Command | What it does |
|---------|-------------|
| `test <feature>` | Write tests, fix code, iterate until proved |
| `purlin:status` | See which rules are proved and which aren't |
| `purlin:unit-test` | Run tests and emit proof files |
| `purlin:verify` | Run all tests, issue verification receipts |
| `purlin:audit` | Check if tests actually prove what they claim |

---

## Proof Markers

A proof marker is metadata on a test that says "this test proves RULE-N for feature X."

```
Test code                     Proof plugin              purlin:status
@pytest.mark.proof(...)  →  collects markers      →  reads JSON
                              writes proofs JSON        diffs against rules
```

### pytest (Python)

```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="integration")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
```

### Jest (JavaScript / TypeScript)

```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:integration]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

Works with `ts-jest` and Vitest (via `--reporter`).

### Shell (Bash)

```bash
source .purlin/plugins/purlin-proof.sh
purlin_proof "auth_login" "PROOF-1" "RULE-1" pass "valid login returns 200"
purlin_proof_finish
```

---

## Test Tiers

Tiers control which proofs run when:

| Tier | When it runs | Use for |
|------|-------------|---------|
| unit (no tag) | Every build | Pure logic, no I/O |
| `@integration` | On check-in / PR | Database, network, filesystem |
| `@e2e` | On release / nightly | Full system, browser |
| `@manual` | Human-initiated | Visual quality, UX judgment |

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")                          # unit
@pytest.mark.proof("login", "PROOF-5", "RULE-5", tier="integration")      # integration
@pytest.mark.proof("login", "PROOF-8", "RULE-8", tier="e2e")              # e2e
```

Each tier writes to a separate file: `login.proofs-unit.json`, `login.proofs-integration.json`. Purlin merges all tiers when reporting coverage.

---

## Proof Levels

Not all proofs are equal:

| Level | What it proves | Example |
|-------|---------------|---------|
| **Level 1** | Value exists or has the right type | `assert config.timeout is not None` |
| **Level 2** | Code behavior with controlled inputs | `POST invalid password → 401` |
| **Level 3** | End-to-end through the real system | `Open browser, enter wrong password, see error` |

**Level 1 is hollow** — reject it. `assert x is not None` proves nothing about behavior.

**Level 2 is the default** — fine for internal logic, data transforms, error handling, validation.

**Level 3 is for certainty** — use when rules describe real-world outcomes:

```
RULE: User completes checkout in under 3 clicks from cart
PROOF: Open browser → add item → count clicks to confirmation → verify ≤ 3 @e2e
```

The rule controls the proof level. If the rule describes observable system behavior, the proof must exercise the real system.

### Anchor rules count toward coverage

When a feature requires an anchor or is subject to a global anchor, those rules are included in its coverage total. Prove them using the anchor's name in the marker:

```python
@pytest.mark.proof("rest_conventions", "PROOF-1", "RULE-1")
```

---

## Manual Proofs

Some rules need human judgment — visual quality, UX flow, brand voice. Mark the proof `@manual` in the spec:

```markdown
- PROOF-5 (RULE-5): Verify error messages are clear and non-technical @manual
```

`purlin:status` shows it as a required action. After verifying by hand:

```
verify login PROOF-5 manually
```

This stamps the spec with who verified, when, and at what commit. If code changes after the stamp, Purlin flags it as stale — you re-verify.

Manual proofs are first-class. A feature with 4 automated proofs and 1 manual stamp is VERIFIED.

| Use manual | Use automated |
|-----------|--------------|
| "Error messages are clear to non-technical users" | "Returns 401 on invalid credentials" |
| "Login page matches the Figma design" | "Button color is #1a73e8" |
| "Checkout flow is intuitive" | "POST /checkout returns 200 with order ID" |

---

## The Workflow

### 1. Check coverage

```
purlin:status
```

### 2. Write and run tests

```
purlin:unit-test
```

The proof plugin collects markers and writes proof files using feature-scoped overwrite — only the tested feature's entries are replaced.

### 3. Fix failures

When a test fails, diagnose first:

- Test expects 401, code returns 200 → **fix the code** (spec says 401)
- Test mocks the wrong thing → **fix the test**
- Spec rule no longer matches intent → **update the spec first**

### 4. Verify and ship

```
purlin:verify
```

Runs ALL tests (every tier), issues receipts for features with 100% coverage.

---

## Enforcement

| Layer | What it does | Blocks on | Setup |
|-------|-------------|-----------|-------|
| **Pre-push hook** | Runs unit tests before push | FAILING proofs | Automatic (`purlin:init`) |
| **CI pipeline** | Runs tiered tests per trigger | FAILING + coverage gates | You write it |
| **Deploy gate** | Clean-room verification | vhash mismatch | You write it |

### Pre-push hook

Two modes (set via `purlin:init --pre-push`):

- **warn** (default) — blocks FAILING proofs, allows partial coverage with a warning
- **strict** — blocks anything not VERIFIED

### CI pipeline

Purlin doesn't ship pipeline configs — you write them. Example (Bitbucket Pipelines):

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Proof Gate
          script:
            - pip install -r requirements.txt
            - pytest
            - python3 scripts/mcp/purlin_server.py --check sync_status

  branches:
    main:
      - step:
          name: Full Verification
          script:
            - pip install -r requirements.txt
            - pytest --run-all-tiers
            - python3 scripts/mcp/purlin_server.py --check sync_status --require-ready
```

| Trigger | Tiers to run | Block on |
|---------|-------------|----------|
| PR / branch push | unit + `@integration` | Any FAIL |
| Merge to main | All tiers | Any FAIL or partial coverage |
| Nightly | `purlin:verify --audit` | vhash mismatch |

### Deploy gate

`purlin:verify --audit` is a clean-room re-execution: deletes all proof files, re-runs every test, recomputes vhash, compares against committed receipts.

```yaml
- name: Deploy Gate
  run: |
    python3 scripts/mcp/purlin_server.py --audit
```

---

## Proof Quality Auditing

`purlin:audit` checks whether tests actually prove what they claim. Three passes:

**Pass 0 — Behavioral filter** (deterministic). Structural proofs (grep, file exists) are excluded from audit and integrity scoring.

**Pass 1 — Structural soundness** (deterministic). Catches: `assert True`, no assertions, logic mirroring, mocking the thing being tested, bare `except: pass`. Any failure here is **HOLLOW** — no override possible.

**Pass 2 — Semantic alignment** (LLM). Checks if assertions match the rule's intent. Returns **STRONG** or **WEAK**.

```
Integrity score = (STRONG + MANUAL) / total proofs x 100%
```

Results are cached in `.purlin/cache/audit_cache.json`. The cache self-invalidates when rule text, proof descriptions, or test code changes.

### Quick path

```
purlin:audit login
```

Or fix everything at once:

```
do a purlin:audit and fix all HOLLOW and WEAK proofs, then re-verify
```

### Cross-model auditing (experimental)

```
purlin:init --audit-llm
```

Use an external LLM for Pass 2 instead of Claude auditing Claude.

---

## Proof Plugins

Built-in plugins for pytest, Jest, and Shell are installed by `purlin:init`. Check `.purlin/plugins/` to see what's active.

### Adding a plugin

```
purlin:init --add-plugin ./my-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-go-proof.git
```

Purlin discovers proof files by globbing `specs/**/*.proofs-*.json`. If your plugin writes files in that pattern, it works automatically.

### Writing a custom plugin (Python)

A proof plugin has one job: read test metadata during execution, write a JSON file after the run.

```python
"""Minimal proof plugin for a custom test framework.

Collects proof results and writes .proofs-<tier>.json files
next to specs. Uses feature-scoped overwrite so other features'
proofs are preserved.
"""

def write_proofs(results, tier="unit"):
    """Write proof results to JSON files next to their specs.

    Args:
        results: list of (feature, proof_id, rule_id, test_file, test_name, passed)
        tier: proof tier name (unit, integration, e2e)
    """
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

Requirements:
1. Read proof metadata from tests (annotations, decorators, tags)
2. Feature-scoped overwrite (purge entries for tested features, preserve others)
3. Write files next to specs: `specs/<category>/<feature>.proofs-<tier>.json`
4. Handle parameterized tests (one entry per proof, pass only if ALL variants pass)

Full JSON schema: [references/formats/proofs_format.md](../references/formats/proofs_format.md)

---

## Proof File Merge Conflicts

Proof files are derived state. When merging:

1. Accept either version of the conflicting file
2. Run `purlin:unit-test` to regenerate from the merged code
3. Commit the result

This works because proof files are feature-scoped — testing feature X only rewrites X's entries.
