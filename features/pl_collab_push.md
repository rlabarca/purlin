# Feature: Collab Push

> Label: "/pl-collab-push: Collab Push"
> Category: "Agent Skills"
> Prerequisite: features/policy_remote_collab.md

[TODO]

## 1. Overview

The `/pl-collab-push` skill pushes local `main` to the remote collaboration branch. It is available only from the main checkout (not from isolated worktrees). The target branch is derived from the active remote session.

---

## 2. Requirements

### 2.1 Remote Collaboration Setup

No manual config editing is required. Sessions are created and managed through the CDD dashboard. The active session is stored in `.purlin/runtime/active_remote_session` (gitignored, per-machine).

Optional config override in `.purlin/config.json`:

```json
{ "remote_collab": { "remote": "origin", "auto_fetch_interval": 300 } }
```

Both fields have defaults and the entire block is optional. No `enabled` flag — presence of the active session runtime file determines whether remote commands work.

### 2.2 Main Branch Guard

```
git rev-parse --abbrev-ref HEAD
```

If result is not `main`: abort with message "This command is only valid from the main checkout."

### 2.3 Session Guard

Read `.purlin/runtime/active_remote_session`. If absent or empty: abort with message "No active remote session. Use the CDD dashboard to start or join a remote collab session."

### 2.4 Shared Preconditions

- Read remote from `remote_collab.remote` in `.purlin/config.json`, default `"origin"` if absent.
- Working tree clean (git status check, excluding `.purlin/` files per collaboration policy).

### 2.5 Push Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log origin/<branch>..main --oneline` (ahead), `git log main..origin/<branch> --oneline` (behind)
3. **SAME**: "Already in sync. Nothing to push." Exit 0.
4. **BEHIND**: "Local main is BEHIND `<remote>/<branch>` by M commits. Run `/pl-collab-pull` before pushing." Exit 1.
5. **DIVERGED**: Print incoming commits. Instruct `/pl-collab-pull`. Exit 1.
6. **AHEAD**: `git push <remote> main:<branch>`. Report "Pushed N commits to `<remote>/<branch>`." If branch does not exist on remote, git creates it automatically. On push failure: print git error, exit 1.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-collab-push Exits When Current Branch Is Not Main

    Given the current branch is isolated/feat1
    When /pl-collab-push is invoked
    Then the command prints "This command is only valid from the main checkout"
    And exits with code 1

#### Scenario: pl-collab-push Exits When No Active Session

    Given the current branch is main
    And .purlin/runtime/active_remote_session is absent
    When /pl-collab-push is invoked
    Then the command prints "No active remote session"
    And exits with code 1

#### Scenario: pl-collab-push Aborts When Working Tree Is Dirty

    Given the current branch is main
    And an active remote session exists
    And the working tree has uncommitted changes outside .purlin/
    When /pl-collab-push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed

#### Scenario: pl-collab-push Blocked When Local Main Is BEHIND Remote

    Given the current branch is main with an active session "v0.5-sprint"
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When /pl-collab-push is invoked
    Then the command prints "Local main is BEHIND" and instructs to run /pl-collab-pull
    And exits with code 1

#### Scenario: pl-collab-push Blocked When Local Main Is DIVERGED

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When /pl-collab-push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-collab-pull
    And exits with code 1

#### Scenario: pl-collab-push Succeeds When AHEAD

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 3 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local main
    When /pl-collab-push is invoked
    Then git push origin main:collab/v0.5-sprint is executed
    And the command reports "Pushed 3 commits"

#### Scenario: pl-collab-push Is No-Op When SAME

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint point to the same commit
    When /pl-collab-push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed

#### Scenario: pl-collab-push Auto-Creates Remote Branch When It Does Not Exist

    Given the current branch is main with an active session "new-session"
    And no collab/new-session branch exists on origin
    When /pl-collab-push is invoked
    Then git push origin main:collab/new-session creates the branch
    And the command reports success

### Manual Scenarios (Human Verification Required)

None.
