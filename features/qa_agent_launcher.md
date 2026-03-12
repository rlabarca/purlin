# Feature: QA Agent Launcher

> Label: "Tool: QA Agent Launcher"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

Role-specific launcher configuration for the QA agent (`pl-run-qa.sh`). Inherits all shared launcher mechanics from `agent_launchers_common.md`.

---

## 2. Requirements

### 2.1 Tool Restrictions (bypass=false)
*   `--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`

### 2.2 Session Message
*   `"Begin QA verification session."`

### 2.3 Instruction Files
1.  `instructions/HOW_WE_WORK_BASE.md`
2.  `instructions/QA_BASE.md`
3.  `.purlin/HOW_WE_WORK_OVERRIDES.md` (if exists)
4.  `.purlin/QA_OVERRIDES.md` (if exists)

### 2.4 Default Config
When `agents.qa` is absent from the resolved config:
```json
{ "model": "", "effort": "", "bypass_permissions": false }
```

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: QA Launcher Dispatches with Config
    Given the resolved config contains agents.qa with model "claude-sonnet-4-6", effort "medium", bypass_permissions false
    When pl-run-qa.sh is executed
    Then it calls resolve_config.py qa to read agent settings
    And it invokes the claude CLI with --model claude-sonnet-4-6 --effort medium
    And it passes --allowedTools with the QA role restrictions
    And it passes --append-system-prompt-file pointing to the assembled prompt

#### Scenario: QA Launcher Assembles Correct Prompt
    Given instructions/QA_BASE.md exists
    And .purlin/QA_OVERRIDES.md exists
    When pl-run-qa.sh is executed
    Then the session prompt includes HOW_WE_WORK_BASE.md content
    And the session prompt includes QA_BASE.md content
    And the session prompt includes QA_OVERRIDES.md content

### Manual Scenarios (Human Verification Required)
None.
