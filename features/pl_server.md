# Feature: Dev Server Management

> Label: "Agent Skills: Engineer: /pl-server Dev Server Management"
> Category: "Agent Skills: Engineer"

[TODO]

## 1. Overview

A shared skill for Engineer and QA that manages dev server processes during web test verification. Handles port availability checking, alternate port selection, server state tracking via `.purlin/runtime/dev_server.json`, cleanup guarantees on session end, and stale server detection from previous sessions.

---

## 2. Requirements

### 2.1 Role Gating

- Engineer mode owns the command. QA mode can invoke `/pl-server` to start/stop servers for verification (cross-mode: run-only) but cannot modify application code.
- Non-Engineer/QA agents MUST receive a redirect message.

### 2.2 Starting a Dev Server

- Check port availability before starting.
- Select alternate port if occupied (default + 100).
- Start using the feature's `> Web Start:` command if available.
- Announce to user with URL and PID.

### 2.3 State Tracking

- Write server PID and port to `.purlin/runtime/dev_server.json`.
- This file is gitignored (runtime artifact).

### 2.4 Cleanup Guarantee

- On verification complete: stop server and remove state file.
- On session end: check state file, kill tracked PID if still running.
- On session start: detect stale servers from previous sessions, warn user.

### 2.5 Stopping a Dev Server

- Read state file, kill tracked PID, remove state file, print confirmation.

### 2.6 Safety Rules

- NEVER manage persistent or production servers.
- NEVER kill processes not tracked in `dev_server.json`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer/QA invocation

    Given a PM agent session
    When the agent invokes /pl-server
    Then the command responds with a redirect message

#### Scenario: Port conflict selects alternate port

    Given port 3000 is already in use
    When /pl-server starts a dev server with default port 3000
    Then port 3100 is selected instead
    And the user is informed of the alternate port

#### Scenario: State file tracks running server

    Given a dev server is started on port 3000 with PID 12345
    When the server is running
    Then .purlin/runtime/dev_server.json contains pid 12345 and port 3000

#### Scenario: Stale server detected on session start

    Given dev_server.json exists from a previous session
    And the tracked PID is still running
    When a new session starts
    Then a warning about the stale server is displayed
    And the user is asked whether to kill it

#### Scenario: Cleanup stops server and removes state

    Given a dev server is tracked in dev_server.json
    When /pl-server stop is invoked
    Then the tracked PID is killed
    And dev_server.json is removed

### QA Scenarios

None.
