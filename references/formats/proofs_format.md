> Format-Version: 5

# Proof File Format

Proof files are JSON files emitted by test runners with proof markers. They live next to the spec they cover.

## File Naming

```
<feature>.proofs-<tier>.json                  platform-agnostic
<feature>.proofs-<tier>@<platform-id>.json    scoped to one platform
```

Examples:
- `specs/auth/login.proofs-unit.json`
- `specs/auth/login.proofs-integration.json`
- `specs/auth/login.proofs-unit@windows-2022.json`
- `specs/webhooks/webhook_delivery.proofs-unit.json`

A result lands in a scoped file when, and only when, its test marker declares platforms
(see "Platform markers" under each framework below). The `<platform-id>` is the host's id:
`PURLIN_PLATFORM` when set, otherwise the detected OS family (`windows`, `macos`, `linux`).
It is `[a-z0-9][a-z0-9-]*`, the same charset as a spec's `@on(...)` tag; a file whose
suffix is outside that charset is not read. The tier is `unit`, `integration` or `e2e`.

Legacy: a `<feature>.proofs-windows.json` from Format-Version 4 is read for one release as
`unit@windows`; `sync_status` prints an advisory naming the file and `purlin:init --update`,
which renames it. `windows` is a platform, never a tier.

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

A scoped file carries `platform` at the top level and on every entry, equal to the id in
its name and constant for the whole file:

```json
{
  "tier": "unit",
  "platform": "windows-2022",
  "proofs": [
    {
      "feature": "login",
      "id": "PROOF-3",
      "rule": "RULE-3",
      "test_file": "tests/test_login.py",
      "test_name": "test_native_lock",
      "status": "pass",
      "tier": "unit",
      "platform": "windows-2022"
    }
  ]
}
```

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `tier` | string | Test tier: `"unit"`, `"integration"` or `"e2e"`. A tier says what kind of test a proof is, never where it must run. |
| `platform` | string | Scoped files only. The platform id from the filename, at the top level and on every entry; absent from an agnostic file and its entries. |
| `proofs[].feature` | string | Feature name (matches spec filename stem) |
| `proofs[].id` | string | Proof ID matching `## Proof` section: `PROOF-1`, `PROOF-2`, etc. |
| `proofs[].rule` | string | Rule ID this proof covers: `RULE-1`, `RULE-2`, etc. |
| `proofs[].test_file` | string | Path to the test file relative to the project root, with `/` separators on every OS |
| `proofs[].test_name` | string | Test function/case name |
| `proofs[].status` | string | `"pass"` or `"fail"` |
| `proofs[].tier` | string | Tier this proof belongs to |
| `proofs[].platform` | string | Scoped files only; equals the top-level `platform` |

## Merge Behavior (Write-Scoped Overwrite)

The merge key is `(feature, tier, platform, test_file)`, with `platform` empty for an
agnostic file. The tier and the platform are carried by the filename, so within one file an
entry is addressed by `(feature, test_file)` and the merge within a file is unchanged from
the three-part key `(feature, tier, test_file)` it grew from. A run that writes a scoped
file never touches the agnostic file or another platform's file.

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
a platform-scoped proof on a remote runner and merge the result back.

With `test_file` in the key, those writers coexist. They can run in any order, in separate
processes, on separate machines.

### How orphans are reaped

A narrower key reaps less, so two rules bound what survives:

- **A deleted or renamed test file is reaped** (step 2's existence check). A rename presents
  as a gone path plus a new one: the old entry is dropped and the new is appended in the
  same write.
- **A marker removed from a file that is not re-run is not reaped.** The entry stays until
  that `(feature, tier, platform)` is run again by something that executes the file. This is
  the deliberate cost of per-file scoping, and it is asserted by a proof so it cannot change
  silently.

The existence check resolves `test_file` relative to the process's working directory, which
the plugins already require to be the repository root (they glob `specs/**/*.md` from it). If
a plugin is run from elsewhere, every path fails the check and the merge degrades to the
older feature-wide purge: narrower than intended, never wider.

A proof the spec tags `@on(windows-2022)` is proved by a scoped file,
`<feature>.proofs-unit@windows-2022.json`, written by the run whose `PURLIN_PLATFORM` was
`windows-2022` (a runner sets it) from a marker that declares that platform. A local run on
macOS with the same marker writes `<feature>.proofs-unit@macos.json` instead, which satisfies
nothing the spec asked for and harms nothing either: a run only rewrites the files it actually
collected proofs for, so the CI-committed `@windows-2022` file survives every local run and is
read by `sync_status`/`purlin:verify` like any other proof file.

### Runners

There is one plugin per framework, everywhere. A runner executes the same plugin file the
developer runs (this repository's `scripts/proof/*`, a consumer project's `.purlin/plugins/*`
copies, byte-identical), and `PURLIN_PLATFORM` is the only per-runner input. The marker
decides whether a result is scoped; the environment only names the file. Plugins never
evaluate version constraints and never read the `platforms` registry: whether a host with a
given id satisfies what a spec asked for is `sync_status`'s judgement, made from the file
name. Nothing in a plugin branches on the host operating system except the family fallback
inside its one host-platform helper, which is what makes a simulated Windows path on macOS
not a Windows proof without a second code path.

### A skipped test writes nothing

`status` records execution, never availability. A test that could not run on this host emits no
entry at all: `"fail"` means it ran and its assertion failed. Writing `"fail"` for a skipped test
is forbidden, because nothing downstream can then tell a broken build from a missing tool. Under
the merge key above, emitting nothing is safe: whatever a capable host last proved for those ids
stays committed and untouched, so the skip neither falsifies nor destroys it.

A proof the spec declares with `@on(...)` and no scoped result for a named platform is reported
as `AWAITING RUNNER` rather than `NO PROOF`. It does not count against coverage and does not
block a receipt; a receipt issued while one is outstanding records it as platform-partial.

## Proof Markers by Framework

### pytest

```python
@pytest.mark.proof("feature_name", "PROOF-1", "RULE-1")
def test_something():
    assert actual == expected

@pytest.mark.proof("feature_name", "PROOF-2", "RULE-2", tier="integration")
def test_integration_thing():
    assert actual == expected

@pytest.mark.proof("feature_name", "PROOF-3", "RULE-3", platforms=("windows-2022",))
def test_platform_specific_thing():
    assert actual == expected
```

Platform markers: `platforms=(...)` takes a tuple of ids, or one id as a bare string. A
marker with it writes the scoped file; a marker without it writes the agnostic file.

Plugin: `scripts/proof/pytest_purlin.py` (scaffolded to `.purlin/plugins/pytest_purlin.py` by `purlin:init`).

### Jest

```javascript
it("does something [proof:feature_name:PROOF-1:RULE-1:unit]", () => {
  expect(actual).toBe(expected);
});

it("does integration thing [proof:feature_name:PROOF-2:RULE-2:integration]", () => {
  expect(actual).toBe(expected);
});

it("locks natively [proof:feature_name:PROOF-3:RULE-3:unit:on(windows-2022)]", () => {
  expect(actual).toBe(expected);
});
```

Platform markers: `[proof:feature:PROOF-N:RULE-N[:tier][:on(a, b)]]`. The tier may be
omitted while `on(...)` is present (`[proof:f:PROOF-3:RULE-3:on(windows)]` is tier `unit`).
The reporter's pattern is `\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]`.

Reporter: `scripts/proof/jest_purlin.js` (scaffolded to `.purlin/plugins/jest_purlin.js` by `purlin:init`).

### Shell

```bash
source scripts/proof/shell_purlin.sh  # or .purlin/plugins/purlin-proof.sh

purlin_proof "feature_name" "PROOF-1" "RULE-1" pass "test description"
purlin_proof "feature_name" "PROOF-2" "RULE-2" fail "test description"
PURLIN_PROOF_PLATFORMS="windows-2022" purlin_proof "feature_name" "PROOF-3" "RULE-3" pass "native lock"
purlin_proof_finish  # writes proof files
```

Platform markers: `PURLIN_PROOF_PLATFORMS`, a comma-separated list of ids, read at each
`purlin_proof` call beside `PURLIN_PROOF_TIER`. Set it for one call (as above) or export it
for a whole script.

### C

```c
#include "c_purlin.h"

int main(void) {
    int result = add(2, 3);
    purlin_proof("feature_name", "PROOF-1", "RULE-1",
                 result == 5, "test_addition", __FILE__, "unit");
    purlin_proof_on("feature_name", "PROOF-3", "RULE-3",
                    locked, "test_native_lock", __FILE__, "unit", "windows-2022");
    purlin_proof_finish();  /* prints JSON to stdout */
    return 0;
}
```

Platform markers: `purlin_proof_on(feature, proof_id, rule_id, passed, name, file, tier,
platforms)` with `platforms` a comma-separated string; `purlin_proof` is the same call with
`NULL`. The header prints `"platforms": "a,b"` on each entry and the emitter does the host
detection and the file naming.

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

/** @purlin feature_name PROOF-3 RULE-3 unit on(windows-2022) */
function testNativeLock() { ... }
```

Platform markers: `@purlin feature PROOF-N RULE-N [tier] [on(a, b)]`; the tier may be
omitted while `on(...)` is present.

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

-- @purlin feature_name PROOF-3 RULE-3 unit on(windows-2022)
-- Test: case-insensitive collation on the native build
SELECT 'PASS';
```

Platform markers: `-- @purlin feature PROOF-N RULE-N [tier] [on(a, b)]`; the tier may be
omitted while `on(...)` is present.

Runner: `bash scripts/proof/sql_purlin.sh tests/test_constraints.sql test.db`

Plugin: `scripts/proof/sql_purlin.sh`.

### Vitest (TypeScript-native)

Same marker syntax as Jest, including `:on(a, b)`. Use the TypeScript reporter for type-safe integration:

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

[Fact]
[Trait("PurlinProof", "feature_name:PROOF-3:RULE-3:unit:on(windows-2022)")]
public void NativeLock() { ... }
```

Platform markers: trait value `feature:PROOF-N:RULE-N[:tier][:on(a, b)]`; `on(...)` may
follow the tier or stand in its place.

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
