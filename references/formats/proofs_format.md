> Format-Version: 7

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
2. Keep an existing entry only if it belongs to a different feature, **or** its `test_file`,
   resolved from the project root, still names a file in the working tree **and** either that
   `test_file` was not executed in this run, or the run skipped the test the entry belongs to
   and did not write that entry afresh.
3. Append the new entries from the current test run.
4. Sort the merged entries by `(id, test_file, test_name)` under plain ordinal string
   comparison, so `PROOF-1` precedes `PROOF-10` and `PROOF-10` precedes `PROOF-2`, and two runs
   of the same tests in any collection order write byte-identical files.
5. Write the merged result.

```python
keep(e) = e["feature"] != feature
          or (os.path.exists(os.path.join(project_root, e["test_file"]))
              and (e["test_file"] not in this_run_files
                   or ((feature, e["id"], e["test_file"]) in this_run_skipped
                       and (e["id"], e["test_file"], e["test_name"]) not in this_run_wrote)))
```

`project_root` is the nearest ancestor of the plugin's working directory holding `specs/` or
`.purlin/`, the same root every recorded `test_file` was measured against, so the check reads
each path from the place that produced it. `this_run_skipped` holds a `(feature, id, test_file)`
triple for each marked test the run skipped; `this_run_wrote` holds an `(id, test_file, test_name)` triple for each entry this
write is about to append, so an executed test always replaces its own entry even when a
skipped test in the same file carries the same proof id. A plugin whose framework has no skip
signal (shell, sql, phpunit, c) leaves `this_run_skipped` empty, and the clause has no effect
there.

An entry whose `test_file` is empty or unresolvable fails the existence check and is reaped,
then rewritten by the same write if the current run produced it. No special case is needed.

The merged file is written in full to `<path>.<pid>.tmp` beside the target, where `<pid>` is the
writing process's own id, and the target is then replaced with it in one filesystem operation.
Nothing deletes the target first. A reader that opens the file while a plugin is writing it
therefore sees either the previous content or the new, never a partial document, and two
plugins writing one proof file in the same run never collide on the temp name. A run leaves no
`*.tmp` file behind.

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
- **A test the run skipped is not reaped**, even though its file ran. Without this, one
  passing test in a file would reap the committed entry of a sibling that a missing tool
  skipped, and the evidence a capable host produced would disappear on a host that cannot
  reproduce it. Only an executed test replaces its own entry.

The existence check resolves `test_file` from the project root, not from the process's working
directory, and so does the `specs/**/*.md` scan that finds where to write. The root is the
nearest ancestor of the working directory holding `specs/` or `.purlin/`, and the working
directory itself when no ancestor holds either. A working directory below the root is the
normal case rather than the exception: the .NET test platform runs a logger from the test
output folder, and `pytest`, `npm test` and `dotnet test` are all run from a subdirectory
often enough. Reading each path from the root is what keeps such a run adding one entry
instead of failing every check and reaping the whole feature.

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
is forbidden, because nothing downstream can then tell a broken build from a missing tool.
Emitting nothing is safe because the merge keeps the skipped test's entry: whatever a capable
host last proved for those ids stays committed and untouched, so the skip neither falsifies nor
destroys it. The merge key alone would not be enough, because a sibling test that did run in the
same file puts that file in `this_run_files`.

Every plugin whose framework reports a skip observes it: pytest reads the skip report (a
`skip`/`skipif` marker, a skipping fixture, or a `pytest.skip()` in the body), jest a `skipped`,
`pending` or `todo` status, vitest a task with no terminal `pass`/`fail` state, and the .NET
logger a `Skipped` outcome. The shell, sql, phpunit and c plugins are exempt: their marker is an
explicit call, so a script that never called it cannot be told apart from one that skipped.

A proof the spec declares with `@on(...)` and no scoped result for a named platform is reported
as `AWAITING RUNNER` rather than `NO PROOF`. It does not count against coverage and does not
block a receipt; a receipt issued while one is outstanding records it as platform-partial.

## Run marker

A run leaves one more record beside the proof files: the run marker
`.purlin/runtime/test_run.json`. Every plugin writes or merges it at the moment it writes its
proof files (`proof_common` RULE-19), so a receipt issued in a project that has no sweep script
still names the run its evidence came from. Without it `evidence.test_run` in a receipt is
`null`, and the receipt says only that some file on disk holds a `pass`.

```json
{
  "at": "2026-03-31T14:02:11Z",
  "commit": "9f1c0a7e2b5d4c8091a3f6e7d2b1c4a5e6f70819",
  "sweep": "pytest_purlin",
  "test_files": ["tests/test_login.py"],
  "passed": 2,
  "failed": 0,
  "skipped": 1,
  "ok": true,
  "runs": [
    {
      "plugin": "pytest_purlin",
      "at": "2026-03-31T14:02:11Z",
      "test_files": ["tests/test_login.py"],
      "passed": 2,
      "failed": 0,
      "skipped": 1
    }
  ],
  "skipped_proofs": [
    {
      "feature": "login",
      "id": "PROOF-4",
      "test_file": "tests/test_login.py",
      "test_name": "test_native_lock",
      "reason": "tool not installed"
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `at` | string | When the run finished, ISO 8601 in UTC. |
| `commit` | string or null | `git rev-parse HEAD` in the project root; `null` outside a git work tree. |
| `sweep` | string | The writer's name: `pytest_purlin`, `jest_purlin`, `vitest_purlin`, `shell_purlin`, `sql_purlin`, `c_purlin`, `phpunit_purlin`, `xunit_purlin`, or the sweep script's own name, so a reader can tell a plugin marker from a sweep marker. |
| `test_files` | array | The project-relative, forward-slash files the run collected proofs from. |
| `passed` | number | Marked results this run observed as passing. |
| `failed` | number | Marked results this run observed as failing. |
| `skipped` | number | Marked tests this run skipped. |
| `ok` | boolean | True only while every merged run had no failure. |
| `runs` | array | One `{plugin, at, test_files, passed, failed, skipped}` object per contributing run. |
| `skipped_proofs` | array | One `{feature, id, test_file, test_name, reason}` object per marked test the run skipped (`proof_common` RULE-20). Written only when the union is non-empty, so a run that skipped nothing adds no key. |

`reason` is the message the framework carried and is never invented. pytest's skip message and
the .NET test platform's skip message are real strings; jest reports a `skipped`, `pending` or
`todo` status with no message and vitest a task with no terminal state and no message, so both
write `null`. A plugin whose framework reports no skip at all (shell, sql, phpunit, c) writes no
`skipped_proofs` entry, because a script that never called the marker cannot be told apart from
one that skipped.

`skipped_proofs` is what turns a kept entry into a stated one. The merge holds the committed
entry of a skipped test in place, and this list is how a surface reading the marker can say the
entry was inherited from the commit that last proved it rather than presenting it as evidence
this run produced.

### Merging

A run whose `commit` equals an existing marker's `commit` is merged into it:

- `test_files` unioned,
- `passed`, `failed` and `skipped` summed,
- the run appended to `runs`,
- `ok` and-ed,
- `skipped_proofs` unioned keyed by `(feature, id, test_file, test_name)`, the entry already in
  the marker winning,
- every other top-level field carried through untouched, so a field a later version of this
  contract adds is never dropped by an older plugin.

Any other commit starts a new marker, because a count carried across commits would describe two
trees.

A sweep script that watches whole suites merges by the same rule and owns the summary: it keeps
`runs` and every field it does not write, and replaces `test_files`, the three counts and `ok`
with its own, because it watched every suite the plugins inside it reported on. It carries
`skipped_proofs` through untouched, because a sweep watches suites and cannot see which marked
test inside one was skipped.

The marker is written the same way a proof file is: in full to a temp file beside it whose name
carries the writing process's own id, then one filesystem operation replacing the target. A
reader sees one whole marker or the other, never a partial document, and two plugins writing one
marker in the same run never collide on the temp name. A read that lands on unparsable JSON is
retried before the writer gives up and starts a fresh marker.

Nothing is written at all when the project root holds no `.purlin/` directory. That is not a
Purlin project, and a plugin must not create one.

## Proof Markers by Framework

### Feature-name token

One row per shipped framework: the subsection below that documents its marker, and the exact
literal in which the feature name sits, with `<feature>` standing for the name itself. This is
the whole of what a rename has to rewrite, and it is the only place the set is written down.
A framework missing a row here is a framework whose markers a rename walks past, leaving live
tests pointing at a name no spec carries any more. `purlin:rename` rewrites every literal in
this column.

| Framework | Marker section | Feature-name token |
|-----------|----------------|--------------------|
| pytest | pytest | `@pytest.mark.proof("<feature>",` |
| jest | Jest | `[proof:<feature>:` |
| vitest | Vitest (TypeScript-native) | `[proof:<feature>:` |
| shell | Shell | `purlin_proof "<feature>"` |
| xunit | xUnit / .NET | `[Trait("PurlinProof", "<feature>:` |
| phpunit | PHP | `@purlin <feature> ` |
| sql | SQL (sqlite3) | `-- @purlin <feature> ` |
| c | C | `purlin_proof("<feature>",` and `purlin_proof_on("<feature>",` |

The trailing space in the PHP and SQL tokens is part of the literal: it is the delimiter
between the feature name and `PROOF-N`, and a rewrite that drops it also rewrites a longer
name that merely starts with the old one. C is the one framework whose feature name sits in
two call forms, the platform-bearing one and the plain one, so both are rewritten.

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

The tier a marker names is also added to the test as a registered pytest marker of its own,
so a tier is selectable with `-m` (for example `-m "not integration and not e2e"` runs only
the unit-tier proofs) without any test having to restate it.

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

Reporter: `scripts/proof/vitest_purlin.ts`. It collects proofs in the `onFinished(files)` hook (stable across Vitest 2.x → 4.x). `jest_purlin.js` is not used for Vitest: Vitest does not call Jest's reporter hooks.

### xUnit / .NET

The marker is a test trait, not a parsed string. The logger reads exactly one trait name, `PurlinProof`, compared ordinally: a trait named `Category`, `Property`, `TestProperty`, or `PurlinProof` in another casing is ignored, and NUnit and MSTest are not supported.

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

Plugin: `scripts/proof/xunit_purlin.cs`: a custom `ITestLoggerWithParameters` that collects results in-process (no `.trx` post-parse).

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
