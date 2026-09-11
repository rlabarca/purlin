> Format-Version: 4

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
| `tier` | string | Test tier: `"unit"`, `"integration"`, `"e2e"`, `"windows"` (platform-gated), etc. Freeform — a proof tagged `@<name>` lives in `<feature>.proofs-<name>.json`. |
| `proofs[].feature` | string | Feature name (matches spec filename stem) |
| `proofs[].id` | string | Proof ID matching `## Proof` section: `PROOF-1`, `PROOF-2`, etc. |
| `proofs[].rule` | string | Rule ID this proof covers: `RULE-1`, `RULE-2`, etc. |
| `proofs[].test_file` | string | Relative path to the test file |
| `proofs[].test_name` | string | Test function/case name |
| `proofs[].status` | string | `"pass"` or `"fail"` |
| `proofs[].tier` | string | Tier this proof belongs to |

## Merge Behavior (Write-Scoped Overwrite)

The merge key is `(feature, tier, test_file)`. The tier is carried by the filename, so within
one tier file an entry is addressed by `(feature, test_file)`.

When proof plugins write a proof file, they:

1. Load the existing file (if any).
2. Keep an existing entry only if it belongs to a different feature, **or** its `test_file`
   was not executed in this run **and** that `test_file` still resolves to a file in the
   working tree.
3. Append the new entries from the current test run.
4. Write the merged result.

```python
keep(e) = e["feature"] != feature
          or (e["test_file"] not in this_run_files and os.path.exists(e["test_file"]))
```

An entry whose `test_file` is empty or unresolvable fails the existence check and is reaped,
then rewritten by the same write if the current run produced it. No special case is needed.

### Why the key includes the test file

Scoping the overwrite per `(feature, tier)` alone means that whenever two test files cover
the same feature at the same tier, whichever runs last erases the other's entries. That
forces every writer for a `(feature, tier)` pair into a single process, which in turn makes
it impossible to split a large suite across files, to run suites independently, or to prove
a platform-gated tier on a remote runner and merge the result back.

With `test_file` in the key, those writers coexist. They can run in any order, in separate
processes, on separate machines.

### How orphans are reaped

A narrower key reaps less, so two rules bound what survives:

- **A deleted or renamed test file is reaped** (step 2's existence check). A rename presents
  as a gone path plus a new one: the old entry is dropped and the new is appended in the
  same write.
- **A marker removed from a file that is not re-run is not reaped.** The entry stays until
  that `(feature, tier)` is run again by something that executes the file. This is the
  deliberate cost of per-file scoping, and it is asserted by a proof so it cannot change
  silently.

The existence check resolves `test_file` relative to the process's working directory, which
the plugins already require to be the repository root (they glob `specs/**/*.md` from it). If
a plugin is run from elsewhere, every path fails the check and the merge degrades to the
older feature-wide purge: narrower than intended, never wider.

A platform-gated tier (e.g. `windows`, emitted only by a CI runner where those tests run, and
skipped elsewhere) is never touched by a host run that skips those tests: a run only rewrites
the tier files it actually collected proofs for. So a CI-committed `<feature>.proofs-windows.json`
survives subsequent local runs and is read by `sync_status`/`purlin:verify` like any other tier.

### A skipped test writes nothing

`status` records execution, never availability. A test that could not run on this host emits no
entry at all: `"fail"` means it ran and its assertion failed. Writing `"fail"` for a skipped test
is forbidden, because nothing downstream can then tell a broken build from a missing tool. Under
the merge key above, emitting nothing is safe: whatever a capable host last proved for those ids
stays committed and untouched, so the skip neither falsifies nor destroys it.

A proof the spec declares at a runner-gated tier with no entry in that tier's file is reported as
`AWAITING RUNNER` rather than `NO PROOF`. It does not count against coverage and does not block a
receipt; a receipt issued while one is outstanding records it as platform-partial.

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

### C

```c
#include "c_purlin.h"

int main(void) {
    int result = add(2, 3);
    purlin_proof("feature_name", "PROOF-1", "RULE-1",
                 result == 5, "test_addition", __FILE__, "unit");
    purlin_proof_finish();  /* prints JSON to stdout */
    return 0;
}
```

Compile and pipe: `gcc -o test test.c && ./test | python3 scripts/proof/c_purlin_emit.py`

Header: `scripts/proof/c_purlin.h`. Emitter: `scripts/proof/c_purlin_emit.py`.

### PHP

```php
<?php
/** @purlin feature_name PROOF-1 RULE-1 unit */
function testValidLogin() {
    $result = login("alice", "secret");
    if ($result !== 200) throw new Exception("Expected 200");
}
```

Runner: `php scripts/proof/phpunit_purlin.php tests/AuthTest.php`

Plugin: `scripts/proof/phpunit_purlin.php`.

### SQL (sqlite3)

```sql
-- @purlin feature_name PROOF-1 RULE-1 unit
-- Test: unique constraint enforced
INSERT INTO users (name, email) VALUES ('Alice', 'a@test.com');
INSERT OR IGNORE INTO users (name, email) VALUES ('Bob', 'a@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='a@test.com') = 1
       THEN 'PASS' ELSE 'FAIL' END;
```

Runner: `bash scripts/proof/sql_purlin.sh tests/test_constraints.sql test.db`

Plugin: `scripts/proof/sql_purlin.sh`.

### Vitest (TypeScript-native)

Same marker syntax as Jest. Use the TypeScript reporter for type-safe integration:

```typescript
it("validates credentials [proof:auth_login:PROOF-1:RULE-1:unit]", () => {
  expect(login("alice", "secret")).toBe(200);
});
```

Reporter: `scripts/proof/vitest_purlin.ts`. It collects proofs in the `onFinished(files)` hook (stable across Vitest 2.x → 4.x). `jest_purlin.js` is not used for Vitest — Vitest does not call Jest's reporter hooks.

### xUnit / .NET

The marker is a test trait, not a parsed string — `[Trait]` (xUnit), `[Category]`/`[Property]` (NUnit), and `[TestProperty]` (MSTest) all surface as `TestCase.Traits`:

```csharp
[Fact]
[Trait("PurlinProof", "feature_name:PROOF-1:RULE-1:unit")]
public void ValidLogin()
{
    Assert.Equal(200, Login("alice", "secret"));
}
```

Runner: `dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true`

Setup: the .NET test platform only discovers loggers from assemblies whose filename ends with `TestLogger.dll`. Compile `scripts/proof/xunit_purlin.cs` into an assembly named `Purlin.TestLogger` and reference that project from the test project so the DLL lands in the test output directory; then `--logger purlin` discovers it by FriendlyName. `CollectSourceInformation=true` populates `TestCase.CodeFilePath` so `test_file` is recorded.

Plugin: `scripts/proof/xunit_purlin.cs` — a custom `ITestLoggerWithParameters` that collects results in-process (no `.trx` post-parse). Spec: `specs/proof/proof_plugins_xunit.md`.

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
