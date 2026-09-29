# Supported test frameworks

Purlin runs your project's own test command and reads the report it writes. A test is tied
to a proof by one comment above it, `purlin: <feature> PROOF-<n>`. `references/formats/marker_format.md` is the contract: the
marker, the `tests` setting, the four report formats and how a result is tied to its marker.

A new project's `tests` setting is empty. Its first test run detects the frameworks below,
runs nothing, and suggests an entry for every one it finds, in the order they are listed, with
the flag that writes the report already in each command:

```
No test command is set in .purlin/config.json, so nothing ran.
Suggested for pytest: python3 -m pytest --ignore=mutants {files} --junitxml={report}
Suggested for vitest: npx vitest run --reporter=default --reporter=junit --outputFile.junit={report} {files}
Suggested tests setting: [{"name": "pytest", ...}, {"name": "vitest", ...}]
```

A framework that needs something added before it can write that report gets one more line,
right after its own, saying what. `purlin:test` shows you each command, asks once, writes the
suggested setting under `tests` and runs again. Where the run detects none, `purlin:test`
reads the project and proposes an entry instead.

On Windows the pytest entry's command starts `py -3 -m pytest` in place of
`python3 -m pytest`, and the rest of it is the same.

## What the first run detects, and what it needs

| Framework | Detected by | Needs added |
|-----------|-------------|-------------|
| pytest | `conftest.py` or `pytest.ini` at the root, or `[tool.pytest` in `pyproject.toml` | nothing; `--junitxml` is pytest's own |
| vitest | `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file | nothing; the `junit` reporter is Vitest's own |
| jest | `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file | the package `jest-junit`: `npm install --save-dev jest-junit` |
| dotnet | a `*.csproj` referencing xUnit, NUnit, MSTest or the test SDK | nothing; the `trx` logger ships with `dotnet test` |
| go | `go.mod` at the root and a `*_test.go` file | nothing; `-json` is `go test`'s own |
| sql | a `test_*.sql`, `*_test.sql` or `*.test.sql` file | the `sqlite3` command; a test fails by raising an error, and another engine is a change to `run` |
| shell | a `*.test.sh` file | nothing |

Detection descends the tree, skipping dot directories, `node_modules`, `bin`, `obj` and
`mutants/`. A project that carries several frameworks is suggested an entry for each, one
suite per entry under `tests`.

## The entry suggested

Each entry is written under `tests` in `.purlin/config.json`. `{report}` is where Purlin wants
the report, and `{files}` is replaced by the test files of the features a run covers, or by
nothing when it runs them all.

### pytest

```json
{
  "name": "pytest",
  "run": "python3 -m pytest --ignore=mutants {files} --junitxml={report}",
  "report": ".purlin/runtime/reports/pytest.xml",
  "format": "junit",
  "files": [
    "**/test_*.py",
    "**/*_test.py"
  ]
}
```

### vitest

```json
{
  "name": "vitest",
  "run": "npx vitest run --reporter=default --reporter=junit --outputFile.junit={report} {files}",
  "report": ".purlin/runtime/reports/vitest.xml",
  "format": "junit",
  "files": [
    "**/*.test.js",
    "**/*.test.jsx",
    "**/*.test.mjs",
    "**/*.test.cjs",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.spec.js",
    "**/*.spec.jsx",
    "**/*.spec.mjs",
    "**/*.spec.cjs",
    "**/*.spec.ts",
    "**/*.spec.tsx"
  ]
}
```

### jest

```json
{
  "name": "jest",
  "run": "JEST_JUNIT_OUTPUT_FILE={report} JEST_JUNIT_ADD_FILE_ATTRIBUTE=true JEST_JUNIT_CLASSNAME='{classname}' JEST_JUNIT_TITLE='{title}' JEST_JUNIT_ANCESTOR_SEPARATOR=' > ' npx jest --ci --reporters=default --reporters=jest-junit {files}",
  "report": ".purlin/runtime/reports/jest.xml",
  "format": "junit",
  "files": [
    "**/*.test.js",
    "**/*.test.jsx",
    "**/*.test.mjs",
    "**/*.test.cjs",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.spec.js",
    "**/*.spec.jsx",
    "**/*.spec.mjs",
    "**/*.spec.cjs",
    "**/*.spec.ts",
    "**/*.spec.tsx"
  ]
}
```

### dotnet

```json
{
  "name": "dotnet",
  "run": "dotnet test --logger trx --results-directory {report}",
  "report": ".purlin/runtime/reports/dotnet",
  "format": "trx",
  "files": [
    "**/*.cs"
  ]
}
```

### go

```json
{
  "name": "go",
  "run": "go test -json ./...",
  "report": "-",
  "format": "gotest",
  "files": [
    "**/*_test.go"
  ]
}
```

A subtest's result counts for the test that declares it, so `TestParse/empty` failing fails
`TestParse`. A test that panics reads `fail`, and a test in the same package that the panic
stopped before it started has no result and reads `not run`. This reading is checked against
the stream `go test -json` prints on Go 1.27.1.

### sql

```json
{
  "name": "sql",
  "run": "sqlite3 -bail :memory: < {files}",
  "report": null,
  "format": "exit",
  "files": [
    "**/test_*.sql",
    "**/*_test.sql",
    "**/*.test.sql"
  ]
}
```

### shell

```json
{
  "name": "shell",
  "run": "bash {files}",
  "report": null,
  "format": "exit",
  "files": [
    "**/*.test.sh"
  ]
}
```

An entry is yours to change once it is written: a different command, another report path,
narrower globs.

## Any other framework

Any test runner that writes JUnit XML, the TRX `dotnet test` writes or the JSON stream
`go test -json` writes is read the same way: write its entry by hand, with its own command,
its report and its format. A runner that writes none of the three can still be used with
the format `exit`, where each test file is one test and passes when the command exits 0.

## Browser tests

A proof that drives a browser describes an observable flow (see `spec_quality_guide.md`,
"Flow proofs"), so any runner that can execute the flow and write one of the four report
formats serves: Playwright, Cypress, or a browser driven from a pytest, Jest or Vitest test.
The marker goes above that test like any other.
