# Feature: Diagnostic Logging and Health Checks

> Label: "Tool: Diagnostic Logging"
> Category: "Install, Update & Scripts"
> Prerequisite: features/test_fixture_repo.md

## 1. Overview

Adds structured error logging and startup health checks to the shell scripts that form the integration boundary between agents and Python tools (`status.sh`, `run.sh`, `start.sh`). Currently, errors at these boundaries are systematically suppressed (redirected to `/dev/null` or swallowed by `|| true`), creating a debugging black hole when agents encounter stale status or missing data. This feature captures diagnostics without changing default behavior.

---

## 2. Requirements

### 2.1 Error Log Capture

- `tools/cdd/status.sh` and `tools/critic/run.sh` MUST redirect suppressed stderr to `.purlin/runtime/purlin.log` instead of `/dev/null`.
- The log file MUST use append mode so that entries accumulate across invocations.
- Each log entry MUST be prefixed with an ISO 8601 timestamp and the script name (e.g., `[2026-03-18T10:30:00Z status.sh]`).
- The log file location (`.purlin/runtime/purlin.log`) respects the submodule safety mandate: all generated artifacts go to `.purlin/runtime/`.
- If `.purlin/runtime/` does not exist, the script MUST create it before writing.
- Error suppression behavior is preserved: errors still do not block execution or produce terminal output by default.

### 2.2 Verbose Mode

- `tools/cdd/status.sh` and `tools/critic/run.sh` MUST accept a `--verbose` flag.
- When `--verbose` is passed, stderr from subprocess calls MUST be tee'd to both the log file and the terminal (stderr).
- When `--verbose` is not passed, behavior is identical to the log-only capture in Section 2.1. No terminal output from suppressed errors.
- The `--verbose` flag MUST NOT conflict with existing flags on these scripts (e.g., `--startup`, `--role`, `--graph`).

### 2.3 CDD Startup Health Check

- After `tools/cdd/start.sh` detects the port file, it MUST verify the server is actually accepting connections.
- The health check MUST send a single HTTP request to `http://localhost:$PORT/status.json` with a 2-second timeout.
- If the health check succeeds (HTTP 200), the startup message MUST indicate the server is confirmed responsive.
- If the health check fails (timeout, connection refused, non-200), a warning MUST be logged to `.purlin/runtime/purlin.log` with the failure reason. The process MUST NOT be killed -- it may still be starting.
- If `curl` is not available on the system, the health check MUST be skipped and the script falls back to the current behavior (port file presence only). No error is reported for missing `curl`.
- The health check runs once, not in a retry loop.

### 2.4 Log Rotation

- No automated log rotation is required. The log file grows unbounded.
- The `purlin.log` path MUST be added to `.gitignore` if not already covered by a `.purlin/runtime/` pattern.

---

## 3. Scenarios

### Unit Tests
#### Scenario: Critic Errors Logged to File

    Given tools/critic/run.sh encounters a Python error during critic execution
    When the script completes
    Then .purlin/runtime/purlin.log contains the error output
    And the log entry includes an ISO 8601 timestamp and script name
    And the script exit code is unchanged from current behavior

#### Scenario: Status Script Errors Logged to File

    Given tools/cdd/status.sh encounters an error from a subprocess
    When the script completes
    Then .purlin/runtime/purlin.log contains the error output
    And the log entry includes an ISO 8601 timestamp and script name

#### Scenario: Verbose Mode Shows Errors on Terminal

    Given tools/cdd/status.sh is invoked with --verbose
    When a subprocess writes to stderr
    Then the stderr output appears on the terminal
    And the stderr output is also written to .purlin/runtime/purlin.log

#### Scenario: Default Mode Suppresses Terminal Error Output

    Given tools/cdd/status.sh is invoked without --verbose
    When a subprocess writes to stderr
    Then no error output appears on the terminal
    And the error is captured in .purlin/runtime/purlin.log

#### Scenario: Health Check Confirms Server Responsive

    Given tools/cdd/start.sh has launched serve.py
    And the port file has been detected
    When the health check sends a request to /status.json
    And the server responds with HTTP 200
    Then the startup message confirms the server is responsive

#### Scenario: Health Check Logs Warning on Failure

    Given tools/cdd/start.sh has launched serve.py
    And the port file has been detected
    When the health check sends a request to /status.json
    And the server does not respond within 2 seconds
    Then a warning is logged to .purlin/runtime/purlin.log
    And the serve.py process is not killed
    And the startup message indicates the server may still be starting

#### Scenario: Health Check Skipped When Curl Unavailable

    Given curl is not available on the system
    When tools/cdd/start.sh detects the port file
    Then the health check is skipped
    And the script falls back to port-file-only detection
    And no error is reported about missing curl

#### Scenario: Log Directory Created If Missing

    Given .purlin/runtime/ does not exist
    When status.sh or run.sh attempts to write to purlin.log
    Then .purlin/runtime/ is created
    And the log entry is written successfully

#### Scenario: Verbose Flag Does Not Conflict With Existing Flags

    Given tools/cdd/status.sh accepts --startup, --role, and --graph flags
    When invoked with --verbose alongside --startup architect
    Then both flags are processed correctly
    And verbose diagnostic output appears on the terminal

### QA Scenarios
None.
