# Feature: Help Command

> Label: "/pl-help Purlin Help"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

Agents print their command vocabulary table at startup, but there is no way to re-display it mid-session. After a long work session or context compression, the user loses visibility into available commands. `/pl-help` provides a quick way to re-print the command table at any time.

---

## 2. Requirements

### 2.1 Role Detection

- The skill MUST detect the current agent role (architect, builder, qa) from system prompt markers (e.g., "Role Definition: The Architect").

### 2.2 Branch Detection

- The skill MUST detect the current branch via `git rev-parse --abbrev-ref HEAD`.
- If the branch starts with `isolated/`, print the Isolated Session Variant.
- Else if `.purlin/runtime/active_branch` exists and is non-empty, print the Branch Collaboration Variant.
- Otherwise, print the Main Branch Variant.

### 2.3 Output

- The skill MUST read the role's command table file (`instructions/references/{role}_commands.md`) and print the appropriate variant verbatim.
- No arguments, no side effects. Output only.

### 2.4 Distribution

- The skill file lives at `.claude/commands/pl-help.md` and is copied to consumer projects by `tools/init.sh` (glob-based copy of all `*.md` files in `.claude/commands/`). No changes to init or update-purlin are required.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Architect re-displays command table (auto-test-only)

    Given an Architect session on the main branch
    When the user runs /pl-help
    Then the Main Branch Variant from architect_commands.md is printed verbatim

#### Scenario: Builder re-displays command table on isolated branch (auto-test-only)

    Given a Builder session on branch isolated/feat1
    When the user runs /pl-help
    Then the Isolated Session Variant from builder_commands.md is printed
    And the header shows [Isolated: feat1]

#### Scenario: QA re-displays command table on collaboration branch (auto-test-only)

    Given a QA session with .purlin/runtime/active_branch containing "collab/v2"
    When the user runs /pl-help
    Then the Branch Collaboration Variant from qa_commands.md is printed
    And the header shows [Branch: collab/v2]

### Manual Scenarios (Human Verification Required)

None.
