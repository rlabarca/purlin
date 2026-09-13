> Format-Version: 7

# Supported Test Frameworks

Proof plugins shipped with Purlin. `purlin:init` detects and scaffolds the appropriate plugin.

## Built-in Plugins

| Framework | Display name | Languages | Plugin file | Installed as | Detection | Marker syntax | Runner setup |
|-----------|-------------|-----------|------------|--------------|-----------|---------------|--------------|
| **pytest** | pytest (Python) | Python | `scripts/proof/pytest_purlin.py` | `pytest_purlin.py` | `conftest.py` or `[tool.pytest]` in `pyproject.toml` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")`; the marker's tier is also added as a registered pytest marker, so `-m "not integration and not e2e"` selects the unit tier | `pip install pytest` |
| **Jest** | jest (JS/TS) | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `jest_purlin.js` | `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file | `[proof:feature:PROOF-1:RULE-1:unit]` in test title | `npm ci` |
| **Vitest** | vitest (JS/TS) | JavaScript, TypeScript | `scripts/proof/vitest_purlin.ts` | `vitest_purlin.ts` | `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file | `[proof:feature:PROOF-1:RULE-1:unit]` in test title (native TS reporter: Vitest loads `.ts` reporters via Vite, so it covers both JS and TS projects) | `npm ci` |
| **C** | c (C/gcc) | C | `scripts/proof/c_purlin.h` + `scripts/proof/c_purlin_emit.py` | `c_purlin.h`, `c_purlin_emit.py` | `Makefile` or `CMakeLists.txt` present AND at least one `*.c` file | `purlin_proof("feature", "PROOF-1", "RULE-1", passed, name, file, tier)` | the platform's C toolchain (`gcc` from the image's package manager on linux, Xcode command line tools on macos, MSVC build tools on windows) |
| **PHP** | php (PHP) | PHP | `scripts/proof/phpunit_purlin.php` | `phpunit_purlin.php` | `composer.json` or `phpunit.xml` present | `/** @purlin feature PROOF-1 RULE-1 unit */` docblock | `composer install` |
| **SQL** | sql (sqlite3) | SQL (sqlite3) | `scripts/proof/sql_purlin.sh` | `sql_purlin.sh` | a `test_*.sql`, `*_test.sql` or `*.test.sql` file in `tests/` | `-- @purlin feature PROOF-1 RULE-1 unit` comment | nothing beyond `python3` (`actions/setup-python` puts it on PATH on all three runner OSes) |
| **Shell** | shell (Bash) | Bash | `scripts/proof/shell_purlin.sh` | `purlin-proof.sh` | No auto-detection: user must select | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` | nothing beyond `python3` (`actions/setup-python` puts it on PATH on all three runner OSes) |

The **Installed as** column is the basename each plugin file takes inside a project's
`.purlin/plugins/`. It is the same name for every framework but shell, which a project installs
as `purlin-proof.sh` because that is the name every shell test sources. `purlin:init` reads this
column when it copies a plugin, and `purlin:init --update` reads it backwards to find the source
of a copy it has to refresh, so neither script holds the fact and the two cannot disagree about
the name a project's file has.

The **Runner setup** column is what `purlin:test` reads when it scaffolds a platform runner
workflow: it becomes the per-framework install step of the template in
[`remote_verification.md`](remote_verification.md). Every listed framework carries a cell,
because a framework with no recorded setup is one a scaffolded workflow cannot run.

`purlin:init` also offers an **other** option in the selection list. When the user selects "other", direct them to `purlin:init --add-plugin` to install a custom proof plugin.

## Additional Plugins (manual setup)

Shipped plugins that `purlin:init` does not yet auto-detect or scaffold: wire them in by hand (see the framework's section in [`formats/proofs_format.md`](formats/proofs_format.md)).

| Framework | Display name | Languages | Plugin file | Installed as | Detection | Marker syntax | Runner setup |
|-----------|-------------|-----------|------------|--------------|-----------|---------------|--------------|
| **xUnit** | xunit (.NET) | C#, F#, VB.NET | `scripts/proof/xunit_purlin.cs` | `xunit_purlin.cs` | `*.csproj` or `*.sln` present | `[Trait("PurlinProof", "feature:PROOF-1:RULE-1:unit")]` test trait | `dotnet restore` |

> **Deterministic Pass-1 coverage:** every framework in both tables above has a Pass-1 static checker in `scripts/audit/static_checks.py`. It reads the same markers the plugin reads, locates each marked test's body, and runs assert-true / no-assertion detection: Python, JavaScript/TypeScript (`.js` `.jsx` `.mjs` `.cjs` `.ts` `.tsx`), Shell, C# (`.cs`), PHP (`.php`), SQL (`.sql`) and C (`.c` `.h`). The per-language checks are listed in [`audit_criteria.md`](audit_criteria.md), Pass 1. This is independent of the runtime proof plugin, which still records pass/fail during the actual test run. A custom plugin for a language not listed here has no checker, so its proofs are simply not measured by Pass 1.

> **Vitest version support:** the Vitest reporter (`vitest_purlin.ts`) collects proofs in the `onFinished(files)` hook, whose shape is stable across Vitest 2.x → 4.x (tested on 2.x and 3.x). Earlier `onTaskUpdate`-based collection broke silently on Vitest 2+ and is no longer used. Note that `jest_purlin.js` is **not** a drop-in for Vitest: Vitest does not call Jest's `onTestResult`/`onRunComplete` hooks, so Vitest projects use `vitest_purlin.ts`.

## End-to-end (browser) proofs

No dedicated e2e proof reporter ships with Purlin yet. `@e2e` proof descriptions are **tool-agnostic by design**: they describe observable flows (arrange → act → observe; see `spec_quality_guide.md`, "E2E proof descriptions"), so any runner that can execute the flow qualifies: Playwright, Cypress, an MCP-driven browser (e.g. Claude in Chrome), or screenshot + vision. The description never references a specific runner's API.

Until a dedicated reporter exists, `@e2e` proofs emit through the existing plugins:

- **Via Vitest or Jest:** drive the browser from a Vitest/Jest test (e.g. Playwright's library API inside a test body) and put the standard marker in the test title with the `e2e` tier: `[proof:feature:PROOF-1:RULE-1:e2e]`. The `vitest_purlin.ts` / `jest_purlin.js` reporter emits the proof JSON as usual.
- **Via shell:** wrap any e2e runner's invocation in a shell test that calls `purlin_proof "feature" "PROOF-1" "RULE-1" pass/fail "desc" "e2e"` based on the runner's exit status (see `shell_purlin.sh`).

A project whose specs carry `@e2e` proofs but has no e2e-capable runner installed cannot record those proofs: `purlin:spec-from-code` warns when it detects this.

## Detection

`purlin:init` detects ALL matching frameworks: not just the first match. A project can have multiple plugins (e.g., pytest for the server, Jest for the client):

| Check | Framework |
|-------|-----------|
| `conftest.py` at root OR `[tool.pytest]` in `pyproject.toml` | pytest |
| `vitest` under `dependencies` or `devDependencies` in `package.json`, or a `vitest.config.*` file | Vitest (`vitest_purlin.ts`) |
| `jest` under `dependencies` or `devDependencies` in `package.json`, or a `jest.config.*` file | Jest |
| `Makefile` or `CMakeLists.txt` AND at least one `*.c` file | C |
| `composer.json` or `phpunit.xml` at root | PHP |
| a `test_*.sql`, `*_test.sql` or `*.test.sql` file in `tests/` | SQL |

All detected frameworks are scaffolded. Shell has no auto-detection heuristic: the user must explicitly select it. If no framework is detected, the full selection list is shown with nothing pre-selected.

The `test_framework` config field records the answer the user gave, not the detection result: `auto` when detection chose the frameworks, or the comma-separated list the user named (`"pytest,jest"`). `auto` is written verbatim so the hook resolves the frameworks from what is on disk on every run.

## Adding More Frameworks

Community or custom plugins can be installed via:

```
purlin:init --add-plugin <path or git URL>
```

What a plugin has to do, and every file a new framework has to be named in before a project can
select it, a hook can run it and the quality gate can grade it, is the checklist in
[`proof_plugin_contract.md`](proof_plugin_contract.md). The tables above are step 2 of its
wiring list, so a framework added here and nowhere else is half wired. A worked sample is in the
[Testing Workflow Guide](../docs/testing-workflow-guide.md#proof-plugins).
