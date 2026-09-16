> Format-Version: 8

# Proof File Format

Proof files are JSON files the proof plugins write while the tests run. They are runtime, not
evidence: the record `purlin:audit` writes is what says a run happened, on which commit, on
which machine, and that is the file that gets committed.

## Location

```
.purlin/runtime/proofs/<feature>.<tier>.json
```

Examples:

- `.purlin/runtime/proofs/login.unit.json`
- `.purlin/runtime/proofs/login.integration.json`
- `.purlin/runtime/proofs/webhook_delivery.e2e.json`

The directory is gitignored. Two runs on two branches never conflict, nothing a plugin writes
reaches a commit, and a test run can never produce a merge conflict. The tier is `unit`,
`integration` or `e2e`; the feature stem may carry dots, so the tier is the last dotted segment
before `.json`.

The project root is the nearest ancestor of the plugin's working directory holding `specs/` or
`.purlin/`, and the working directory itself when no ancestor holds either. Every path a plugin
reads or writes is resolved from there. A working directory below the root is the normal case
rather than the exception: vstest runs a logger from the test output folder, and
`pytest`, `npm test` and `dotnet test` are all run from a subdirectory often enough.

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
| `tier` | string | Test tier: `"unit"`, `"integration"` or `"e2e"`. A tier says what kind of test a proof is, never where it must run. |
| `proofs[].feature` | string | Feature name, matching the spec filename stem. |
| `proofs[].id` | string | Proof id matching the spec's `## Proof` section: `PROOF-1`, `PROOF-2`. |
| `proofs[].rule` | string | Rule id this proof covers: `RULE-1`, `RULE-2`. |
| `proofs[].test_file` | string | Path to the test file relative to the project root, with `/` separators on every operating system. |
| `proofs[].test_name` | string | Test function or case name. |
| `proofs[].status` | string | `"pass"` or `"fail"`. |
| `proofs[].tier` | string | Tier this proof belongs to. |

Seven fields, and no eighth. Fields earlier versions carried and this one does not:

| Retired field | What replaced it |
|---------------|------------------|
| the operating-system field on the file and on every entry | `@env(windows)`, `@env(macos)` or `@env(linux)` on the proof line in the spec. The operating system a proof must be proved on is a property of the claim, not of the test run. |
| the `@<os>` filename suffix | the record, which carries `environment.os` once per run and is named `<timestamp>-<commit7>-ci-<os>.json` when CI wrote it. |
| the run marker `.purlin/runtime/test_run.json` | the record. It says what ran, on which commit, and what passed, once, and it is committed. |

## Merge Behavior (Write-Scoped Overwrite)

The merge key is `(feature, tier, test_file)`. The tier is carried by the filename, so within
one file an entry is addressed by `(feature, test_file)`.

When a proof plugin writes a proof file, it:

1. Loads the existing file, if any.
2. Keeps an existing entry only if it belongs to a different feature, **or** its `test_file`,
   resolved from the project root, still names a file in the working tree **and** either that
   `test_file` was not executed in this run, or the run skipped the test the entry belongs to
   and did not write that entry afresh.
3. Appends the new entries from the current test run.
4. Sorts the merged entries by `(id, test_file, test_name)` under plain ordinal string
   comparison, so `PROOF-1` precedes `PROOF-10` and `PROOF-10` precedes `PROOF-2`, and two runs
   of the same tests in any collection order write byte-identical files.
5. Writes the merged result.

```python
keep(e) = e["feature"] != feature
          or (os.path.exists(os.path.join(project_root, e["test_file"]))
              and (e["test_file"] not in this_run_files
                   or ((feature, e["id"], e["test_file"]) in this_run_skipped
                       and (e["id"], e["test_file"], e["test_name"]) not in this_run_wrote)))
```

`this_run_skipped` holds a `(feature, id, test_file)` triple for each marked test the run
skipped; `this_run_wrote` holds an `(id, test_file, test_name)` triple for each entry this write
is about to append, so an executed test always replaces its own entry even when a skipped test in
the same file carries the same proof id. A plugin whose framework has no skip signal (shell,
sql) leaves `this_run_skipped` empty, and the clause has no effect there.

An entry whose `test_file` is empty or unresolvable fails the existence check and is reaped, then
rewritten by the same write if the current run produced it. No special case is needed.

The merged file is written in full to `<path>.<pid>.tmp` beside the target, where `<pid>` is the
writing process's own id, and the target is then replaced with it in one filesystem operation.
Nothing deletes the target first. A reader that opens the file while a plugin is writing it
therefore sees either the previous content or the new, never a partial document, and two plugins
writing one proof file in the same run never collide on the temp name. A run leaves no `*.tmp`
file behind.

### Why the key includes the test file

Scoping the overwrite per `(feature, tier)` alone means that whenever two test files cover the
same feature at the same tier, whichever runs last erases the other's entries. That forces every
writer for a `(feature, tier)` pair into a single process, which in turn makes it impossible to
split a large suite across files or to run suites independently.

With `test_file` in the key, those writers coexist. They can run in any order, in separate
processes.

### How orphans are reaped

A narrower key reaps less, so three rules bound what survives:

- **A deleted or renamed test file is reaped** (step 2's existence check). A rename presents as a
  gone path plus a new one: the old entry is dropped and the new is appended in the same write.
- **A marker removed from a file that is not re-run is not reaped.** The entry stays until that
  `(feature, tier)` is run again by something that executes the file.
- **A test the run skipped is not reaped**, even though its file ran. Without this, one passing
  test in a file would reap the entry of a sibling that a missing tool skipped. Only an executed
  test replaces its own entry.

`scripts/run/purlin_run.py` empties `.purlin/runtime/proofs/` before the first arm of a run, so
what a `--quick` or `--record` run reads afterwards is what that run observed and nothing else.
A plugin invoked on its own merges into whatever is already there, by the rules above.

### A skipped test writes nothing

`status` records execution, never availability. A test that could not run on this host emits no
entry at all: `"fail"` means it ran and its assertion failed. Writing `"fail"` for a skipped test
is forbidden, because nothing downstream can then tell a broken build from a missing tool.
Emitting nothing is safe because the merge keeps the skipped test's entry. The merge key alone
would not be enough, because a sibling test that did run in the same file puts that file in
`this_run_files`.

Every plugin whose framework reports a skip observes it: pytest reads the skip report (a
`skip`/`skipif` marker, a skipping fixture, or a `pytest.skip()` in the body), jest a `skipped`,
`pending` or `todo` status, vitest a task with no terminal `pass`/`fail` state, and the .NET
logger a `Skipped` outcome. The shell and sql plugins are exempt: their marker is an explicit
call, so a script that never called it cannot be told apart from one that skipped.

### A plugin that saw markers and wrote nothing fails

A plugin that collected at least one marker and appended no entry at all exits non-zero and
prints one line naming the features whose evidence went missing. Silence there leaves a reader
with a proof file from an earlier run believing it describes this one, which is the one failure
failure a test framework cannot report on its own. `scripts/run/purlin_run.py` checks the same
thing a second way, per arm and per marker, so a plugin that was never reached is caught too.

## Proof Markers by Framework

### Feature-name token

One row per shipped framework: the subsection below that documents its marker, and the exact
literal in which the feature name sits, with `<feature>` standing for the name itself. This is
the whole of what a rename has to rewrite, and it is the only place the set is written down. A
framework missing a row here is a framework whose markers a rename walks past, leaving live tests
pointing at a name no spec carries any more. `purlin:rename` rewrites every literal in this
column.

| Framework | Marker section | Feature-name token |
|-----------|----------------|--------------------|
| pytest | pytest | `@pytest.mark.proof("<feature>",` |
| jest | Jest | `[proof:<feature>:` |
| vitest | Vitest (TypeScript-native) | `[proof:<feature>:` |
| shell | Shell | `purlin_proof "<feature>"` |
| sql | SQL | `-- @purlin <feature> ` |
| xunit | xUnit / .NET | `[Trait("PurlinProof", "<feature>:` |

The trailing space in the SQL token is part of the literal: it is the delimiter between the
feature name and `PROOF-N`, and a rewrite that drops it also rewrites a longer name that merely
starts with the old one.

### The retired operating-system keyword

Every marker syntax below once took a list of operating systems: `platforms=(...)` in pytest, `:on(a, b)` in
the jest, vitest and xUnit markers, `on(a, b)` in the SQL comment, and
`PURLIN_PROOF_PLATFORMS` in the shell harness. None of them is read any more. A marker that still
carries one is refused rather than ignored: the plugin prints one line naming the marker and the
replacement, and the run exits non-zero. The replacement is `@env(windows)`, `@env(macos)` or
`@env(linux)` on the proof line in the spec, which is where the claim about the operating system
belongs.

### pytest

```python
@pytest.mark.proof("feature_name", "PROOF-1", "RULE-1")
def test_something():
    assert actual == expected

@pytest.mark.proof("feature_name", "PROOF-2", "RULE-2", tier="integration")
def test_integration_thing():
    assert actual == expected
```

The tier a marker names is also added to the test as a registered pytest marker of its own, so a
tier is selectable with `-m` (for example `-m "not integration and not e2e"` runs only the
unit-tier proofs) without any test having to restate it.

Runner: `python3 -m pytest -q`

Plugin: `scripts/proof/pytest_purlin.py`, scaffolded to `.purlin/plugins/pytest_purlin.py` by
`purlin:init`.

### Jest

```javascript
it("does something [proof:feature_name:PROOF-1:RULE-1:unit]", () => {
  expect(actual).toBe(expected);
});

it("does integration thing [proof:feature_name:PROOF-2:RULE-2:integration]", () => {
  expect(actual).toBe(expected);
});
```

The tier may be omitted: `[proof:feature_name:PROOF-1:RULE-1]` is tier `unit`. The reporter's
pattern is `\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]`; the last group
exists only so the retired keyword can be refused by name.

Runner: `npx jest`

Reporter: `scripts/proof/jest_purlin.js`, scaffolded to `.purlin/plugins/jest_purlin.js` by
`purlin:init`.

### Vitest (TypeScript-native)

Same marker syntax as Jest:

```typescript
it("validates credentials [proof:auth_login:PROOF-1:RULE-1:unit]", () => {
  expect(login("alice", "secret")).toBe(200);
});
```

The reporter collects proofs in `onTestRunEnd(testModules, errors, reason)`, the reporter hook
Vitest 3 and later call, and keeps `onFinished(files)` for Vitest 1 and 2, which have no
`onTestRunEnd`. Whichever fires first writes the files. `jest_purlin.js` is not a drop-in for
Vitest: Vitest does not call Jest's `onTestResult`/`onRunComplete` hooks.

Runner: `npx vitest run`

Reporter: `scripts/proof/vitest_purlin.ts`, scaffolded to `.purlin/plugins/vitest_purlin.ts` by
`purlin:init`.

### Shell

```bash
source scripts/proof/shell_purlin.sh  # or .purlin/plugins/purlin-proof.sh

purlin_proof "feature_name" "PROOF-1" "RULE-1" pass "test description"
purlin_proof "feature_name" "PROOF-2" "RULE-2" fail "test description"
purlin_proof_finish  # writes proof files
```

The tier comes from `PURLIN_PROOF_TIER` and defaults to `unit`.

Runner: `bash tests/my_feature.test.sh`

Plugin: `scripts/proof/shell_purlin.sh`, scaffolded to `.purlin/plugins/purlin-proof.sh` by
`purlin:init`, which is the name every shell test sources.

### SQL

```sql
-- @purlin feature_name PROOF-1 RULE-1 unit
-- Test: unique constraint enforced
INSERT INTO users (name, email) VALUES ('Alice', 'a@test.com');
INSERT OR IGNORE INTO users (name, email) VALUES ('Bob', 'a@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='a@test.com') = 1
       THEN 'PASS' ELSE 'FAIL' END;
```

The tier may be omitted: `-- @purlin feature_name PROOF-1 RULE-1` is tier `unit`. Each block ends
at the next `@purlin` marker or at the end of the file, and must produce a result starting with
`PASS` or `FAIL`.

The engine is the project's `sql_engine` setting from `.purlin/config.json`, defaulting to
`sqlite3`; `PURLIN_SQL_ENGINE` overrides it for one run.

Runner: `bash scripts/proof/sql_purlin.sh tests/test_constraints.sql test.db`

Plugin: `scripts/proof/sql_purlin.sh`.

### xUnit / .NET

The marker is a test trait, not a parsed string. The logger reads exactly one trait name,
`PurlinProof`, compared ordinally: a trait named `Category`, `Property`, `TestProperty`, or
`PurlinProof` in another casing is ignored, and NUnit and MSTest are not supported.

```csharp
[Fact]
[Trait("PurlinProof", "feature_name:PROOF-1:RULE-1:unit")]
public void ValidLogin()
{
    Assert.Equal(200, Login("alice", "secret"));
}
```

The tier may be omitted: `"feature_name:PROOF-1:RULE-1"` is tier `unit`.

Runner: `dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true`

Setup: vstest only discovers loggers from assemblies whose filename ends with
`TestLogger.dll`. Compile `scripts/proof/xunit_purlin.cs` into an assembly named
`Purlin.TestLogger` and reference that project from the test project so the DLL lands in the test
output directory; then `--logger purlin` discovers it by FriendlyName.
`CollectSourceInformation=true` populates `TestCase.CodeFilePath`, which is where `test_file`
comes from.

Plugin: `scripts/proof/xunit_purlin.cs`: a custom `ITestLoggerWithParameters` that collects
results in-process, with no `.trx` post-parse.

## Manual proofs

A rule that no test can settle carries `@manual` on its proof line. No test is written and no proof
entry is ever produced for it, so the rule's strong cell reads `needs a person`. The evidence is
a signature file carrying a one-line note, always written by a person. CI writes no signature
file, at any risk level and under any gate.

## Proof quality guidance

- **Assert behavior, not implementation.** Test what the code does, not how it is structured.
- **Test the attack, not the defense.** Send invalid input and assert the error response.
- **Never assert true.** Every assertion must check a specific expected value.
- **Use realistic inputs.** Test with data shapes that match production, not empty or trivial
  cases.
- **No self-mocking.** Mock external dependencies, but call the code under test for real.

## Git behavior

Proof files are never committed. `.purlin/runtime/` is gitignored, and a proof file that reaches
a commit is a mistake to remove rather than evidence to keep. What gets committed is the record.
