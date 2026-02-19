# Feature: Submodule Bootstrap

> Label: "Tool: Bootstrap"
> Category: "Initialization & Update"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 6: Layered Instruction Architecture)

## 1. Overview
Initializes a consumer project that has added `agentic-dev-core` as a git submodule. Creates the `.agentic_devops/` override directory, generates launcher scripts, and configures the project for the layered instruction architecture.

## 2. Requirements

### 2.1 Project Root Detection
*   **Script Location:** `tools/bootstrap.sh` (executable, `chmod +x`).
*   **Root Detection:** The script MUST detect the consumer project root as the parent of the directory containing the submodule (i.e., if the submodule is at `<project_root>/agentic-dev/`, the project root is `<project_root>/`). The detection logic MUST work when the script is invoked from any working directory.
*   **Submodule Path:** The script MUST detect the submodule directory name dynamically from its own location (e.g., the grandparent of `tools/bootstrap.sh`).

### 2.2 Guard: Prevent Re-Initialization
*   **Abort Condition:** If `.agentic_devops/` already exists at the project root, the script MUST print an error message and exit with a non-zero status code.
*   **Message:** The error message MUST state that `.agentic_devops/` already exists and suggest removing it if re-initialization is intended.

### 2.3 Override Directory Initialization
*   **Source:** Copy all files from `agentic_devops.sample/` (located in the submodule root) to `<project_root>/.agentic_devops/`.
*   **Config Patching:** After copying, set the `tools_root` value in the copied `config.json` to the correct relative path from the project root to the submodule's `tools/` directory (e.g., `agentic-dev/tools` if the submodule is at `agentic-dev/`).

### 2.4 Upstream SHA Marker
*   **SHA Recording:** Record the current submodule HEAD SHA to `.agentic_devops/.upstream_sha`. This file is used by `sync_upstream.sh` to detect upstream changes.
*   **Format:** Plain text, single line, the full 40-character SHA.

### 2.5 Launcher Script Generation
*   **Files Generated:** `run_claude_architect.sh`, `run_claude_builder.sh`, and `run_claude_qa.sh` at the project root. All MUST be marked executable (`chmod +x`).
*   **Architect Launcher Logic:**
    1. Determine the framework directory (the submodule path) relative to the script's location.
    2. Create a temporary file (cleaned up on exit via `trap`).
    3. Concatenate in order: `<framework>/instructions/HOW_WE_WORK_BASE.md`, `<framework>/instructions/ARCHITECT_BASE.md`, `.agentic_devops/HOW_WE_WORK_OVERRIDES.md` (if exists), `.agentic_devops/ARCHITECT_OVERRIDES.md` (if exists).
    4. Launch `claude --append-system-prompt-file <temp_file>`.
*   **Builder Launcher Logic:** Same concatenation pattern with BUILDER files. Launch with `claude --append-system-prompt-file <temp_file> --dangerously-skip-permissions`.
*   **QA Launcher Logic:** Same concatenation pattern with QA files (`QA_BASE.md`, `QA_OVERRIDES.md`). Launch with `claude --append-system-prompt-file <temp_file>`.
*   **Override Tolerance:** If an override file does not exist, the launcher MUST skip it silently (no error).

### 2.6 Project Scaffolding
*   **Features Directory:** Create `features/` at the project root if it does not exist.
*   **Process History:** Create a starter `PROCESS_HISTORY.md` at the project root if it does not exist. The starter file MUST contain a header and a single entry documenting the bootstrap.

### 2.7 Gitignore Guidance
*   **Warning:** If `.agentic_devops` appears in the project's `.gitignore`, the script MUST print a warning that `.agentic_devops/` should be tracked (committed) and NOT gitignored.
*   **Recommended Ignores:** If no `.gitignore` exists, create one with recommended ignores (OS files, Python artifacts, tool logs/pids). If `.gitignore` exists, append recommended ignores that are not already present.
*   **Critical Constraint:** The script MUST NOT add `.agentic_devops` to `.gitignore`.

### 2.8 Summary Output
*   **Completion Message:** On success, print a summary listing all files and directories created, and next steps (e.g., "Run `./run_claude_architect.sh` to start the Architect agent").

### 2.9 Tool Start Script Config Discovery (Submodule-Aware)
*   **Scope:** `tools/cdd/start.sh` and `tools/software_map/start.sh` MUST be updated to support the submodule directory layout.
*   **Current Behavior:** Both scripts look for config at `$DIR/../../.agentic_devops/config.json` (the standalone path, where `$DIR` is the tool's directory).
*   **Required Behavior:** If the standalone path does not exist, the scripts MUST try the submodule path at `$DIR/../../../.agentic_devops/config.json` (one level higher, for when tools are at `<project_root>/agentic-dev/tools/cdd/`).
*   **Fallback:** If neither config file is found, the scripts MUST use their existing default port values.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Bootstrap a Fresh Consumer Project
    Given agentic-dev-core is added as a submodule at "agentic-dev/"
    And no .agentic_devops/ directory exists at the project root
    When the user runs "agentic-dev/tools/bootstrap.sh"
    Then .agentic_devops/ is created with ARCHITECT_OVERRIDES.md, BUILDER_OVERRIDES.md, QA_OVERRIDES.md, HOW_WE_WORK_OVERRIDES.md, and config.json
    And config.json contains "tools_root": "agentic-dev/tools"
    And .agentic_devops/.upstream_sha contains the current submodule HEAD SHA
    And run_claude_architect.sh, run_claude_builder.sh, and run_claude_qa.sh exist at the project root
    And all launcher scripts are executable
    And features/ directory exists at the project root
    And PROCESS_HISTORY.md exists at the project root

#### Scenario: Prevent Double Initialization
    Given .agentic_devops/ already exists at the project root
    When the user runs "agentic-dev/tools/bootstrap.sh"
    Then the script exits with a non-zero status
    And an error message is printed

#### Scenario: Launcher Script Concatenation Order
    Given bootstrap has been run successfully
    When run_claude_architect.sh is executed
    Then the system prompt file contains HOW_WE_WORK_BASE.md content first
    Then ARCHITECT_BASE.md content second
    Then HOW_WE_WORK_OVERRIDES.md content third (if it exists)
    Then ARCHITECT_OVERRIDES.md content fourth (if it exists)

#### Scenario: QA Launcher Script Concatenation Order
    Given bootstrap has been run successfully
    When run_claude_qa.sh is executed
    Then the system prompt file contains HOW_WE_WORK_BASE.md content first
    Then QA_BASE.md content second
    Then HOW_WE_WORK_OVERRIDES.md content third (if it exists)
    Then QA_OVERRIDES.md content fourth (if it exists)

#### Scenario: Gitignore Warning
    Given .agentic_devops is listed in the project's .gitignore
    When the user runs bootstrap.sh
    Then a warning is printed that .agentic_devops should be tracked

#### Scenario: Tool Start Script Config Discovery (Submodule Layout)
    Given the project uses agentic-dev-core as a submodule at "agentic-dev/"
    And .agentic_devops/config.json exists at the project root with cdd_port 8086
    When tools/cdd/start.sh is run
    Then it discovers the config at the submodule-relative path
    And starts the server on port 8086

#### Scenario: Tool Start Script Config Discovery (Standalone Layout)
    Given agentic-dev-core is used standalone (not as a submodule)
    And .agentic_devops/config.json exists with cdd_port 9086
    When tools/cdd/start.sh is run
    Then it discovers the config at the standard path
    And starts the server on port 9086

## 4. Implementation Notes
*   **Shell Compatibility:** Use `#!/bin/bash` with POSIX-compatible patterns where possible. Avoid bashisms that would fail on older systems.
*   **Temp File Cleanup:** Launcher scripts MUST use `trap "rm -f '$PROMPT_FILE'" EXIT` to ensure cleanup even on error.
*   **Config Patching:** Use `sed` or a simple JSON-aware approach to set `tools_root` in the copied config.json. Do not require `jq` as a dependency.
*   **Idempotent Gitignore:** When appending recommended ignores, check each line before adding to avoid duplicates.
*   **Start Script Climbing:** The config discovery logic in start scripts uses a simple two-step fallback: try `$DIR/../../.agentic_devops/config.json` first (standalone), then `$DIR/../../../.agentic_devops/config.json` (submodule). This mirrors the existing Python scripts' climbing logic.
