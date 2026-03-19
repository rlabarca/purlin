# Feature: Builder Agent Launcher

> Label: "Tool: Builder Agent Launcher"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

Role-specific launcher configuration for the Builder agent (`pl-run-builder.sh`). Inherits all shared launcher mechanics from `agent_launchers_common.md`.

---

## 2. Requirements

### 2.1 Tool Restrictions (bypass=false)
*   No `--allowedTools` flag (default permissions, user confirms each tool use).

### 2.2 Session Message
*   `"Begin Builder session."`

### 2.3 Instruction Files
1.  `instructions/HOW_WE_WORK_BASE.md`
2.  `instructions/BUILDER_BASE.md`
3.  `.purlin/HOW_WE_WORK_OVERRIDES.md` (if exists)
4.  `.purlin/BUILDER_OVERRIDES.md` (if exists)

### 2.4 Default Config
When `agents.builder` is absent from the resolved config:
```json
{ "model": "", "effort": "", "bypass_permissions": false }
```

### 2.5 Startup Sequence Config
*   The Builder uses `find_work: true` and `auto_start: false` by default, consistent with other agent roles.
*   These values are read from the resolved config via `AGENT_FIND_WORK` and `AGENT_AUTO_START` shell variables (see `agent_launchers_common.md` Section 2.3).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Builder Launcher Dispatches with Config
    Given the resolved config contains agents.builder with model "claude-opus-4-6", effort "high", bypass_permissions true
    When pl-run-builder.sh is executed
    Then it calls resolve_config.py builder to read agent settings
    And it invokes the claude CLI with --model claude-opus-4-6 --effort high
    And it passes --dangerously-skip-permissions
    And it passes --append-system-prompt-file pointing to the assembled prompt

#### Scenario: Builder Launcher Uses Default Permissions When bypass=false
    Given the resolved config contains agents.builder with bypass_permissions false
    When pl-run-builder.sh is executed
    Then it does not pass --allowedTools
    And it does not pass --dangerously-skip-permissions
    And the user is prompted to confirm each tool use

#### Scenario: Builder Launcher Assembles Correct Prompt
    Given instructions/BUILDER_BASE.md exists
    And .purlin/BUILDER_OVERRIDES.md exists
    When pl-run-builder.sh is executed
    Then the session prompt includes HOW_WE_WORK_BASE.md content
    And the session prompt includes BUILDER_BASE.md content
    And the session prompt includes BUILDER_OVERRIDES.md content

### Manual Scenarios (Human Verification Required)
None.
