# Feature: Unified Version-Aware Update

> Label: "Tool: Unified Version-Aware Update"
> Category: "Install, Update & Scripts"

## 1. Overview

A single `purlin:update` command that detects the consumer project's current Purlin installation model and version, computes the migration path to the current plugin version, and executes each step in order. Replaces both the former submodule-only `purlin:update` and the one-time `purlin:upgrade` (submodule-to-plugin migration) with a unified, version-aware flow. The command is idempotent --- interrupted runs resume from the last completed step, and running on an already-current project produces "Already up to date."

---

## 2. Requirements

### 2.1 Command Interface

```
purlin:update [<version>] [--dry-run] [--auto-approve]
```

- `<version>`: Optional explicit target. If omitted, targets the current plugin version.
- `--dry-run`: Show the migration plan without modifying files.
- `--auto-approve`: Skip confirmation prompts.

### 2.2 Standalone Mode Guard

Before any work, detect if this is the Purlin plugin repo itself (not a consumer project):
- Detection: `${CLAUDE_PLUGIN_ROOT}` resolves to the current project root AND `.claude-plugin/plugin.json` exists at project root.
- If true: "purlin:update is for consumer projects. This is the Purlin framework repo." Stop.

### 2.3 Three-Layer Architecture

The update flow uses three layers:

1. **Version Detector** (`scripts/migration/version_detector.py`): Examines the consumer project and emits a structured fingerprint.
2. **Migration Registry** (`scripts/migration/migration_registry.py`): Ordered list of migration steps with preconditions, `plan()` (dry-run), and `execute()` methods.
3. **Skill orchestration** (`skills/update/SKILL.md`): Calls detector, computes path, shows plan, executes steps, produces summary.

### 2.4 Version Detection

The version detector examines the consumer project directory and produces a fingerprint: `{model, era, version_hint, migration_version}`.

#### 2.4.1 Distribution Model Detection

Signals are checked in priority order:

| Priority | Signal | Model |
|----------|--------|-------|
| 1 | `.claude/settings.json` has `enabledPlugins` containing `purlin` | `plugin` |
| 2 | `.gitmodules` contains a purlin submodule entry | `submodule` |
| 3 | `.purlin/` exists but no submodule or plugin declaration | `fresh` |
| 4 | No Purlin-related artifacts found | `none` |

#### 2.4.2 Submodule Era Detection

When the model is `submodule`, the detector inspects the consumer's `.purlin/config.json` (or `.purlin/config.local.json`) to determine the version era:

| Signal | Era | Version Range |
|--------|-----|---------------|
| `agents.architect` with `startup_sequence` key | `pre-unified-legacy` | v0.7.x |
| `agents.architect` with `find_work` key, no `agents.pm` | `pre-unified-modern` | v0.8.0-v0.8.3 |
| `agents.pm` exists, no `agents.purlin` | `pre-unified-with-pm` | v0.8.4 |
| `agents.purlin` exists, `_migration_version` present | `unified` | v0.8.5 |
| `agents.purlin` with only `model`+`effort`, `agents.builder` still present | `unified-partial` | v0.8.4 partial migration |

Additional signals:
- `.purlin/.upstream_sha` --- submodule version tracker file.
- `tools_root` config key --- submodule-era path resolution.
- Role-specific launchers (`pl-run-architect.sh`, etc.) vs unified launcher (`pl-run.sh`) at project root.

#### 2.4.3 Plugin Version Detection

When the model is `plugin`:
- Read `_migration_version` from consumer config to determine migration completeness.
- Current plugin version is available via `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.

#### 2.4.4 Fingerprint Schema

```json
{
  "model": "submodule" | "plugin" | "fresh" | "none",
  "era": "pre-unified-legacy" | "pre-unified-modern" | "pre-unified-with-pm" | "unified" | "unified-partial" | "plugin" | null,
  "version_hint": "v0.7.x" | "v0.8.0-v0.8.3" | "v0.8.4" | "v0.8.5" | "v0.9.x" | null,
  "migration_version": <integer> | null,
  "submodule_path": <string> | null
}
```

#### 2.4.5 CLI Interface

The detector MUST be callable as a CLI for testing:
```
python3 scripts/migration/version_detector.py --project-root <path>
```
Output: JSON fingerprint to stdout.

### 2.5 Migration Registry

#### 2.5.1 Step Interface

Each migration step is a Python class with:
- `step_id: int` --- the `_migration_version` value this step stamps on completion.
- `name: str` --- human-readable name (e.g., "Unified Agent Model").
- `from_era: str` --- the era this step migrates FROM.
- `to_era: str` --- the era this step migrates TO.
- `preconditions(fingerprint, project_root) -> (bool, str)` --- checks if this step can run. Returns `(True, "")` or `(False, "reason")`.
- `plan(fingerprint, project_root) -> list[str]` --- dry-run: returns list of actions that would be taken.
- `execute(fingerprint, project_root, auto_approve=False) -> bool` --- runs the migration. Returns True on success. Stamps `_migration_version` on completion.

#### 2.5.2 Step Definitions

| Step | `_migration_version` | From -> To | Name | Key Actions |
|------|---------------------|-----------|------|-------------|
| 1 | 1 | Pre-unified submodule -> Unified submodule | Unified Agent Model | Advance submodule to v0.8.5+. Consolidate 4-role config into `agents.purlin`. Merge override files. Clean old launchers. |
| 2 | 2 | Unified submodule -> Plugin | Submodule to Plugin | Remove submodule. Clean stale artifacts (launchers, commands, agents, `.upstream_sha`). Declare plugin in `.claude/settings.json`. Migrate config (remove `tools_root`, `models`, deprecated agents). Update CLAUDE.md and .gitignore. Remove old hooks from settings. |
| 3 | 3 | Plugin -> Current | Plugin Refresh | Check plugin version. Diff skills/agents/hooks between versions. Config sync (add missing keys). MCP manifest diff (report added/removed/changed servers). Stale artifact cleanup. |

#### 2.5.3 Path Computation

`compute_path(fingerprint, target_migration_version) -> list[Step]`

The function returns the ordered list of steps whose `step_id` is greater than the fingerprint's `migration_version` (or 0 if null) and less than or equal to `target_migration_version`.

Examples:
- Fingerprint `{migration_version: null, era: "pre-unified-legacy"}` -> steps [1, 2, 3]
- Fingerprint `{migration_version: null, era: "pre-unified-with-pm"}` -> steps [1, 2, 3]
- Fingerprint `{migration_version: 1, era: "unified"}` -> steps [2, 3]
- Fingerprint `{migration_version: 2, era: "plugin"}` -> steps [3]
- Fingerprint `{migration_version: 3, era: "plugin"}` -> [] (already current)

Special cases:
- `unified-partial` era: step 1 runs in repair mode (completes the partial migration).
- `fresh` model with no `_migration_version`: inform user to run `purlin:init` first if `.purlin/` is missing, or run step 3 if plugin is already declared.
- `none` model: "Not a Purlin project. Run `purlin:init` to set up." Stop.

#### 2.5.4 CLI Interface

The registry MUST be callable as a CLI for testing:
```
python3 scripts/migration/migration_registry.py --project-root <path> [--dry-run]
```
Output: The computed migration path with step names and planned actions.

### 2.6 Execution Flow

1. **Detect:** Run version detector on the consumer project.
2. **Guard:** If model is `none`, advise `purlin:init`. If standalone, reject.
3. **Compute path:** Call `compute_path(fingerprint, current_migration_version)`.
4. **Empty path:** "Already up to date." Stop.
5. **Show plan:** List each step with name and planned actions. If `--dry-run`, stop here.
6. **Confirm:** Prompt user for confirmation. Skip if `--auto-approve`.
7. **Execute:** Run each step sequentially. Each step stamps `_migration_version` on completion.
8. **Summary:** Report what was done, what version the project is now at.

### 2.7 Step 1: Unified Agent Model (Detail)

Precondition: Submodule exists, consumer has pre-unified config (`migration_version` < 1 or null).

Actions:
- Advance submodule to latest tag with unified agent support.
- Run `init.sh --quiet` from submodule to refresh artifacts.
- Execute migration module: consolidate 4-role config into `agents.purlin`, merge override files into single `PURLIN_OVERRIDES.md`, clean old role-specific launchers.
- Stamp `_migration_version: 1`.

Repair mode (for `unified-partial` era): Complete the partial migration --- add missing `find_work`/`auto_start`/`default_mode` to `agents.purlin`, deprecate old agent entries.

### 2.8 Step 2: Submodule to Plugin (Detail)

Precondition: Submodule exists, `migration_version >= 1`.

Actions:
1. Pre-flight: Verify clean working tree. Create safety commit with current state.
2. Preserve: Verify `features/`, `.purlin/PURLIN_OVERRIDES.md`, `.purlin/config.json`, `tests/` are intact.
3. Remove submodule: `git submodule deinit -f`, `git rm -f`, clean `.git/modules/`.
4. Clean stale artifacts: delete `pl-run.sh`, `pl-init.sh`, `.claude/commands/pl-*.md`, `.claude/agents/*.md`, `.purlin/.upstream_sha`.
5. Declare plugin: Add inline marketplace + `enabledPlugins` to `.claude/settings.json`, preserving existing permissions and settings.
6. Migrate config: Remove `tools_root`, `models` array, deprecated agent entries (`agents.architect`, `agents.builder`, `agents.qa`, `agents.pm`). Preserve `agents.purlin`.
7. Update CLAUDE.md: Replace submodule references with plugin template.
8. Update .gitignore: Remove submodule entries, add plugin patterns.
9. Remove old hooks: Remove `SessionStart`/`SessionEnd` entries from `.claude/settings.json` that reference old `tools/hooks/` paths.
10. Verify: Validate all JSON files, check `features/` intact, display summary.
11. Commit: `chore(purlin): migrate from submodule to plugin distribution`.
12. Stamp `_migration_version: 2`.

### 2.9 Step 3: Plugin Refresh (Detail)

Precondition: Plugin model active (`migration_version >= 2`).

Actions:
1. Check current plugin version vs running plugin version.
2. If already at target: check for pending config sync, run it if needed. Otherwise "Already up to date."
3. Config sync: Add missing keys from plugin template config to consumer's `config.local.json`.
4. MCP manifest diff: Compare consumer's MCP server list against plugin's `.mcp.json`. Report added/removed/changed servers with reconfiguration commands.
5. Stale artifact cleanup: Check for and remove any leftover pre-plugin artifacts.
6. Stamp `_migration_version: 3` (or current target).

### 2.10 Idempotency

- Each step checks `_migration_version` before running. If the step's `step_id` is <= the current `_migration_version`, it is skipped.
- Interruption recovery: If the process is interrupted mid-step, the `_migration_version` is NOT stamped (it stamps on completion). The next run re-executes the interrupted step from scratch.
- Running `purlin:update` on an already-current project always produces "Already up to date." with no file modifications.

### 2.11 Error Handling

- **Uncommitted changes** (steps 1, 2): "Commit or stash changes before updating." Stop.
- **Network failure** (step 1 submodule fetch): "Could not fetch from submodule remote." Stop.
- **Invalid explicit version**: "Version '<v>' not found in tags." Stop.
- **Missing `.purlin/`**: "Not a Purlin project. Run `purlin:init` to set up." Stop.
- **Submodule removal failure** (step 2): Report error, do NOT proceed. Safety commit provides rollback.

### 2.12 Regression Testing

Regression tests use the fixture-based harness (`scripts/test_support/harness_runner.py`).

**Fixture setup script:** `dev/setup_version_fixtures.sh` creates deterministic consumer project snapshots for each version era, tagged in the fixture repository.

**Fixture tags:**
| Tag | Era | Key State |
|-----|-----|-----------|
| `main/purlin_update/submodule-v0.7.x` | v0.7.x | `agents.architect` with `startup_sequence`, role-specific `run_*.sh` launchers |
| `main/purlin_update/submodule-v0.8.0-v0.8.3` | v0.8.0-v0.8.3 | `agents.architect` with `find_work`, `pl-run-*.sh` launchers, `pl-cdd-*.sh` |
| `main/purlin_update/submodule-v0.8.4` | v0.8.4 | `agents.pm` added, no `agents.purlin`, 4 role launchers |
| `main/purlin_update/submodule-v0.8.4-partial` | v0.8.4 partial | Submodule at v0.8.5 but migration incomplete |
| `main/purlin_update/submodule-v0.8.5` | v0.8.5 | `agents.purlin`, `_migration_version: 1`, single `pl-run.sh` |
| `main/purlin_update/plugin-v0.9.0` | v0.9.0 | Plugin model, no submodule, `_migration_version: 2` |
| `main/purlin_update/fresh-project` | Fresh | Just `.purlin/` and `features/`, no version markers |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Detect v0.7.x submodule project

    Given a consumer project with submodule-v0.7.x fixture state
    When the version detector runs
    Then the fingerprint model is "submodule"
    And the fingerprint era is "pre-unified-legacy"
    And migration_version is null

#### Scenario: Detect v0.8.4 submodule project

    Given a consumer project with submodule-v0.8.4 fixture state
    When the version detector runs
    Then the fingerprint model is "submodule"
    And the fingerprint era is "pre-unified-with-pm"
    And migration_version is null

#### Scenario: Detect v0.8.5 unified submodule project

    Given a consumer project with submodule-v0.8.5 fixture state
    When the version detector runs
    Then the fingerprint model is "submodule"
    And the fingerprint era is "unified"
    And migration_version is 1

#### Scenario: Detect v0.8.4 partial migration

    Given a consumer project with submodule-v0.8.4-partial fixture state
    When the version detector runs
    Then the fingerprint model is "submodule"
    And the fingerprint era is "unified-partial"

#### Scenario: Detect plugin-based project

    Given a consumer project with plugin-v0.9.0 fixture state
    When the version detector runs
    Then the fingerprint model is "plugin"
    And migration_version is 2

#### Scenario: Detect fresh project

    Given a consumer project with fresh-project fixture state
    When the version detector runs
    Then the fingerprint model is "fresh"

#### Scenario: Detect non-Purlin project

    Given a directory with no .purlin/ and no Purlin artifacts
    When the version detector runs
    Then the fingerprint model is "none"

#### Scenario: Compute path from v0.7.x to current

    Given a fingerprint with era "pre-unified-legacy" and migration_version null
    When compute_path is called with target migration_version 3
    Then the path contains steps [1, 2, 3]

#### Scenario: Compute path from v0.8.5 to current

    Given a fingerprint with era "unified" and migration_version 1
    When compute_path is called with target migration_version 3
    Then the path contains steps [2, 3]

#### Scenario: Compute path from plugin v0.9.0 to current

    Given a fingerprint with migration_version 2
    When compute_path is called with target migration_version 3
    Then the path contains steps [3]

#### Scenario: Already current produces empty path

    Given a fingerprint with migration_version 3
    When compute_path is called with target migration_version 3
    Then the path is empty

#### Scenario: Partial migration computes repair path

    Given a fingerprint with era "unified-partial" and migration_version null
    When compute_path is called with target migration_version 3
    Then the path contains steps [1, 2, 3]
    And step 1 runs in repair mode

#### Scenario: Fresh project with no plugin advises init

    Given a fingerprint with model "fresh"
    When purlin:update runs
    Then the output contains "Run purlin:init first"

#### Scenario: Standalone mode guard rejects Purlin repo

    Given the current directory is the Purlin plugin repo itself
    When purlin:update runs
    Then the output contains "purlin:update is for consumer projects"

#### Scenario: Dry-run shows plan without modifying files

    Given a consumer project with submodule-v0.8.5 fixture state
    When purlin:update --dry-run runs
    Then the output lists steps 2 and 3 with planned actions
    And no files are modified

#### Scenario: Idempotency --- second run is no-op

    Given purlin:update has already migrated a project to current
    When purlin:update runs again
    Then the output is "Already up to date."
    And no files are modified

#### Scenario: Uncommitted changes block migration

    Given a consumer project with uncommitted changes
    When purlin:update runs and step 2 would execute
    Then the output contains "Commit or stash changes"
    And no migration steps execute

#### Scenario: Step stamps migration_version on completion

    Given a consumer project at migration_version 1
    When step 2 executes successfully
    Then config contains _migration_version: 2

#### Scenario: Interrupted step does not stamp version

    Given step 2 fails mid-execution
    When checking _migration_version in config
    Then the value is still 1

#### Scenario: Step 2 removes submodule and declares plugin

    Given a consumer project with submodule-v0.8.5 fixture state at migration_version 1
    When step 2 executes
    Then .gitmodules no longer contains a purlin entry
    And .claude/settings.json contains enabledPlugins with purlin
    And pl-run.sh does not exist at project root
    And .purlin/.upstream_sha does not exist
    And config.json does not contain tools_root key

#### Scenario: Step 2 preserves features and tests

    Given a consumer project with 3 feature specs and test fixtures
    When step 2 executes
    Then all 3 feature specs still exist unchanged
    And test fixtures are intact

#### Scenario: Step 3 syncs new config keys

    Given a plugin project at migration_version 2
    And the plugin template config has a new key "server_port"
    When step 3 executes
    Then config.local.json contains the new key with the template default

#### Scenario: Version detector CLI outputs valid JSON

    Given a consumer project directory
    When python3 scripts/migration/version_detector.py --project-root <path> runs
    Then stdout is valid JSON matching the fingerprint schema

#### Scenario: Migration registry CLI shows computed path

    Given a consumer project at migration_version 1
    When python3 scripts/migration/migration_registry.py --project-root <path> runs
    Then stdout shows steps 2 and 3 with names and action summaries

### QA Scenarios

#### @manual Scenario: Full migration from v0.7.x submodule to current plugin

    Given a consumer project created from the submodule-v0.7.x fixture
    When purlin:update is run interactively
    Then all three migration steps execute in order
    And the project is fully functional as a plugin consumer
    And purlin:start runs successfully in the migrated project

#### @manual Scenario: Full migration from v0.8.5 submodule to current plugin

    Given a consumer project created from the submodule-v0.8.5 fixture
    When purlin:update is run interactively
    Then steps 2 and 3 execute
    And the project has no submodule artifacts remaining
    And purlin:start runs successfully

## Regression Guidance

- Version detection is the foundation --- any detection error cascades to wrong migration path. Test detection against ALL fixture states.
- Step 2 (submodule removal) is destructive and hard to reverse. The safety commit MUST be created before any submodule operations.
- Idempotency is critical for user trust. Running update twice must never corrupt state.
- The `_migration_version` stamp is the single source of truth for migration state. It must be written atomically (no partial stamps).
- Fixture states must be deterministic. The setup script must produce byte-identical results on repeated runs.
