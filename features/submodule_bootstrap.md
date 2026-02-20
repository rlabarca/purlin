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

### 2.10 Config Patching JSON Safety
*   **Comma Preservation:** The `sed` command used to patch `tools_root` in `config.json` (Section 2.3) MUST only replace the value portion of the `"tools_root"` key. It MUST NOT strip trailing commas, closing braces, or any other JSON structural characters. The correct regex replaces only the quoted value between `"tools_root": "` and the next `"`, preserving everything after.
*   **JSON Validation:** After patching `config.json`, the bootstrap script MUST validate that the resulting file is valid JSON by running `python3 -c "import json; json.load(open('<path>'))"` (or equivalent). If validation fails, the script MUST print a descriptive error and exit with a non-zero status code.
*   **Test Coverage:** The bootstrap test (`tools/test_bootstrap.sh`) MUST include a JSON validity assertion on the patched `config.json`. A `grep` for the expected `tools_root` value is necessary but NOT sufficient -- the test MUST also verify JSON parseability.

### 2.11 Project Root Environment Variable
*   **Launcher Export:** All generated launcher scripts (`run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`) MUST export `AGENTIC_PROJECT_ROOT` set to the absolute path of the consumer project root (i.e., `$SCRIPT_DIR`). This variable is the authoritative project root for all tools invoked during the session.
*   **Python Tool Detection:** All Python tools (`tools/critic/critic.py`, `tools/cdd/serve.py`, `tools/software_map/serve.py`, `tools/software_map/generate_tree.py`) MUST check the `AGENTIC_PROJECT_ROOT` environment variable first. If set and the path exists, use it as the project root without climbing. If not set, fall back to directory-climbing detection.
*   **Climbing Priority Reversal:** When using the directory-climbing fallback (no `AGENTIC_PROJECT_ROOT`), Python tools MUST try the FURTHER path first (`../../../.agentic_devops/config.json` -- the submodule layout where `tools/` is 3 levels deep) before the nearer path (`../../.agentic_devops/config.json` -- standalone layout). This prevents the submodule's own `.agentic_devops/` from shadowing the consumer project's config.
*   **Shell Tool Detection:** Shell-based tool scripts (`tools/critic/run.sh`, `tools/cdd/start.sh`, `tools/software_map/start.sh`) MUST check `AGENTIC_PROJECT_ROOT` before falling back to relative path climbing. When set, they MUST derive config paths from `$AGENTIC_PROJECT_ROOT/.agentic_devops/config.json`.

### 2.12 Generated Artifact Isolation
*   **Problem:** Tools currently write log files, PID files, and data caches inside the `tools/` directory tree. When `tools/` lives inside a git submodule, these artifacts dirty the submodule's git state and may cause `git submodule update` conflicts.
*   **Runtime Directory:** Log files and PID files MUST be written to `<project_root>/.agentic_devops/runtime/` instead of alongside the tool scripts:
    - `tools/cdd/cdd.log` -> `.agentic_devops/runtime/cdd.log`
    - `tools/cdd/cdd.pid` -> `.agentic_devops/runtime/cdd.pid`
    - `tools/software_map/software_map.log` -> `.agentic_devops/runtime/software_map.log`
    - `tools/software_map/software_map.pid` -> `.agentic_devops/runtime/software_map.pid`
*   **Cache Directory:** Generated data files MUST be written to `<project_root>/.agentic_devops/cache/` instead of alongside the tool scripts:
    - `tools/cdd/feature_status.json` -> `.agentic_devops/cache/feature_status.json`
    - `tools/software_map/feature_graph.mmd` -> `.agentic_devops/cache/feature_graph.mmd`
    - `tools/software_map/dependency_graph.json` -> `.agentic_devops/cache/dependency_graph.json`
    - `tools/critic/.cache/*.json` -> `.agentic_devops/cache/critic/*.json`
*   **Directory Auto-Creation:** Tools MUST create `runtime/` and `cache/` (and any needed subdirectories) under `.agentic_devops/` if they do not exist.
*   **Gitignore Update:** The bootstrap script's recommended gitignore entries (Section 2.7) MUST include `.agentic_devops/runtime/` and `.agentic_devops/cache/`.

### 2.13 Python Tool Config Resilience
*   **Error Handling:** All Python tools that read `.agentic_devops/config.json` MUST wrap `json.load()` in a `try/except` block handling `json.JSONDecodeError`, `IOError`, and `OSError`.
*   **Fallback Defaults:** On config parse failure, tools MUST fall back to default configuration values (`cdd_port: 8086`, `map_port: 8087`, `tools_root: "tools"`, `critic_llm_enabled: false`) and print a warning to stderr.
*   **No Crash Invariant:** A malformed or missing `config.json` MUST NOT cause any Python tool to crash with an unhandled exception. Tools MUST remain functional with defaults.

### 2.14 Utility Script Project Root Detection
*   **Scope:** `tools/cleanup_orphaned_features.py` and any future utility scripts MUST use the same project root detection as other Python tools (Section 2.11: `AGENTIC_PROJECT_ROOT` env var first, then climbing fallback).
*   **No Hardcoded CWD Paths:** Utility scripts MUST NOT use hardcoded relative directory paths (e.g., `dirs_to_check = ["features"]` relative to CWD). They MUST resolve `features/` relative to the detected project root.

### 2.15 Submodule Simulation Test Infrastructure
*   **Test Harness:** The bootstrap test script (`tools/test_bootstrap.sh`) MUST construct a temporary sandbox that simulates the consumer-project-with-submodule directory layout. The sandbox MUST include:
    - A temporary directory acting as the consumer project root.
    - A git-initialized consumer project (for `git` commands to work).
    - A clone of the current repository placed inside the consumer project at a submodule-like path (e.g., `my-project/agentic-dev/`).
    - Any uncommitted tool/script changes overlaid onto the clone so tests exercise the latest code.
*   **Submodule-Specific Test Scenarios:** The test harness MUST exercise scenarios that are unique to the submodule environment:
    - Config patching produces valid JSON (Section 2.10).
    - Python tools resolve the consumer project root, not the submodule root, via both `AGENTIC_PROJECT_ROOT` and climbing fallback (Section 2.11).
    - Generated artifacts are written to `.agentic_devops/runtime/` and `.agentic_devops/cache/`, not inside the submodule `tools/` directory (Section 2.12).
    - Python tools survive a malformed `config.json` without crashing (Section 2.13).
*   **Sandbox Cleanup:** The test harness MUST clean up all temporary directories on exit (via `trap` or equivalent), even on test failure.
*   **Dual-Layout Coverage:** Where feasible, tests SHOULD run the same assertions in both standalone layout (tools at `<root>/tools/`) and submodule layout (tools at `<root>/agentic-dev/tools/`) to catch layout-dependent regressions.

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

#### Scenario: Config JSON Validity After Bootstrap
    Given agentic-dev-core is added as a submodule at "agentic-dev/"
    And no .agentic_devops/ directory exists at the project root
    When the user runs "agentic-dev/tools/bootstrap.sh"
    Then .agentic_devops/config.json is valid JSON (parseable by python3 json.load)
    And all original key-value pairs from the sample config are preserved
    And the only change is the "tools_root" value

#### Scenario: Launcher Scripts Export Project Root
    Given bootstrap has been run successfully
    When any generated launcher script (run_claude_architect.sh, run_claude_builder.sh, run_claude_qa.sh) is inspected
    Then the script contains an export of AGENTIC_PROJECT_ROOT
    And its value is set to the absolute path of the project root ($SCRIPT_DIR)

#### Scenario: Python Tool Uses AGENTIC_PROJECT_ROOT
    Given AGENTIC_PROJECT_ROOT is set to a valid project root
    And the project root contains .agentic_devops/config.json
    When a Python tool (critic.py, serve.py, generate_tree.py) resolves its project root
    Then it uses $AGENTIC_PROJECT_ROOT as the project root
    And it reads config from $AGENTIC_PROJECT_ROOT/.agentic_devops/config.json

#### Scenario: Python Tool Climbing Prefers Submodule Layout
    Given AGENTIC_PROJECT_ROOT is not set
    And the tool is located at <project_root>/agentic-dev/tools/<tool>/
    And both <project_root>/.agentic_devops/config.json and <project_root>/agentic-dev/.agentic_devops/config.json exist
    When the Python tool uses climbing fallback to find config
    Then it discovers <project_root>/.agentic_devops/config.json (submodule/further path)
    And it does NOT use <project_root>/agentic-dev/.agentic_devops/config.json (standalone/nearer path)

#### Scenario: Generated Artifacts Written Outside Submodule
    Given the project uses agentic-dev-core as a submodule at "agentic-dev/"
    When CDD Monitor, Software Map, or Critic tools produce runtime artifacts
    Then log files and PID files are written to <project_root>/.agentic_devops/runtime/
    And data caches are written to <project_root>/.agentic_devops/cache/
    And no generated files are written inside the agentic-dev/ submodule directory

#### Scenario: Python Tool Survives Malformed Config
    Given .agentic_devops/config.json contains invalid JSON (e.g., missing comma, truncated)
    When a Python tool (critic.py, serve.py, generate_tree.py) starts
    Then it falls back to default configuration values
    And it prints a warning to stderr
    And it does not crash with an unhandled exception

#### Scenario: Cleanup Script Uses Project Root Detection
    Given the project uses agentic-dev-core as a submodule at "agentic-dev/"
    And AGENTIC_PROJECT_ROOT is set to the project root
    When cleanup_orphaned_features.py is run
    Then it scans <project_root>/features/ (not CWD/features/)
    And it does not scan the framework's own features/ directory

#### Scenario: Submodule Simulation Test Sandbox
    Given the test harness creates a temporary consumer project
    And clones the framework repository as a submodule at "agentic-dev/"
    And overlays latest uncommitted scripts onto the clone
    When the test suite runs bootstrap and tool scenarios
    Then all path resolution uses the consumer project root (not the submodule root)
    And the sandbox is cleaned up on exit even if tests fail

## 4. Implementation Notes
*   **Shell Compatibility:** Use `#!/bin/bash` with POSIX-compatible patterns where possible. Avoid bashisms that would fail on older systems.
*   **Temp File Cleanup:** Launcher scripts MUST use `trap "rm -f '$PROMPT_FILE'" EXIT` to ensure cleanup even on error.
*   **Config Patching (sed safety):** The sed regex for `tools_root` must be precise: replace only the value between quotes, not the entire line. Use a pattern like `s|"tools_root": "[^"]*"|"tools_root": "NEW_VALUE"|` which matches the shortest quoted string and preserves trailing commas. Do not require `jq` as a dependency. Always validate the result with `python3 json.load()`.
*   **Idempotent Gitignore:** When appending recommended ignores, check each line before adding to avoid duplicates.
*   **Start Script Climbing:** When `AGENTIC_PROJECT_ROOT` is not set, shell start scripts use a two-step fallback. Note the order was reversed from the original implementation: try submodule path (`$DIR/../../../.agentic_devops/config.json`) first, then standalone path (`$DIR/../../.agentic_devops/config.json`). When `AGENTIC_PROJECT_ROOT` IS set, scripts use `$AGENTIC_PROJECT_ROOT/.agentic_devops/config.json` directly.
*   **Python Climbing Priority:** The climbing order in Python tools was a source of bugs. The standalone path (`../../`) is nearer and matches first, but in submodule mode this resolves to the submodule's own `.agentic_devops/`, not the consumer project's. The fix is: (1) always prefer `AGENTIC_PROJECT_ROOT` if set, (2) when climbing, try the further path (`../../../`) before the nearer path (`../../`).
*   **Artifact Isolation:** The `.agentic_devops/runtime/` and `.agentic_devops/cache/` directories are gitignored. Tools must `os.makedirs(..., exist_ok=True)` before writing. Existing code that reads `feature_status.json` or `dependency_graph.json` from `tools/` subdirectories must be updated to read from the cache directory. The Critic reads `feature_status.json` via `_read_cdd_feature_status()` -- this path must change.
*   **Config Resilience Pattern:** All Python tools should use a shared helper or consistent pattern: `try: CONFIG = json.load(f) except (json.JSONDecodeError, IOError, OSError): print("Warning: ...", file=sys.stderr); CONFIG = {}`. Then use `.get()` with defaults for all config values.
*   **Submodule Simulation Test Architecture:** The existing `test_bootstrap.sh` already creates a sandbox with `setup_sandbox()` that clones the repo and overlays scripts. This sandbox was extended to test the new scenarios (Sections 2.10-2.14). Key additions: (1) After bootstrap, run `python3 -c "import json; json.load(open(...))"` on the patched config.json. (2) Set `AGENTIC_PROJECT_ROOT` and invoke Python tools to verify they use it. (3) Write a malformed config.json and verify tools fall back gracefully. (4) Check that `AGENTIC_PROJECT_ROOT` appears in generated launcher scripts. The sandbox cleanup already uses `trap cleanup_sandbox EXIT` which handles failure cases.
*   **Software Map serve.py Route Update:** When `dependency_graph.json` moved to `.agentic_devops/cache/`, the Software Map serve.py needed a new explicit route for `/dependency_graph.json` requests to serve from the cache directory, since the default static file handler serves from the tool's directory.
*   **Gitignore Test Precision:** The test assertion for "gitignore does not ignore .agentic_devops" was updated from a broad pattern match to an exact-line regex (`^\\.agentic_devops/?$`) to avoid false positives from the new `.agentic_devops/runtime/` and `.agentic_devops/cache/` gitignore entries.
