# Feature: Agent Config Skill

> Label: "/pl-agent-config Agent Configuration"
> Category: "Agent Skills"
> Prerequisite: features/cdd_agent_configuration.md
> Prerequisite: features/config_layering.md

[TODO]

## 1. Overview

The `/pl-agent-config` skill provides the ONLY sanctioned way for agents to modify agent configuration. It writes to `.purlin/config.local.json` (the gitignored local config), never to the committed `config.json`. Because the local config is gitignored, no git commit is made after changes.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-agent-config [<role>] <key> <value>
```

- **role** (optional): `architect`, `builder`, or `qa`. If omitted, the current agent infers its own role from instruction context.
- **key**: A dot-path key within the role's config block (e.g., `find_work`, `model`, `effort`, `bypass_permissions`, `auto_start`).
- **value**: The new value. Booleans are accepted as `true`/`false`. String values are accepted as-is.

**Examples:**
```
/pl-agent-config find_work false                   # sets for current role
/pl-agent-config architect model claude-opus-4-6
/pl-agent-config builder auto_start true
/pl-agent-config effort high                      # sets for current role
```

### 2.2 Key Validation

The skill MUST reject unknown keys with a clear error. Valid keys for any role are:

- `model` -- must match an `id` in the `models` array in config. When the matched model has a `warning` field and the model ID is NOT in `acknowledged_warnings`, the warning text MUST be displayed in the confirmation output AND the model ID is auto-acknowledged (added to `acknowledged_warnings` in `config.local.json`). See Section 2.5.
- `effort` -- must be one of `low`, `medium`, `high`
- `find_work` -- must be `true` or `false`
- `auto_start` -- must be `true` or `false`
- `bypass_permissions` -- must be `true` or `false`
- `qa_mode` -- must be `true` or `false`. Builder-only. When `true`, the Builder runs in QA mode (verification-focused session). See `builder_qa_mode.md`.

### 2.3 Atomic Write

The skill writes config changes atomically:

1. Read the current config JSON from the target path (MAIN local config).
2. Update the specified key within the role's block.
3. Write to a temp file first, then rename to final path.

### 2.4 No Commit (Gitignored File)

Because `config.local.json` is gitignored, no git commit is made after writing. The skill confirms the change with a status message but does not invoke any git commands.

### 2.5 Warning Display and Auto-Acknowledgment on Model Change

When the `model` key is set and the matched model has a non-empty `warning` field:

*   **First time (model ID NOT in `acknowledged_warnings`):** The confirmation output MUST include the warning text. If the model has `warning_dismissible: true`, the model ID is automatically added to `acknowledged_warnings` in `config.local.json` (creating the array if absent, deduplicating). The user does not need to take any additional action -- acknowledgment is implicit in setting the model.

    ```
    Updated: agents.<role>.model = <model_id>
    Config:  <LOCAL_CONFIG_PATH>

    WARNING: <warning text>
    ```

*   **Previously acknowledged (model ID in `acknowledged_warnings`):** The warning is omitted from the confirmation output.

*   **Non-dismissible (`warning_dismissible: false`):** The warning is always displayed in the confirmation output regardless of `acknowledged_warnings`, and the array is not modified.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Config Change Applied to Local Config

    Given the current branch is main
    And .purlin/config.local.json has find_work true for builder
    When /pl-agent-config builder find_work false is invoked
    Then .purlin/config.local.json has find_work false for builder
    And .purlin/config.json is unchanged
    And no git commit is made

#### Scenario: Invalid Key Rejected

    Given a valid .purlin/config.json exists at the project root
    When /pl-agent-config builder unknown_key value is invoked
    Then the skill exits with an error listing valid keys
    And no config file is modified

#### Scenario: Invalid Model Value Rejected

    Given the config models array contains only claude-sonnet-4-6 and claude-haiku-4-5
    When /pl-agent-config architect model claude-gpt-5 is invoked
    Then the skill exits with an error listing valid model IDs
    And no config file is modified

#### Scenario: Setting Model With Warning Shows Warning and Auto-Acknowledges
    Given the models array contains a model with a warning field and warning_dismissible true
    And the model ID is not in acknowledged_warnings
    When /pl-agent-config architect model <model_id> is invoked
    Then the confirmation output includes the warning text
    And the model ID is added to acknowledged_warnings in config.local.json

#### Scenario: Setting Model With Previously Acknowledged Warning Omits Warning
    Given the models array contains a model with a warning field and warning_dismissible true
    And the model ID is in the acknowledged_warnings array
    When /pl-agent-config architect model <model_id> is invoked
    Then the confirmation output does not include the warning text

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Implementation Notes

**No commit needed:** Because `config.local.json` is gitignored, the previous `git add + git commit` step is eliminated. The skill simply writes the file and confirms the change to the user.

**Role inference:** When no role argument is given, the agent uses its own role (e.g., the Architect sets `architect` keys by default). The role must be validated against `[architect, builder, qa]`.
