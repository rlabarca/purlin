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

A shared agent skill (`/pl-context-guard`) that lets any agent view and toggle the context guard on or off for any role. Changes are persisted to `config.local.json` (gitignored) and are immediately reflected in the CDD Dashboard's Agent Config section on the next auto-refresh cycle. The skill follows the same config-write patterns as `/pl-agent-config`.

---

## 2. Requirements

### 2.1 Subcommands

The skill supports two subcommands:

| Subcommand | Usage | Description |
|---|---|---|
| `status` | `/pl-context-guard [<role>]` | Show current guard state for the specified role (or all roles if omitted) |
| `on` / `off` | `/pl-context-guard <role> on` or `/pl-context-guard <role> off` | Enable or disable the guard for a role |

**Argument parsing rules:**
- When only a role is provided (no second arg): treat as `status` for that role.
- When no arguments are provided: treat as `status` for all roles.
- When the second argument is `on` or `off`: treat as enable/disable.

### 2.2 Status Output

**All roles (no argument):**
```
Context Guard Status
────────────────────
  architect:  ON
  builder:    ON
  qa:         OFF
```

**Single role:**
```
Context Guard: architect
  Enabled:    true
```

### 2.3 Enable / Disable

- `/pl-context-guard <role> on` sets `agents.<role>.context_guard` to `true`.
- `/pl-context-guard <role> off` sets `agents.<role>.context_guard` to `false`.

### 2.4 Config Write Protocol

Follows the same protocol as `/pl-agent-config`:

1. **Target:** Always `config.local.json` in the project root.
2. **Copy-on-first-access:** If `config.local.json` does not exist, copy `config.json` to it before writing.
3. **Atomic write:** Write to temp file, then rename.
4. **No git commit:** `config.local.json` is gitignored.

### 2.5 Confirmation Output

After a successful write, print:

```
Updated: agents.<role>.context_guard = <value>
Config:  <path>/config.local.json
```

### 2.6 CDD Dashboard Reflection

Changes made by this skill are persisted to `config.local.json`, which is the same file the CDD Dashboard reads via the config resolver. The Dashboard's 5-second auto-refresh cycle will pick up the new values and update the Context Guard checkbox without any additional coordination.

### 2.7 Role Validation

Valid roles: `architect`, `builder`, `qa`. If an invalid role is provided, abort:
```
Error: Unknown role '<role>'. Must be one of: architect, builder, qa
```

### 2.8 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/pl_context_guard/mixed-states` | Project with different context guard enabled states per role |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Status with no arguments shows all roles

    Given config.local.json has architect context_guard true, builder context_guard true, qa context_guard false
    When /pl-context-guard is invoked with no arguments
    Then the output shows all three roles with their enabled state (ON or OFF)

#### Scenario: Status for single role shows enabled state

    Given agents.builder.context_guard is true in config.local.json
    When /pl-context-guard builder is invoked
    Then the output shows "Enabled: true"

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
    When /pl-context-guard admin on is invoked
    Then the output contains "Error: Unknown role 'admin'"

#### Scenario: Copy-on-first-access when config.local.json missing

    Given config.local.json does not exist
    And config.json exists with default values
    When /pl-context-guard builder off is invoked
    Then config.local.json is created as a copy of config.json
    And agents.builder.context_guard is set to false

#### Scenario: Dashboard reflects guard toggle from skill (auto-web)

    Given the CDD Dashboard is running with the Agents section expanded
    And the qa Context Guard checkbox is checked
    When config.local.json is modified to set agents.qa.context_guard to false
    Then within 5 seconds the Dashboard's qa Context Guard checkbox becomes unchecked

### Manual Scenarios (Human Verification Required)

None.
