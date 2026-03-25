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
*   `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`
*   The Architect's zero-code mandate is enforced by instruction-level constraints in `ARCHITECT_BASE.md`, not by tool-level blocking. The Architect needs Write and Edit access for spec files, instruction files, and process configuration.

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
    And it passes --allowedTools with the Architect role restrictions including Write and Edit
    And it passes --append-system-prompt-file pointing to the assembled prompt

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
