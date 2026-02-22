# Feature: Python Environment Isolation

> Label: "Tool: Python Environment"
> Category: "Install, Update & Scripts"
> Prerequisite: features/submodule_bootstrap.md

## 1. Overview
Standardizes how all shell scripts in the framework discover and invoke Python. Today, 1 of 6 scripts (`cdd/start.sh`) has ad-hoc venv detection while the other 5 use bare `python3`. This creates a split-brain problem: if a consumer creates a `.venv/` (e.g., to install the optional `anthropic` SDK), only the server script finds it. The Critic, CDD status, bootstrap, and lifecycle test scripts silently use system Python instead.

This feature introduces a shared resolution helper (`tools/resolve_python.sh`) that all scripts source, two dependency manifests (`requirements.txt`, `requirements-optional.txt`) establishing the convention, and migrates all 6 shell scripts to the unified resolution path.

## 2. Requirements

### 2.1 Shared Python Resolution Helper (`tools/resolve_python.sh`)
*   **File Location:** `tools/resolve_python.sh` at the submodule/framework root, alongside `bootstrap.sh`.
*   **Sourceable Design:** The script MUST be designed to be sourced (`. resolve_python.sh` or `source resolve_python.sh`), not executed directly. It MUST NOT contain `set -e`, `set -u`, `exit`, or any construct that would terminate the sourcing script.
*   **Output Variable:** After sourcing, `$PYTHON_EXE` MUST be set to the resolved Python interpreter path.
*   **Resolution Priority:** The helper MUST resolve `$PYTHON_EXE` using the following priority order (first match wins):
    1. `$AGENTIC_PYTHON` environment variable, if set and the path exists and is executable.
    2. `$PURLIN_PROJECT_ROOT/.venv/` — project root venv (requires `$PURLIN_PROJECT_ROOT` to be set).
    3. Climbing detection from the sourcing script's directory: `../../.venv` (standalone layout), then `../../../.venv` (submodule layout). The climbing base MUST be derived from `${BASH_SOURCE[1]}` (the sourcing script's path, not the helper's own path).
    4. System `python3` (via `command -v python3`).
    5. System `python` (via `command -v python`).
*   **Cross-Platform Venv Path:** When checking a `.venv/` directory, the helper MUST check for the platform-appropriate interpreter:
    - Unix (default): `.venv/bin/python3`
    - MSYS / MinGW / Cygwin (detected via `$OSTYPE`): `.venv/Scripts/python.exe`
*   **Diagnostic Output:** When a non-system Python is resolved (priority 1, 2, or 3), the helper MUST print a diagnostic message to stderr: `[resolve_python] Using <source> at <path>`. When falling back to system Python, the helper MUST NOT print any output (silent fallback).
*   **Stderr Only:** All diagnostic output MUST go to stderr (`>&2`). The helper MUST NOT write anything to stdout, as sourcing scripts may capture stdout for JSON output (e.g., `status.sh`).
*   **Auto-Resolve on Source:** The helper MUST call its resolution function automatically at the end of the file, so that sourcing it is sufficient to set `$PYTHON_EXE`.
*   **Approximate Size:** ~35 lines. No external dependencies.

### 2.2 Shell Script Migration
All shell scripts that invoke Python MUST source the shared helper and use `$PYTHON_EXE` instead of bare `python3`. The following 6 scripts MUST be migrated:

| Script | Current Python Invocation | Migration Action |
|--------|--------------------------|------------------|
| `tools/critic/run.sh` | `exec python3 "$SCRIPT_DIR/critic.py"` | Source helper, replace `python3` with `$PYTHON_EXE` |
| `tools/cdd/status.sh` | `exec python3 "$SCRIPT_DIR/serve.py"` | Source helper, replace `python3` with `$PYTHON_EXE` |
| `tools/cdd/start.sh` | Ad-hoc 5-line venv detection block | Remove ad-hoc block, source helper instead |
| `tools/cdd/stop.sh` | No Python invocation | No migration needed (does not invoke Python) |
| `tools/bootstrap.sh` | `python3 -c "import json; ..."` | Source helper, replace `python3` with `$PYTHON_EXE` |
| `tools/cdd/test_lifecycle.sh` | `python3 -c "..."` in helper functions | Source helper, replace `python3` with `$PYTHON_EXE` |

**Source Path Convention:** Each script MUST compute the path to `resolve_python.sh` relative to its own location. For scripts in `tools/<subtool>/`, the path is `"$SCRIPT_DIR/../resolve_python.sh"`. For scripts directly in `tools/`, the path is `"$SCRIPT_DIR/resolve_python.sh"`.

**Ad-Hoc Block Removal:** `tools/cdd/start.sh` MUST remove its existing venv detection block (the `if [ -d "$DIR/../../.venv" ]; then ... fi` construct) and replace it entirely with the shared helper.

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
    anthropic>=0.18.0  # LLM-based logic drift detection (Critic tool)
    ```

### 2.4 Bootstrap Venv Suggestion
After bootstrap completes (Section 8 of `submodule_bootstrap.md`), the summary output MUST include an optional venv setup suggestion if `.venv/` does not already exist at the project root. The suggestion MUST:
*   Be clearly marked as optional (not a required step).
*   Include the correct submodule-relative path to `requirements-optional.txt`.
*   Not cause bootstrap to fail if Python is unavailable or if the user skips venv creation.

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
    Given the script is located at <project_root>/tools/critic/run.sh
    And <project_root>/.venv/bin/python3 exists
    And AGENTIC_PYTHON is not set
    And PURLIN_PROJECT_ROOT is not set
    When tools/critic/run.sh sources tools/resolve_python.sh
    Then $PYTHON_EXE is set to <project_root>/.venv/bin/python3

#### Scenario: resolve_python Climbing Detection (Submodule Layout)
    Given the script is located at <project_root>/agentic-dev/tools/critic/run.sh
    And <project_root>/.venv/bin/python3 exists
    And AGENTIC_PYTHON is not set
    And PURLIN_PROJECT_ROOT is not set
    When tools/critic/run.sh sources tools/resolve_python.sh
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

#### Scenario: Critic run.sh Uses Resolved Python
    Given a .venv/ exists at the project root with python3
    When tools/critic/run.sh is executed
    Then it invokes the Critic using the venv Python interpreter
    And not the system python3

#### Scenario: CDD status.sh Uses Resolved Python
    Given a .venv/ exists at the project root with python3
    When tools/cdd/status.sh is executed
    Then it invokes serve.py using the venv Python interpreter

#### Scenario: CDD start.sh Replaced Ad-Hoc Detection
    Given tools/cdd/start.sh has been migrated
    When the script is inspected
    Then it does not contain the pattern 'if [ -d "$DIR/../../.venv" ]'
    And it sources tools/resolve_python.sh

#### Scenario: Bootstrap Uses Resolved Python for JSON Validation
    Given bootstrap.sh has been migrated
    When bootstrap.sh runs the JSON validation step
    Then it uses $PYTHON_EXE instead of bare python3

#### Scenario: test_lifecycle.sh Uses Resolved Python
    Given test_lifecycle.sh has been migrated
    When the helper functions invoke Python
    Then they use $PYTHON_EXE instead of bare python3

#### Scenario: requirements.txt Exists with No Packages
    Given the framework root is inspected
    When requirements.txt is read
    Then it contains only comment lines
    And no package specifiers are present

#### Scenario: requirements-optional.txt Lists anthropic
    Given the framework root is inspected
    When requirements-optional.txt is read
    Then it contains "anthropic>=0.18.0"

#### Scenario: Bootstrap Prints Venv Suggestion When No Venv Exists
    Given no .venv/ directory exists at the consumer project root
    When bootstrap.sh completes successfully
    Then the summary output includes a venv setup suggestion
    And the suggestion includes the path to requirements-optional.txt

#### Scenario: Bootstrap Omits Venv Suggestion When Venv Exists
    Given .venv/ already exists at the consumer project root
    When bootstrap.sh completes successfully
    Then the summary output does not include a venv setup suggestion

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

## 4. Implementation Notes
See [python_environment.impl.md](python_environment.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
