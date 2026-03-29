# Feature: purlin:merge Worktree Merge

> Label: "Agent Skills: Common: purlin:merge Worktree Merge"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_worktree_concurrency.md

## 1. Overview

The `purlin:merge` skill merges the current worktree branch back to the source branch and cleans up the worktree directory. It handles conflict resolution, auto-resolves safe files, and presents code/spec conflicts to the user.

---

## 2. Requirements

### 2.1 Merge Protocol

1. Acquire `.purlin/cache/merge.lock` (write PID + timestamp). If another merge is in progress (lock exists, PID alive), retry after 2s up to 3 times. If still blocked, abort with message: "Merge blocked: another worktree is merging to main."
2. Commit any pending work before merging.
3. Save the worktree path and main project root as variables before any directory changes.
4. Merge the worktree branch to the source branch via `git merge --no-edit`.
5. On conflict with safe files (`.purlin/cache/*`, `.purlin/delivery_plan.md`): auto-resolve by keeping main's version.
6. On conflict with code or spec files: present the conflict to the user.
7. After successful merge, run ALL cleanup in a single Bash call that begins with `cd "$MAIN_ROOT"`: delete `.purlin_session.lock` from the worktree, remove worktree directory (`git worktree remove`), delete branch (`git branch -d`), release merge lock. This MUST be a single chained command — the worktree removal deletes the agent's CWD, and any subsequent Bash call will fail because the Bash tool validates CWD existence before executing.
8. Update the iTerm badge and terminal title to reflect the current mode on the source branch (no longer in a worktree). Badge: `<mode> (<branch>)`. Title: `<project> - <mode> (<branch>)`.

On merge failure (conflict not resolved): release merge lock, write breadcrumb per `purlin_worktree_concurrency.md` Section 2.8.

### 2.2 Preconditions

- MUST only work when running in a worktree. If not in a worktree, respond: "Not in a worktree. Nothing to merge."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Merge succeeds and cleans up

    Given the agent is in a purlin worktree with committed work
    When purlin:merge is invoked
    Then the worktree branch is merged to the source branch
    And the worktree directory is removed
    And the branch is deleted
    And the iTerm badge shows the current mode on the source branch

#### Scenario: Cleanup runs as single command to avoid CWD invalidation

    Given the agent is in a purlin worktree
    And the merge to the source branch succeeds
    When cleanup executes
    Then worktree removal, branch deletion, and lock release run in a single Bash call starting with cd to the main project root
    And no subsequent Bash calls depend on the worktree path existing

#### Scenario: Not in a worktree

    Given the agent is not running in a worktree
    When purlin:merge is invoked
    Then it responds "Not in a worktree"

### Manual Scenarios (Human Verification Required)

None.
