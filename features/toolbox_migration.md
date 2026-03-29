# Feature: Agentic Toolbox — Migration from Release Steps

> Label: "Tool: Toolbox Migration"
> Category: "Install, Update & Scripts"
> Owner: PM
> Prerequisite: toolbox_core.md

## 1. Overview

This feature defines the automated migration from the old Release Steps system to the new Agentic Toolbox system. The migration runs during `purlin:update` (as step 7c) and converts `.purlin/release/` files into `.purlin/toolbox/` files. It is non-destructive: old files are preserved for one release cycle as a safety net.

The migration handles consumer projects that have existing release step configurations. The Purlin framework repository itself also migrates its own local steps.

---

## 2. Requirements

### 2.1 Detection

The migration is needed when:
*   `.purlin/release/config.json` OR `.purlin/release/local_steps.json` exists, AND
*   `.purlin/toolbox/.migrated_from_release` does NOT exist.

The migration is skipped when:
*   `.purlin/toolbox/.migrated_from_release` exists (already migrated), OR
*   Neither `.purlin/release/config.json` nor `.purlin/release/local_steps.json` exists (nothing to migrate — fresh project or already cleaned up).

### 2.2 Migration Algorithm

**Script location:** `tools/migration/migrate_release_to_toolbox.py`

**Arguments:** `--project-root <path>` (required), `--dry-run` (optional)

**Steps:**

1. **Read source files:**
    *   Read `.purlin/release/local_steps.json` if it exists. Parse `steps` array.
    *   Read `.purlin/release/config.json` if it exists (for informational logging only — no data is migrated from config since the toolbox has no enable/disable or ordering concept).

2. **Transform local steps to project tools:**
    *   For each step in `local_steps.json`:
        *   Copy all existing fields (`id`, `friendly_name`, `description`, `code`, `agent_instructions`).
        *   Add `"metadata": {"last_updated": "<today>"}`.
    *   Wrap in `{"schema_version": "2.0", "tools": [...]}`.

3. **Create directory structure:**
    *   `mkdir -p .purlin/toolbox/community/`

4. **Write transformed files:**
    *   Write `.purlin/toolbox/project_tools.json` with the transformed tools.
    *   Write `.purlin/toolbox/community_tools.json` with `{"schema_version": "2.0", "tools": []}`.

5. **Write migration marker:**
    *   Write `.purlin/toolbox/.migrated_from_release` containing:
        ```json
        {
          "migrated_at": "<ISO 8601 timestamp>",
          "source_local_steps_checksum": "<SHA-256 of local_steps.json content>",
          "tools_migrated": <count>
        }
        ```
    *   This marker is written LAST to ensure atomicity — its absence indicates incomplete migration.

6. **Do NOT delete old files:**
    *   `.purlin/release/` is preserved for one release cycle.
    *   The next `purlin:update` run (after the migration release) can prompt for deletion as a stale artifact.

**Dry-run behavior:** When `--dry-run` is passed, print what would be created/written without modifying the filesystem. Exit with code 0.

### 2.3 Edge Cases

*   **No local_steps.json:** If only `config.json` exists (no custom tools), create an empty `project_tools.json` (`{"schema_version": "2.0", "tools": []}`). The config is discarded (no ordering/enable-disable in the new system).
*   **Empty local_steps.json:** If `local_steps.json` exists but has an empty `steps` array, create an empty `project_tools.json`.
*   **Corrupt JSON:** If any source file contains invalid JSON, log an error and skip that file. Write what can be migrated. The marker is still written (the migration is "complete" even if some files were corrupt — re-running won't fix corrupt source files).
*   **Partial migration (re-run):** If `.purlin/toolbox/` exists but no marker, the migration re-runs and overwrites existing toolbox files. This handles crashes mid-migration.
*   **Tool ID conflicts:** Local steps with `purlin.` prefix (which was invalid in the old system too) are migrated as-is. The toolbox resolver will catch the prefix violation at resolution time.

### 2.4 Integration with pl-update-purlin

The migration runs as step 7c in `purlin:update`, after config sync (step 6) and existing migration module (step 7):

```
Step 7c: Release-to-Toolbox Migration
  - Detection check per Section 2.1
  - If needed: run python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migration/migrate_release_to_toolbox.py --project-root <project_root>
  - Report results in summary: "Migrated N tools from release steps to Agentic Toolbox."
  - If --dry-run: run with --dry-run flag, show what would change
```

### 2.5 Integration with init.sh

For NEW projects (full init mode):
*   Copy `purlin-config-sample/toolbox/` to `.purlin/toolbox/` instead of `purlin-config-sample/release/`.
*   Create `.purlin/toolbox/community/` directory.
*   The sample `project_tools.json` contains an example tool (similar to the old `local_steps.json` example).

For EXISTING projects (refresh mode):
*   Do NOT touch `.purlin/toolbox/` (project-owned, never overwritten by refresh).
*   Do NOT touch `.purlin/release/` (if it still exists).

### 2.6 Stale Artifact Cleanup

After successful migration (marker exists), the next `purlin:update` run should:
*   Check if `.purlin/release/` still exists.
*   If yes: include it in the stale artifact check (step 8). Prompt: `"Found legacy release config at .purlin/release/. This has been migrated to .purlin/toolbox/. Delete the old directory?"`
*   Only delete on explicit user confirmation.

### 2.7 Regression Testing

**Unit tests** for the migration script, covering:

| Scenario | Input | Expected |
|---|---|---|
| No release dir | `.purlin/release/` absent | Returns "nothing_to_migrate" |
| Already migrated | `.migrated_from_release` exists | Returns "already_migrated" |
| Default config only | `config.json` with global steps, no `local_steps.json` | Empty `project_tools.json`, marker written |
| Custom local tools | `local_steps.json` with 3 tools | `project_tools.json` with 3 tools, each has `metadata.last_updated` |
| Empty local steps | `local_steps.json` with empty `steps` array | Empty `project_tools.json` |
| Corrupt source JSON | `local_steps.json` with invalid JSON | Error logged, empty `project_tools.json`, marker written |
| Dry run | `--dry-run` flag | No files created, report generated |
| Partial migration resumes | `toolbox/` exists but no marker | Re-runs migration, overwrites, writes marker |
| Marker contains checksum | Normal migration | Marker has correct checksum and tool count |
| Idempotent re-run | Run migration twice on same source | Second run detects marker, returns "already_migrated" |

**Fixture tags** for regression testing:

| Tag | State | Purpose |
|---|---|---|
| `main/toolbox_migration/default-config` | `.purlin/release/config.json` with 6 global steps, no local | Happy path: default consumer project |
| `main/toolbox_migration/custom-local-tools` | `config.json` + `local_steps.json` with 3 custom tools | Local tools preserved during migration |
| `main/toolbox_migration/disabled-steps` | Config with 2 steps `enabled: false` | Config is discarded (no enable/disable in toolbox) |
| `main/toolbox_migration/orphaned-refs` | Config referencing nonexistent step IDs | Config is discarded cleanly |
| `main/toolbox_migration/no-release-dir` | No `.purlin/release/` directory | Detection returns "nothing_to_migrate" |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Migration of local steps to project tools

    Given .purlin/release/local_steps.json contains 3 steps
    And .purlin/toolbox/ does not exist
    When the migration script runs
    Then .purlin/toolbox/project_tools.json contains 3 tools
    And each tool has metadata.last_updated set
    And .purlin/toolbox/community_tools.json is created with empty tools array
    And .purlin/toolbox/.migrated_from_release marker exists
    And .purlin/release/ is NOT deleted

#### Scenario: Migration skipped when already migrated

    Given .purlin/toolbox/.migrated_from_release exists
    When the migration script runs
    Then no files are modified
    And the script reports "already_migrated"

#### Scenario: Migration skipped when no release dir

    Given .purlin/release/ does not exist
    When the migration script runs
    Then no files are created
    And the script reports "nothing_to_migrate"

#### Scenario: Config-only migration (no local tools)

    Given .purlin/release/config.json exists but local_steps.json does not
    When the migration script runs
    Then .purlin/toolbox/project_tools.json is created with empty tools array
    And .purlin/toolbox/community_tools.json is created with empty tools array
    And marker is written

#### Scenario: Dry run creates no files

    Given .purlin/release/local_steps.json contains 2 steps
    When the migration script runs with --dry-run
    Then no files are created or modified
    And a report is printed showing what would be created

#### Scenario: Corrupt source handled gracefully

    Given .purlin/release/local_steps.json contains invalid JSON
    When the migration script runs
    Then an error is logged for the corrupt file
    And .purlin/toolbox/project_tools.json is created with empty tools array
    And the migration marker is still written

#### Scenario: Partial migration recovery

    Given .purlin/toolbox/ exists but .migrated_from_release does not
    When the migration script runs
    Then the migration re-runs and overwrites existing toolbox files
    And the marker is written

#### Scenario: Integration with pl-update-purlin

    Given a consumer project has .purlin/release/local_steps.json
    And the Purlin submodule is updated to a version with toolbox support
    When purlin:update runs
    Then step 7c detects the migration need
    And the migration script is executed
    And the update summary reports the migration

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Migration must be tested against real fixture repo scenarios, not just unit tests with synthetic JSON.
- The partial migration recovery path (toolbox dir exists, no marker) is the most fragile edge case — verify it does not corrupt existing toolbox state if the user has already started using the toolbox manually.
