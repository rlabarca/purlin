---
name: init
description: Initialize a project for Purlin
---

Set up a project for spec-driven development. Creates `.purlin/`, `specs/`, detects the test framework, and scaffolds the proof plugin.

## Usage

```
purlin:init                     Initialize a new project
purlin:init --force             Re-initialize (preserves existing config)
```

## Step 1 — Pre-flight

- If `.purlin/` exists and `--force` is not set: "Project already initialized. Use `--force` to re-initialize." Stop.
- If `.purlin/` exists and `--force` is set: proceed, preserve existing `config.json`.

## Step 2 — Create Directory Structure

```
.purlin/
  config.json         # from templates/config.json
  plugins/            # proof plugin installed here
specs/
  _invariants/        # invariant specs go here
```

## Step 3 — Detect Test Framework

Check project files and show the user what was detected and why:

- `conftest.py` or `pyproject.toml` with `[tool.pytest]` → `"pytest"`
- `package.json` with `jest` → `"jest"`
- `*.test.sh` files → `"shell"`

Display the detection result:
```
Detected: pytest (found conftest.py at project root)
Scaffolding: .purlin/plugins/purlin_proof.py
```

If no framework is detected, do NOT silently default to `"auto"` or `"shell"`. Ask the user:
```
No test framework detected (no conftest.py, package.json, or go.mod found).
Which framework? [pytest / jest / shell / other]
```

Write the detected (or user-selected) framework to `.purlin/config.json` under `test_framework`.

## Step 4 — Scaffold Proof Plugin

Copy the appropriate proof plugin from `scripts/proof/` to `.purlin/plugins/`:

| Framework | Source | Destination |
|-----------|--------|-------------|
| pytest | `scripts/proof/pytest_purlin.py` | `.purlin/plugins/pytest_purlin.py` |
| jest | `scripts/proof/jest_purlin.js` | `.purlin/plugins/jest_purlin.js` |
| shell | `scripts/proof/shell_purlin.sh` | `.purlin/plugins/purlin-proof.sh` |

For pytest, also create or update `conftest.py` at the project root:

```python
pytest_plugins = [".purlin.plugins.pytest_purlin"]
```

For jest, add reporter config to `jest.config.js` or `package.json`:

```json
{
  "reporters": ["default", ".purlin/plugins/jest_purlin.js"]
}
```

## Step 5 — Update .gitignore

Ensure `.gitignore` contains:

```
# Purlin runtime (not committed)
.purlin/runtime/
.purlin/plugins/__pycache__/
```

## Step 6 — Confirmation

```
Project initialized for Purlin.

Created:
  .purlin/config.json
  .purlin/plugins/<proof_plugin>
  specs/
  specs/_invariants/

Test framework: <detected>
Proof plugin: .purlin/plugins/<name>

Next steps:
  purlin:spec <topic>    — create your first spec
  purlin:status          — see rule coverage
```

## Step 7 — Commit

```
git commit -m "chore: initialize purlin project"
```
