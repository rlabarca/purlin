# Feature: Architect Agent Launcher

> Label: "Tool: Architect Agent Launcher"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

Role-specific launcher configuration for the Architect agent (`pl-run-architect.sh`). Inherits all shared launcher mechanics from `agent_launchers_common.md`.

---

## 2. Requirements

### 2.1 Tool Restrictions (bypass=false)
*   `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep"`
*   `--disallowedTools "Write,Edit,NotebookEdit"` -- enforces zero-code mandate at the CLI level.

### 2.1.1 Hook Fallback for Tool Enforcement
*   A `PreToolUse` hook in `.claude/settings.json` MUST check the `AGENT_ROLE` environment variable.
*   When `AGENT_ROLE` is `architect`, the hook blocks `Write`, `Edit`, and `NotebookEdit` tool calls (exit code 2).
*   The hook is a fallback for environments where `--disallowedTools` is not supported or bypassed.

### 2.2 Session Message
*   `"Begin Architect session."`

### 2.3 Instruction Files
1.  `instructions/HOW_WE_WORK_BASE.md`
2.  `instructions/ARCHITECT_BASE.md`
3.  `.purlin/HOW_WE_WORK_OVERRIDES.md` (if exists)
4.  `.purlin/ARCHITECT_OVERRIDES.md` (if exists)

### 2.4 Default Config
When `agents.architect` is absent from the resolved config:
```json
{ "model": "", "effort": "", "bypass_permissions": false }
```

### 2.5 Startup Sequence Config
*   The Architect uses `find_work: true` and `auto_start: false` by default, consistent with other agent roles.
*   These values are read from the resolved config via `AGENT_FIND_WORK` and `AGENT_AUTO_START` shell variables (see `agent_launchers_common.md` Section 2.3).

---

## 3. Scenarios

### Unit Tests
#### Scenario: Architect Launcher Dispatches with Config
    Given the resolved config contains agents.architect with model "claude-sonnet-4-6", effort "high", bypass_permissions false
    When pl-run-architect.sh is executed
    Then it calls resolve_config.py architect to read agent settings
    And it invokes the claude CLI with --model claude-sonnet-4-6 --effort high
    And it passes --allowedTools with the Architect role restrictions
    And it passes --disallowedTools "Write,Edit,NotebookEdit"
    And it passes --append-system-prompt-file pointing to the assembled prompt

#### Scenario: Architect Launcher Blocks Write Tool via disallowedTools
    Given pl-run-architect.sh includes --disallowedTools "Write,Edit,NotebookEdit"
    When the Architect session attempts to use the Write tool
    Then the CLI blocks the tool call
    And no file is written

#### Scenario: Hook Fallback Blocks Write When AGENT_ROLE is Architect
    Given .claude/settings.json contains a PreToolUse hook checking AGENT_ROLE
    And AGENT_ROLE is set to "architect"
    When the Architect session attempts to use the Edit tool
    Then the hook exits with code 2
    And the tool call is blocked

#### Scenario: Architect Launcher Falls Back When Config is Missing
    Given config.json does not contain an agents.architect section
    When pl-run-architect.sh is executed
    Then it uses default values (empty model, empty effort, bypass_permissions false)
    And find_work defaults to true
    And auto_start defaults to false

#### Scenario: Architect Launcher Assembles Correct Prompt
    Given instructions/ARCHITECT_BASE.md exists
    And .purlin/ARCHITECT_OVERRIDES.md exists
    When pl-run-architect.sh is executed
    Then the session prompt includes HOW_WE_WORK_BASE.md content
    And the session prompt includes ARCHITECT_BASE.md content
    And the session prompt includes ARCHITECT_OVERRIDES.md content

### QA Scenarios
None.
