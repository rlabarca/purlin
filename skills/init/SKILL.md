---
name: init
description: Initialize a project for Purlin
---

Set up a project for spec-driven development. Creates `.purlin/`, `specs/`, detects the test framework, and scaffolds the proof plugin.

## Usage

```
purlin:init                             Full setup (all steps)
purlin:init --force                     Re-run full setup
purlin:init --add-plugin <source>       Add a proof plugin
purlin:init --list-plugins              List proof plugins
purlin:init --sync-audit-criteria       Sync external audit criteria
purlin:init --audit-llm                 Change audit LLM (default/external)
purlin:init --pre-push                  Change pre-push mode (warn/strict)
purlin:init --report                    Toggle HTML dashboard report (on/off)
purlin:init --digest                    Change digest mode (auto/warn/off)
```

Each `--flag` runs ONLY that step, not the full init.

## Step 1 — Pre-flight

- **Git check (mandatory):** Run `git rev-parse --git-dir`. If it fails, the project is not a git repository. Print: `"Purlin requires git. Run 'git init' first."` Stop. Do NOT proceed without git — proofs, receipts, manual stamps, drift detection, and the pre-push hook all depend on git.
- If `.purlin/` exists and `--force` is not set: "Project already initialized. Use `--force` to re-initialize." Stop.
- If `.purlin/` exists and `--force` is set: proceed, preserve existing `config.json`.

## Step 2 — Create Directory Structure

```
.purlin/
  config.json         # from templates/config.json
  plugins/            # proof plugin installed here
specs/
  _anchors/           # anchor specs go here
```

Read the Purlin framework version from `${CLAUDE_PLUGIN_ROOT}/VERSION` and write it as the `version` field in config.json. This ensures the config always matches the installed framework version.

Config template fields (from `templates/config.json`):

| Field | Default | Description |
|-------|---------|-------------|
| `version` | `"0.9.0"` | Purlin framework version |
| `test_framework` | `"auto"` | Detected test framework(s) |
| `spec_dir` | `"specs"` | Directory containing specs |
| `pre_push` | `"warn"` | Pre-push hook mode (`warn` or `strict`) |
| `report` | `true` | HTML dashboard report generation |
| `digest` | `"auto"` | Digest generation mode (`auto`, `warn`, or `off`) |

## Step 3 — Detect Test Framework

**Print `DETECTING CODEBASE` before scanning.** Framework detection scans multiple files across the project and can take noticeable time — the user must see that work is happening:

```
DETECTING CODEBASE
Scanning project files for test frameworks...
```

Read `references/supported_frameworks.md` for the complete framework list, detection heuristics, and plugin file mappings. That file is the single source of truth — do NOT hardcode framework names here. Check project files for ALL matching frameworks using the detection table in that reference.

**Always present the framework selection list to the user**, even when auto-detection succeeds. Build the list dynamically from `references/supported_frameworks.md`. Pre-select detected frameworks with `[x]`, show undetected as `[ ]`. Always include `other` as the last option for custom plugins. This lets the user confirm, add, or remove frameworks before scaffolding.

When one or more frameworks are detected:

```
DETECTING CODEBASE
Scanning project files for test frameworks...

Test frameworks (detected frameworks are pre-selected):
  [x] <detected framework>    — <detection reason>
  [ ] <other framework>
  ...
  [ ] other

Confirm selection, or change? [enter to confirm]
```

When no framework is detected, do NOT silently default to shell. Show the list with nothing pre-selected:

```
DETECTING CODEBASE
Scanning project files for test frameworks...

No test framework detected.

Test frameworks (select one or more):
  [ ] <framework>
  ...
  [ ] other

Which framework(s)? You can select multiple, e.g.: pytest, jest
```

If the user selects "other", suggest `purlin:init --add-plugin` to install a custom proof plugin.

Write selected frameworks to `.purlin/config.json` under `test_framework`. For multiple frameworks, use a comma-separated list: `"pytest,jest"`.

## Step 4 — Scaffold Proof Plugins

Copy ALL selected proof plugins from `scripts/proof/` to `.purlin/plugins/`. Use the plugin file column in `references/supported_frameworks.md` to map each framework to its source file. If multiple frameworks were selected, scaffold ALL of them.

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
.purlin/cache/

# Dashboard HTML (symlinked from framework)
/purlin-report.html
```

**Note:** `.purlin/report-data.js` is NOT gitignored — it is the project digest and should be committed. If upgrading from a prior version, remove any existing `.purlin/report-data.js` entry from `.gitignore`.

## Step 5b — Dashboard Report

The HTML dashboard is enabled by default. Ask the user:

```
HTML dashboard report:
  [on]  Generate purlin-report.html — open in browser for live coverage (default)
  [off] Disable dashboard report generation
```

If **on** (default): set `"report": true` in `.purlin/config.json`. Create a symlink at the project root: `purlin-report.html -> ${CLAUDE_PLUGIN_ROOT}/scripts/report/purlin-report.html`. This ensures the dashboard always reflects the latest Purlin version without manual copies. Print: `Dashboard: purlin-report.html (open in browser after running purlin:status)`

If **off**: set `"report": false` in `.purlin/config.json`. Do not copy the HTML file.

When called via `purlin:init --report`, ONLY this step runs. Read the current config, show the current setting, and ask to toggle:

```
Dashboard report is currently: on
  [on]  Keep enabled
  [off] Disable
```

After changing, update `"report"` in `.purlin/config.json`. If turning on, copy the HTML file to project root. If turning off, do NOT delete an existing HTML file (the user may want to keep it).

## Step 5c — Configure MCP Server

Create or update `.mcp.json` at the project root so Claude Code starts the Purlin MCP server (providing `sync_status`, `purlin_config`, and `drift` tools).

If `.mcp.json` does not exist, create it:

```json
{
  "mcpServers": {
    "purlin": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin_server.py"]
    }
  }
}
```

If `.mcp.json` already exists, read it as JSON and merge the `purlin` key into the existing `mcpServers` object. Do NOT overwrite other MCP server entries. If a `purlin` key already exists, update it to the current path.

Resolve `${CLAUDE_PLUGIN_ROOT}` to its absolute path at init time — `.mcp.json` does not support environment variable expansion.

Print: `MCP server configured: sync_status, purlin_config, drift tools available.`

## Step 6 — Confirmation

```
Project initialized for Purlin.

Created:
  .purlin/config.json
  .purlin/plugins/<proof_plugin>
  .mcp.json (MCP server configuration)
  specs/
  specs/_anchors/
  purlin-report.html (if report enabled)
  .git/hooks/pre-push (if installed)

Test framework: <detected>
Proof plugin: .purlin/plugins/<name>
Dashboard: on (open purlin-report.html in browser)
Digest: auto (regenerated on every commit)

Next steps:
  purlin:spec <topic>    — create your first spec
  purlin:status          — see rule coverage
```

## Step 7 — Install Git Pre-push Hook

Install the Purlin pre-push hook so `git push` checks proof coverage before code reaches the remote.

The hook has two modes, set in `.purlin/config.json` under `"pre_push"`:
- **`"warn"`** (default) — blocks on FAILING proofs, warns on PARTIAL and UNTESTED coverage
- **`"strict"`** — blocks on anything not VERIFIED (requires verification receipt)

Ask the user which mode they want:
```
Pre-push hook mode:
  [warn]   Block on FAILING, allow PASSING and PARTIAL (default)
  [strict] Block on anything not VERIFIED (requires verification receipt)
```

Write the chosen mode to `.purlin/config.json` as `"pre_push": "warn"` or `"pre_push": "strict"`.

When called via `purlin:init --pre-push`, ONLY the mode selection above runs (no hook installation). The hook install steps below only run during the full init flow.

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

## Step 7a — Pre-commit Hook (Project Digest)

Install the Purlin pre-commit hook so `git commit` automatically regenerates the project digest (coverage + drift data in `.purlin/report-data.js`). The digest is committed to the repo so non-engineer stakeholders (QA, PM, compliance) can access project status without running Purlin tools.

The digest has three modes, set in `.purlin/config.json` under `"digest"`:
- **`"auto"`** (default) — regenerate digest before every commit, auto-stage the file
- **`"warn"`** — warn if the digest is stale, don't regenerate or block
- **`"off"`** — disable the pre-commit hook entirely

Ask the user which mode they want:

```
Project digest (auto-generates coverage + drift data for stakeholders):
  [auto] Regenerate on every commit — always up-to-date (default)
  [warn] Warn if digest is stale, don't auto-regenerate
  [off]  Disable digest hook

NOTE: Digest generation runs coverage scan and drift only.
It NEVER triggers an audit — cached audit data is included.
Run purlin:audit separately when you want fresh audit scores.
```

Write the chosen mode to `.purlin/config.json` as `"digest": "auto"` (or `"warn"` or `"off"`).

When called via `purlin:init --digest`, run the mode selection above AND the hook installation steps below. Also remove `.purlin/report-data.js` from `.gitignore` if present. This makes `--digest` a complete setup command for existing projects — the user runs one command and gets the full digest feature.

1. Check if `.git/hooks/pre-commit` already exists:
   - If it exists and is already the Purlin hook (contains `purlin`): skip, print `Pre-commit hook already installed.`
   - If it exists and is a different hook: warn and skip — do NOT overwrite. Print: `Existing pre-commit hook found — skipping Purlin hook install. To add manually, see scripts/hooks/pre-commit.sh`
   - If it does not exist: proceed.
2. Create a symlink or copy:
   ```bash
   # Preferred: symlink (stays in sync with framework updates)
   ln -s "$PURLIN_SCRIPTS/scripts/hooks/pre-commit.sh" .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```
   If the symlink target is not resolvable, copy the file instead:
   ```bash
   cp "$PURLIN_SCRIPTS/scripts/hooks/pre-commit.sh" .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```
3. Print: `Installed git pre-commit hook (project digest).`

## Step 7b — Audit Criteria

Ask the user which audit criteria to use:

```
Audit criteria:
  [default] Use Purlin's built-in audit criteria only
  [additional] Add team-specific criteria from a git-hosted file
               (appended to built-in — does not replace defaults)
```

If **default**: no config change needed — `purlin:audit` loads built-in criteria via `load_criteria()`.

If **additional**: ask for the git URL and file path (e.g., `git@github.com:acme/quality-standards.git#audit_criteria.md`). Set `audit_criteria` and `audit_criteria_pinned` in `.purlin/config.json`:

```json
{
  "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "<current remote HEAD sha>"
}
```

Clone the repo to a temp directory, read the file at HEAD, **save to `.purlin/cache/additional_criteria.md`**, record the commit SHA as `audit_criteria_pinned`, then clean up. The `load_criteria()` function in `static_checks.py` reads this cached file and appends it to the built-in criteria.

## Step 7c — Audit LLM Configuration

Ask the user which LLM should perform proof audits:

```
Audit LLM:
  [default] Claude audits (same model — fastest, independent context)
  [external] Use a different LLM for cross-model auditing (experimental)
```

If **default**: no config change. The auditor runs in an independent context.

If **external**: ask for the CLI command:

```
Enter the command to call your external LLM.
Use {prompt} where the audit prompt should go.

Examples:
  gemini -m pro -p "{prompt}"
  openai chat -m gpt-4o "{prompt}"
  ollama run llama3 "{prompt}"

Command:
```

After the user enters the command:

1. **Test it:** shell out with a simple test prompt — replace `{prompt}` with `"Respond with exactly: PURLIN_AUDIT_OK"` and run the command.
2. **Check the response** contains `PURLIN_AUDIT_OK`.
3. **If it works:** save to `.purlin/config.json`:
   ```json
   {
     "audit_llm": "gemini -m pro -p \"{prompt}\"",
     "audit_llm_name": "Gemini Pro"
   }
   ```
   Print: `Audit LLM configured: Gemini Pro ✓`
4. **If it fails:** print the error and ask the user to try again or skip.

This step is also callable independently via `purlin:init --audit-llm`.

## Step 8 — Commit

Commit per `references/commit_conventions.md`:

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
   | TypeScript (`.ts`) | `proofs` and `JSON` |
   | C header (`.h`) | `purlin_proof` function |
   | PHP (`.php`) | `proofs` and `json_encode` |
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

List all files in `.purlin/plugins/`. For built-in plugins, look up the framework name from `references/supported_frameworks.md` (match the plugin filename to the "Plugin file" column). Label anything not in that reference as `custom`.

```
Installed proof plugins:
  .purlin/plugins/pytest_purlin.py (Python/pytest)
  .purlin/plugins/jest_purlin.js (JavaScript/Jest)
  .purlin/plugins/my_go_plugin.py (custom)
```

If `.purlin/plugins/` doesn't exist or is empty: `No proof plugins installed. Run purlin:init to set up.`

---

## Subcommand: --sync-audit-criteria

```
purlin:init --sync-audit-criteria
```

Syncs the additional team criteria file to the latest version.

### Steps

1. Read `.purlin/config.json`. If `audit_criteria` is not set: `"No external audit criteria configured. Using built-in defaults."` Stop.

2. Parse the git URL and file path from `audit_criteria` (format: `git@host:org/repo.git#path/to/file.md`).

3. Clone the repo to a temp directory: `git clone <url> /tmp/purlin-audit-criteria-sync`

4. Get the current remote HEAD SHA: `git rev-parse HEAD`

5. Compare to `audit_criteria_pinned` in config:
   - If same: `"Audit criteria up to date."` Clean up and stop.
   - If different: read the file at HEAD, **save to `.purlin/cache/additional_criteria.md`**, update `audit_criteria_pinned` in config to the new SHA, print `"Audit criteria updated: <old SHA> → <new SHA>"`

6. Clean up: `rm -rf /tmp/purlin-audit-criteria-sync`
