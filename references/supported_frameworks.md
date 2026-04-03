> Format-Version: 1

# Supported Test Frameworks

Proof plugins shipped with Purlin. `purlin:init` detects and scaffolds the appropriate plugin.

## Built-in Plugins

| Framework | Languages | Plugin file | Detection | Marker syntax |
|-----------|-----------|------------|-----------|---------------|
| **pytest** | Python | `scripts/proof/pytest_purlin.py` | `conftest.py` or `[tool.pytest]` in `pyproject.toml` | `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` |
| **Jest** | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `package.json` contains `jest` | `[proof:feature:PROOF-1:RULE-1:default]` in test title |
| **Vitest** | JavaScript, TypeScript | `scripts/proof/jest_purlin.js` | `package.json` contains `vitest` | Same as Jest — Vitest supports Jest-compatible reporters |
| **Shell** | Bash | `scripts/proof/shell_purlin.sh` | Fallback when no other framework detected | `purlin_proof "feature" "PROOF-1" "RULE-1" pass "desc"` |

## Detection Order

`purlin:init` detects frameworks in this order (first match wins):

1. `conftest.py` at project root OR `[tool.pytest]` in `pyproject.toml` → **pytest**
2. `package.json` contains `vitest` → **Jest** (Vitest-compatible)
3. `package.json` contains `jest` → **Jest**
4. No match → **Shell** (fallback)

## Adding More Frameworks

Community or custom plugins can be installed via:

```
purlin:init --add-plugin <path or git URL>
```

See the [Testing Workflow Guide](../docs/testing-workflow-guide.md#adding-support-for-another-framework) for details on writing custom plugins.
