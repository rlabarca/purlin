> Format-Version: 5

# Supported Test Frameworks

Proof plugins shipped with Purlin. `purlin:init` detects and scaffolds the appropriate plugin.

## Built-in Plugins

| Framework | Display name | Languages | Plugin file | Detection | Marker syntax |
|-----------|-------------|-----------|------------|-----------|---------------|
| **pytest** | pytest (Python) | Python | `scripts/proof/pytest_purlin.py` | `conftest.py` or `[tool.pytest]` in `pyproject.toml` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | jest (JS/TS) | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `package.json` contains `jest` | `[proof:feature:PROOF-1:RULE-1:unit]` in test title |
| **Vitest** | vitest (JS/TS) | JavaScript, TypeScript | `scripts/proof/vitest_purlin.ts` | `package.json` contains `vitest` | `[proof:feature:PROOF-1:RULE-1:unit]` in test title (native TS reporter — Vitest loads `.ts` reporters via Vite, so it covers both JS and TS projects) |
| **C** | c (C/gcc) | C | `scripts/proof/c_purlin.h` + `scripts/proof/c_purlin_emit.py` | `Makefile` or `CMakeLists.txt` present | `purlin_proof("feature", "PROOF-1", "RULE-1", passed, name, file, tier)` |
| **PHP** | php (PHP) | PHP | `scripts/proof/phpunit_purlin.php` | `composer.json` or `phpunit.xml` present | `/** @purlin feature PROOF-1 RULE-1 unit */` docblock |
| **SQL** | sql (sqlite3) | SQL (sqlite3) | `scripts/proof/sql_purlin.sh` | `.sql` test files in `tests/` | `-- @purlin feature PROOF-1 RULE-1 unit` comment |
| **Shell** | shell (Bash) | Bash | `scripts/proof/shell_purlin.sh` | No auto-detection — user must select | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

`purlin:init` also offers an **other** option in the selection list. When the user selects "other", direct them to `purlin:init --add-plugin` to install a custom proof plugin.

## Additional Plugins (manual setup)

Shipped plugins that `purlin:init` does not yet auto-detect or scaffold — wire them in by hand (see the framework's section in [`formats/proofs_format.md`](formats/proofs_format.md)).

| Framework | Display name | Languages | Plugin file | Detection | Marker syntax | Spec |
|-----------|-------------|-----------|------------|-----------|---------------|------|
| **xUnit** | xunit (.NET) | C#, F#, VB.NET | `scripts/proof/xunit_purlin.cs` | `*.csproj` or `*.sln` present | `[Trait("PurlinProof", "feature:PROOF-1:RULE-1:unit")]` test trait | `specs/proof/proof_plugins_xunit.md` |

> **Vitest version support:** the Vitest reporter (`vitest_purlin.ts`) collects proofs in the `onFinished(files)` hook, whose shape is stable across Vitest 2.x → 4.x (tested on 2.x and 3.x). Earlier `onTaskUpdate`-based collection broke silently on Vitest 2+ and is no longer used. Note that `jest_purlin.js` is **not** a drop-in for Vitest — Vitest does not call Jest's `onTestResult`/`onRunComplete` hooks, so Vitest projects use `vitest_purlin.ts`.

## Detection

`purlin:init` detects ALL matching frameworks — not just the first match. A project can have multiple plugins (e.g., pytest for the server, Jest for the client):

| Check | Framework |
|-------|-----------|
| `conftest.py` at root OR `[tool.pytest]` in `pyproject.toml` | pytest |
| `package.json` contains `vitest` | Vitest (`vitest_purlin.ts`) |
| `package.json` contains `jest` | Jest |
| `Makefile` or `CMakeLists.txt` at root | C |
| `composer.json` or `phpunit.xml` at root | PHP |
| `.sql` files in `tests/` directory | SQL |

All detected frameworks are scaffolded. Shell has no auto-detection heuristic — the user must explicitly select it. If no framework is detected, the full selection list is shown with nothing pre-selected.

The `test_framework` config field stores a comma-separated list when multiple are detected: `"pytest,jest"`.

## Adding More Frameworks

Community or custom plugins can be installed via:

```
purlin:init --add-plugin <path or git URL>
```

See the [Testing Workflow Guide](../docs/testing-workflow-guide.md#adding-support-for-another-framework) for details on writing custom plugins.
