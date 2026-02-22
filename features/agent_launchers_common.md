# Feature: Agent Launchers

> Label: "Tool: Agent Launchers"
> Category: "Install, Update & Scripts"
> Prerequisite: features/models_configuration.md (config drives model selection)


## 1. Overview
Shell scripts that launch Purlin agents (Architect, Builder, QA) using the Claude CLI. The scripts read agent configuration from `config.json`, assemble the layered instruction prompt, and dispatch to Claude.

Scripts are named `run_architect.sh`, `run_builder.sh`, and `run_qa.sh` and live at the project root.


## 2. Requirements

### 2.1 Script Names and Location
*   **Files:** `run_architect.sh`, `run_builder.sh`, and `run_qa.sh` at the project root. All MUST be marked executable (`chmod +x`).
*   **Submodule detection:** Each script MUST check for `$SCRIPT_DIR/purlin/instructions/` and fall back to `$SCRIPT_DIR/instructions/` when not in a submodule consumer context.
*   **Project root export:** Each script MUST export `PURLIN_PROJECT_ROOT="$SCRIPT_DIR"` before invoking the LLM CLI.

### 2.2 Prompt Assembly
1.  Create a temporary file via `mktemp`. Register cleanup with `trap "rm -f '$PROMPT_FILE'" EXIT`.
2.  Concatenate in order: `<framework>/instructions/HOW_WE_WORK_BASE.md`, `<framework>/instructions/<ROLE>_BASE.md`.
3.  If `.purlin/HOW_WE_WORK_OVERRIDES.md` exists, append it.
4.  If `.purlin/<ROLE>_OVERRIDES.md` exists, append it.
5.  Each appended file is preceded by `printf "\n\n"` to ensure separation.

### 2.3 Config Reading
*   Read `AGENT_MODEL`, `AGENT_EFFORT`, and `AGENT_BYPASS` from `config.json` using the Python one-liner pattern (see `models_configuration.md` Section 2.2).
*   Default values when config is absent: `AGENT_MODEL=""`, `AGENT_EFFORT=""`, `AGENT_BYPASS="false"`.

### 2.4 Claude Dispatch
```
claude [--model $AGENT_MODEL] [--effort $AGENT_EFFORT] [--dangerously-skip-permissions | --allowedTools ...] --append-system-prompt-file "$PROMPT_FILE" "<session message>"
```
*   `--model` is passed only when `AGENT_MODEL` is non-empty.
*   `--effort` is passed only when `AGENT_EFFORT` is non-empty.
*   When `AGENT_BYPASS=true`: pass `--dangerously-skip-permissions`.
*   When `AGENT_BYPASS=false`: pass role-specific `--allowedTools` (see Section 2.5).

### 2.5 Role-Specific Tool Restrictions (bypass=false)
*   **Architect:** `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep"`
*   **Builder:** No `--allowedTools` flag (default permissions, user confirms each tool use).
*   **QA:** `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`

### 2.6 Session Messages
Session messages are passed as the trailing positional argument to the Claude CLI.

*   **Architect:** `"Begin Architect session."`
*   **Builder:** `"Begin Builder session."`
*   **QA:** `"Begin QA verification session."`


## 3. Scenarios

### Automated Scenarios

#### Scenario: Claude Launcher Dispatches with Model and Effort
    Given config.json contains agents.architect with model "claude-sonnet-4-6", effort "high", bypass_permissions false
    When run_architect.sh is executed
    Then it invokes the claude CLI with --model claude-sonnet-4-6 --effort high
    And it passes --allowedTools with the Architect role restrictions
    And it passes --append-system-prompt-file pointing to the assembled prompt

#### Scenario: Launcher Exports PURLIN_PROJECT_ROOT
    Given a launcher script is invoked from any working directory
    When any launcher script (run_architect.sh, run_builder.sh, run_qa.sh) is executed
    Then PURLIN_PROJECT_ROOT is exported as the absolute path of the project root

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.


## Implementation Notes

### Launcher Config Reading
Launchers use inline Python to parse nested JSON from config.json. The Python block is wrapped in `eval "$(python3 -c '...')"` to set shell variables. No `provider` field is read — Claude is implicit.

### These scripts are the standalone versions.
Bootstrap-generated equivalents (Section 2.3 of `submodule_bootstrap.md`) are produced by `tools/bootstrap.sh` and follow the same structure with a submodule-specific `CORE_DIR` path.
