---
name: update
description: Version-aware Purlin update with migration path detection
---

**Version-Aware Purlin Update**

Detects the consumer project's current Purlin installation model and version, computes the migration path to the current plugin version, and executes each step in order. Replaces the former submodule-only update and the one-time `purlin:upgrade` with a unified, version-aware flow.

## Usage

```
purlin:update [<version>] [--dry-run] [--auto-approve]
```

- `<version>`: Optional explicit target tag or branch. If omitted, targets the current plugin version.
- `--dry-run`: Show the migration plan without modifying files.
- `--auto-approve`: Skip confirmation prompts.

---

## Execution Flow

### Step 0 -- Setup

Print the skill banner:

```
━━━ purlin:update ━━━━━━━━━━━━━━━━━━━━━
```

### Step 1 -- Resolve Project Root

Resolve the consumer project root:
- Use `PURLIN_PROJECT_ROOT` env var if set and `.purlin/` exists there.
- Otherwise, detect from the current working directory by climbing until `.purlin/` is found.
- If no `.purlin/` found: print `✗ Not a Purlin project. Run purlin:init to set up.` Stop.
- **Do NOT narrate** the resolution process. Only print if it fails.

Set `<project_root>` to the resolved path.

### Step 2 -- Version Detection

Run the version detector:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migration/version_detector.py --project-root <project_root>
```

Parse the JSON fingerprint from stdout. The fingerprint contains: `{model, era, version_hint, migration_version, submodule_path}`.

Print detection result:

```
[1/4] Detecting version...
      Model: <model> · Era: <era> · Migration: <migration_version or "none">
```

**Guard checks on fingerprint:**
- If `model` is `"none"`: print `✗ Not a Purlin project. Run purlin:init to set up.` Stop.
- If `model` is `"fresh"` and `migration_version` is null: print `✗ Fresh project detected. Run purlin:init first.` Stop.

### Step 3 -- Compute Migration Path

Run the migration registry to compute the path:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migration/migration_registry.py --project-root <project_root> --dry-run
```

Parse the output. The registry outputs the computed steps with names and planned actions.

Alternatively, invoke the registry programmatically by reading the fingerprint and calling `compute_path()` logic:
- Steps with `step_id > migration_version` (or 0 if null) and `step_id <= CURRENT_MIGRATION_VERSION` are included.
- If the path is empty: print `✓ Already up to date.` with summary footer. Stop.

Print the plan:

```
[2/4] Computing migration path...
      <N> step(s) required: <step names joined by " → ">
```

### Step 4 -- Show Plan and Confirm

List each step with its planned actions:

```
Migration Plan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step <id>: <name> (<from_era> → <to_era>)
  - <action 1>
  - <action 2>
  ...

Step <id>: <name> (<from_era> → <to_era>)
  - <action 1>
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If `--dry-run`:** Print the plan and stop. Do not execute any steps.

**If NOT `--auto-approve`:** Prompt: `Proceed with migration? [y/n]`. If declined, stop.

**If `--auto-approve`:** Proceed without prompting.

### Step 5 -- Execute Migration Steps

Execute each step sequentially:

```
[3/4] Executing migration...
```

For each step in the computed path:

1. **Check preconditions:** Call `step.preconditions(fingerprint, project_root)`. If `(False, reason)`: print `✗ Step <id> (<name>) blocked: <reason>` and stop.

2. **Execute:** Call `step.execute(fingerprint, project_root, auto_approve)`.
   - Print `▸ Step <id>: <name>...`
   - On success: print `  ✓ Complete — stamped _migration_version: <step_id>`
   - On failure: print `  ✗ Step <id> failed.` and stop. The `_migration_version` was NOT stamped, so the next run will retry this step.

3. **Re-detect:** After each step completes, re-run version detection to get the updated fingerprint for the next step. This ensures each step sees the current project state.

Run the steps via CLI:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migration/migration_registry.py --project-root <project_root>
```

Or orchestrate step-by-step by calling the Python modules directly. The registry CLI handles sequential execution with re-detection between steps.

### Step 6 -- Summary

```
[4/4] Summary

━━━ Results ━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project:      <project_root basename>
From:         <original model>/<era> (migration_version: <original>)
To:           plugin/current (migration_version: <final>)
Steps:        <N> executed
Status:       ✓ Migration complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If step 4 (Figma to Design Invariant) created any invariant files, append:

```
Next: To sync Figma design data and populate Design Variables:
  1. Set up Figma MCP if not already: claude mcp add --transport http figma https://mcp.figma.com/mcp
  2. Restart the session, then run /mcp → select Figma → complete OAuth
  3. Run: purlin:invariant sync --all
     This fetches version IDs, extracts design variable definitions (via get_variable_defs),
     re-extracts annotations (via get_design_context), and detects Code Connect availability.
  4. Run: purlin:invariant validate
     Verify all invariants pass format checks.
```

If the project was migrated from submodule to plugin (step 2 or 3 removed the submodule), append:

```
Next: Run purlin:resume to verify the plugin works.
```

---

## Step-Specific Behavior

### Step 1: Unified Agent Model

When the skill orchestrates step 1 (pre-unified submodule to unified submodule):

- The registry's `Step1UnifiedAgentModel.execute()` handles config consolidation, launcher cleanup, and version stamping.
- If the era is `unified-partial`, step 1 runs in **repair mode**: completes the partial `agents.purlin` config and removes deprecated agent entries.
- If the consumer has a submodule, the skill should advance it to the latest tag before running step 1:
  ```bash
  git -C <submodule_path> fetch --tags
  git -C <submodule_path> checkout <latest_tag>
  ```

### Step 2: Submodule to Plugin

When the skill orchestrates step 2:

- The registry's `Step2SubmoduleToPlugin.execute()` handles submodule removal, stale artifact cleanup, plugin declaration, config migration, and commit.
- **Prerequisite:** Step 2's preconditions require a clean working tree. The step creates a safety commit before destructive operations.
- After step 2 completes, the submodule is gone and the plugin is declared. The consumer project is now in plugin mode.

### Step 3: Plugin Refresh

When the skill orchestrates step 3:

- The registry's `Step3PluginRefresh.execute()` handles config sync, stale artifact cleanup, and version stamping.
- This is the most common step for existing plugin consumers — it runs alone when the project is already on the plugin model.

### Step 6: Mode to Sync Migration

When the skill orchestrates step 6 (mode_to_sync):

- **Precondition:** Only relevant for projects that had the mode system (mode state files or mode hooks exist). Projects without mode artifacts skip this step.
- **Actions:** Deletes mode state files (`.purlin/runtime/current_mode*`), deletes `session_writes.json` and `companion_debt.json`, creates empty `.purlin/sync_ledger.json`, removes mode-related config keys (`default_mode`, `mode_on_start`), updates `.gitignore` to add `sync_state.json` and remove `session_writes.json`.
- **New state created:** `.purlin/sync_ledger.json` (empty object, populated by sync-ledger-update pre-commit hook on subsequent commits).
- Hook config updates happen via the plugin update itself (new hook files replace `mode-guard.sh` with `write-guard.sh` and `companion-debt-tracker.sh` with `sync-tracker.sh`). The migration step only handles consumer-side artifacts.

---

## Error Handling

| Condition | Message | Action |
|-----------|---------|--------|
| Not a Purlin project | `✗ Not a Purlin project. Run purlin:init to set up.` | Stop |
| Purlin framework repo | `✗ purlin:update is for consumer projects.` | Stop |
| Fresh project, no migration | `✗ Fresh project detected. Run purlin:init first.` | Stop |
| Already up to date | `✓ Already up to date.` | Stop (success) |
| Uncommitted changes (step 2) | `✗ Step 2 blocked: Commit or stash changes before updating.` | Stop |
| Step precondition failure | `✗ Step <id> (<name>) blocked: <reason>` | Stop |
| Step execution failure | `✗ Step <id> failed.` | Stop (version not stamped, safe to retry) |

---

## Post-Migration: Organize Features

After all migration steps complete (or if already up to date), run feature file organization as permanent housekeeping. This step runs on every `purlin:update` invocation and is idempotent.

**Writes:** feature files, .purlin/ config files

### Organize Step -- Feature File Placement

1. **Rename legacy special folders** (if old names exist):
   - `features/tombstones/` → `features/_tombstones/`
   - `features/digests/` → `features/_digests/`
   - `features/design/` → `features/_design/`
   - Delete `features/companions/` if empty (content should have been merged into `.impl.md` files)

2. **Scan `features/` root** for any `.md` files not already in a category subfolder. Skip `_`-prefixed system folders and non-`.md` files.

3. **For each root-level `.md` file** (excluding `.impl.md` and `.discoveries.md`):
   a. If the file has an `i_*` prefix (invariant), target folder is `_invariants/`.
   b. Otherwise, extract `> Category:` metadata from the file.
   c. Slugify the category to derive the folder name: lowercase, strip quotes, replace spaces with `_`, replace non-alphanumeric characters (except `_`) with nothing. Examples: `"UI"` → `ui`, `"Framework Core"` → `framework_core`, `"Install, Update & Scripts"` → `install_update_scripts`.
   d. If no `> Category:` metadata exists, print a warning and skip: `⚠ <filename>: no category metadata — skipped`
   e. Create the target folder if it doesn't exist.
   f. Move the file into the target folder.
   g. Move companion files alongside it: if `<name>.impl.md` exists at root, move it too. Same for `<name>.discoveries.md`.

4. **Report:**
   - If files were moved: `Organized <N> feature(s) into category folders`
   - If nothing to move: no output (silent)

### Organize Step -- Drift Detection

After organizing, scan all category subfolders for drift:
- For each feature file in a subfolder, extract `> Category:` and slugify it.
- If the file is in the wrong folder (slugified category doesn't match the containing folder name), print: `⚠ <path>: category "<category>" does not match folder "<folder>"`
- Do NOT move these files automatically — drift requires investigation.

---

## Idempotency

- Each step checks `_migration_version` before running. Steps with `step_id <= migration_version` are skipped.
- Interrupted runs resume from the last completed step (the interrupted step's version was not stamped).
- Running `purlin:update` on an already-current project always produces `✓ Already up to date.` with no file modifications.

---

## Examples

```
purlin:update                    # Update to current version
purlin:update --dry-run          # Preview the migration plan
purlin:update --auto-approve     # Update without prompts
```

**Implementation:** See `features/purlin_update.md`
