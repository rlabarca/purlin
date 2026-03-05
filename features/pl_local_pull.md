# Feature: Local Pull

> Label: "/pl-local-pull: Local Pull"
> Category: "Agent Skills"
> Prerequisite: features/policy_collaboration.md

[TODO]

## 1. Overview

The `/pl-local-pull` skill pulls the latest commits from the collaboration branch into the current isolation branch via rebase. The collaboration branch is `collab/<session>` during an active remote session, or `main` when no session is active. It is available only inside an isolated worktree — the command file is placed in the worktree's `.claude/commands/` by `create_isolation.sh` and does not exist in the project root.

Use case: an agent wants updated specs or code from the collaboration branch without pushing own work first.

---

## 2. Requirements

### 2.1 Clean Working Tree Guard

Checks that the working tree is clean. Aborts with message "Commit or stash changes before pulling" if dirty.

### 2.2 Collaboration Branch Detection

Read `.purlin/runtime/active_remote_session` from PROJECT_ROOT (the main checkout, not the worktree). If present and non-empty, the collaboration branch is `collab/<value>`. Otherwise, the collaboration branch is `main`.

### 2.3 State Detection

Computes N (commits behind the collaboration branch) and M (commits ahead of the collaboration branch). Prints both counts and a state label: SAME / AHEAD / BEHIND / DIVERGED.

### 2.4 State Dispatch

*   **SAME:** Already up to date. Stop.
*   **AHEAD:** Nothing to pull. Prints "N commits ahead, nothing to pull. Run /pl-local-push when ready." Stop.
*   **BEHIND:** Runs `git rebase <collaboration-branch>` (fast-forward — no conflict risk). Reports commits incorporated.
*   **DIVERGED:** Prints a pre-rebase context report (`git log HEAD..<collaboration-branch> --stat --oneline`) showing all commits coming in from the collaboration branch with per-file stats. Runs `git rebase <collaboration-branch>`. On success reports the branch is now AHEAD by M commits.

### 2.5 Conflict Reporting

On rebase conflict: for each conflicting file prints the commits from the collaboration branch that touched it, the commits from the worktree branch that touched it, and a resolution hint (`features/` -> Architect priority; `tests/` -> preserve passing tests; other -> review carefully). Ends with instructions to `git add` and `git rebase --continue`, or `git rebase --abort` to abandon.

### 2.6 Post-Rebase Command Re-Sync

After a successful rebase (BEHIND or DIVERGED states), re-apply the isolation command file setup:

1. For each file in `.claude/commands/` that is NOT `pl-local-push.md` or `pl-local-pull.md`: delete the file from disk, then run `git update-index --skip-worktree .claude/commands/<file>`. This marks the deletion as intentional so git does not report it as a dirty working tree.
2. Ensure `pl-local-push.md` and `pl-local-pull.md` are present in `.claude/commands/` (copy from project root if missing).
3. This step is skipped for SAME and AHEAD states (no rebase occurs).

### 2.7 Physical Command Placement

`pl-local-pull.md` is placed ONLY in the worktree's `.claude/commands/` directory (by `create_isolation.sh`). It is NOT present in the project root's `.claude/commands/` directory.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-local-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-local-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git rebase is executed

#### Scenario: pl-local-pull Rebases Collaboration Branch Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And the collaboration branch has 3 new commits not in the worktree branch
    And the worktree branch has no commits not in the collaboration branch
    When /pl-local-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase <collaboration-branch> is executed
    And the output reports 3 new commits incorporated

#### Scenario: pl-local-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in the collaboration branch
    And the collaboration branch has 3 commits not in the worktree branch
    When /pl-local-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits from the collaboration branch with file stats
    And git rebase <collaboration-branch> is executed
    And on success the branch is AHEAD of the collaboration branch by 2 commits

#### Scenario: pl-local-pull Reports Per-File Commit Context On Conflict

    Given /pl-local-pull is invoked and git rebase <collaboration-branch> halts with a conflict on features/foo.md
    When the conflict is reported
    Then the output includes commits from the collaboration branch that touched features/foo.md
    And the output includes commits from the worktree branch that touched features/foo.md
    And a resolution hint is shown for features/ files
    And the output includes instructions to git add and git rebase --continue or git rebase --abort

#### Scenario: pl-local-pull Re-Syncs Command Files After Rebase

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains pl-local-push.md, pl-local-pull.md, and pl-status.md (restored by rebase)
    When /pl-local-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And .claude/commands/pl-status.md is deleted from the worktree
    And .claude/commands/pl-local-push.md and pl-local-pull.md still exist
    And .claude/commands/ at the project root is unaffected

#### Scenario: Post-Rebase Sync Leaves Working Tree Clean

    Given the current worktree is clean
    And the collaboration branch has 1 new commit not in the worktree branch
    And rebase restores extra command files to .claude/commands/ in the worktree
    When /pl-local-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And git status --porcelain reports no file changes in the worktree
    And .claude/commands/ in the worktree contains only pl-local-push.md and pl-local-pull.md

#### Scenario: pl-local-pull Does Not Fail When Extra Command Files Are Already Absent

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains only pl-local-push.md and pl-local-pull.md (no extra files)
    When /pl-local-pull is invoked
    Then git rebase <collaboration-branch> succeeds
    And no error is raised

#### Scenario: pl-local-pull Uses Collab Branch During Active Session

    Given the current worktree is clean
    And an active remote session "v0.5-sprint" exists at PROJECT_ROOT
    And the collaboration branch collab/v0.5-sprint has 2 new commits not in the worktree branch
    When /pl-local-pull is invoked
    Then the state detection uses collab/v0.5-sprint as the reference branch
    And git rebase collab/v0.5-sprint is executed

### Manual Scenarios (Human Verification Required)

None.
