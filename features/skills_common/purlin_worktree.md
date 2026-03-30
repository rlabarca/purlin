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

### 2.3 Subcommand: `check-lock` (internal)

Internal helper used by `purlin:resume` to determine whether a worktree is safe to enter before creating or resuming a session. Not user-invocable via the skill.

- Accept a worktree path as argument.
- Read `.purlin_session.lock` and `.purlin_worktree_label` from the worktree.
- Classify the worktree:
  - **orphaned** (no lock file) → `safe: true`
  - **stale** (lock exists, PID dead) → `safe: true`
  - **active** (lock exists, PID alive) → `safe: false`
- Return JSON: `{"safe": bool, "status": "...", "pid": N|null, "label": "...", "mode": "..."}`

### 2.4 Subcommand: `claim` (internal)

Internal helper used by `purlin:resume` to take ownership of a stale or orphaned worktree. Not user-invocable via the skill.

- Accept a worktree path and optional `--mode <mode>` argument.
- If the worktree has an active session lock (PID alive), reject with error and return `{"claimed": false, ...}`.
- Otherwise, write a new `.purlin_session.lock` with the current PID, timestamp, and mode.
- Preserve the existing worktree label from `.purlin_worktree_label`.
- Return JSON: `{"claimed": true, "pid": N, "label": "...", "mode": "..."}`

### 2.5 Mode and Access

- Available in any mode (shared skill).
- Does not activate or switch modes.
- Read-only for `list`. `cleanup-stale` modifies worktree state.
- `check-lock` and `claim` are internal to the framework (used by `purlin:resume`), not exposed as user-facing skill subcommands.

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

#### Scenario: Cleanup dry-run does not remove worktrees

    Given worktree W4 is stale with no uncommitted changes
    When purlin:worktree cleanup-stale --dry-run is invoked
    Then W4 is reported but not removed

#### Scenario: Check-lock reports orphaned worktree as safe

    Given a worktree with no .purlin_session.lock
    When manage.sh check-lock is called with the worktree path
    Then the result has safe: true and status: "orphaned"

#### Scenario: Check-lock reports stale worktree as safe

    Given a worktree with .purlin_session.lock containing a dead PID
    When manage.sh check-lock is called with the worktree path
    Then the result has safe: true and status: "stale"

#### Scenario: Check-lock reports active worktree as unsafe

    Given a worktree with .purlin_session.lock containing a live PID
    When manage.sh check-lock is called with the worktree path
    Then the result has safe: false and status: "active"

#### Scenario: Claim succeeds on stale worktree

    Given a worktree with .purlin_session.lock containing a dead PID and label W1
    When manage.sh claim is called with --mode qa
    Then claimed: true is returned
    And the label W1 is preserved
    And the lock file is updated with mode "qa"

#### Scenario: Claim succeeds on orphaned worktree

    Given a worktree with no .purlin_session.lock
    When manage.sh claim is called
    Then claimed: true is returned
    And a new lock file is created

#### Scenario: Claim rejected on active worktree

    Given a worktree with .purlin_session.lock containing a live PID
    When manage.sh claim is called
    Then the claim is rejected with an "active session" error

### QA Scenarios

None.
