# Feature: CDD Dashboard Skill

> Label: "Skill: CDD Dashboard"
> Category: "Skills"
> Prerequisite: features/cdd_lifecycle.md

[TODO]

## 1. Overview

A shared agent skill (`/pl-cdd`) that lets any agent start, stop, or restart the CDD Dashboard server. The skill is a thin orchestration layer that invokes `start.sh` and `stop.sh` and prints the server URL. It eliminates the need for agents or users to remember port numbers, script paths, or process management commands.

---

## 2. Requirements

### 2.1 Subcommands

| Usage | Description |
|---|---|
| `/pl-cdd` | Start the CDD server (or show URL if already running) |
| `/pl-cdd stop` | Stop the CDD server |
| `/pl-cdd restart` | Stop then start the CDD server |

- Default action (no arguments) is `start`.
- Invalid arguments produce an error listing valid subcommands.

### 2.2 Role Access

Global skill -- available to all roles (architect, builder, qa).

### 2.3 Start Behavior

1. Resolve `PURLIN_PROJECT_ROOT` and `tools_root` from `.purlin/config.json`.
2. Invoke `tools/cdd/start.sh` via Bash. The script handles all restart logic internally (see `cdd_lifecycle.md` Section 2.9): if a server is already running, it stops the existing instance and starts fresh on the same port.
3. Print the output from the script (restart notice if applicable, followed by URL).

### 2.4 Stop Behavior

1. Invoke `tools/cdd/stop.sh` via Bash.
2. Print confirmation message.

### 2.5 Restart Behavior

1. Invoke `stop.sh`, then `start.sh` sequentially.
2. Print the new URL from the start output.

### 2.6 URL Output

The skill prints the full clickable URL exactly as emitted by `start.sh`: `http://localhost:<port>`. No additional wrapping or formatting beyond what the script provides.

### 2.7 Server Persistence

The CDD server persists after the agent session exits. This is already handled by `nohup` in `start.sh`. The skill does not need to manage process lifetime beyond start/stop.

### 2.8 Error Handling

- If `start.sh` fails (non-zero exit), print the error output from the script and advise checking `.purlin/runtime/cdd.log`.
- If `stop.sh` reports "not running", relay the message without treating it as an error.
- Invalid argument: print `Error: Unknown argument '<arg>'. Valid: stop, restart`

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Start when not running

    Given no CDD server is running for this project
    When /pl-cdd is invoked with no arguments
    Then start.sh is executed
    And the CDD server starts
    And the full URL is printed

#### Scenario: Start when already running restarts via start.sh

    Given a CDD server is running for this project on port 9090
    When /pl-cdd is invoked with no arguments
    Then start.sh handles the restart internally
    And "Restarted CDD server on port 9090" is printed
    And "http://localhost:9090" is printed

#### Scenario: Stop a running server

    Given a CDD server is running for this project
    When /pl-cdd stop is invoked
    Then stop.sh is executed
    And the server is terminated
    And a confirmation message is printed

#### Scenario: Restart cycles the server

    Given a CDD server is running for this project
    When /pl-cdd restart is invoked
    Then stop.sh is executed first
    And then start.sh is executed
    And the new URL is printed

#### Scenario: Invalid argument produces error

    Given the skill is invoked
    When /pl-cdd badarg is provided
    Then the output contains "Error: Unknown argument 'badarg'"
    And "Valid: stop, restart" is included

### Manual Scenarios (Human Verification Required)

None.
