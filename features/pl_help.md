# Feature: Help Command

> Label: "Agent Skills: Common: /pl-help Purlin Help"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

The Purlin agent does NOT print the command table at startup — it shows `Use /pl-help for commands` instead. `/pl-help` is the **sole owner** of command table display. It prints the unified command table and discovers user-facing CLI scripts on demand.

---

## 2. Requirements

### 2.1 Command Table

- The skill MUST read `references/purlin_commands.md` and print the Default Variant verbatim. This single table shows all modes (Engineer, PM, QA) and common commands.
- No role detection is needed — the Purlin agent uses one unified command table regardless of active mode.
- No arguments, no side effects. Output only.

### 2.2 Help Output Convention

- Every `pl-*.sh` script in the project root MUST respond to `--help`.
- The `--help` block MUST print a compact help block to stdout: script name (via `basename "$0"`), one-line description, and options list.
- The script MUST exit 0 immediately after printing help.
- The `--help` check MUST appear before any initialization (no Python, no config, no env setup).
- `--help` itself MUST be listed as an option in the help output.
- Scripts with no functional flags still respond to `--help` (showing only `--help` as an option).

### 2.3 CLI Script Discovery

- The skill MUST dynamically discover user-facing scripts by globbing `pl-*.sh` in the project root (`$PURLIN_PROJECT_ROOT` if set, else `git rev-parse --show-toplevel`).
- For each discovered script, the skill MUST list the script name.
- The skill MUST NOT hard-code any script names, descriptions, or flags.

### 2.4 Combined Output

- The skill MUST print two sections in order:
  1. **Slash Commands** -- the unified command table from `purlin_commands.md`.
  2. **CLI Scripts** -- discovered script names from the project root.
- If no `pl-*.sh` scripts are found, the CLI Scripts section MUST print "(no CLI scripts found in project root)".

### 2.5 Distribution

- The skill file lives at `.claude/commands/pl-help.md` and is copied to consumer projects by `tools/init.sh` (glob-based copy of all `*.md` files in `.claude/commands/`). No changes to init or update-purlin are required.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Command table file exists and is readable

    Given the project root directory
    When checking for references/purlin_commands.md
    Then the file exists
    And the file contains "Purlin Agent"
    And the file contains "Engineer Mode"
    And the file contains "PM Mode"
    And the file contains "QA Mode"

#### Scenario: CLI scripts are discoverable in project root

    Given the project root directory
    When globbing for pl-*.sh files
    Then at least one pl-*.sh file is found
    And each found file is executable

#### Scenario: CLI scripts respond to --help

    Given pl-run.sh exists in the project root
    When pl-run.sh is invoked with --help
    Then it exits with code 0
    And the output contains "Usage"

### QA Scenarios

#### Scenario: Full help output displays both sections @auto

    Given a Purlin agent session
    When the user runs /pl-help
    Then the output includes the unified command table from purlin_commands.md
    And the output includes a "CLI Scripts" section after the command table
    And the CLI Scripts section lists discovered pl-*.sh files

#### Scenario: Help output with no CLI scripts @auto

    Given a project root with no pl-*.sh scripts
    When the user runs /pl-help
    Then the command table is printed normally
    And the CLI Scripts section shows "(no CLI scripts found in project root)"

### Manual Scenarios (Human Verification Required)

None.
