# Feature: Agent Launchers (Shared)

> Label: "Tool: Agent Launchers (Shared)"
> Category: "Install, Update & Scripts"
> Prerequisite: features/models_configuration.md (config drives model selection)
> Prerequisite: features/config_layering.md (launcher reads resolved config, not raw config.json)


## 1. Overview
Defines the shared mechanical requirements for all Purlin agent launcher scripts. Each agent role (PM, Engineer, QA, PM) has its own launcher script that follows this common pattern. Role-specific details (tool restrictions, session messages, instruction files) are defined in each role's own launcher feature spec.

Scripts are named `pl-run-<role>.sh` and live at the project root. Currently: `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, and `pl-run-pm.sh`.


## 2. Requirements

### 2.1 Script Names and Location
*   **Naming convention:** `pl-run-<role>.sh` at the project root. All MUST be marked executable (`chmod +x`).
*   **Submodule detection:** Each script MUST check for `$SCRIPT_DIR/purlin/instructions/` and fall back to `$SCRIPT_DIR/instructions/` when not in a submodule consumer context.
*   **Project root export:** Each script MUST export `PURLIN_PROJECT_ROOT="$SCRIPT_DIR"` before invoking the LLM CLI.
*   **Agent role export:** Each script MUST `export AGENT_ROLE="<role>"` (where `<role>` is `architect`, `builder`, `qa`, or `pm`) before invoking `claude`. This env var is consumed by hooks and tools for per-agent configuration resolution.

### 2.2 Prompt Assembly
1.  Create a temporary file via `mktemp`. Register cleanup with `trap "rm -f '$PROMPT_FILE'" EXIT`.
2.  Concatenate in order: `<framework>/instructions/HOW_WE_WORK_BASE.md`, `<framework>/instructions/<ROLE>_BASE.md`.
3.  If `.purlin/HOW_WE_WORK_OVERRIDES.md` exists, append it.
4.  If `.purlin/<ROLE>_OVERRIDES.md` exists, append it.
5.  Each appended file is preceded by `printf "\n\n"` to ensure separation.

### 2.3 Config Reading
*   Read `AGENT_MODEL`, `AGENT_EFFORT`, `AGENT_BYPASS`, `AGENT_FIND_WORK`, `AGENT_AUTO_START`, `AGENT_MODEL_WARNING`, and `AGENT_MODEL_WARNING_DISMISSED` from the **resolved config** using the config resolver CLI (see `config_layering.md` Section 2.1 and 2.2).
*   The generated launcher MUST call `resolve_config.py <role>` (via `$CORE_DIR/tools/config/resolve_config.py`) and `eval` the shell variable assignments it returns. It MUST NOT use an inline `python3 -c "import json; ..."` pattern that reads `config.json` directly.
*   `AGENT_MODEL_WARNING` contains the `warning` field value from the agent's assigned model (empty string if absent). `AGENT_MODEL_WARNING_DISMISSED` is `true` if the model ID appears in the top-level `acknowledged_warnings` array AND the model has `warning_dismissible: true`; `false` otherwise.
*   Default values when the resolver is unavailable or config is absent: `AGENT_MODEL=""`, `AGENT_EFFORT=""`, `AGENT_BYPASS="false"`, `AGENT_FIND_WORK="true"`, `AGENT_AUTO_START="false"`, `AGENT_MODEL_WARNING=""`, `AGENT_MODEL_WARNING_DISMISSED="false"`.

### 2.4 CLI Auto-Update

Before invoking `claude`, every launcher MUST check whether the Claude Code CLI is up to date and update it if needed. This runs after config reading (Section 2.3) and before dispatch (Section 2.5). CLI flags can change between versions, so the update must complete before any `claude` invocation.

*   Run `claude update --check` to test whether an update is available. If the exit code indicates an update is available, run `claude update` to perform the update.
*   Print a status line to stderr: `Checking for Claude Code updates...` before the check. If an update is performed, print `Claude Code updated successfully.` after it completes. If already up to date, print nothing (silent success).
*   If `claude` is not found on `PATH`, skip the update check silently and let the dispatch step fail with a clear error.
*   If `claude update` fails (non-zero exit), print a warning to stderr (`WARNING: Claude Code update failed. Continuing with current version.`) and proceed with the existing version. The launcher MUST NOT exit on update failure.
*   The update check adds a small latency to every launch. This is acceptable because CLI flag compatibility is a correctness requirement, not a performance optimization.

### 2.5 Claude Dispatch
```
claude [--model $AGENT_MODEL] [--effort $AGENT_EFFORT] [--dangerously-skip-permissions | --allowedTools ...] --append-system-prompt-file "$PROMPT_FILE" "<session message>"
```
*   When `AGENT_MODEL_WARNING` is non-empty AND `AGENT_MODEL_WARNING_DISMISSED` is not `true`, the launcher MUST:
    1.  Print to stderr before invoking `claude`:
        ```
        ============================================================
        WARNING: <warning text>
        By continuing, you are acknowledging this warning.
        ============================================================
        ```
    2.  Auto-acknowledge the warning by calling `resolve_config.py acknowledge_warning <model_id>`, which adds the model ID to `acknowledged_warnings` in `config.local.json`. This ensures the warning is shown only once per model.
*   When the warning has been acknowledged (`AGENT_MODEL_WARNING_DISMISSED=true`), no warning is printed and no acknowledgment write occurs.
*   `--model` is passed only when `AGENT_MODEL` is non-empty.
*   `--effort` is passed only when `AGENT_EFFORT` is non-empty.
*   When `AGENT_BYPASS=true`: pass `--dangerously-skip-permissions`.
*   When `AGENT_BYPASS=false`: pass role-specific `--allowedTools` as defined in the role's launcher feature spec.

### 2.6 Role-Specific Details
Each role's launcher feature spec defines:
*   **Tool restrictions** (`--allowedTools` flags when `bypass_permissions` is `false`).
*   **Session message** (trailing positional argument to `claude`).
*   **Instruction files** (role-specific `<ROLE>_BASE.md` and `<ROLE>_OVERRIDES.md`).
*   **Default config values** (fallback when `agents.<role>` is absent from config).

See: `architect_agent_launcher.md`, `builder_agent_launcher.md`, `qa_agent_launcher.md`, `pm_agent_launcher.md`.


## 3. Scenarios

### Unit Tests

#### Scenario: Launcher Exports PURLIN_PROJECT_ROOT
    Given a launcher script is invoked from any working directory
    When any launcher script (pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh, pl-run-pm.sh) is executed
    Then PURLIN_PROJECT_ROOT is exported as the absolute path of the project root

#### Scenario: Launcher Exports AGENT_ROLE
    Given a launcher script is invoked
    When any launcher script is executed
    Then AGENT_ROLE is exported as the corresponding role name
    And the env var is visible to child processes and PostToolUse hooks

#### Scenario: Launcher Reads Resolved Config
    Given config.json and config.local.json exist with agent settings
    When any launcher script is executed
    Then it calls resolve_config.py with its role name to read agent settings
    And it does not read config.json directly via inline Python

#### Scenario: Launcher Prints Warning and Auto-Acknowledges on First Run
    Given the agent's assigned model has a non-empty warning field with warning_dismissible true
    And the model ID is not in the acknowledged_warnings array
    When the launcher script is executed
    Then it prints the warning text to stderr in a bordered block before invoking claude
    And the block includes "By continuing, you are acknowledging this warning."
    And the model ID is added to acknowledged_warnings in config.local.json

#### Scenario: Launcher Suppresses Warning on Subsequent Runs
    Given the agent's assigned model has a non-empty warning field
    And the model ID appears in the acknowledged_warnings array
    And the model has warning_dismissible true
    When the launcher script is executed
    Then no warning is printed to stderr

#### Scenario: Launcher Falls Back When Config is Absent
    Given config.json does not contain an agents section
    And resolve_config.py is unavailable
    When any launcher script is executed
    Then it uses default values (empty model, empty effort, bypass false)

#### Scenario: Launcher Updates Claude CLI When Out of Date

    Given the claude CLI is installed and on PATH
    And claude update --check indicates an update is available
    When any launcher script is executed
    Then "Checking for Claude Code updates..." is printed to stderr
    And claude update is run before the claude session command
    And "Claude Code updated successfully." is printed to stderr after the update

#### Scenario: Launcher Skips Update When Already Current

    Given the claude CLI is installed and on PATH
    And claude update --check indicates the CLI is up to date
    When any launcher script is executed
    Then "Checking for Claude Code updates..." is printed to stderr
    And claude update is NOT run
    And no update message is printed

#### Scenario: Launcher Continues When Update Fails

    Given the claude CLI is installed and on PATH
    And claude update fails with a non-zero exit code
    When any launcher script is executed
    Then a warning is printed to stderr: "WARNING: Claude Code update failed. Continuing with current version."
    And the launcher proceeds to invoke the claude session command

#### Scenario: Launcher Skips Update Check When Claude Not on PATH

    Given the claude command is not found on PATH
    When any launcher script is executed
    Then no update check is attempted
    And the launcher proceeds to the dispatch step

### QA Scenarios

None.
