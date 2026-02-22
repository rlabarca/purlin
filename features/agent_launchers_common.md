# Feature: Agent Launchers (Multi-Provider)

> Label: "Tool: Agent Launchers"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_configuration.md (config drives provider/model selection)


## 1. Overview
Provider-agnostic shell scripts that launch Purlin agents (Architect, Builder, QA) using any supported LLM CLI. The scripts read agent configuration from `config.json`, assemble the layered instruction prompt, and dispatch to the correct CLI. Supported providers are `claude` (Anthropic Claude Code CLI) and `gemini` (Google Gemini CLI).

Scripts are named `run_architect.sh`, `run_builder.sh`, and `run_qa.sh` and live at the project root. They replace the earlier `run_claude_*.sh` scripts.


## 2. Requirements

### 2.1 Script Names and Location
*   **Files:** `run_architect.sh`, `run_builder.sh`, and `run_qa.sh` at the project root. All MUST be marked executable (`chmod +x`).
*   **Submodule detection:** Each script MUST check for `$SCRIPT_DIR/purlin/instructions/` and fall back to `$SCRIPT_DIR/instructions/` when not in a submodule consumer context.
*   **Project root export:** Each script MUST export `AGENTIC_PROJECT_ROOT="$SCRIPT_DIR"` before invoking the LLM CLI.

### 2.2 Prompt Assembly
1.  Create a temporary file via `mktemp`. Register cleanup with `trap "rm -f '$PROMPT_FILE'" EXIT`.
2.  Concatenate in order: `<framework>/instructions/HOW_WE_WORK_BASE.md`, `<framework>/instructions/<ROLE>_BASE.md`.
3.  If `.agentic_devops/HOW_WE_WORK_OVERRIDES.md` exists, append it.
4.  If `.agentic_devops/<ROLE>_OVERRIDES.md` exists, append it.
5.  Each appended file is preceded by `printf "\n\n"` to ensure separation.

### 2.3 Config Reading
*   Read `AGENT_PROVIDER`, `AGENT_MODEL`, `AGENT_EFFORT`, and `AGENT_BYPASS` from `config.json` using the Python one-liner pattern (see `agent_configuration.md` Section 2.4).
*   Default values when config is absent: `AGENT_PROVIDER="claude"`, `AGENT_MODEL=""`, `AGENT_EFFORT=""`, `AGENT_BYPASS="false"`.

### 2.4 Provider Dispatch: Claude
```
claude [--model $AGENT_MODEL] [--effort $AGENT_EFFORT] [--dangerously-skip-permissions | --allowedTools ...] --append-system-prompt-file "$PROMPT_FILE" "<session message>"
```
*   `--model` is passed only when `AGENT_MODEL` is non-empty.
*   `--effort` is passed only when `AGENT_EFFORT` is non-empty.
*   When `AGENT_BYPASS=true`: pass `--dangerously-skip-permissions`.
*   When `AGENT_BYPASS=false`: pass role-specific `--allowedTools` (see Section 2.6).

### 2.5 Provider Dispatch: Gemini
```
GEMINI_SYSTEM_MD="$PROMPT_FILE" gemini -m $AGENT_MODEL --no-gitignore [--yolo]
```
*   `-m $AGENT_MODEL` is always passed (Gemini CLI requires a model flag).
*   `--no-gitignore` is always passed. Gemini CLI respects `.gitignore` by default, which blocks agent access to required generated artifacts (`CRITIC_REPORT.md`, `tests/*/critic.json`, `.agentic_devops/cache/*.json`).
*   When `AGENT_BYPASS=true`: pass `--yolo`.
*   When `AGENT_BYPASS=false`: no `--yolo`; interactive approval is used.
*   **No `-p` flag.** The Gemini CLI `-p` flag enables non-interactive pipe mode — it sends the prompt and exits. Agents require an interactive session. The session kickoff is implicit in the system prompt injected via `GEMINI_SYSTEM_MD`; no separate `-p` argument is needed or permitted.
*   Gemini does NOT support effort levels. If `AGENT_EFFORT` is set, it is silently skipped.
*   Concurrent safety: each launcher instance writes to its own `mktemp` file pointed to by `GEMINI_SYSTEM_MD`, so concurrent invocations do not interfere.
*   No `--allowedTools` equivalent exists for Gemini; tool access is governed by `--yolo` vs. interactive mode.

### 2.6 Role-Specific Tool Restrictions (Claude, bypass=false)
*   **Architect:** `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep"`
*   **Builder:** No `--allowedTools` flag (default permissions, user confirms each tool use).
*   **QA:** `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`

### 2.7 Unsupported Providers
If `AGENT_PROVIDER` is neither `claude` nor `gemini`, the script MUST:
1. Print `ERROR: Provider '$AGENT_PROVIDER' is not yet supported for agent invocation.`
2. Print the list of supported providers.
3. Exit with status code 1.

### 2.8 Session Messages
Session messages are passed as the trailing positional argument to the Claude CLI only.

*   **Architect:** `"Begin Architect session."`
*   **Builder:** `"Begin Builder session."`
*   **QA:** `"Begin QA verification session."`

For the Gemini provider, no session message argument is passed. The `GEMINI_SYSTEM_MD` system prompt already contains the role-specific startup instructions; the Gemini CLI starts interactively without a seed prompt.


## 3. Scenarios

### Automated Scenarios

#### Scenario: Claude Launcher Dispatches with Model and Effort
    Given config.json contains agents.architect with provider "claude", model "claude-sonnet-4-6", effort "high", bypass_permissions false
    When run_architect.sh is executed
    Then it invokes the claude CLI with --model claude-sonnet-4-6 --effort high
    And it passes --allowedTools with the Architect role restrictions
    And it passes --append-system-prompt-file pointing to the assembled prompt

#### Scenario: Gemini Launcher Sets GEMINI_SYSTEM_MD
    Given config.json contains agents.qa with provider "gemini", model "gemini-3.0-pro", bypass_permissions true
    When run_qa.sh is executed
    Then GEMINI_SYSTEM_MD is set to the temporary prompt file path
    And it invokes gemini -m gemini-3.0-pro --no-gitignore --yolo
    And no -p argument is passed to gemini
    And the temporary prompt file is cleaned up on exit

#### Scenario: Gemini Launcher Passes --no-gitignore for All Invocations
    Given config.json contains agents.qa with provider "gemini", model "gemini-2.5-pro", bypass_permissions true
    When run_qa.sh is executed
    Then it invokes gemini with --no-gitignore

#### Scenario: Gemini Launcher Skips Effort Flag
    Given config.json contains agents.builder with provider "gemini", model "gemini-2.5-flash", effort "high"
    When run_builder.sh is executed
    Then it invokes gemini without any effort-related argument

#### Scenario: Concurrent Gemini Launches Do Not Interfere
    Given two concurrent invocations of run_qa.sh both use provider "gemini"
    When both scripts run simultaneously
    Then each invocation uses a distinct GEMINI_SYSTEM_MD file path
    And neither invocation overwrites the other's prompt file

#### Scenario: Unsupported Provider Exits with Error
    Given config.json contains agents.builder with provider "openai"
    When run_builder.sh is executed
    Then it prints an error message listing supported providers (claude, gemini)
    And exits with a non-zero status code

#### Scenario: Launcher Exports AGENTIC_PROJECT_ROOT
    When any launcher script (run_architect.sh, run_builder.sh, run_qa.sh) is executed
    Then AGENTIC_PROJECT_ROOT is exported as the absolute path of the project root

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.


## Implementation Notes

Gemini CLI system context injection uses the `GEMINI_SYSTEM_MD` environment variable (per-process, safe for concurrent agents). This is the canonical method as of Gemini CLI v1.x — no GEMINI.md file required.

The `--yolo` flag is the Gemini CLI equivalent of Claude's `--dangerously-skip-permissions`.

Gemini CLI's `read_file` tool respects `.gitignore` filtering regardless of `--yolo` mode. The `--no-gitignore` flag must be passed unconditionally to allow agents to read generated artifacts (`CRITIC_REPORT.md`, `critic.json` files, `cache/*.json` files) that are correctly excluded from git but required by the startup protocols.

The Gemini CLI `-p` flag enables non-interactive pipe mode: it sends the given prompt, waits for a single response, and exits. This is incompatible with agent sessions, which require a persistent interactive loop. Do NOT pass `-p` or any positional prompt argument when launching Gemini as an agent. The session kickoff is embedded in the system prompt via `GEMINI_SYSTEM_MD`.

These scripts are the standalone versions. Bootstrap-generated equivalents (Section 2.5 of `submodule_bootstrap.md`) are produced by `tools/bootstrap.sh` and follow the same structure with a submodule-specific `CORE_DIR` path.
