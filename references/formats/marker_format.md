> Format-Version: 2

# Marker format

How a test in a project's own suite is tied to a proof. A proof says in plain
language how a rule is shown to hold; a test is any test in the project's
suite that carries one comment naming the proof. Nothing of Purlin is
installed in the test suite: Purlin runs the project's own test command, reads
the report that command writes, and ties each result to the markers above its
test.

## The marker

One comment, in the language's own comment syntax, on a line above the test:

```python
# purlin: login PROOF-4
def test_rejects_a_wrong_password():
```

```go
// purlin: login PROOF-4
func TestRejectsAWrongPassword(t *testing.T) {
```

The shape is `purlin: <feature> PROOF-<n>`: the feature is the spec's name,
and the proof is one of its `## Proof` lines. The marker names the proof only;
the spec already says which rule a proof serves.

Where a rule has no proof, which is allowed at the gate `passed`, the marker
names the rule instead: `purlin: <feature> RULE-<n>`. A rule that has proofs is
marked by one of them.

`purlin:` is read after any of `#`, `//`, `--`, `;`, `%` and `'`, and inside a
one-line `/* */` or `<!-- -->`. The comment is the whole line, leading
whitespace aside. A `purlin:` comment of any other shape ties nothing, and a
run says nothing of it: `purlin:build` finds and repairs it (see "Comments
that are nearly a marker" below).

A Python file's comments are read with Python's own tokenizer, so a
marker-shaped line inside a string is not a marker. A shell file's here
documents are stepped over for the same reason.

### Placement

- The marker belongs to the next test declared after it in its file.
- Blank lines, decorators, attributes and other comments may sit between the
  marker and the test.
- Every marker between the previous test's declaration and this one belongs to
  this one. A test may carry several markers, one line each, and its result
  counts for each.
- A marker with no test after it is tied to none, and is reported.
- In a file of an `exit` suite the file is the test, so every marker in it
  belongs to the file, wherever it sits. By convention the markers go at the
  top.

A test is declared by:

| Language | Declaration |
|----------|-------------|
| Python | a function whose name starts with `test`, at module level or in a class |
| JavaScript, TypeScript | an `it` or `test` call with a literal title, inside any number of `describe` calls; `it.each(table)(title, ...)` too |
| C# | a method carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]`, `[TestCaseSource]`, `[TestMethod]` or `[DataTestMethod]` |
| Go | `func TestX(t *testing.T)` |

## The `tests` setting

`.purlin/config.json` holds the project's suites under one key, `tests`, a
list with one entry per suite:

```json
"tests": [
  {"name": "pytest",
   "run": "python3 -m pytest {files} --junitxml={report}",
   "report": ".purlin/runtime/reports/pytest.xml",
   "format": "junit",
   "files": ["**/test_*.py", "**/*_test.py"]}
]
```

| Field | Type | What it holds |
|-------|------|---------------|
| `name` | string | the suite's name, printed as `Running the <name> suite.` |
| `run` | string | the project's own command. It runs through bash from the project root |
| `report` | string or null | where the report lands, relative to the project root; a folder is read file by file; `-` is the command's standard output; null for an `exit` suite |
| `format` | string | `junit`, `trx`, `gotest` or `exit` |
| `files` | list of strings | globs naming where this suite's test files live |

`run` takes two optional placeholders:

- `{report}` becomes the `report` path.
- `{files}` becomes the test files, each quoted, that carry a marker of a
  feature the run covers, on a run over some features; on a run over every
  feature it becomes nothing, and the suite runs whole. A suite with no
  `{files}` runs whole every time it runs. A run over some features starts no
  suite with none of their test files.

`files` decides which suite a marked file belongs to, and only a file one
suite's globs match is read for markers. `*` and `?` match within one path
segment and `**` matches any number of segments; a glob with no `/` matches
that file name in any directory. A file two suites match belongs to the
first.

An entry with no `run`, a `format` outside the four, or no `files` is left out,
and the run says so in one line. With no entry left, the run runs nothing and
suggests one (`references/supported_frameworks.md`). Purlin writes reports under
`.purlin/runtime/reports/`, which git ignores, and deletes a suite's report
before the suite runs, so a report from an earlier run is never read. An entry
that names no `report` gets `.purlin/runtime/reports/<name>.xml` for `junit`,
`.purlin/runtime/reports/<name>` for `trx` and
`.purlin/runtime/reports/<name>.json` for `gotest`.

## The four report formats

### `junit`

JUnit XML, as pytest's `--junitxml`, Vitest's `junit` reporter and Jest's
`jest-junit` write it. Purlin reads every `<testcase>` element, nested under
any number of `<testsuite>` elements:

| Read | From |
|------|------|
| the name | `name`; a title with ` > ` in it is `outer > inner > title` |
| the class | `classname`: a path, a dotted Python module and class, or the outer titles joined by ` > ` |
| the file | `file` on the `<testcase>`, else `file` or `filepath` on its `<testsuite>`, where the writer adds one |
| the outcome | a `<failure>` or `<error>` child fails it, a `<skipped>` child skips it, and otherwise it passed |

### `trx`

What `dotnet test --logger trx` writes. Purlin reads each `UnitTestResult`:

| Read | From |
|------|------|
| the outcome | `outcome`: `Passed` passes; `Failed`, `Error`, `Timeout` and `Aborted` fail; any other value is skipped |
| the class and method | the `TestMethod` of the `UnitTest` whose `id` is the result's `testId`: its `className` (a nested class after `+`) and its `name` |

### `gotest`

The JSON stream `go test -json` prints, one event per line, read from the
command's standard output when `report` is `-`. Purlin reads each event whose
`Test` is set and whose `Action` is `pass`, `fail` or `skip`, with its
`Package`. Every other event, and every line that is not JSON, is left alone.

### `exit`

No report. Each file `files` matches is one test: the command runs once per
file, with `{files}` that one file, and the file passes when the command exits
0. This is how shell and SQL scripts are tests.

## Tying a result to its marker, by name

For each case in the report:

1. **The file.** The case's file attribute where there is one. Otherwise its
   class name where that is a path. Otherwise the class or package name is
   resolved against the marked files of that suite: a dotted Python module
   against the files' paths, a C# class chain against the classes the files
   declare, narrowed by namespace, and a Go package against the directory of
   each file under the `module` line of its `go.mod`.
2. **The test.** The case's own name is found among the tests that file
   declares. A parametrised test's cases (`test_x[a]`, `TestX/a`,
   `Method(x: 1)`, the rows of an `it.each` table) all belong to the one test.
   A nested title is matched by its last part, then narrowed by the outer
   parts when two tests share it; a Python class and a C# class narrow the
   same way.
3. **The markers.** The markers tied to that test take the case's outcome.

A case that matches more than one test is counted for none of them, and the
run says so. A case whose test carries no marker is ignored: a test with no
marker runs as always.

A marker's result:

| Result | When |
|--------|------|
| `pass` | every case of its test passed |
| `fail` | any case of its test failed or errored |
| `not run` | every case was skipped, some were skipped and none failed, or the report holds no case for its test |

In the evidence a `pass` or `fail` is written as it is, and `not run` is
written as `missing`, except for a proof tagged `@env` for another operating
system, which is written as `not run`. The test is named as `<file>::<name>`: `Class::test_x`
for Python, `outer > inner > title` for JavaScript and TypeScript,
`Class.Method` for C#, `TestX` for Go, and the file's own name for a file of
an `exit` suite.

## What is reported

Purlin never guesses. Each of these is printed as one line, by file and line:

| Line | Counts as |
|------|-----------|
| `purlin: <feature> <id> at <file>:<line> is tied to no test` | `not run` |
| `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.` | nothing, and fails the run |
| `purlin: <feature> <id> at <file>:<line> names a rule that has proofs; name one of them` | nothing, and fails the run |
| `purlin: the report's <name> matches <n> tests in <file>, so its result is not counted` | `not run` for those tests |

The second line covers a feature no spec has, and a proof or a rule its feature's
spec does not have. A run with either of the two that fail it exits 1, whatever
its tests did.

A run also prints `Markers: <n> tied to a test, <k> not tied.`, and ends with
`Evidence is missing: ...` and exit code 1 when a suite left no report to
read, or when a marker of a feature it covers has no `pass` or `fail`.

## Comments that are nearly a marker

A test run does not look for them. `purlin:build` does, through

```
python3 scripts/mcp/purlin/markers.py --near-misses [--project-root DIR]
```

which reads every file one suite's `files` globs match, prints one JSON array and
exits 0; a wrong command line exits 2. Each entry is one comment:

| Field | What it holds |
|-------|---------------|
| `file` | the file, relative to the project root, `/` separated |
| `line` | the line number, from 1 |
| `text` | the comment as written, leading whitespace aside |
| `fix` | the marker it meant, or null where the comment cannot be read |
| `why` | one sentence saying what is wrong |

A comment is a near miss when `purlin` is misspelled by one letter or written in
capitals, when there is no space after the colon, when a `purlin:` comment names
no feature and PROOF or RULE id that can be read, or when its feature, or its
PROOF or RULE id, is one character from exactly one that exists. One character
from two or more is not a near miss: Purlin never guesses.
