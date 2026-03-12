# Feature: Agent Launchers (Shared)

> Label: "Tool: Agent Launchers (Shared)"
> Category: "Install, Update & Scripts"
> Prerequisite: features/models_configuration.md (config drives model selection)
> Prerequisite: features/config_layering.md (launcher reads resolved config, not raw config.json)


## 1. Overview
Defines the shared mechanical requirements for all Purlin agent launcher scripts. Each agent role (Architect, Builder, QA, PM) has its own launcher script that follows this common pattern. Role-specific details (tool restrictions, session messages, instruction files) are defined in each role's own launcher feature spec.

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
*   Read `AGENT_MODEL`, `AGENT_EFFORT`, `AGENT_BYPASS`, `AGENT_STARTUP`, and `AGENT_RECOMMEND` from the **resolved config** using the config resolver CLI (see `config_layering.md` Section 2.1 and 2.2).
*   The generated launcher MUST call `resolve_config.py <role>` (via `$CORE_DIR/tools/config/resolve_config.py`) and `eval` the shell variable assignments it returns. It MUST NOT use an inline `python3 -c "import json; ..."` pattern that reads `config.json` directly.
*   Default values when the resolver is unavailable or config is absent: `AGENT_MODEL=""`, `AGENT_EFFORT=""`, `AGENT_BYPASS="false"`, `AGENT_STARTUP="true"`, `AGENT_RECOMMEND="true"`.

### 2.4 Claude Dispatch
```
claude [--model $AGENT_MODEL] [--effort $AGENT_EFFORT] [--dangerously-skip-permissions | --allowedTools ...] --append-system-prompt-file "$PROMPT_FILE" "<session message>"
```
*   `--model` is passed only when `AGENT_MODEL` is non-empty.
*   `--effort` is passed only when `AGENT_EFFORT` is non-empty.
*   When `AGENT_BYPASS=true`: pass `--dangerously-skip-permissions`.
*   When `AGENT_BYPASS=false`: pass role-specific `--allowedTools` as defined in the role's launcher feature spec.

### 2.5 Role-Specific Details
Each role's launcher feature spec defines:
*   **Tool restrictions** (`--allowedTools` flags when `bypass_permissions` is `false`).
*   **Session message** (trailing positional argument to `claude`).
*   **Instruction files** (role-specific `<ROLE>_BASE.md` and `<ROLE>_OVERRIDES.md`).
*   **Default config values** (fallback when `agents.<role>` is absent from config).

See: `architect_agent_launcher.md`, `builder_agent_launcher.md`, `qa_agent_launcher.md`, `pm_agent_launcher.md`.


## 3. Scenarios

### Automated Scenarios

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

#### Scenario: Launcher Falls Back When Config is Absent
    Given config.json does not contain an agents section
    And resolve_config.py is unavailable
    When any launcher script is executed
    Then it uses default values (empty model, empty effort, bypass false)

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.
