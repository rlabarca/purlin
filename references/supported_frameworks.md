> Format-Version: 8

# Supported Test Frameworks

Six proof plugins ship with Purlin, across five languages. `purlin:init` detects a project's
frameworks and scaffolds the plugins that match.

## Built-in Plugins

| Framework | Display name | Languages | Plugin file | Installed as | Detection | Marker syntax | Runner setup |
|-----------|-------------|-----------|------------|--------------|-----------|---------------|--------------|
| **pytest** | pytest (Python) | Python | `scripts/proof/pytest_purlin.py` | `pytest_purlin.py` | `conftest.py` at the root, or `[tool.pytest` in `pyproject.toml` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")`; the marker's tier is also added as a registered pytest marker, so `-m "not integration and not e2e"` selects the unit tier | `pip install pytest` |
| **Vitest** | vitest (JS/TS) | JavaScript, TypeScript | `scripts/proof/vitest_purlin.ts` | `vitest_purlin.ts` | `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file beside it | `[proof:feature:PROOF-1:RULE-1:unit]` in the test title (a native TypeScript reporter: Vitest loads `.ts` reporters through Vite, so it covers JavaScript and TypeScript projects alike) | `npm ci` |
| **Jest** | jest (JS/TS) | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `jest_purlin.js` | `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file beside it | `[proof:feature:PROOF-1:RULE-1:unit]` in the test title | `npm ci` |
| **xUnit** | xunit (.NET) | C# | `scripts/proof/xunit_purlin.cs` | `xunit_purlin.cs` | any `*.csproj` referencing the `xunit` package | `[Trait("PurlinProof", "feature:PROOF-1:RULE-1:unit")]` test trait | `dotnet restore` |
| **SQL** | sql (sqlite3) | SQL | `scripts/proof/sql_purlin.sh` | `sql_purlin.sh` | a `test_*.sql`, `*_test.sql` or `*.test.sql` file in `tests/` | `-- @purlin feature PROOF-1 RULE-1 unit` comment | the engine named by `sql_engine` in `.purlin/config.json`, `sqlite3` by default, plus `python3` |
| **Shell** | shell (Bash) | Bash | `scripts/proof/shell_purlin.sh` | `purlin-proof.sh` | none: shell is the fallback when nothing else is detected, and is otherwise selected by hand | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` | nothing beyond `python3` |

The **Installed as** column is the basename each plugin file takes inside a project's
`.purlin/plugins/`. It is the same name for every framework but shell, which a project installs
as `purlin-proof.sh` because that is the name every shell test sources. `purlin:init` reads this
column when it copies a plugin, and `purlin:init --update` reads it backwards to find the source
of a copy it has to refresh, so neither script holds the fact and the two cannot disagree about
the name a project's file has.

The **Runner setup** column is what the workflow `purlin:init` writes reads: it becomes the
per-framework install step of the job that runs `purlin:verify --ci`. Every listed framework
carries a cell, because a framework with no recorded setup is one a scaffolded workflow cannot
run.

Two languages were dropped in 0.10.0: C and PHP. Their plugins, their detection entries and
their marker syntax are gone, and a project that used one keeps its proofs only by writing a
custom plugin. `purlin:init` also offers an **other** option in its selection list; when the user
selects it, direct them to `purlin:init --add-plugin` to install a custom proof plugin.

## Detection

`purlin:init` detects ALL matching frameworks, not just the first match. A project can have
several plugins (pytest for the server, Vitest for the client):

| Check | Framework |
|-------|-----------|
| `conftest.py` at the root, or `[tool.pytest` in `pyproject.toml` | pytest |
| `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file | Vitest |
| `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file | Jest |
| any `*.csproj` referencing the `xunit` package | xUnit |
| a `test_*.sql`, `*_test.sql` or `*.test.sql` file in `tests/` | SQL |

Detection descends the tree, skipping dot directories and `node_modules`: a vendored package's
own fixtures are not this project's frameworks. Shell has no heuristic, so it is the fallback
that keeps a runner always present: a project where nothing else matches resolves to shell rather
than to nothing.

All detected frameworks are scaffolded. The `test_framework` config field records the answer the
user gave, not the detection result: `auto` when detection chose the frameworks, or the
comma-separated list the user named (`"pytest,vitest"`). `auto` is written verbatim, so every run
resolves the frameworks from what is on disk. A name outside the six is reported rather than run:
a typo must not silently run nothing.

## Where each framework runs

`scripts/run/purlin_run.py` has one arm per framework, and that is the only place a project's
suite is invoked:

| Framework | Arm |
|-----------|-----|
| pytest | `python3 -m pytest -q`, with `-m "not integration and not e2e"` at `--tier unit`; an exit code of 5 (nothing collected) is not a failure |
| jest | `npx jest --passWithNoTests`, with `--testPathPattern=unit` at `--tier unit` |
| vitest | `npx vitest run --passWithNoTests` |
| xunit | `dotnet test --logger purlin` |
| shell | `bash <name>` for each `*.test.sh` at the project root, stopping at the first failure |
| sql | `bash sql_purlin.sh tests/<name>.sql` for each `.sql` file in `tests/`, against `sql_engine` |

## End-to-end (browser) proofs

No dedicated e2e proof reporter ships with Purlin. `@e2e` proof descriptions are tool-agnostic by
design: they describe observable flows (arrange, act, observe; see `spec_quality_guide.md`, "E2E
proof descriptions"), so any runner that can execute the flow qualifies: Playwright, Cypress, an
agent-driven browser, or a screenshot compared by eye. The description never references a
specific runner's API.

`@e2e` proofs emit through the existing plugins:

- **Through Vitest or Jest:** drive the browser from a test (Playwright's library API inside a
  test body, for example) and put the standard marker in the test title with the `e2e` tier:
  `[proof:feature:PROOF-1:RULE-1:e2e]`.
- **Through shell:** wrap any e2e runner's invocation in a shell test that calls
  `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` based on the runner's exit status, with
  `PURLIN_PROOF_TIER=e2e` set.

A test that captures a screenshot writes it to
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png`; `purlin:verify` hashes it into the record
and CI keeps it as an artifact.

A project whose specs carry `@e2e` proofs but has no e2e-capable runner installed cannot record
those proofs: `purlin:spec-from-code` warns when it detects this.

## Adding more frameworks

Community or custom plugins can be installed with:

```
purlin:init --add-plugin <path or git URL>
```

What a plugin has to do, and every file a new framework has to be named in before a project can
select it and a run can execute it, is the checklist in
[`proof_plugin_contract.md`](proof_plugin_contract.md). The tables above are one step of its
wiring list, so a framework added here and nowhere else is half wired. A worked sample is in the
[Testing Workflow Guide](../docs/testing-workflow-guide.md#proof-plugins).
