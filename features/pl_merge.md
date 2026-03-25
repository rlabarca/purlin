# Feature: /pl-merge Worktree Merge

> Label: "Agent Skills: Common: /pl-merge Worktree Merge"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_worktree_concurrency.md

## 1. Overview

The `/pl-merge` skill merges the current worktree branch back to the source branch and cleans up the worktree directory. It handles conflict resolution, auto-resolves safe files, and presents code/spec conflicts to the user.

---

## 2. Requirements

### 2.1 Merge Protocol

1. Acquire `.purlin/cache/merge.lock` (write PID + timestamp). If another merge is in progress (lock exists, PID alive), retry after 2s up to 3 times. If still blocked, abort with message: "Merge blocked: another worktree is merging to main."
2. Commit any pending work before merging.
3. Merge the worktree branch to the source branch via `git merge --no-edit`.
4. On conflict with safe files (`.purlin/cache/*`, `.purlin/delivery_plan.md`): auto-resolve by keeping main's version.
5. On conflict with code or spec files: present the conflict to the user.
6. After successful merge: delete `.purlin_session.lock` from the worktree, remove worktree directory, delete branch.
7. Release `.purlin/cache/merge.lock`.

On merge failure (conflict not resolved): release merge lock, write breadcrumb per `purlin_worktree_concurrency.md` Section 2.8.

### 2.2 Preconditions

- MUST only work when running in a worktree. If not in a worktree, respond: "Not in a worktree. Nothing to merge."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Merge succeeds and cleans up

    Given the agent is in a purlin worktree with committed work
    When /pl-merge is invoked
    Then the worktree branch is merged to the source branch
    And the worktree directory is removed
    And the branch is deleted

#### Scenario: Not in a worktree

    Given the agent is not running in a worktree
    When /pl-merge is invoked
    Then it responds "Not in a worktree"

### Manual Scenarios (Human Verification Required)

None.
