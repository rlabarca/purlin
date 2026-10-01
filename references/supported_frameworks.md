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
suggested setting under `tests` and runs again. Where the run detects none, it prints:

```
No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.
```

and `purlin:test` reads the project and proposes an entry instead.

On Windows the pytest entry's command starts `py -3 -m pytest` in place of
`python3 -m pytest`, and the rest of it is the same.

## What the first run detects, and what it needs

| Framework | Detected by | Needs added |
|-----------|-------------|-------------|
| pytest | `conftest.py` or `pytest.ini` at the root, `[tool.pytest` in `pyproject.toml`, or a file named `test_*.py` under `tests/` | nothing; `--junitxml` is pytest's own |
| vitest | `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file | nothing; the `junit` reporter is Vitest's own |
| jest | `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file | the package `jest-junit`: `yarn add --dev jest-junit` where the root holds `yarn.lock`, `pnpm add --save-dev jest-junit` where it holds `pnpm-lock.yaml`, and `npm install --save-dev jest-junit` otherwise |
| dotnet | a `*.csproj` referencing xUnit, NUnit, MSTest or the test SDK | nothing; the `trx` logger ships with `dotnet test` |
| go | `go.mod` at the root and a `*_test.go` file | nothing; `-json` is `go test`'s own |
| sql | a `test_*.sql`, `*_test.sql` or `*.test.sql` file | the `sqlite3` command; a test fails by raising an error, and another engine is a change to `run` |
| shell | a `*.test.sh` file | nothing |

Detection descends the tree, skipping dot directories, `node_modules`, `bin` and `obj`. It also
skips every folder named `fixtures`, `fixture`, `samples`, `sample`, `testdata`, `test_data` or
`test-data`, at any depth. A project kept there to test against is not a tool this project
uses, so the first test run names only the project's own. A project that carries several
frameworks is suggested an entry for each, one suite per entry under `tests`.

## The entry suggested

Each entry is written under `tests` in `.purlin/config.json`. `{report}` is where Purlin wants
the report, and `{files}` is replaced by the test files of the features a run covers, or by
nothing when it runs them all. In the jest entry `{files}` comes before `--reporters`, because
jest reads every word after that option as another reporter.

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
  "run": "JEST_JUNIT_OUTPUT_FILE={report} JEST_JUNIT_ADD_FILE_ATTRIBUTE=true JEST_JUNIT_CLASSNAME='{classname}' JEST_JUNIT_TITLE='{title}' JEST_JUNIT_ANCESTOR_SEPARATOR=' > ' npx jest --ci {files} --reporters=default --reporters=jest-junit",
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

## Leaving a slow test out

`purlin:test` without `--all` never starts the test of a proof tagged `@slow`. Nothing is added
to the test or to your suite: Purlin adds the tool's own option to the command in the `tests`
setting, after the files it names, or at its end where it names none.

| Framework | How the test is left out |
|-----------|--------------------------|
| pytest | `--deselect <file>::<test>`, one per slow test |
| vitest, jest | `--testNamePattern`, with a pattern every title but the slow tests' matches. Both match a title in every file, so a slow test that shares its full title with a test that is not slow is started |
| dotnet | `--filter`, with `FullyQualifiedName!=<namespace>.<class>.<method>` for each slow test, joined by `&`. A test whose name carries its arguments, as NUnit's `TestCase` does, is not matched: it runs, and its result counts |
| go | `-skip`, with the slow tests' names; needs Go 1.20. It matches a name in every package, so a slow test that shares its name with a test that is not slow in another package is started |
| sql, shell, any `exit` suite | the file is the test, and a slow file is not run |

In four cases a slow test is started all the same:

- the suite's command is none of these tools';
- the command already carries that option;
- the command names no `{files}` and pipes, chains or redirects;
- the slow test shares its title or name with another test, as the table says.

The run says so in one line, as in
`Started 1 slow test in the e2e suite: its command gives Purlin no way to leave one test out.`
Its result counts like any other.

A test left out by vitest or jest is in their report as skipped. A test with the same title in
a file that carries no test comment is left out with it.

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
