# Feature: Purlin Worktree Identity

> Label: "Install, Update & Scripts: Purlin Worktree Identity"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_mode_system.md
> Prerequisite: features/purlin_worktree_concurrency.md

## 1. Overview

When the Purlin agent runs in a worktree (via `--worktree`), it needs a short, human-readable label (W1, W2, etc.) to distinguish concurrent sessions at a glance. This label appears in the iTerm badge, terminal title, and Claude session name. The label applies only to the main Purlin agent's worktrees created by `pl-run.sh` -- not to sub-agent worktrees created by the Agent tool's `isolation: "worktree"` mechanism for parallel builds.

This feature also standardizes the badge format: the badge displays the mode name alone (e.g., `Engineer`, not `Purlin: Engineer`), with the worktree label appended in parentheses when running in a worktree.

---

## 2. Requirements

### 2.1 Worktree Label Assignment

- Each main-agent worktree MUST be assigned a sequential label: `W1`, `W2`, `W3`, etc.
- The label MUST be assigned at worktree creation time in `pl-run.sh`.
- The next available number MUST be computed by finding the lowest unused positive integer among active purlin worktrees. Active worktrees are those listed by `git worktree list` with branches matching `purlin-*`.
- Numbers from cleaned-up worktrees MUST be reused (gap-filling), keeping labels small and dense.
- The label MUST be persisted in a file `.purlin_worktree_label` at the worktree root directory, containing only the label string (e.g., `W1`).

### 2.2 Label Scope

- Worktree labels apply only to main Purlin agent worktrees created by `pl-run.sh --worktree` under `.purlin/worktrees/`.
- Sub-agent worktrees (created by the Claude Agent tool with `isolation: "worktree"` for parallel builds, located under `.claude/worktrees/`) MUST NOT receive worktree labels or label files.
- The distinction is directory-based: `.purlin/worktrees/` = labeled, `.claude/worktrees/` = unlabeled.

### 2.3 Badge Format

- The iTerm badge MUST display only the mode name: `Engineer`, `PM`, `QA`, or `Purlin` (open mode).
- The badge MUST NOT prefix the mode name with "Purlin:" or any other qualifier.
- When running in a labeled worktree, the badge MUST append the label in parentheses: e.g., `Engineer (W1)`, `Purlin (W2)`, `QA (W1)`.
- When NOT in a worktree, the badge is the mode name alone: `Engineer`, `PM`, `QA`, `Purlin`.

### 2.4 Terminal Title Format

- The terminal title MUST follow the pattern `<project> - <badge>`.
- `<badge>` is the full badge string including any worktree label.
- Examples: `purlin - Engineer`, `myapp - QA (W1)`, `purlin - Purlin (W2)`.

### 2.5 Claude Session Name

- The `--name` argument passed to the `claude` CLI MUST use the same string as the badge.
- Examples: `Engineer`, `Engineer (W1)`, `Purlin`, `Purlin (W2)`.
- This name appears in the Claude Code resume picker and remote control interfaces.

### 2.6 Identity Updates on Mode Switch

- When the agent switches modes (via `/pl-mode` or skill activation), the badge, title, and session name MUST update to reflect the new mode while preserving the worktree label.
- The agent MUST detect whether it is running in a worktree by checking for `.purlin_worktree_label` in the project root directory.
- If the label file exists, read the label and append ` (<label>)` to the mode name in all identity calls.
- If the label file does not exist, the identity is the mode name alone.

### 2.7 Launcher Identity Sequencing

- `pl-run.sh` MUST compute the display identity AFTER worktree creation so the label is available.
- The identity computation is: `<mode_name>` + (if in worktree: ` (<label>)`).
- `<mode_name>` is `Engineer`, `PM`, `QA`, or `Purlin` (no "Purlin:" prefix).
- The launcher MUST pass this identity to both `set_agent_identity` and the `--name` CLI argument.

### 2.8 Legacy Launcher Exemption

- Role-specific launchers (`pl-run-builder.sh`, `pl-run-architect.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) are NOT affected by this feature. They retain their existing badge format (`Builder`, `Architect`, `QA`, `PM`).
- Only `pl-run.sh` (the unified Purlin launcher) implements worktree labels and the updated badge format.

---

## 3. Scenarios

### Unit Tests

#### Scenario: First worktree gets label W1

    Given no active purlin worktrees exist
    When pl-run.sh is invoked with --worktree
    Then the file .purlin_worktree_label in the worktree root contains "W1"

#### Scenario: Second concurrent worktree gets label W2

    Given one active purlin worktree with label W1
    When pl-run.sh is invoked with --worktree again
    Then the new worktree's .purlin_worktree_label contains "W2"

#### Scenario: Gap-filling reuses cleaned-up numbers

    Given active worktrees with labels W1 and W3 (W2 was cleaned up)
    When pl-run.sh is invoked with --worktree
    Then the new worktree's .purlin_worktree_label contains "W2"

#### Scenario: Badge format without worktree

    Given pl-run.sh is invoked with --mode engineer (no --worktree)
    When the launcher sets terminal identity
    Then set_agent_identity is called with "Engineer"
    And --name is passed as "Engineer"

#### Scenario: Badge format with worktree

    Given pl-run.sh is invoked with --worktree --mode engineer
    And the worktree is assigned label W1
    When the launcher sets terminal identity
    Then set_agent_identity is called with "Engineer (W1)"
    And --name is passed as "Engineer (W1)"

#### Scenario: Open mode badge in worktree

    Given pl-run.sh is invoked with --worktree (no --mode)
    And the worktree is assigned label W1
    When the launcher sets terminal identity
    Then set_agent_identity is called with "Purlin (W1)"
    And --name is passed as "Purlin (W1)"

#### Scenario: Mode switch preserves worktree label

    Given the agent is in a worktree labeled W1 in Engineer mode
    When the user switches to QA mode via /pl-mode qa
    Then the iTerm badge changes to "QA (W1)"
    And the terminal title changes to "<project> - QA (W1)"

#### Scenario: Mode switch without worktree has no label

    Given the agent is running without --worktree in Engineer mode
    When the user switches to QA mode via /pl-mode qa
    Then the iTerm badge changes to "QA"
    And the terminal title changes to "<project> - QA"

#### Scenario: Sub-agent worktrees do not get label files

    Given the agent spawns a sub-agent with isolation: "worktree"
    When the sub-agent worktree is created under .claude/worktrees/
    Then no .purlin_worktree_label file exists in the sub-agent worktree

#### Scenario: Terminal title includes project and badge

    Given pl-run.sh is invoked with --worktree --mode qa in project "myapp"
    And the worktree is assigned label W1
    When the launcher sets terminal identity
    Then the terminal title is "myapp - QA (W1)"

### QA Scenarios

#### Scenario: Badge never uses "Purlin:" prefix @auto

    Given any Purlin agent session (worktree or non-worktree)
    When inspecting pl-run.sh for ROLE_DISPLAY values
    Then no ROLE_DISPLAY value starts with "Purlin:"
    And all values are one of: Purlin, Engineer, PM, QA (optionally followed by " (W<N>)")

#### Scenario: Worktree label file exists in worktree sessions @auto

    Given pl-run.sh was invoked with --worktree
    When the worktree is created
    Then .purlin_worktree_label exists in the worktree root
    And its content matches the pattern "W[0-9]+"

#### Scenario: No label file in non-worktree sessions @auto

    Given pl-run.sh was invoked without --worktree
    When checking the project root
    Then .purlin_worktree_label does NOT exist

#### Scenario: Agent reads label file during mode switch @manual

    Given a running Purlin session in a worktree labeled W1
    When switching from Engineer to PM mode
    Then the badge updates to "PM (W1)"
    And the terminal title updates to "<project> - PM (W1)"

## Regression Guidance
- Verify badge never shows "Purlin: Engineer" (old format) in pl-run.sh or PURLIN_BASE.md
- Verify worktree label survives mode switches within the same session
- Verify label file is NOT created in the main repo when running without --worktree
- Verify role-specific launchers are unaffected (no label files, existing badge format unchanged)
- Verify --name argument to claude CLI matches the badge text exactly
- Verify gap-filling works when middle worktrees are cleaned up
- Verify sub-agent worktrees under .claude/worktrees/ never contain label files
