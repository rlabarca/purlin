---
name: init
description: Initialize a project for Purlin
---

Set up a project for spec-driven development. Creates `.purlin/`, `specs/`, detects the test framework, and scaffolds the proof plugin.

## Usage

```
purlin:init                             Initialize a new project
purlin:init --force                     Re-initialize (preserves existing config)
purlin:init --add-plugin <source>       Install a proof plugin from file or git URL
purlin:init --list-plugins              List installed proof plugins
purlin:init --sync-audit-criteria       Sync external audit criteria to latest version
```

## Step 1 — Pre-flight

- **Git check (mandatory):** Run `git rev-parse --git-dir`. If it fails, the project is not a git repository. Print: `"Purlin requires git. Run 'git init' first."` Stop. Do NOT proceed without git — proofs, receipts, manual stamps, changelog, and the pre-push hook all depend on git.
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
  .git/hooks/pre-push (if installed)

Test framework: <detected>
Proof plugin: .purlin/plugins/<name>

Next steps:
  purlin:spec <topic>    — create your first spec
  purlin:status          — see rule coverage
```

## Step 7 — Install Git Pre-push Hook

Install the Purlin pre-push hook so `git push` checks proof coverage before code reaches the remote.

The hook has two modes, set in `.purlin/config.json` under `"pre_push"`:
- **`"warn"`** (default) — blocks on FAILING proofs, warns on partial coverage
- **`"strict"`** — blocks on anything non-READY (all features must be fully proved)

Ask the user which mode they want:
```
Pre-push hook mode:
  [warn]   Block on failing proofs, warn on partial coverage (default)
  [strict] Block unless all features are READY (fully proved)
```

Write the chosen mode to `.purlin/config.json` as `"pre_push": "warn"` or `"pre_push": "strict"`.

1. Locate the Purlin plugin root (`$CLAUDE_PLUGIN_ROOT` or the framework scripts directory).
2. Check if `.git/hooks/pre-push` already exists:
   - If it exists and is already the Purlin hook (contains `purlin`): skip, print `Pre-push hook already installed.`
   - If it exists and is a different hook: warn and skip — do NOT overwrite. Print: `Existing pre-push hook found — skipping Purlin hook install. To add manually, see scripts/hooks/pre-push.sh`
   - If it does not exist: proceed.
3. Create a symlink or copy:
   ```bash
   # Preferred: symlink (stays in sync with framework updates)
   ln -s "$PURLIN_SCRIPTS/scripts/hooks/pre-push.sh" .git/hooks/pre-push
   chmod +x .git/hooks/pre-push
   ```
   If the symlink target is not resolvable (e.g., consumer project without local framework checkout), copy the file instead:
   ```bash
   cp "$PURLIN_SCRIPTS/scripts/hooks/pre-push.sh" .git/hooks/pre-push
   chmod +x .git/hooks/pre-push
   ```
4. Print: `Installed git pre-push hook (proof coverage check).`

## Step 7b — Audit Criteria

Ask the user which audit criteria to use:

```
Audit criteria:
  [default] Use Purlin's built-in audit criteria
  [custom]  Point to an external criteria file (git URL)
```

If **default**: no config change needed — `purlin:audit` reads `references/audit_criteria.md` automatically.

If **custom**: ask for the git URL and file path (e.g., `git@github.com:acme/quality-standards.git#audit_criteria.md`). Set `audit_criteria` and `audit_criteria_pinned` in `.purlin/config.json`:

```json
{
  "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "<current remote HEAD sha>"
}
```

Clone the repo to a temp directory, read the file at HEAD, record the commit SHA as `audit_criteria_pinned`, then clean up.

## Step 8 — Commit

```
git commit -m "chore: initialize purlin project"
```

---

## Subcommand: --add-plugin

```
purlin:init --add-plugin <source>
```

Source can be:
- A local file path: `./my_proof_plugin.py` or `/path/to/plugin.sh`
- A git URL: `git@github.com:someone/purlin-go-proof.git` or `https://...`

### Steps

1. **Verify `.purlin/plugins/` exists.** If not, tell the user to run `purlin:init` first and stop.

2. **If source is a local file path:**
   - Verify the file exists
   - Copy it to `.purlin/plugins/`
   - Print: `Added proof plugin: .purlin/plugins/<filename>`

3. **If source is a git URL:**
   - Clone to a temp directory: `git clone <url> /tmp/purlin-plugin-install`
   - Look for proof plugin files (`*.py`, `*.js`, `*.sh`, `*.java` in the repo root or a `plugin/` directory)
   - If one file found: copy to `.purlin/plugins/`
   - If multiple found: list them and ask the user which to install
   - Clean up the temp directory: `rm -rf /tmp/purlin-plugin-install`
   - Print: `Added proof plugin: .purlin/plugins/<filename>`

4. **Validate the plugin** after copying:

   | Language | Must contain |
   |----------|-------------|
   | Python (`.py`) | `proofs` and `json` |
   | JavaScript (`.js`) | `proofs` and `JSON` |
   | Shell (`.sh`) | `purlin_proof` function |
   | Java (`.java`) | `proofs` and `Proof` |

   If validation fails, warn but still install:
   ```
   ⚠ This file doesn't look like a standard proof plugin.
   It should read test markers and write .proofs-*.json files.
   See references/formats/proofs_format.md for the schema.
   ```

5. **Print next steps:**
   ```
   Plugin installed. To use it:
   1. Add proof markers to your tests using the plugin's marker syntax
   2. Run your tests — the plugin emits .proofs-*.json files
   3. purlin:status shows coverage
   ```

---

## Subcommand: --list-plugins

```
purlin:init --list-plugins
```

List all files in `.purlin/plugins/`:

```
Installed proof plugins:
  .purlin/plugins/pytest_purlin.py (Python/pytest)
  .purlin/plugins/jest_purlin.js (JavaScript/Jest)
  .purlin/plugins/purlin-proof.sh (Bash/shell)
  .purlin/plugins/my_go_plugin.py (custom)
```

For built-in plugins, show the framework name:

| Filename | Label |
|----------|-------|
| `pytest_purlin.py` | Python/pytest |
| `jest_purlin.js` | JavaScript/Jest |
| `purlin-proof.sh` | Bash/shell |
| Anything else | custom |

If `.purlin/plugins/` doesn't exist or is empty: `No proof plugins installed. Run purlin:init to set up.`

---

## Subcommand: --sync-audit-criteria

```
purlin:init --sync-audit-criteria
```

Syncs the external audit criteria file to the latest version.

### Steps

1. Read `.purlin/config.json`. If `audit_criteria` is not set: `"No external audit criteria configured. Using built-in defaults."` Stop.

2. Parse the git URL and file path from `audit_criteria` (format: `git@host:org/repo.git#path/to/file.md`).

3. Clone the repo to a temp directory: `git clone <url> /tmp/purlin-audit-criteria-sync`

4. Get the current remote HEAD SHA: `git rev-parse HEAD`

5. Compare to `audit_criteria_pinned` in config:
   - If same: `"Audit criteria up to date."` Clean up and stop.
   - If different: read the file at HEAD, update `audit_criteria_pinned` in config to the new SHA, print `"Audit criteria updated: <old SHA> → <new SHA>"`

6. Clean up: `rm -rf /tmp/purlin-audit-criteria-sync`
