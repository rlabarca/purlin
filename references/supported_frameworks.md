# Supported test frameworks

Purlin runs your project's own test command and reads the report it writes. Nothing of
Purlin is installed in your test suite: a test is tied to a proof by one comment above it,
`purlin: <feature> PROOF-<n>`. `references/formats/marker_format.md` is the contract: the
marker, the `tests` setting, the four report formats and how a result is tied to its marker.

`purlin:init` detects every framework below that the project uses and writes one entry of
the `tests` setting for each, with the flag that writes the report already in the command.
It says in one line what a framework needs added before it can write that report. Where it
detects none, it asks for the command that runs the tests and where the report lands.

## What init detects, and what it needs

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
`mutants/`. A project can carry several frameworks, and gets one suite for each.

## The entry init writes

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
narrower globs. `purlin:init` keeps a `tests` setting a project already carries, and `--add
<framework>` appends one more entry.

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
