# Feature: Shared Bootstrap Module

> Label: "Tool: Bootstrap Module"
> Category: "Install, Update & Scripts"
> Prerequisite: features/test_fixture_repo.md

## 1. Overview

> **Migrating:** The plugin migration (`features/plugin_migration.md`) moves this module from `tools/bootstrap.py` to `scripts/mcp/bootstrap.py` and simplifies path detection. The submodule climbing fallback (§2.1 nearer/further disambiguation) is no longer needed — the plugin model provides `${CLAUDE_PLUGIN_ROOT}` directly. The module retains `detect_project_root()`, `load_config()`, and `atomic_write()` APIs but the climbing logic is replaced with a direct `PURLIN_PROJECT_ROOT` or `CLAUDE_PLUGIN_ROOT` lookup.

A shared Python module providing canonical implementations of project root detection, config loading, and atomic file writing. These three patterns are currently duplicated across 24+ files in `tools/`, each containing a near-identical 10-20 line block that can independently drift. The module centralizes the logic so that a fix or enhancement applies everywhere simultaneously.

---

## 2. Requirements

### 2.1 Project Root Detection

- The module MUST export a `detect_project_root(script_dir)` function.
- The function MUST check the `PURLIN_PROJECT_ROOT` environment variable first. If set and the path is a valid directory, return it immediately.
- If the env var is not set or invalid, the function MUST use a climbing fallback: walk up from `script_dir` looking for a `.purlin/` directory marker.
- The climbing fallback MUST be submodule-aware: try the further path (3 levels up from `script_dir`) before the nearer path (2 levels up). This ensures the consumer project root is found before the submodule root.
- **Nested-project disambiguation:** When BOTH the further and nearer candidates contain `.purlin/`, the function MUST check the type of `<nearer>/.git` to determine whether the nearer candidate is a submodule or a standalone repository:
  - If `<nearer>/.git` is a **regular file** (a gitlink, indicating a submodule): prefer the further candidate. This is the normal submodule case — the consumer project root is at the further path.
  - If `<nearer>/.git` is a **directory** (a standalone repository): prefer the nearer candidate. The further candidate's `.purlin/` belongs to an unrelated parent project that happens to contain the Purlin repo in its directory tree.
  - If `<nearer>/.git` does not exist: prefer the further candidate (existing fallback behavior).
- The function MUST return an absolute path.
- If no `.purlin/` directory is found at any candidate, the function MUST fall back to 2 levels up from `script_dir` (preserving current behavior).

### 2.2 Config Loading

- The module MUST export a `load_config(project_root)` function.
- The function MUST delegate to `scripts/mcp/config_engine.py` for the actual resolution logic (layered config: `config.local.json` over `config.json`).
- If the import fails (e.g., broken Python path), the function MUST return a default empty dict rather than raising.

### 2.3 Atomic File Writing

- The module MUST export an `atomic_write(path, data, as_json=False)` function.
- The function MUST create parent directories if they do not exist (`os.makedirs` with `exist_ok=True`).
- The function MUST use the `tempfile.mkstemp` + `os.replace` pattern for atomic writes.
- When `as_json=True`, the function MUST serialize `data` with `json.dump(data, f, indent=2)` followed by a trailing newline.
- When `as_json=False`, the function MUST write `data` as a string directly.
- On failure, the function MUST clean up the temporary file and re-raise the exception.

### 2.4 Callsite Migration

- All 24+ files in `tools/` that contain the inline project root detection pattern MUST be migrated to import from `tools/bootstrap.py`.
- Each callsite replaces its inline 10-20 line block with an import and single function call.
- The duplicated atomic write implementation (`_atomic_write` in `tools/release/manage_step.py`) MUST be replaced with an import from `tools/bootstrap.py`.
- Existing tests MUST continue to pass without modification after migration. No behavioral change is introduced.

### 2.5 Submodule Compatibility

- The module MUST live at `scripts/mcp/bootstrap.py` to preserve layout compatibility.
- No generated artifacts may be written inside `tools/`.
- The module MUST NOT introduce any new external dependencies.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Detect Project Root via Environment Variable

    Given PURLIN_PROJECT_ROOT is set to a valid directory path
    When detect_project_root is called with any script_dir
    Then it returns the PURLIN_PROJECT_ROOT value as an absolute path
    And the climbing fallback is not executed

#### Scenario: Detect Project Root via Climbing Fallback

    Given PURLIN_PROJECT_ROOT is not set
    And a .purlin/ directory exists 3 levels above the script directory
    When detect_project_root is called
    Then it returns the directory containing .purlin/ as an absolute path

#### Scenario: Climbing Fallback Prefers Further Path for Submodule

    Given PURLIN_PROJECT_ROOT is not set
    And a .purlin/ directory exists both 2 levels and 3 levels above the script directory
    And the 2-level-up directory has a .git file (submodule gitlink)
    When detect_project_root is called
    Then it returns the 3-level-up path (consumer project root)
    And the 2-level-up path (submodule root) is not returned

#### Scenario: Climbing Prefers Nearer Path When Standalone Repo Inside Parent Project

    Given PURLIN_PROJECT_ROOT is not set
    And a .purlin/ directory exists both 2 levels and 3 levels above the script directory
    And the 2-level-up directory has a .git directory (standalone repo, not a submodule)
    When detect_project_root is called
    Then it returns the 2-level-up path (the standalone repo root)
    And the 3-level-up path (unrelated parent project) is not returned

#### Scenario: Atomic Write Creates File Atomically

    Given a target file path that does not yet exist
    When atomic_write is called with string data
    Then the file is created with the expected content
    And no partial writes are visible to concurrent readers

#### Scenario: Atomic Write Creates Parent Directories

    Given a target file path whose parent directory does not exist
    When atomic_write is called
    Then the parent directories are created
    And the file is written successfully

#### Scenario: Atomic Write JSON Mode

    Given data as a Python dict
    When atomic_write is called with as_json=True
    Then the file contains JSON formatted with indent=2
    And the file ends with a trailing newline

#### Scenario: Atomic Write Cleans Up on Failure

    Given a target path in a read-only directory
    When atomic_write fails
    Then the temporary file is removed
    And the original exception is re-raised

#### Scenario: Config Loading with Valid Config

    Given a project root with a valid .purlin/config.json
    When load_config is called
    Then it returns the resolved configuration dict

#### Scenario: Config Loading Falls Back on Missing Config

    Given a project root with no .purlin/config.json
    When load_config is called
    Then it returns an empty dict
    And no exception is raised

#### Scenario: Migrated Callsites Preserve Behavior

    Given all 24+ files have been migrated to use bootstrap imports
    When the full test suite is run
    Then all existing tests pass without modification

### Manual Scenarios (Human Verification Required)

None.
