# Feature: Python Environment Isolation

> Label: "Tool: Python Environment"
> Category: "Install, Update & Scripts"
> Prerequisite: features/project_init.md

## 1. Overview

> **Superseded:** The plugin migration (`features/plugin_migration.md`) replaces per-invocation Python resolution with a persistent MCP server (`scripts/mcp/purlin_server.py`). The MCP server starts once per session and the Python interpreter is resolved at server startup — `resolve_python.sh` and the shell script sourcing pattern are no longer needed. The dependency manifests (`requirements.txt`, `requirements-optional.txt`) remain valid as documentation of the stdlib-only constraint.

Standardizes how all shell scripts in the framework discover and invoke Python. Shell scripts that invoke Python use bare `python3`, which ignores any project-level `.venv/`. If a consumer creates a `.venv/` (e.g., to install the optional `anthropic` SDK), scripts silently use system Python instead.

This feature introduces a shared resolution helper (`tools/resolve_python.sh`) that all scripts source, two dependency manifests (`requirements.txt`, `requirements-optional.txt`) establishing the convention, and migrates shell scripts to the unified resolution path.

## 2. Requirements

### 2.1 Shared Python Resolution Helper (`tools/resolve_python.sh`)
*   **File Location:** `tools/resolve_python.sh` at the submodule/framework root, alongside `init.sh`.
*   **Sourceable Design:** The script MUST be designed to be sourced (`. resolve_python.sh` or `source resolve_python.sh`), not executed directly. It MUST NOT contain `set -e`, `set -u`, `exit`, or any construct that would terminate the sourcing script.
*   **Output Variable:** After sourcing, `$PYTHON_EXE` MUST be set to the resolved Python interpreter path.
*   **Resolution Priority:** The helper MUST resolve `$PYTHON_EXE` using the following priority order (first match wins):
    1. `$AGENTIC_PYTHON` environment variable, if set and the path exists and is executable.
    2. `$PURLIN_PROJECT_ROOT/.venv/` — project root venv (requires `$PURLIN_PROJECT_ROOT` to be set).
    3. Climbing detection from the sourcing script's directory: `../../../.venv` (submodule layout) first, then `../../.venv` (standalone layout). The submodule path is checked first because it is farther from the script and represents the consumer project root, which is the higher-priority context per the Submodule Compatibility Mandate (further path before nearer path). The climbing base MUST be derived from `${BASH_SOURCE[1]}` (the sourcing script's path, not the helper's own path).
    4. System `python3` (via `command -v python3`).
    5. System `python` (via `command -v python`).
*   **Cross-Platform Venv Path:** When checking a `.venv/` directory, the helper MUST check for the platform-appropriate interpreter:
    - Unix (default): `.venv/bin/python3`
    - MSYS / MinGW / Cygwin (detected via `$OSTYPE`): `.venv/Scripts/python.exe`
*   **Diagnostic Output:** When a non-system Python is resolved (priority 1, 2, or 3), the helper MUST print a diagnostic message to stderr: `[resolve_python] Using <source> at <path>`. When falling back to system Python, the helper MUST NOT print any output (silent fallback).
*   **Stderr Only:** All diagnostic output MUST go to stderr (`>&2`). The helper MUST NOT write anything to stdout, as sourcing scripts may capture stdout for JSON output (e.g., `scan.sh`).
*   **Auto-Resolve on Source:** The helper MUST call its resolution function automatically at the end of the file, so that sourcing it is sufficient to set `$PYTHON_EXE`.
*   **Approximate Size:** ~35 lines. No external dependencies.

### 2.2 Shell Script Migration
All shell scripts that invoke Python MUST source the shared helper and use `$PYTHON_EXE` instead of bare `python3`. The following scripts MUST be migrated:

| Script | Current Python Invocation | Migration Action |
|--------|--------------------------|------------------|
| `tools/cdd/scan.sh` | `exec python3 "$SCRIPT_DIR/scan.py"` | Source helper, replace `python3` with `$PYTHON_EXE` |
| `tools/init.sh` | `python3 -c "import json; ..."` (JSON validation) | Source helper, replace `python3` with `$PYTHON_EXE` |

**Source Path Convention:** Each script MUST compute the path to `resolve_python.sh` relative to its own location. For scripts in `tools/<subtool>/`, the path is `"$SCRIPT_DIR/../resolve_python.sh"`. For scripts directly in `tools/`, the path is `"$SCRIPT_DIR/resolve_python.sh"`.

### 2.3 Dependency Manifests
Two dependency manifest files MUST be created at the framework/submodule root (alongside `README.md` and `tools/`):

*   **`requirements.txt`:** Contains only a comment header establishing the convention. The framework has zero required Python dependencies (stdlib only). The file MUST NOT list any packages.
    ```
    # Purlin: No required Python dependencies.
    # All tools use Python stdlib only.
    # See requirements-optional.txt for optional dependencies.
    ```
*   **`requirements-optional.txt`:** Lists optional dependencies with minimum version pins.
    ```
    # Optional dependencies for Purlin.
    # Install with: pip install -r requirements-optional.txt
    anthropic>=0.18.0  # LLM-based analysis features
    ```

### 2.4 Init Venv Suggestion
After `tools/init.sh` full-init completes (Section 2.3 of `project_init.md`), the summary output MUST include an optional venv setup suggestion if `.venv/` does not already exist at the project root. The suggestion MUST:
*   Be clearly marked as optional (not a required step).
*   Include the correct submodule-relative path to `requirements-optional.txt`.
*   Not cause init to fail if Python is unavailable or if the user skips venv creation.

Example output:
```
  (Optional) Set up a Python virtual environment for optional dependencies:
    python3 -m venv .venv
    .venv/bin/pip install -r <submodule>/requirements-optional.txt
```

## 3. Scenarios

### Automated Scenarios

#### Scenario: resolve_python Uses AGENTIC_PYTHON Override
    Given AGENTIC_PYTHON is set to a valid Python interpreter path
    And a .venv/ exists at the project root
    When a script sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to the value of $AGENTIC_PYTHON
    And the .venv/ is not used

#### Scenario: resolve_python Finds Project Root Venv via PURLIN_PROJECT_ROOT
    Given PURLIN_PROJECT_ROOT is set to a valid project root
    And $PURLIN_PROJECT_ROOT/.venv/bin/python3 exists
    And AGENTIC_PYTHON is not set
    When a script sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to $PURLIN_PROJECT_ROOT/.venv/bin/python3

#### Scenario: resolve_python Climbing Detection (Standalone Layout)
    Given the script is located at <project_root>/tools/cdd/scan.sh
    And <project_root>/.venv/bin/python3 exists
    And AGENTIC_PYTHON is not set
    And PURLIN_PROJECT_ROOT is not set
    When tools/cdd/scan.sh sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to <project_root>/.venv/bin/python3

#### Scenario: resolve_python Climbing Detection (Submodule Layout)
    Given the script is located at <project_root>/purlin/tools/cdd/scan.sh
    And <project_root>/.venv/bin/python3 exists
    And AGENTIC_PYTHON is not set
    And PURLIN_PROJECT_ROOT is not set
    When tools/cdd/scan.sh sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to <project_root>/.venv/bin/python3

#### Scenario: resolve_python Falls Back to System Python
    Given no .venv/ exists at any detectable location
    And AGENTIC_PYTHON is not set
    And PURLIN_PROJECT_ROOT is not set
    When a script sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to the system python3 path
    And no diagnostic output is printed to stderr

#### Scenario: resolve_python Diagnostic Output to Stderr Only
    Given a .venv/ exists at the project root
    When a script sources tools/resolve_python.sh
    Then a diagnostic message is printed to stderr containing "[resolve_python]"
    And stdout is empty (no pollution of JSON output)

#### Scenario: CDD scan.sh Uses Resolved Python
    Given a .venv/ exists at the project root with python3
    When tools/cdd/scan.sh is executed
    Then it invokes scan.py using the venv Python interpreter

#### Scenario: Init Uses Resolved Python for JSON Validation
    Given tools/init.sh has been migrated
    When init.sh runs the JSON validation step
    Then it uses $PYTHON_EXE instead of bare python3

#### Scenario: requirements.txt Exists with No Packages
    Given the framework root is inspected
    When requirements.txt is read
    Then it contains only comment lines
    And no package specifiers are present

#### Scenario: requirements-optional.txt Lists anthropic
    Given the framework root is inspected
    When requirements-optional.txt is read
    Then it contains "anthropic>=0.18.0"

#### Scenario: Init Prints Venv Suggestion When No Venv Exists
    Given no .venv/ directory exists at the consumer project root
    When tools/init.sh completes full-init successfully
    Then the summary output includes a venv setup suggestion
    And the suggestion includes the path to requirements-optional.txt

#### Scenario: Init Omits Venv Suggestion When Venv Exists
    Given .venv/ already exists at the consumer project root
    When tools/init.sh completes full-init successfully
    Then the summary output does not include a venv setup suggestion

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

