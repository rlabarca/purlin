# Feature: Isolated Pull

> Label: "/pl-isolated-pull Isolated Pull"
> Category: "Agent Skills"
> Prerequisite: features/policy_collaboration.md

[TODO]

## 1. Overview

The `/pl-isolated-pull` skill pulls the latest commits from the collaboration branch into the current isolation branch via rebase. The collaboration branch is read from `.purlin/runtime/active_branch` at PROJECT_ROOT during active branch collaboration, or `main` when no branch is active. It is available only inside an isolated worktree -- the command file is placed in the worktree's `.claude/commands/` by `create_isolation.sh` and does not exist in the project root.

Use case: an agent wants updated specs or code from the collaboration branch without pushing own work first.

---

## 2. Requirements

### 2.1 Clean Working Tree Guard

Checks that the working tree is clean. Aborts with message "Commit or stash changes before pulling" if dirty.

### 2.2 Collaboration Branch Detection

Read `.purlin/runtime/active_branch` from PROJECT_ROOT (the main checkout, not the worktree). If present and non-empty, the collaboration branch is that value. Otherwise, the collaboration branch is `main`.

### 2.3 State Detection

Computes N (commits behind the collaboration branch) and M (commits ahead of the collaboration branch). Prints both counts and a state label: SAME / AHEAD / BEHIND / DIVERGED.

### 2.4 State Dispatch

*   **SAME:** Already up to date. Stop.
*   **AHEAD:** Nothing to pull. Prints "N commits ahead, nothing to pull. Run /pl-isolated-push when ready." Stop.
*   **BEHIND:** Runs `git rebase <collaboration-branch>` (fast-forward -- no conflict risk). Reports commits incorporated.
*   **DIVERGED:** Prints a pre-rebase context report (`git log HEAD..<collaboration-branch> --stat --oneline`) showing all commits coming in from the collaboration branch with per-file stats. Runs `git rebase <collaboration-branch>`. On success reports the branch is now AHEAD by M commits.

### 2.5 Conflict Reporting

On rebase conflict: for each conflicting file prints the commits from the collaboration branch that touched it, the commits from the worktree branch that touched it, and a resolution hint (`features/` -> Architect priority; `tests/` -> preserve passing tests; other -> review carefully). Ends with instructions to `git add` and `git rebase --continue`, or `git rebase --abort` to abandon.

### 2.6 Post-Rebase Command Re-Sync

After a successful rebase (BEHIND or DIVERGED states), re-apply the isolation command file setup:

1. For each file in `.claude/commands/` that is NOT `pl-isolated-push.md` or `pl-isolated-pull.md`: delete the file from disk, then run `git update-index --skip-worktree .claude/commands/<file>`. This marks the deletion as intentional so git does not report it as a dirty working tree.
2. Ensure `pl-isolated-push.md` and `pl-isolated-pull.md` are present in `.claude/commands/` (copy from project root if missing).
3. This step is skipped for SAME and AHEAD states (no rebase occurs).

### 2.7 Physical Command Placement

`pl-isolated-pull.md` is placed ONLY in the worktree's `.claude/commands/` directory (by `create_isolation.sh`). It is NOT present in the project root's `.claude/commands/` directory.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-isolated-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-isolated-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git rebase is executed

#### Scenario: pl-isolated-pull Rebases Collaboration Branch Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And the collaboration branch has 3 new commits not in the worktree branch
    And the worktree branch has no commits not in the collaboration branch
    When /pl-isolated-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase <collaboration-branch> is executed
    And the output reports 3 new commits incorporated

#### Scenario: pl-isolated-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in the collaboration branch
    And the collaboration branch has 3 commits not in the worktree branch
    When /pl-isolated-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits from the collaboration branch with file stats
    And git rebase <collaboration-branch> is executed
    And on success the branch is AHEAD of the collaboration branch by 2 commits

#### Scenario: pl-isolated-pull Reports Per-File Commit Context On Conflict

    Given /pl-isolated-pull is invoked and git rebase <collaboration-branch> halts with a conflict on features/foo.md
    When the conflict is reported
    Then the output includes commits from the collaboration branch that touched features/foo.md
    And the output includes commits from the worktree branch that touched features/foo.md
    And a resolution hint is shown for features/ files
    And the output includes instructions to git add and git rebase --continue or git rebase --abort

#### Scenario: pl-isolated-pull Re-Syncs Command Files After Rebase

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains pl-isolated-push.md, pl-isolated-pull.md, and pl-status.md (restored by rebase)
    When /pl-isolated-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And .claude/commands/pl-status.md is deleted from the worktree
    And .claude/commands/pl-isolated-push.md and pl-isolated-pull.md still exist
    And .claude/commands/ at the project root is unaffected

#### Scenario: Post-Rebase Sync Leaves Working Tree Clean

    Given the current worktree is clean
    And the collaboration branch has 1 new commit not in the worktree branch
    And rebase restores extra command files to .claude/commands/ in the worktree
    When /pl-isolated-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And git status --porcelain reports no file changes in the worktree
    And .claude/commands/ in the worktree contains only pl-isolated-push.md and pl-isolated-pull.md

#### Scenario: pl-isolated-pull Does Not Fail When Extra Command Files Are Already Absent

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains only pl-isolated-push.md and pl-isolated-pull.md (no extra files)
    When /pl-isolated-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And no error is raised

#### Scenario: pl-isolated-pull Uses Active Collaboration Branch

    Given the current worktree is clean
    And an active branch "feature/auth" exists at PROJECT_ROOT in .purlin/runtime/active_branch
    And the collaboration branch feature/auth has 2 new commits not in the worktree branch
    When /pl-isolated-pull is invoked
    Then the state detection uses feature/auth as the reference branch
    And git rebase feature/auth is executed

### Manual Scenarios (Human Verification Required)

None.
