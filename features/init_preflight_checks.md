# Feature: Init Preflight Checks

> Label: "Tool: Init Preflight Checks"
> Category: "Install, Update & Scripts"
> Prerequisite: project_init.md

## 1. Overview

Before running any initialization logic, `tools/init.sh` validates that required and recommended tools are installed. If required tools are missing, the script prints actionable installation commands and exits. If optional tools are missing, the script warns and continues. After successful initialization, the script replaces the current flat file list with a narrative "What's Next" guide that tells first-time users which agent to run and what to expect.

---

## 2. Requirements

### 2.1 Prerequisite Detection

- The script MUST check for `git` before any other operation (required -- blocks init).
- The script MUST check for `claude` (Claude Code CLI) as a recommended tool (warns, continues).
- The script MUST check for `node`/`npx` as an optional tool needed for Playwright MCP (warns, continues).
- Each check uses `command -v <tool>` for detection.
- Preflight MUST run before mode detection (Section 2 of init.sh) so no work is done before validation.

### 2.2 Required Tool Failure

- When a required tool is missing, the script MUST print the tool name, a status marker (e.g., "NOT FOUND"), the installation command, and a documentation URL.
- When multiple tools are missing, the script MUST print ALL missing tools before exiting (do not exit on first failure).
- Installation commands MUST be platform-aware: detect macOS (`uname -s` == "Darwin") vs Linux and suggest `brew install` or `apt-get install` accordingly.
- The script MUST exit with a non-zero code when any required tool is missing.
- The script MUST print a final line: "Fix these and re-run" with the init command.

### 2.3 Recommended/Optional Tool Warnings

- When `claude` is missing, the script MUST print a warning with the install command (`npm install -g @anthropic-ai/claude-code`) and explain that MCP servers will not be installed.
- When `node`/`npx` is missing, the script MUST print a warning explaining Playwright web testing will be unavailable.
- Warnings MUST NOT block initialization.

### 2.4 Post-Init Narrative Output

- After successful full initialization, the script MUST replace the current flat file list (lines 661-694 of init.sh) with a structured "What's Next" narrative.
- The narrative MUST include numbered steps: (1) commit command, (2) which agent to start with and why -- distinguishing "have designs" (PM) vs "have requirements" (PM), (3) what Engineer mode does.
- After successful refresh, the script MUST print an abbreviated refresh summary (not the full numbered narrative).
- The narrative MUST use box-drawing or separator characters to visually stand out from earlier init output.

### 2.5 Quiet Mode Compatibility

- Preflight output MUST respect the existing `--quiet` flag (errors still go to stderr).
- The post-init narrative MUST also respect `--quiet`.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: All prerequisites present

    Given git, claude, and node are installed
    When the user runs init.sh
    Then the preflight section completes without printing warnings
    And initialization proceeds to mode detection

#### Scenario: Git missing blocks init

    Given git is not installed
    When the user runs init.sh
    Then the output includes "git" and "not found" (case-insensitive)
    And the output includes a platform-appropriate install command
    And the script exits with a non-zero code
    And no initialization steps are executed (no .purlin/ created, no files staged)

#### Scenario: Claude CLI missing warns and continues

    Given git is installed
    And claude CLI is not installed
    When the user runs init.sh in full-init mode
    Then the output includes a warning that claude is not found
    And the output includes "npm install -g @anthropic-ai/claude-code"
    And the output notes MCP servers will not be installed
    And initialization completes successfully

#### Scenario: Node missing warns and continues

    Given git and claude are installed
    And node/npx is not installed
    When the user runs init.sh
    Then the output includes a warning that node is not found
    And the output notes Playwright web testing will be unavailable
    And initialization completes successfully

#### Scenario: Multiple tools missing reports all before exit

    Given git and node are both not installed
    When the user runs init.sh
    Then the output lists git as missing with its install command
    And the output lists node as missing with its install command
    And the script exits with a non-zero code (git is required)
    And both missing tools appear in the output before the exit

#### Scenario: Platform detection for install commands

    Given git is not installed
    And the platform is macOS (uname -s returns Darwin)
    When the user runs init.sh
    Then the install suggestion includes "brew install git"

#### Scenario: Post-init narrative on full init

    Given all prerequisites are present
    And the project has not been initialized before
    When init.sh completes full initialization
    Then the output includes a numbered "What's Next" section
    And step 1 mentions "git commit"
    And step 2 mentions "purlin:resume" with a "designs" context
    And step 2 also mentions "purlin:resume" with a "requirements" context

#### Scenario: Post-init narrative on refresh

    Given all prerequisites are present
    And the project has been initialized before
    When init.sh completes refresh
    Then the output includes an abbreviated refresh summary
    And the output does not include the full numbered narrative

#### Scenario: Quiet mode suppresses preflight output

    Given claude is not installed
    When the user runs init.sh --quiet
    Then no preflight warnings appear on stdout
    And initialization completes (git is present)

### Manual Scenarios (Human Verification Required)

None.
