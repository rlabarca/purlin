# Feature: Purlin Worktree Identity

> Label: "Tool: Purlin Worktree Identity"
> Category: "Framework Core"
> Prerequisite: purlin_mode_system.md
> Prerequisite: purlin_worktree_concurrency.md

## 1. Overview

When the Purlin agent runs in a worktree (via `--worktree`), it needs a short, human-readable label (W1, W2, etc.) to distinguish concurrent sessions at a glance. This label appears in the iTerm badge, terminal title, and Claude session name. The label applies only to the main Purlin agent's worktrees created by `purlin:resume` -- not to sub-agent worktrees created by the Agent tool's `isolation: "worktree"` mechanism for parallel builds.

This feature also standardizes the badge format: the badge displays the mode name alone (e.g., `Engineer`, not `Purlin: Engineer`), with the worktree label appended in parentheses when running in a worktree.

---

## 2. Requirements

### 2.1 Worktree Label Assignment

- Each main-agent worktree MUST be assigned a sequential label: `W1`, `W2`, `W3`, etc.
- The label MUST be assigned at worktree creation time in `purlin:resume`.
- The next available number MUST be computed by finding the lowest unused positive integer among active purlin worktrees. Active worktrees are those listed by `git worktree list` with branches matching `purlin-*`.
- Numbers from cleaned-up worktrees MUST be reused (gap-filling), keeping labels small and dense.
- The label MUST be persisted in a file `.purlin_worktree_label` at the worktree root directory, containing only the label string (e.g., `W1`).
- `.purlin_worktree_label` MUST be listed in the project's `.gitignore` to prevent it from being committed during auto-commit (e.g., by the SessionEnd merge hook's `git add -A`).

### 2.2 Label Scope

- Worktree labels apply only to main Purlin agent worktrees created by `purlin:resume --worktree` under `.purlin/worktrees/`.
- Sub-agent worktrees (created by the Claude Agent tool with `isolation: "worktree"` for parallel builds, located under `.claude/worktrees/`) MUST NOT receive worktree labels or label files.
- The distinction is directory-based: `.purlin/worktrees/` = labeled, `.claude/worktrees/` = unlabeled.

### 2.3 Unified Identity Format

All terminal environments (badge, title, Warp tab) and the remote session name use the unified format:

```
<short_mode>(<context>) | <label>
```

- **Mode shortening:** `Engineer` -> `Eng`; `PM`, `QA`, `Purlin` unchanged.
- **Context:** Worktree label when in a worktree (e.g., `W1`), otherwise the branch name.
- **Label:** Project name by default; long-running skills may replace with a task description.
- **Worktree examples:** `Eng(W1) | purlin`, `QA(W2) | purlin`, `Purlin(W1) | purlin`.
- **Non-worktree examples:** `Eng(main) | purlin`, `PM(feature-xyz) | purlin`.

### 2.4 Identity Updates on Mode Switch

- When the agent switches modes (via `purlin:mode` or skill activation), all identity layers MUST update to reflect the new mode while preserving the worktree label or branch context.
- The agent MUST detect whether it is running in a worktree by checking for `.purlin_worktree_label` in the project root directory.
- If the label file exists, read the label and append ` (<label>)` to the mode name in all identity calls.
- If the label file does not exist, the identity is the mode name alone.

### 2.7 Session Entry Point Identity Sequencing

- `purlin:resume` MUST compute the display identity AFTER worktree creation so the label is available.
- The identity computation is: `<mode_name>` + (if in worktree: ` (<label>)`).
- `<mode_name>` is `Engineer`, `PM`, `QA`, or `Purlin` (no "Purlin:" prefix).
- The session entry point MUST pass this identity to both `set_agent_identity` and the session name mechanism.

### [RETIRED] 2.8 Legacy Launcher Exemption

This section described exemptions for the old role-specific shell launchers. Those launchers have been fully retired. The `purlin:resume` skill is the sole session entry point and implements worktree labels and the updated badge format.

---

## 3. Scenarios

### Unit Tests

#### Scenario: First worktree gets label W1

    Given no active purlin worktrees exist
    When purlin:resume is invoked with --worktree
    Then the file .purlin_worktree_label in the worktree root contains "W1"

#### Scenario: Second concurrent worktree gets label W2

    Given one active purlin worktree with label W1
    When purlin:resume is invoked with --worktree again
    Then the new worktree's .purlin_worktree_label contains "W2"

#### Scenario: Gap-filling reuses cleaned-up numbers

    Given active worktrees with labels W1 and W3 (W2 was cleaned up)
    When purlin:resume is invoked with --worktree
    Then the new worktree's .purlin_worktree_label contains "W2"

#### Scenario: Badge format without worktree

    Given purlin:resume is invoked with --mode engineer (no --worktree)
    And the current branch is "main" and project is "purlin"
    When the session entry point sets terminal identity
    Then the terminal identity is "Eng(main) | purlin"

#### Scenario: Identity format with worktree

    Given purlin:resume is invoked with --worktree --mode engineer
    And the worktree is assigned label W1 and project is "purlin"
    When the session entry point sets terminal identity
    Then the terminal identity is "Eng(W1) | purlin"

#### Scenario: Open mode identity in worktree

    Given purlin:resume is invoked with --worktree (no --mode)
    And the worktree is assigned label W1 and project is "purlin"
    When the session entry point sets terminal identity
    Then the terminal identity is "Purlin(W1) | purlin"

#### Scenario: Mode switch preserves worktree label

    Given the agent is in a worktree labeled W1 in Engineer mode
    When the user switches to QA mode via purlin:mode qa
    Then the terminal identity changes to "QA(W1) | <project>"

#### Scenario: Mode switch without worktree uses branch

    Given the agent is running without --worktree in Engineer mode on branch "main"
    When the user switches to QA mode via purlin:mode qa
    Then the terminal identity changes to "QA(main) | <project>"

#### Scenario: Sub-agent worktrees do not get label files

    Given the agent spawns a sub-agent with isolation: "worktree"
    When the sub-agent worktree is created under .claude/worktrees/
    Then no .purlin_worktree_label file exists in the sub-agent worktree

#### Scenario: Terminal identity includes project in worktree

    Given purlin:resume is invoked with --worktree --mode qa in project "myapp"
    And the worktree is assigned label W1
    When the session entry point sets terminal identity
    Then the terminal identity is "QA(W1) | myapp"

### QA Scenarios

#### Scenario: Badge never uses "Purlin:" prefix @auto

    Given any Purlin agent session (worktree or non-worktree)
    When inspecting purlin:resume for ROLE_DISPLAY values
    Then no identity string starts with "Purlin:"
    And all identity strings match the unified format "<short_mode>(<context>) | <label>"

#### Scenario: Worktree label file exists in worktree sessions @auto

    Given purlin:resume was invoked with --worktree
    When the worktree is created
    Then .purlin_worktree_label exists in the worktree root
    And its content matches the pattern "W[0-9]+"

#### Scenario: No label file in non-worktree sessions @auto

    Given purlin:resume was invoked without --worktree
    When checking the project root
    Then .purlin_worktree_label does NOT exist

#### Scenario: Agent reads label file during mode switch @manual

    Given a running Purlin session in a worktree labeled W1
    When switching from Engineer to PM mode
    Then the terminal identity updates to "PM(W1) | <project>"

## Regression Guidance
- Verify identity uses unified format `<short_mode>(<context>) | <label>` everywhere
- Verify `Engineer` is shortened to `Eng`; `PM`, `QA`, `Purlin` unchanged
- Verify worktree label survives mode switches within the same session
- Verify label file is NOT created in the main repo when running without --worktree
- Verify gap-filling works when middle worktrees are cleaned up
- Verify sub-agent worktrees under .claude/worktrees/ never contain label files
