# Feature: /pl-merge Worktree Merge

> Label: "Agent Skills: Common: /pl-merge Worktree Merge"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_worktree_concurrency.md

## 1. Overview

The `/pl-merge` skill merges the current worktree branch back to the source branch and cleans up the worktree directory. It handles conflict resolution, auto-resolves safe files, and presents code/spec conflicts to the user.

---

## 2. Requirements

### 2.1 Merge Protocol

- MUST commit any pending work before merging.
- MUST merge the worktree branch to the source branch via `git merge --no-edit`.
- On conflict with safe files (`.purlin/cache/*`, `.purlin/delivery_plan.md`): auto-resolve by keeping main's version.
- On conflict with code or spec files: present the conflict to the user.
- After successful merge: remove worktree directory and delete branch.

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
