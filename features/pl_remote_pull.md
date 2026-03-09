# Feature: Remote Pull

> Label: "/pl-remote-pull Remote Pull"
> Category: "Agent Skills"
> Prerequisite: features/policy_branch_collab.md

[TODO]

## 1. Overview

The `/pl-remote-pull` skill pulls the remote collaboration branch into the local collaboration branch via merge. During an active branch, the local machine is on the collaboration branch and merges from the same-named remote branch -- a symmetric same-branch pull. It is available only from the collaboration branch checkout. The target branch is read from `.purlin/runtime/active_branch`.

Merge (not rebase) is used because the collaboration branch is a shared integration branch -- rebasing rewrites commits other contributors' copies or the remote already have.

---

## 2. Requirements

### 2.1 Branch Collaboration Setup

No manual config editing is required. Branches are created and managed through the CDD dashboard. The active branch is stored in `.purlin/runtime/active_branch` (gitignored, per-machine).

Optional config override in `.purlin/config.json`:

```json
{ "branch_collab": { "remote": "origin", "auto_fetch_interval": 300 } }
```

Both fields have defaults and the entire block is optional. Backward compatibility: read `remote_collab` if `branch_collab` absent. No `enabled` flag -- presence of the active branch runtime file determines whether remote commands work.

### 2.2 Branch Guard

Read `.purlin/runtime/active_branch`. If absent or empty: abort with message "No active collaboration branch. Use the CDD dashboard to create or join a branch."

### 2.3 Collaboration Branch Guard

```
git rev-parse --abbrev-ref HEAD
```

If result does not match the value from the active branch file: abort with message "This command must be run from the collaboration branch (<branch>)."

### 2.4 Shared Preconditions

- Read remote from `branch_collab.remote` in `.purlin/config.json`, default `"origin"` if absent. Fallback to `remote_collab.remote`.
- Working tree clean (git status check, excluding `.purlin/` files per collaboration policy).

### 2.5 Pull Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log origin/<branch>..<branch> --oneline` (ahead), `git log <branch>..origin/<branch> --oneline` (behind)
3. **SAME**: "Local <branch> is already in sync with remote." Exit 0.
4. **AHEAD**: "Local <branch> is AHEAD by N commits. Nothing to pull -- run `/pl-remote-push` when ready." Exit 0.
5. **BEHIND**: `git merge --ff-only origin/<branch>`. Report "Fast-forwarded local <branch> by M commits from `<remote>/<branch>`." On ff-failure (race condition): "Fast-forward failed -- re-run `/pl-remote-pull`." Exit 1.
6. **DIVERGED**: Print pre-merge context (`git log <branch>..origin/<branch> --stat --oneline`). Run `git merge origin/<branch>`. On conflict: print per-file conflict context (commits from each side that touched each conflicting file); provide resolution instructions (`git add` + `git merge --continue` or `git merge --abort`); exit 1.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-remote-pull Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-pull is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1

#### Scenario: pl-remote-pull Exits When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When /pl-remote-pull is invoked
    Then the command prints "No active collaboration branch"
    And exits with code 1

#### Scenario: pl-remote-pull Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed

#### Scenario: pl-remote-pull Fast-Forwards When BEHIND

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 3 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote-pull is invoked
    Then git merge --ff-only origin/feature/auth is executed
    And the command reports "Fast-forwarded local feature/auth by 3 commits"

#### Scenario: pl-remote-pull Creates Merge Commit When DIVERGED No Conflicts

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    And the changes do not conflict
    When /pl-remote-pull is invoked
    Then git merge origin/feature/auth creates a merge commit
    And the command reports success

#### Scenario: pl-remote-pull Exits On Conflict With Per-File Context

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth have conflicting changes to features/foo.md
    When /pl-remote-pull is invoked
    Then git merge origin/feature/auth halts with conflicts
    And the command prints commits from each side that touched features/foo.md
    And provides instructions for git add and git merge --continue or git merge --abort
    And exits with code 1

#### Scenario: pl-remote-pull Is No-Op When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 2 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote-pull is invoked
    Then the command prints "Local feature/auth is AHEAD by 2 commits. Nothing to pull"
    And no git merge is executed

#### Scenario: pl-remote-pull Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote-pull is invoked
    Then the command prints "Local feature/auth is already in sync with remote"
    And no git merge is executed

### Manual Scenarios (Human Verification Required)

None.
