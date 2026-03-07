# Feature: Context Guard Skill

> Label: "/pl-context-guard Context Guard"
> Category: "Agent Skills"
> Prerequisite: features/context_guard.md
> Prerequisite: features/config_layering.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

[TODO]

## 1. Overview

A shared agent skill (`/pl-context-guard`) that lets any agent view, enable/disable, and adjust the context guard threshold for any role. Changes are persisted to `config.local.json` (gitignored) and are immediately reflected in the CDD Dashboard's Agent Config section on the next auto-refresh cycle. The skill follows the same config-write patterns as `/pl-agent-config`.

---

## 2. Requirements

### 2.1 Subcommands

The skill supports three subcommands:

| Subcommand | Usage | Description |
|---|---|---|
| `status` | `/pl-context-guard [<role>]` | Show current guard state and threshold for the specified role (or all roles if omitted) |
| `set` | `/pl-context-guard <role> <threshold>` | Set the threshold for a role (integer 5-200) |
| `on` / `off` | `/pl-context-guard <role> on` or `/pl-context-guard <role> off` | Enable or disable the guard for a role |

**Argument parsing rules:**
- When only a role is provided (no second arg): treat as `status` for that role.
- When no arguments are provided: treat as `status` for all roles.
- When the second argument is an integer: treat as `set`.
- When the second argument is `on` or `off`: treat as enable/disable.

### 2.2 Status Output

**All roles (no argument):**
```
Context Guard Status
────────────────────
  architect:  ON   45 turns
  builder:    ON   30 turns
  qa:         OFF  45 turns

  Global default: 45 turns
```

**Single role:**
```
Context Guard: architect
  Enabled:    true
  Threshold:  45 turns  (per-agent)
```

The `(per-agent)` annotation appears when the threshold comes from `agents.<role>.context_guard_threshold`. When falling back to the global value, show `(global default)` instead.

### 2.3 Set Threshold

- Validates the value is an integer in the range 5-200.
- If out of range, abort: `Error: Threshold must be an integer between 5 and 200. Got: <value>`
- Writes to `agents.<role>.context_guard_threshold` in `config.local.json`.

### 2.4 Enable / Disable

- `/pl-context-guard <role> on` sets `agents.<role>.context_guard` to `true`.
- `/pl-context-guard <role> off` sets `agents.<role>.context_guard` to `false`.

### 2.5 Config Write Protocol

Follows the same protocol as `/pl-agent-config`:

1. **Target:** Always `config.local.json` in the MAIN project root. Never the worktree copy.
2. **Copy-on-first-access:** If `config.local.json` does not exist, copy `config.json` to it before writing.
3. **Atomic write:** Write to temp file, then rename.
4. **No git commit:** `config.local.json` is gitignored.
5. **Worktree warning:** When invoked from an `isolated/*` branch, display the same worktree context warning as `/pl-agent-config` and require confirmation before proceeding.

### 2.6 Confirmation Output

After a successful write, print:

```
Updated: agents.<role>.<key> = <value>
Config:  <path>/config.local.json
```

### 2.7 CDD Dashboard Reflection

Changes made by this skill are persisted to `config.local.json`, which is the same file the CDD Dashboard reads via the config resolver. The Dashboard's 5-second auto-refresh cycle will pick up the new values and update the Context Guard column (checkbox state and threshold number) without any additional coordination.

### 2.8 Role Validation

Valid roles: `architect`, `builder`, `qa`. If an invalid role is provided, abort:
```
Error: Unknown role '<role>'. Must be one of: architect, builder, qa
```

### 2.9 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/pl_context_guard/mixed-thresholds` | Project with different context guard thresholds and enabled states per role |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Status with no arguments shows all roles

    Given config.local.json has architect context_guard true threshold 45, builder context_guard true threshold 30, qa context_guard false threshold 45
    When /pl-context-guard is invoked with no arguments
    Then the output shows all three roles with their enabled state and threshold
    And the global default threshold is displayed

#### Scenario: Status for single role shows per-agent annotation

    Given agents.builder.context_guard_threshold is 30 in config.local.json
    And the global context_guard_threshold is 45
    When /pl-context-guard builder is invoked
    Then the output shows "Threshold: 30 turns (per-agent)"

#### Scenario: Status shows global default annotation when no per-agent threshold

    Given agents.architect does not have context_guard_threshold set
    And the global context_guard_threshold is 45
    When /pl-context-guard architect is invoked
    Then the output shows "Threshold: 45 turns (global default)"

#### Scenario: Set threshold persists to config.local.json

    Given config.local.json exists with default values
    When /pl-context-guard builder 30 is invoked
    Then config.local.json contains agents.builder.context_guard_threshold as 30
    And confirmation output shows "Updated: agents.builder.context_guard_threshold = 30"

#### Scenario: Set threshold rejects out-of-range value

    Given config.local.json exists
    When /pl-context-guard architect 300 is invoked
    Then the output contains "Error: Threshold must be an integer between 5 and 200"
    And config.local.json is unchanged

#### Scenario: Disable guard for a role

    Given config.local.json has agents.qa.context_guard as true
    When /pl-context-guard qa off is invoked
    Then config.local.json contains agents.qa.context_guard as false
    And confirmation output shows "Updated: agents.qa.context_guard = false"

#### Scenario: Enable guard for a role

    Given config.local.json has agents.qa.context_guard as false
    When /pl-context-guard qa on is invoked
    Then config.local.json contains agents.qa.context_guard as true
    And confirmation output shows "Updated: agents.qa.context_guard = true"

#### Scenario: Invalid role rejected

    Given config.local.json exists
    When /pl-context-guard admin 30 is invoked
    Then the output contains "Error: Unknown role 'admin'"

#### Scenario: Copy-on-first-access when config.local.json missing

    Given config.local.json does not exist
    And config.json exists with default values
    When /pl-context-guard builder 25 is invoked
    Then config.local.json is created as a copy of config.json
    And agents.builder.context_guard_threshold is set to 25

#### Scenario: Dashboard reflects threshold change from skill (auto-web)

    Given the CDD Dashboard is running with the Agents section expanded
    And the builder Context Guard threshold shows 45
    When config.local.json is modified to set agents.builder.context_guard_threshold to 30
    Then within 5 seconds the Dashboard's builder threshold input updates to 30

#### Scenario: Dashboard reflects guard toggle from skill (auto-web)

    Given the CDD Dashboard is running with the Agents section expanded
    And the qa Context Guard checkbox is checked
    When config.local.json is modified to set agents.qa.context_guard to false
    Then within 5 seconds the Dashboard's qa Context Guard checkbox becomes unchecked
    And the qa threshold input becomes disabled with opacity 0.4

### Manual Scenarios (Human Verification Required)

None.
