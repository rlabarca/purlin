# Feature: purlin:worktree Worktree Management

> Label: "Agent Skills: Common: purlin:worktree Worktree Management"
> Category: "Agent Skills: Common"
> Prerequisite: purlin_worktree_concurrency.md

[Complete]

## 1. Overview

The `purlin:worktree` command provides visibility into active, stale, and orphaned worktrees. Subcommands: `list` shows full detail for all worktrees, `cleanup-stale` removes worktrees whose agent has exited without merging.

---

## 2. Requirements

### 2.1 Subcommand: `list`

- Scan all entries from `git worktree list` that are under `.purlin/worktrees/`.
- For each worktree, read `.purlin_worktree_label` for the label and `.purlin_session.lock` for PID, mode, and start time.
- Classify each worktree:
  - **active** — session lock exists, PID is alive (`kill -0 $PID` succeeds)
  - **stale** — session lock exists, PID is dead
  - **orphaned** — no session lock file
- Display in table format:
  ```
  Active worktrees:
    W1  Engineer  PID 12345  active    2h ago   purlin-engineer-20260325-1430
    W2  PM        PID 67890  stale     5h ago   purlin-pm-20260325-1130
    W3  QA        (no lock)  orphaned  1d ago   purlin-qa-20260324-0900
  ```
- If no worktrees exist, print: "No active worktrees."

### 2.2 Subcommand: `cleanup-stale`

- Scan for stale and orphaned worktrees (same classification as `list`).
- For each stale/orphaned worktree:
  - Check for uncommitted work (`git -C <path> status --porcelain`).
  - If uncommitted work exists: prompt user — "Worktree W2 has uncommitted changes. Merge back to main, or discard?"
  - If no uncommitted work: auto-remove (worktree directory + branch).
- Report summary: "Cleaned up N worktrees."
- Skip active worktrees entirely.

### 2.3 Mode and Access

- Available in any mode (shared skill).
- Does not activate or switch modes.
- Read-only for `list`. `cleanup-stale` modifies worktree state.

---

## 3. Scenarios

### Unit Tests

#### Scenario: List shows active worktree

    Given a worktree W1 with .purlin_session.lock containing a live PID
    When purlin:worktree list is invoked
    Then W1 appears with status "active"

#### Scenario: List shows stale worktree

    Given a worktree W2 with .purlin_session.lock containing a dead PID
    When purlin:worktree list is invoked
    Then W2 appears with status "stale"

#### Scenario: List shows orphaned worktree

    Given a worktree W3 with no .purlin_session.lock
    When purlin:worktree list is invoked
    Then W3 appears with status "orphaned"

#### Scenario: No worktrees

    Given no worktrees exist under .purlin/worktrees/
    When purlin:worktree list is invoked
    Then "No active worktrees." is printed

#### Scenario: Cleanup removes stale worktree without uncommitted work

    Given worktree W2 is stale with no uncommitted changes
    When purlin:worktree cleanup-stale is invoked
    Then W2's directory is removed
    And W2's branch is deleted

#### Scenario: Cleanup prompts for stale worktree with uncommitted work

    Given worktree W2 is stale with uncommitted changes
    When purlin:worktree cleanup-stale is invoked
    Then the user is prompted to merge or discard

#### Scenario: Cleanup skips active worktrees

    Given worktree W1 is active (PID alive)
    When purlin:worktree cleanup-stale is invoked
    Then W1 is not touched

### QA Scenarios

None.
