# Feature: Remote Push

> Label: "/pl-remote-push Remote Push"
> Category: "Agent Skills"
> Prerequisite: features/policy_branch_collab.md

[TODO]

## 1. Overview

The `/pl-remote-push` skill pushes the local collaboration branch to the remote. During an active branch, the local machine is on the collaboration branch and pushes directly to the same-named remote branch -- a symmetric same-branch push. It is available only from the collaboration branch checkout (not from isolated worktrees). The target branch is read from `.purlin/runtime/active_branch`.

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

### 2.5 Push Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log origin/<branch>..<branch> --oneline` (ahead), `git log <branch>..origin/<branch> --oneline` (behind)
3. **SAME**: "Already in sync. Nothing to push." Exit 0.
4. **BEHIND**: "Local <branch> is BEHIND `<remote>/<branch>` by M commits. Run `/pl-remote-pull` before pushing." Exit 1.
5. **DIVERGED**: Print incoming commits. Instruct `/pl-remote-pull`. Exit 1.
6. **AHEAD**: `git push <remote> <branch>`. Report "Pushed N commits to `<remote>/<branch>`." On push failure: print git error, exit 1.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-remote-push Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1

#### Scenario: pl-remote-push Exits When On Wrong Branch

    Given the current branch is hotfix/urgent
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "This command must be run from the collaboration branch (feature/auth)"
    And exits with code 1

#### Scenario: pl-remote-push Exits When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "No active collaboration branch"
    And exits with code 1

#### Scenario: pl-remote-push Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote-push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed

#### Scenario: pl-remote-push Blocked When Local Is BEHIND Remote

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote-push is invoked
    Then the command prints "Local feature/auth is BEHIND" and instructs to run /pl-remote-pull
    And exits with code 1

#### Scenario: pl-remote-push Blocked When Local Is DIVERGED

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    When /pl-remote-push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-remote-pull
    And exits with code 1

#### Scenario: pl-remote-push Succeeds When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote-push is invoked
    Then git push origin feature/auth is executed
    And the command reports "Pushed 3 commits"

#### Scenario: pl-remote-push Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote-push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed

### Manual Scenarios (Human Verification Required)

None.
