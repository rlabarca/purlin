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
PROOF: Insert "café" record → search for "cafe" → verify the record appears @integration
```

The pattern: **when the rule describes a real-world outcome, the proof must exercise the real system.** The rule controls the proof level.

### Required rules count for coverage

When a feature requires an anchor (via `> Requires:`) or is subject to a global anchor (with `> Global: true`), those rules are included in coverage. You must write proofs for **all** required rules -- not just your own. Use the required spec's feature name in the proof marker:

```python
# Own rule
@pytest.mark.proof("login", "PROOF-1", "RULE-1")

# Required rule from api_rest_conventions anchor
@pytest.mark.proof("api_rest_conventions", "PROOF-1", "RULE-1")
```

`sync_status` displays required and global rules with labels so you can see what's needed:
```
login: 3/5 rules proved
  RULE-1: PASS (own)
  RULE-2: NO PROOF (own)
  api_rest_conventions/RULE-1: PASS (required)
  security_no_eval/RULE-1: PASS (global)
  security_no_eval/RULE-2: NO PROOF (global)
```

### Level 3 through anchors

Anchors with external references are the strongest enforcement mechanism for Level 3. When a PM, security engineer, or architect writes an anchor, every feature that requires it must prove those rules. No shortcuts.

**PM -- product brief:**
```markdown
# Anchor: prodbrief_checkout

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

**Security -- compliance requirements:**
```markdown
# Anchor: security_session_policy

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

Every feature that `> Requires:` these anchors must prove every rule. The engineer can't mock their way out -- the rules describe observable system behavior.

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
| unit (no tag) | Every build | Level 2 — unit tests |
| `@integration` | On check-in / PR | Level 2 — tests needing I/O, DB, network |
| `@e2e` | On release / nightly | Level 3 — full system tests |
| `@manual` | Human-initiated | Manual verification |

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")                          # unit — always
@pytest.mark.proof("login", "PROOF-5", "RULE-5", tier="integration")      # on PR
@pytest.mark.proof("login", "PROOF-8", "RULE-8", tier="e2e")              # nightly
```

Each tier writes to a separate file: `login.proofs-unit.json`, `login.proofs-integration.json`. `sync_status` merges all tiers.

| Command | What runs |
|---------|-----------|
| `purlin:unit-test` | Unit tier only |
| `purlin:unit-test --all` | All tiers |
| `purlin:verify` | All tiers |

---

## Proof File Merge Conflicts

Proof files (`*.proofs-*.json`) are regenerated by `purlin:unit-test` every time tests run. When two developers test the same feature on different branches, the proof files will conflict on merge.

**Resolution: re-run tests.** Proof files are derived state — they're generated from test results, not hand-written. When you hit a merge conflict on a proof file:

```bash
# Accept either version (doesn't matter which)
git checkout --theirs specs/auth/login.proofs-unit.json
git add specs/auth/login.proofs-unit.json

# Then re-run tests to regenerate from the current code
purlin:unit-test
```

The re-run produces the correct proof file for the merged code. Commit the result.

**Why this works:** proof files are feature-scoped. Running `purlin:unit-test` for feature X only overwrites X's entries — other features' proofs are preserved. The regenerated file reflects the actual test results on the merged codebase.

**To reduce conflicts:** avoid committing proof files on every test run. Commit them when you're done — alongside the implementation commit or the verify receipt commit. Don't commit intermediate proof files from debugging sessions.

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
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1", tier="integration")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
```

Args: `(feature_name, proof_id, rule_id)`. Optional: `tier="integration"`.

### Jest (JavaScript / TypeScript)

```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:integration]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
});
```

Marker embedded in test title: `[proof:feature:PROOF-ID:RULE-ID:tier]`.

Works with `ts-jest` for TypeScript projects. **Vitest** users: Vitest supports Jest-compatible reporters — the same proof plugin works via `--reporter`. If you hit incompatibilities, install a Vitest-specific plugin via `purlin:init --add-plugin`.

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
| **Jest** | JavaScript / TypeScript (also Vitest) | `scripts/proof/jest_purlin.js` | `[proof:feature:PROOF-1:RULE-1:default]` in test title |
| **Shell** | Bash | `scripts/proof/shell_purlin.sh` | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

`purlin:init` detects your framework and copies the right plugin to `.purlin/plugins/`.

### Which plugin is active?

Check `.purlin/plugins/` — that's your project's proof plugin, scaffolded by `purlin:init`.

### Adding support for another framework

```
purlin:init --add-plugin ./my-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-go-proof.git
```

Copies the plugin to `.purlin/plugins/`. No registration needed — `sync_status` discovers proof files by globbing `specs/**/*.proofs-*.json`. If your plugin writes files in that pattern, it works automatically.

To see what's installed: `purlin:init --list-plugins`

To write your own plugin, see [Writing a Custom Proof Plugin](#writing-a-custom-proof-plugin) below. Full proof file schema: [references/formats/proofs_format.md](../references/formats/proofs_format.md).

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

---

## Manual Proofs

Some rules can't be automated — visual quality, UX flow, brand voice, accessibility feel. These need a human to verify and stamp.

### How manual proofs work

1. **Mark the proof `@manual` in the spec** when writing it:

```markdown
## Proof
- PROOF-1 (RULE-1): POST valid credentials; verify 200 and JWT
- PROOF-2 (RULE-2): POST invalid password; verify 401
- PROOF-5 (RULE-5): Verify login error messages are clear and non-technical @manual
```

2. **`sync_status` surfaces it** as a required action:

```
login: 2/5 rules proved
  RULE-1: PASS
  RULE-2: PASS
  RULE-5: MANUAL PROOF NEEDED
  → Verify manually, then run: purlin:verify --manual login PROOF-5
```

The directive tells you exactly which proof needs human attention and what command to run after verifying.

3. **Verify by hand** — read the proof description, perform the check. In this case: open the login page, enter a wrong password, read the error message, decide if it's clear to a non-technical user.

4. **Stamp it:**

```
verify login PROOF-5 manually
```

This writes a stamp directly into the spec file:

```markdown
- PROOF-5 (RULE-5): Verify login error messages are clear and non-technical @manual(alice@company.com, 2026-04-02, f8e9d0c)
```

The stamp captures:
- **Who** — `git config user.email` (the person who verified)
- **When** — today's date
- **What commit** — `git rev-parse HEAD` (the exact code state that was verified)

5. **`sync_status` counts it as PASS:**

```
login: 3/5 rules proved
  RULE-5: PASS (PROOF-5, manual, verified 2026-04-02)
```

### Staleness detection

When code changes after a manual stamp, the stamp becomes stale. `sync_status` detects this automatically by checking if any files in `> Scope:` have commits newer than the stamp's commit SHA:

```
login: 4/5 rules proved
  RULE-5: MANUAL PROOF STALE (PROOF-5, verified 2026-04-02)
  → Re-verify and run: purlin:verify --manual login PROOF-5
```

This means: someone changed the code after you verified. The error message might have changed. Re-verify and re-stamp.

### When to use manual proofs

| Use manual | Use automated |
|-----------|--------------|
| "Error messages are clear to non-technical users" | "Returns 401 on invalid credentials" |
| "Login page matches the Figma design" | "Button color is #1a73e8" |
| "Checkout flow is intuitive — under 3 clicks" | "POST /checkout returns 200 with order ID" |
| "Brand voice in error copy is friendly, not scary" | "Error response contains 'error' field" |
| "Accessibility: screen reader can navigate the form" | "All inputs have aria-label attributes" |

The rule of thumb: if a human must make a judgment call, use `@manual`. If a machine can check it, automate it.

### Manual proofs count toward coverage

A feature with 5 rules, 4 automated proofs, and 1 manual stamp is READY — `purlin:verify` issues a receipt. Manual proofs are first-class proofs, not second-class workarounds.

---

## Real-World Loop

One prompt does the whole cycle:

```
test login — iterate until all rules pass and verify
```

```
Reading specs/auth/login.md... 5 rules found.

Running build and independent audit...

Builder: writing tests with proof markers...
  PROOF-1 (RULE-1): POST valid credentials → 200 + JWT
  PROOF-2 (RULE-2): POST invalid password → 401
  PROOF-3 (RULE-3): bcrypt hash check
  PROOF-4 (RULE-4): Rate limit after 10 attempts → 429
  PROOF-5 (RULE-5): error messages @manual (skipping)

Builder: running pytest... 3 passed, 1 failed
  FAIL: test_rate_limiting — expected 429, got 200
  Diagnosis: code bug — rate_limit.py doesn't check attempt count
  Fixing src/auth/rate_limit.py...

Builder: running pytest... 4 passed

Auditor: reviewing 4 proofs...
  Auditor → Builder: "PROOF-3 WEAK — asserts hash exists but doesn't verify bcrypt specifically."
  Builder → Auditor: "Fixed — now calls bcrypt.checkpw with original password."
  Auditor → Builder: "PROOF-3 now STRONG ✓."

Auditor: login integrity 100% (4/4 STRONG)

sync_status: login 4/5 rules proved (PROOF-5 is @manual)
Receipt issued: login vhash=a3f7c912

Done. 4/4 auto proofs STRONG. 1 manual proof pending (PROOF-5).
```

The builder and auditor handle the quality loop autonomously. The builder fixes code and tests, the auditor checks honesty, they iterate until the proofs are strong.

---

## Enforcement

Proofs are only valuable if they're actually run. Purlin ships a pre-push hook and provides patterns for CI and deploy integration:

| Layer | What it does | Blocks on | Setup |
|-------|-------------|-----------|-------------|
| **Layer 1: Git pre-push hook** | Runs unit-tier tests before push | FAILING proofs | Automatic (`purlin:init`) |
| **Layer 2: CI pipeline** | Runs tiered tests per trigger | FAILING proofs + coverage gates | You write the pipeline config |
| **Layer 3: Deploy gate** | Clean-room verification | vhash mismatch | You write the deploy config |

### Layer 1: Pre-push hook (built into Purlin)

`purlin:init` installs a git pre-push hook that runs unit-tier tests before code reaches the remote.

**Two modes** (set in `.purlin/config.json` → `"pre_push"`):

| Mode | Blocks on | Allows |
|------|----------|--------|
| `"warn"` (default) | FAILING proofs | Partial coverage (NO PROOF) with a warning |
| `"strict"` | Anything non-READY | Only fully proved features |

**Warn mode** — for incremental development:
```
purlin: partial coverage:
  checkout → RULE-3: NO PROOF (own)

purlin: passing features:
  login
```
Push goes through. You're still writing tests.

**Strict mode** — for teams that want hard enforcement:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ PUSH BLOCKED (strict mode) — features not fully proved

  checkout: 2/3 rules proved

All features must be READY before push in strict mode.
  → Run: test checkout
  → Run: purlin:verify
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Set the mode during `purlin:init` or change it in `.purlin/config.json`:
```json
{ "pre_push": "strict" }
```

**`--no-verify` is prohibited.** The Purlin agent definition explicitly forbids bypassing the hook. The hook exists to catch problems before they reach the remote — skipping it defeats the purpose.

### Layer 2: CI pipeline

Configure your CI to run tiered tests based on the trigger. Purlin doesn't ship pipeline configs — you write them for your CI system.

**GitHub Actions:**

```yaml
name: Purlin Proof Gate

on:
  pull_request:
    branches: [main]

jobs:
  proof-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit + integration tier tests
        run: |
          pytest  # runs unit + integration tiers via conftest
          python3 scripts/mcp/purlin_server.py --check sync_status

      - name: Check for failing proofs
        run: |
          python3 -c "
          import subprocess, sys
          result = subprocess.run(['python3', 'scripts/mcp/purlin_server.py', '--check', 'sync_status'],
                                  capture_output=True, text=True)
          if 'FAIL' in result.stdout:
              print(result.stdout)
              sys.exit(1)
          print('All proofs passing.')
          "
```

**Bitbucket Pipelines:**

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

**What to enforce per trigger:**

| Trigger | Tiers to run | Block on |
|---------|-------------|----------|
| PR / branch push | unit + `@integration` | Any FAIL |
| Merge to main | All tiers (unit + `@integration` + `@e2e`) | Any FAIL or partial coverage |
| Nightly | `purlin:verify --audit` | vhash mismatch |

### Layer 3: Deploy gate

The strongest enforcement. `purlin:verify --audit` is a clean-room re-execution:

1. Deletes all proof files
2. Re-runs every test (all tiers)
3. Recomputes vhash for every feature
4. Compares against committed receipts

If the locally-computed vhash matches the committed receipt, CI independently confirmed the verification. If not — something changed between verification and deploy.

```yaml
# Add to your deploy pipeline
- name: Deploy Gate
  run: |
    python3 scripts/mcp/purlin_server.py --audit
    # Exit code 0 = all receipts match
    # Exit code 1 = mismatch or missing receipt
```

This catches:
- Tests that were weakened after verification
- Code changes committed after `purlin:verify` without re-verification
- Proof files manually edited to show false passes

---

## Proof Quality Auditing

After tests pass, `purlin:audit` checks whether your tests actually prove what they claim. Three passes, each catching a different class of problem.

Full criteria: [references/audit_criteria.md](../references/audit_criteria.md) (Criteria-Version: 9).

### How the audit works

**Pass 0 — Are the spec's rules behavioral?** (deterministic, no LLM)

Structural proofs (grep checks, file existence, section presence) are **excluded from the audit entirely**. They are not assessed, not scored, and not included in the integrity score. They still run as checks, but they are not proofs.

This prevents structural specs from inflating your score. A spec like "verify agent.md contains ## Core Loop" is a useful check, but it doesn't prove the agent actually follows the core loop.

```
N structural checks excluded from audit
→ Add behavioral rules that test what the system does, not what files contain
```

**Pass 1 — Are the tests structurally sound?** (deterministic, no LLM)

Catches defects that are always wrong, regardless of what the rule says:

| Check | What it catches | Example |
|-------|----------------|---------|
| Tautological assertion | `assert True`, `assert x is not None`, `assert len(x) >= 0` | Always true regardless of code behavior |
| No assertions | Test runs code but checks nothing | `def test_login(): client.post(...)` — no assert |
| Logic mirroring | Expected value computed by same function as SUT | `expected = hash(x); assert hash(x) == expected` |
| Mock target match | Mocking the exact function the rule is about | `@patch("auth.bcrypt")` on a test proving bcrypt usage |
| Bare except:pass | Swallows failures silently | `except Exception: pass` around the code under test |

Any proof that fails here is **HOLLOW** (`✗`). No LLM override possible.

**Pass 2 — Does the test match the rule's intent?** (Claude or external LLM)

For proofs that survived Pass 0 and Pass 1, an LLM checks semantic alignment. It can only return **STRONG** (`✓`) or **WEAK** (`~`):

- STRONG: every assertion matches the proof description, exercises real code, uses the right inputs
- WEAK: missing assertions, happy-path only, looser than described, deep mocking on critical paths

### Scoring

```
Integrity score = (STRONG + MANUAL) / total proofs × 100%
```

WEAK, HOLLOW, and structural-only proofs all count as 0. They're in the denominator, not the numerator.

### Audit caching

Results are cached in `.purlin/cache/audit_cache.json`. The cache key is a hash of (rule text + proof description + test code). If none of those changed since the last audit, the cached STRONG/WEAK result is reused — no LLM call needed. Pass 0 and Pass 1 always run (they're fast and deterministic). Only Pass 2 is cached. Delete the cache file to force a full re-audit.

### Audit results are reused

After `purlin:audit` runs, results are cached in `.purlin/cache/audit_cache.json`. Both `purlin:status` and the HTML dashboard read this cache to display the integrity score without re-running the audit. The cache self-invalidates when rule text, proof descriptions, or test code changes.

### How it runs

`purlin:verify` spawns an independent audit automatically after issuing receipts. The auditor and builder are separate agents — the auditor reads tests, the builder fixes them, they loop until proofs are strong:

```
Auditor → Builder: "PROOF-3 HOLLOW — mocks bcrypt. Use real bcrypt call."
Builder → Auditor: "Fixed."
Auditor → Builder: "PROOF-3 now STRONG ✓."
```

### Cross-model auditing

By default, Claude audits Claude. For independence, use an external LLM:

```
purlin:init --audit-llm
```

Pass 1 still runs deterministically — `assert True` is caught even if the external model would miss it. The external model only does Pass 2 (semantic alignment).

### Structural-only in --audit mode

`purlin:verify --audit` separates behavioral and structural-only features in the report:

```
Behavioral features: 2/2 MATCH
Structural-only features: 2/2 MATCH (not counted toward integrity score)
→ Structural-only features need behavioral rules and E2E proofs for full audit credit
```

Both get receipts and MATCH/MISMATCH reporting, but only behavioral features count toward the integrity score.

### Anchor rules with external references

Audit can't suggest changing anchor rules that are synced from external sources -- those are owned by the external author. It tells the builder to strengthen the test. If the rule itself is ambiguous, it flags it for the anchor's external author.

### Custom criteria

Point to an external criteria file owned by your QA or compliance team:

```json
{ "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md" }
```

Configure via `purlin:init` or `purlin:init --sync-audit-criteria`.

### Quick path

```
purlin:audit login
```

Or fix everything at once:

```
do a purlin:audit and fix all HOLLOW and WEAK proofs, then re-verify until integrity is above 90%
```

---

## Writing a Custom Proof Plugin

### What a proof plugin does

One job: read test metadata during execution, write a JSON file after the run.

### The JSON schema

```json
{
  "tier": "unit",
  "proofs": [
    {
      "feature": "auth_login",
      "id": "PROOF-1",
      "rule": "RULE-1",
      "test_file": "tests/test_login.py",
      "test_name": "test_valid_login",
      "status": "pass",
      "tier": "unit"
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
def write_proofs(results, tier="unit"):
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

