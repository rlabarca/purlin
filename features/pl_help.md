# Feature: Help Command

> Label: "/pl-help Purlin Help"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

Agents print their command vocabulary table at startup, but there is no way to re-display it mid-session. After a long work session or context compression, the user loses visibility into available commands. `/pl-help` provides a quick way to re-print the command table and discover user-facing CLI scripts at any time.

---

## 2. Requirements

### 2.1 Role Detection

- The skill MUST detect the current agent role (architect, builder, qa) from system prompt markers (e.g., "Role Definition: The Architect").

### 2.2 Branch Detection

- The skill MUST detect the current branch via `git rev-parse --abbrev-ref HEAD`.
- If `.purlin/runtime/active_branch` exists and is non-empty, print the Branch Collaboration Variant.
- Otherwise, print the Main Branch Variant.

### 2.3 Output

- The skill MUST read the role's command table file (`instructions/references/{role}_commands.md`) and print the appropriate variant verbatim.
- No arguments, no side effects. Output only.

### 2.4 Help Output Convention

- Every `pl-*.sh` script in the project root MUST respond to `--help`.
- The `--help` block MUST print a compact help block to stdout: script name (via `basename "$0"`), one-line description, and options list.
- The script MUST exit 0 immediately after printing help.
- The `--help` check MUST appear before any initialization (no Python, no config, no env setup).
- `--help` itself MUST be listed as an option in the help output.
- Scripts with no functional flags still respond to `--help` (showing only `--help` as an option).

### 2.5 CLI Script Discovery

- The skill MUST dynamically discover user-facing scripts by globbing `pl-*.sh` in the project root (`$PURLIN_PROJECT_ROOT` if set, else `git rev-parse --show-toplevel`).
- For each discovered script, the skill MUST run it with `--help` (stderr suppressed, 3-second timeout).
- If a script produces no output or exits non-zero, the skill MUST show it with "(no help -- run pl-init.sh to refresh)" instead of help text.
- The skill MUST NOT hard-code any script names, descriptions, or flags.

### 2.6 Combined Output

- The skill MUST print two sections in order:
  1. **Slash Commands** -- the existing role command table (unchanged behavior from 2.3).
  2. **CLI Scripts** -- discovered script help output, each script's `--help` output displayed sequentially.
- If no `pl-*.sh` scripts are found, the CLI Scripts section MUST print "(no CLI scripts found in project root)".

### 2.7 Distribution

- The skill file lives at `.claude/commands/pl-help.md` and is copied to consumer projects by `tools/init.sh` (glob-based copy of all `*.md` files in `.claude/commands/`). No changes to init or update-purlin are required.

---

## 3. Scenarios

### Unit Tests
#### Scenario: Architect re-displays command table (auto-test-only)

    Given an Architect session on the main branch
    When the user runs /pl-help
    Then the Main Branch Variant from architect_commands.md is printed verbatim

#### Scenario: QA re-displays command table on collaboration branch (auto-test-only)

    Given a QA session with .purlin/runtime/active_branch containing "collab/v2"
    When the user runs /pl-help
    Then the Branch Collaboration Variant from qa_commands.md is printed
    And the header shows [Branch: collab/v2]

#### Scenario: Skill discovers CLI scripts dynamically (auto-test-only)

    Given the project root contains pl-run-builder.sh and pl-cdd-start.sh with --help support
    When the user runs /pl-help
    Then the output includes a "CLI Scripts" section after the slash command table
    And each script's name, description, and options are shown

#### Scenario: Stale launcher without --help (auto-test-only)

    Given pl-run-architect.sh does not support --help
    When the user runs /pl-help
    Then pl-run-architect.sh appears with a refresh note instead of help text

#### Scenario: Agent resolves how-do-I-run question (auto-test-only)

    Given a user asks "how do I start the builder in continuous mode?"
    When the agent invokes /pl-help
    Then the output includes pl-run-builder.sh with --continuous documented

### QA Scenarios
None.
