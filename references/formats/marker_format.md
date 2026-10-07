> Format-Version: 6

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
and the proof is one of its `## Proof` lines. The feature is any name a spec
may hold, as [spec_format.md](spec_format.md), "Location", says: `sample-age`
is one. The marker names the proof only;
the spec already says which rule a proof serves.

Where a rule has no proof, the marker names the rule instead: `purlin: <feature> RULE-<n>`. A rule that has proofs is
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
| JavaScript, TypeScript | an `it` or `test` call whose title is one plain string, inside any number of `describe` calls; `it.each(table)(title, ...)` too |
| C# | a method carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]`, `[TestCaseSource]`, `[TestMethod]`, `[DataTestMethod]`, `[SkippableFact]` or `[SkippableTheory]` |
| Go | `func TestX(t *testing.T)` |

### The test of an AI proof

The test of a proof tagged `@ai` is marked like any other test. The run
starts it alone and sets three variables for it:

| Variable | What it holds |
|----------|---------------|
| `PURLIN_AI` | the full path of `scripts/ai/purlin_ai.py`, the helper the test starts |
| `PURLIN_AI_MODEL` | the model this start is for, one of the models the proof's tag names |
| `PURLIN_AI_OUT` | the full path of the folder this start writes its output to, emptied first |

The test reads `PURLIN_AI` to start the helper, and the helper reads the
other two. A test that makes the output its own way reads `PURLIN_AI_MODEL`
to know which model to ask. `references/formats/evidence_format.md`, "The
models of an AI proof", says what the run records of each start.

A test that also carries the marker of a proof that is not an AI proof is
started with the suites as well, with none of the three set, and what it
does there counts for that other proof alone.

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
| `name` | string | the suite's name, printed as `Running <name>: <the command as run>` |
| `run` | string | the project's own command. It runs through bash from the project root |
| `report` | string or null | where the report lands, relative to the project root; a folder is read file by file; `-` is the command's standard output; null for an `exit` suite |
| `format` | string | `junit`, `trx`, `gotest` or `exit` |
| `files` | list of strings | globs naming where this suite's test files live |

`run` takes two optional placeholders:

- `{report}` becomes the `report` path.
- `{files}` becomes the test files, each quoted, that carry the markers of
  the proofs the run selected.
  - Every run gets the test files of the features it runs, and starts no
    suite that holds none of them. A run over every feature gets every
    marked file.
  - Where the command with its files would pass 30,000 characters, the
    suite is started with no file list, and the run says so.
  - A `--ci` run selects the proofs tagged `@env` for its own system.
  - A suite with no `{files}` runs every test it holds each time it runs.

`files` decides which suite a marked file belongs to, and only a file one
suite's globs match is read for markers. `*` and `?` match within one path
segment and `**` matches any number of segments; a glob with no `/` matches
that file name in any directory. A file two suites match belongs to the
first. With no suite set, the comments in every tracked file of a language
Purlin reads tests in are read: Python, JavaScript, TypeScript, C# and Go.

An entry with no `run`, a `format` outside the four, or no `files` is left out,
and the run says so in one line. With no entry left, the run runs nothing and
suggests one for each test tool it recognises
(`references/supported_frameworks.md`). Purlin writes reports under
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
| a skip's reason | the `<skipped>` child's `message`, else its text |
| how long it took | `time`, in seconds; none where the case has no `time` |
| a failure's text | each `<failure>` and `<error>` child's `message` and then its text, in order, a blank line between two; a `message` the text already holds is left out |

### `trx`

What `dotnet test --logger trx` writes. Purlin reads each `UnitTestResult`:

| Read | From |
|------|------|
| the outcome | `outcome`: `Passed`, `Warning`, `Completed` and `PassedButRunAborted` pass; `Failed`, `Error`, `Timeout` and `Aborted` fail; any other value is skipped |
| the class and method | the `TestMethod` of the `UnitTest` whose `id` is the result's `testId`: its `className` (a nested class after `+`) and its `name` |
| a skip's reason | the result's `Output/ErrorInfo/Message`, else the last line of `Output/StdOut` |
| how long it took | `duration`, written `hh:mm:ss.fffffff`, read as seconds; none where the result has no `duration` |
| a failure's text | the result's `Output/ErrorInfo/Message`, then its `Output/ErrorInfo/StackTrace`, a blank line between them |

### `gotest`

The JSON stream `go test -json` prints, one event per line, read from the
command's standard output when `report` is `-`. Purlin reads each event whose
`Test` is set and whose `Action` is `pass`, `fail` or `skip`, with its
`Package`. A skipped test's reason is its last `output` event before the
`skip`, `go test`'s own `=== ` and `--- ` lines aside, with the leading
`<file>:<line>: ` cut: `t.Skip("nothing to check: no screens")` on line 12 of
`screens_test.go` gives `nothing to check: no screens`. Every other event, and
every line that is not JSON, is left alone.

How long a test took is the `Elapsed` of its `pass`, `fail` or `skip` event,
in seconds, none where the event has no `Elapsed`. A failed test's text is
every `output` event of the test, in order, `go test`'s own `=== ` and `--- `
lines aside.

### `exit`

No report. Each file `files` matches is one test: the command runs once per
file, with `{files}` that one file, and the file passes when the command exits
0. This is how shell and SQL scripts are tests. A file of an `exit` suite
gives no skip reason, no duration and no failure text: there is no report to
read them from.

### What is kept of a report

For each test the evidence keeps what the report holds for its cases, under
`reported`: each case's name, its outcome, how long it took and, where it
failed, stopped on an error or was skipped, the text above. The run also
keeps each report file it read, under the sha256 of its bytes, so a sign-off
can commit it with the evidence package.
`references/formats/evidence_format.md`, "What the report held", holds the
fields.

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
   A JavaScript or TypeScript title is read as the string it makes: `\'`
   and `\"` are the quote, pieces joined with `+` are one title, and white
   space at either end is cut.
   A nested title is matched by its last part, then narrowed by the outer
   parts when two tests share it; a Python class and a C# class narrow the
   same way.
3. **The markers.** The markers tied to that test take the case's outcome.

A test whose title is not one plain string, a template holding `${}` or a
variable, can be matched to no case. A marker above it is not tied, and the
run prints `<file>:<line>: test title not read. It is not one plain string.
Write it as one string.`

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
written as `missing`. A proof tagged `@env` for another operating system is
written as `not run` whatever its test did. The test is named as `<file>::<name>`: `Class::test_x`
for Python, `outer > inner > title` for JavaScript and TypeScript,
`Class.Method` for C#, `TestX` for Go, and the file's own name for a file of
an `exit` suite.

### Nothing to check

A test skipped through its tool's own skip, with a reason starting exactly
`nothing to check:`, says the project holds nothing for its proof to check:

```python
# purlin: security_baseline PROOF-3
def test_every_screen_escapes_its_input():
    screens = find_screens()
    if not screens:
        pytest.skip('nothing to check: this project has no screens')
```

A proof whose every tied test skipped so reads `nothing to check` in the
evidence, with the text after `nothing to check: ` as its reason. On an
anchor's rule it counts as passed and the reason is shown; on any other
spec's rule it counts as not run, the reason kept. A test skipped for any
other reason reads `missing`.

## What is reported

Purlin never guesses. Each of these is printed as one line, by file and line:

| Line | Counts as |
|------|-----------|
| `<feature> <ID>: test comment with no test. No test follows <file>:<line>. Run purlin:build.` | `not run` |
| `<feature> <ID>: test comment to correct. <file>:<line> names it, and no spec has it. Run purlin:build.` | nothing, and fails the run |
| `<feature> <RULE-N>: test comment to correct. <file>:<line> names the rule, and a comment names one of its proofs. Run purlin:build.` | nothing, and fails the run |
| `<case>: test name not unique. It matches <n> tests in <files>. Give the tests different names, then run purlin:test.` | `not run` for those tests |

The second line covers a feature no spec has, and a proof or a rule its feature's
spec does not have. A run with either of the two that fail it exits 1, whatever
its tests did.

A run also prints `Markers: <n> tied to a test, <k> not tied.`, and ends with
a line of the kind `evidence missing` and exit code 1 when a suite left no
report to read, or when a marker of a feature it covers has no `pass` or `fail`.

## Comments that are nearly a marker

A test run does not look for them. `purlin:build` does, through

```
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses [--project-root DIR]
```

which reads every file one suite's `files` globs match, prints one JSON array and
exits 0; a wrong command line exits 2. Each entry is one comment:

| Field | What it holds |
|-------|---------------|
| `file` | the file, relative to the project root, `/` separated |
| `line` | the line number, from 1 |
| `text` | the comment as written, leading whitespace aside |
| `fix` | the marker it meant, or null where the comment cannot be read or its feature holds a character no spec's name may hold |
| `why` | one sentence saying what is wrong |

A comment is a near miss when `purlin` is misspelled by one letter or written in
capitals, when there is no space after the colon, when a `purlin:` comment names
no feature and PROOF or RULE id that can be read, or when its feature, or its
PROOF or RULE id, is one character from exactly one that exists. A suggestion
names only an id a comment may name: a proof, or a rule that has no proof. A
comment one character from a rule with exactly one proof is offered that
proof, and its `why` says both steps: for `RULE-30`, where `login`'s `RULE-3`
has the one proof `PROOF-3`, it reads
`` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3`. ``
One character from a rule with two or more proofs, or from two or more ids
that exist, is not a near miss: Purlin never guesses.

A comment whose feature holds a character no spec's name may hold has no fix,
and its `why` names the characters a name holds: for
`# purlin: sample.age PROOF-1` it reads
`` `sample.age` holds a character a spec's name cannot: a name holds letters, digits, `_` and `-`. ``
