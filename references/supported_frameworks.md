> Format-Version: 2

# Supported Test Frameworks

Proof plugins shipped with Purlin. `purlin:init` detects and scaffolds the appropriate plugin.

## Built-in Plugins

| Framework | Languages | Plugin file | Detection | Marker syntax |
|-----------|-----------|------------|-----------|---------------|
| **pytest** | Python | `scripts/proof/pytest_purlin.py` | `conftest.py` or `[tool.pytest]` in `pyproject.toml` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `package.json` contains `jest` | `[proof:feature:PROOF-1:RULE-1:unit]` in test title |
| **Vitest** | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `package.json` contains `vitest` | Same as Jest — Vitest supports Jest-compatible reporters |
| **Vitest (TS)** | TypeScript | `scripts/proof/vitest_purlin.ts` | `package.json` contains `vitest` + `tsconfig.json` exists | Same as Jest — TypeScript-native reporter |
| **C** | C | `scripts/proof/c_purlin.h` + `c_purlin_emit.py` | `Makefile` or `CMakeLists.txt` present | `purlin_proof("feature", "PROOF-1", "RULE-1", passed, name, file, tier)` |
| **PHP** | PHP | `scripts/proof/phpunit_purlin.php` | `composer.json` or `phpunit.xml` present | `/** @purlin feature PROOF-1 RULE-1 unit */` docblock |
| **SQL** | SQL (sqlite3) | `scripts/proof/sql_purlin.sh` | `.sql` test files in `tests/` | `-- @purlin feature PROOF-1 RULE-1 unit` comment |
| **Shell** | Bash | `scripts/proof/shell_purlin.sh` | Fallback when no other framework detected | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

## Detection

`purlin:init` detects ALL matching frameworks — not just the first match. A project can have multiple plugins (e.g., pytest for the server, Jest for the client):

| Check | Framework |
|-------|-----------|
| `conftest.py` at root OR `[tool.pytest]` in `pyproject.toml` | pytest |
| `package.json` contains `vitest` | Jest (Vitest-compatible) |
| `package.json` contains `jest` | Jest |
| `Makefile` or `CMakeLists.txt` at root | C |
| `composer.json` or `phpunit.xml` at root | PHP |
| `.sql` files in `tests/` directory | SQL |

All detected frameworks are scaffolded. If none are detected, the user is asked to choose or install a custom plugin.

The `test_framework` config field stores a comma-separated list when multiple are detected: `"pytest,jest"`.

## Adding More Frameworks

Community or custom plugins can be installed via:

```
purlin:init --add-plugin <path or git URL>
```

See the [Testing Workflow Guide](../docs/testing-workflow-guide.md#adding-support-for-another-framework) for details on writing custom plugins.
