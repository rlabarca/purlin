# Feature: Diagnostic Logging

> Label: "Tool: Diagnostic Logging"
> Category: "Install, Update & Scripts"
> Prerequisite: test_fixture_repo.md

## 1. Overview

Adds structured error logging to the shell scripts that form the integration boundary between agents and Python tools (`scan.sh`). Currently, errors at these boundaries are systematically suppressed (redirected to `/dev/null` or swallowed by `|| true`), creating a debugging black hole when agents encounter stale status or missing data. This feature captures diagnostics without changing default behavior.

---

## 2. Requirements

### 2.1 Error Log Capture

- `tools/cdd/scan.sh` MUST redirect suppressed stderr to `.purlin/runtime/purlin.log` instead of `/dev/null`.
- The log file MUST use append mode so that entries accumulate across invocations.
- Each log entry MUST be prefixed with an ISO 8601 timestamp and the script name (e.g., `[2026-03-18T10:30:00Z scan.sh]`).
- The log file location (`.purlin/runtime/purlin.log`) respects the submodule safety mandate: all generated artifacts go to `.purlin/runtime/`.
- If `.purlin/runtime/` does not exist, the script MUST create it before writing.
- Error suppression behavior is preserved: errors still do not block execution or produce terminal output by default.

### 2.2 Verbose Mode

- `tools/cdd/scan.sh` MUST accept a `--verbose` flag.
- When `--verbose` is passed, stderr from subprocess calls MUST be tee'd to both the log file and the terminal (stderr).
- When `--verbose` is not passed, behavior is identical to the log-only capture in Section 2.1. No terminal output from suppressed errors.
- The `--verbose` flag MUST NOT conflict with existing flags on these scripts (e.g., `--startup`, `--role`, `--graph`).

### 2.3 Log Rotation

- No automated log rotation is required. The log file grows unbounded.
- The `purlin.log` path MUST be added to `.gitignore` if not already covered by a `.purlin/runtime/` pattern.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Status Script Errors Logged to File

    Given tools/cdd/scan.sh encounters an error from a subprocess
    When the script completes
    Then .purlin/runtime/purlin.log contains the error output
    And the log entry includes an ISO 8601 timestamp and script name

#### Scenario: Verbose Mode Shows Errors on Terminal

    Given tools/cdd/scan.sh is invoked with --verbose
    When a subprocess writes to stderr
    Then the stderr output appears on the terminal
    And the stderr output is also written to .purlin/runtime/purlin.log

#### Scenario: Default Mode Suppresses Terminal Error Output

    Given tools/cdd/scan.sh is invoked without --verbose
    When a subprocess writes to stderr
    Then no error output appears on the terminal
    And the error is captured in .purlin/runtime/purlin.log

#### Scenario: Log Directory Created If Missing

    Given .purlin/runtime/ does not exist
    When scan.sh attempts to write to purlin.log
    Then .purlin/runtime/ is created
    And the log entry is written successfully

#### Scenario: Verbose Flag Does Not Conflict With Existing Flags

    Given tools/cdd/scan.sh accepts --startup, --role, and --graph flags
    When invoked with --verbose alongside --startup architect
    Then both flags are processed correctly
    And verbose diagnostic output appears on the terminal

### Manual Scenarios (Human Verification Required)

None.
