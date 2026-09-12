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
| `purlin:test` | Run tests and emit proof files |
| `purlin:verify` | Run all tests, issue verification receipts |
| `purlin:audit` | Check proof quality: are the claims provable, and are they proven |

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

Works with `ts-jest`. For **Vitest**, use the native TypeScript reporter `scripts/proof/vitest_purlin.ts` instead of `jest_purlin.js` — Vitest does not call Jest's reporter hooks. Register it in `vitest.config.ts`: `test: { reporters: ['default', '.purlin/plugins/vitest_purlin.ts'] }`.

### xUnit (.NET — C#, F#, VB.NET)

The marker is a test trait, not a parsed string:

```csharp
[Fact]
[Trait("PurlinProof", "auth_login:PROOF-1:RULE-1:unit")]
public void ValidLoginReturns200()
{
    Assert.Equal(200, Login("alice", "secret"));
}
```

NUnit `[Category]`/`[Property]` and MSTest `[TestProperty]` surface the same way. Run with `dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true`. Setup is manual — see [proofs_format.md](../references/formats/proofs_format.md) for wiring the `Purlin.TestLogger` assembly.

`CollectSourceInformation=true` (plus full PDBs) is what populates each proof's `test_file`; without surfaced source info `dotnet test` leaves it empty. `purlin:audit` handles that case anyway — it resolves the source from the fully-qualified `test_name` via `static_checks.py --resolve-source`, so C# Pass-1/Pass-2 works even when `test_file` is blank.

### Shell (Bash)

```bash
source .purlin/plugins/shell_purlin.sh
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
| `@on(<platform-id>)` | Only on a host that satisfies that platform | Behaviour that needs a named platform: native `msvcrt` locking on `@on(windows-2022)`, an APFS rename on `@on(macos-14)`. Not a tier: it sits beside one. See `references/formats/spec_format.md`, "Platform tags" |
| `@manual` | Human-initiated | Visual quality, UX judgment |

`@on(...)` is not a tier. A tier says what kind of test a proof is; `@on(...)` says
where it must run, and a proof carries both (`@unit @on(windows-2022)`). A proof
declared on a platform no result satisfies reports `AWAITING RUNNER` rather than
`NO PROOF`, does not count against coverage and does not block a receipt, and a
receipt issued while one is outstanding records it as platform-partial. So
declaring `@on(...)` on a test any host could run quietly removes it from the
coverage denominator. `references/remote_verification.md` covers the runner loop
that closes the gap.

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

**Level 1 is UNPROVABLE** — reject it. `assert x is not None` proves nothing about behavior. `purlin:audit --design` flags a Level 1 *description* automatically, before any test is written against it. (HOLLOW is the matching verdict on the test side; the vocabularies stay separate on purpose — PROVABLE/LOOSE/UNPROVABLE describe descriptions, STRONG/WEAK/HOLLOW describe tests.)

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

There is no required order. This is the common path; `purlin:status` reads what exists and tells
you the next step for the state you are actually in. Working spec-first, you stay at step 0
until Proof Design is where you want it — nothing below needs to exist yet.

### 0. Grade the proofs (no tests required)

```
purlin:audit <feature> --design
```

Scores every proof description as PROVABLE, LOOSE, UNPROVABLE or STRUCTURAL from the spec
alone. Fix findings with `purlin:spec`. This is the cheapest step in the workflow: a LOOSE
description caps what the test can prove, and an UNPROVABLE one guarantees the test gets
written, audited, rejected and rewritten.

### 1. Check coverage

```
purlin:status
```

### 2. Write and run tests

```
purlin:test
```

The proof plugin collects markers and writes proof files using write-scoped overwrite: within a tier file, it replaces only the tested feature's entries from the test files this run executed. Entries from another feature, or from a test file this run did not touch, are left alone.

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

Purlin doesn't ship pipeline configs — you write them. Example (GitHub Actions):

```yaml
on:
  pull_request:        # PRs: unit + integration tiers
  push:
    branches: [main]   # main: all tiers

jobs:
  proofs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - if: github.event_name == 'pull_request'
        run: pytest -m "not e2e"
      - if: github.event_name == 'push'
        run: pytest
```

| Trigger | Tiers to run | Block on |
|---------|-------------|----------|
| PR / branch push | unit + `@integration` | Any FAIL |
| Merge to main | All tiers | Any FAIL or partial coverage |
| Nightly | `purlin:verify --recheck` | vhash mismatch |

### Deploy gate

`purlin:verify --recheck` is a clean-room re-execution: re-runs every test, recomputes vhash, and compares against committed receipts.

```yaml
- name: Deploy Gate
  run: |
    # Run purlin:verify --recheck via Claude Code in CI
    # This re-runs all tests (all tiers) and validates vhash against committed receipts
    pytest
```

---

## Proof Quality Auditing

`purlin:audit` measures two gauges. It picks its mode from what exists — design-only when no
proof has executed anywhere, both otherwise — and says which it chose.

**Proof Design** (`--design`) asks *is the claim provable?* It reads the rule and its proof
description, needs no test code, and grades each description PROVABLE, LOOSE, UNPROVABLE or
STRUCTURAL. Score = PROVABLE / (PROVABLE + LOOSE + UNPROVABLE); STRUCTURAL is excluded, just as
EXCLUDED is excluded from Integrity. That is the assessed score; what the dashboard and
`purlin:status` headline is that score weighted by measurement coverage (see below).

**Proof Integrity** (`--integrity`) asks *is the claim proven?* It reads test code. Three passes:

**Pass 0.5 — Proof-file structural checks** (deterministic, JSON-only). Pre-audit validation of `.proofs-*.json` files before reading source code. Catches proof ID collisions (same PROOF-N targeting different RULE-N values) and orphaned proofs (PROOF-N targeting non-existent RULE-N).

**Pass 1 — Static analysis: structural defect detection** (deterministic). Catches: `assert True`, no assertions, logic mirroring, mocking the thing being tested, bare `except: pass`. Any failure here is **HOLLOW** — no override possible.

**Pass 2 — Classification + semantic alignment** (LLM). First classifies each proof as structural or behavioral by examining test code AND fixture/setup context — structural proofs that only check pre-existing files are excluded from scoring. Then checks if behavioral assertions match the rule's intent. Returns **STRONG**, **WEAK**, or **EXCLUDED**.

```
Integrity score = (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) x 100%
```

### Assessed score vs reported score

Both formulas above score the proofs the audit cache actually holds. Every project-wide surface
— the dashboard cards, the `purlin:status` summary line — reports that score weighted by how
much of the project it covers:

```
reported = passing / (gradeable + unmeasured)
```

An unassessed proof is unknown, not passing, so it counts in the denominator until someone
looks at it. At full coverage the two figures are equal. Below it they diverge, and both are
shown: the headline is the reported figure, with the denominator and the assessed score beside
it. Without this a repo reported 100% Integrity from 11 graded proofs while 39 of its 40 feature
rows read `not audited`. Per-feature gauges report the assessed score directly, because a
partially assessed feature reads `not audited` rather than a number.

**Fix Design first.** Four WEAK criteria and three STRONG criteria are comparisons against the
proof description ("the description says verify X AND Y but the test only checks X"). Against a
description like "Verify authentication works" none of them can fire, so a test asserting
almost nothing scores STRONG. A high Integrity score over LOOSE descriptions is evidence of an
unfalsifiable spec, not of good tests.

**What moves what.** HOLLOW is decided by static analysis of test code — no spec edit moves it.
EXCLUDED is decided by the test's shape. WEAK is the only Integrity level spec prose can move,
and narrowing a description to match a weak test lowers the claim instead of strengthening the
evidence — never do that, and never on an anchor rule. The Design levels are the ones prose is
meant to move.

**Reaching a target.** With `N` behavioural proofs and `H` HOLLOW, the ceiling is `(N - H) / N`,
a target `T` is reachable only if `H <= (1 - T) x N`, and the tests you must rewrite number
`max(0, H - floor((1 - T) x N))`. For 287 proofs with 57 HOLLOW the ceiling is 80%, so a 90%
target needs 29 tests rewritten — answer that before starting work, not after.

Results are cached in `.purlin/cache/audit_cache.json`, and Design results in
`.purlin/cache/design_cache.json` (keyed without test code, so a design grade survives test
edits). Both self-invalidate when their inputs change.

### Quick path

```
purlin:audit login
```

Or fix everything at once:

```
do a purlin:audit and fix all HOLLOW and WEAK proofs in the build loop, and all UNPROVABLE and LOOSE proof descriptions with purlin:spec, then re-verify
```

### Cross-model auditing (experimental)

```
purlin:init --audit-llm
```

Use an external LLM for Pass 2 instead of Claude auditing Claude.

---

## Proof Plugins

Built-in plugins for pytest, Jest, Vitest, C, PHP, SQL, and Shell are installed by `purlin:init` based on your framework selection; the xUnit (.NET) plugin ships too but needs manual wiring (see [supported frameworks](../references/supported_frameworks.md)). Check `.purlin/plugins/` to see what's active.

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
next to specs. Merges on (feature, tier, test_file) so other
features' proofs, and this feature's proofs from test files
this run did not execute, are preserved.
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
2. Write-scoped overwrite: replace this feature's entries from the test files this run executed, reap entries whose test file no longer exists, preserve everything else
3. Write files next to specs: `specs/<category>/<feature>.proofs-<tier>.json`
4. Handle parameterized tests (one entry per proof, pass only if ALL variants pass)

Full JSON schema: [references/formats/proofs_format.md](../references/formats/proofs_format.md)

---

## Proof File Merge Conflicts

Proof files are derived state. When merging:

1. Accept either version of the conflicting file
2. Run `purlin:test` to regenerate from the merged code
3. Commit the result

This works because the merge is write-scoped: re-running a test file rewrites only that file's entries for that feature and tier. Re-run every suite that writes the conflicting tier file, not just one, or the suites you skip keep whatever the merge inherited.
