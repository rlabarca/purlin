# Feature: Collab Push

> Label: "/pl-collab-push: Collab Push"
> Category: "Agent Skills"
> Prerequisite: features/policy_remote_collab.md

[TODO]

## 1. Overview

The `/pl-collab-push` skill pushes the local collaboration branch to the remote. During an active session, the local machine is on the `collab/<session>` branch and pushes directly to the same-named remote branch — a symmetric same-branch push. It is available only from the collaboration branch checkout (not from isolated worktrees). The target branch is derived from the active remote session.

---

## 2. Requirements

### 2.1 Remote Collaboration Setup

No manual config editing is required. Sessions are created and managed through the CDD dashboard. The active session is stored in `.purlin/runtime/active_remote_session` (gitignored, per-machine).

Optional config override in `.purlin/config.json`:

```json
{ "remote_collab": { "remote": "origin", "auto_fetch_interval": 300 } }
```

Both fields have defaults and the entire block is optional. No `enabled` flag — presence of the active session runtime file determines whether remote commands work.

### 2.2 Session Guard

Read `.purlin/runtime/active_remote_session`. If absent or empty: abort with message "No active remote session. Use the CDD dashboard to start or join a remote collab session."

### 2.3 Collaboration Branch Guard

```
git rev-parse --abbrev-ref HEAD
```

If result is not `collab/<session>` (where `<session>` is the value from the active session file): abort with message "This command must be run from the collaboration branch (collab/<session>)."

### 2.4 Shared Preconditions

- Read remote from `remote_collab.remote` in `.purlin/config.json`, default `"origin"` if absent.
- Working tree clean (git status check, excluding `.purlin/` files per collaboration policy).

### 2.5 Push Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log origin/collab/<session>..collab/<session> --oneline` (ahead), `git log collab/<session>..origin/collab/<session> --oneline` (behind)
3. **SAME**: "Already in sync. Nothing to push." Exit 0.
4. **BEHIND**: "Local collab/<session> is BEHIND `<remote>/collab/<session>` by M commits. Run `/pl-collab-pull` before pushing." Exit 1.
5. **DIVERGED**: Print incoming commits. Instruct `/pl-collab-pull`. Exit 1.
6. **AHEAD**: `git push <remote> collab/<session>`. Report "Pushed N commits to `<remote>/collab/<session>`." On push failure: print git error, exit 1.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-collab-push Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active remote session "v0.5-sprint" exists
    When /pl-collab-push is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1

#### Scenario: pl-collab-push Exits When On Wrong Collab Branch

    Given the current branch is collab/other-session
    And an active remote session "v0.5-sprint" exists
    When /pl-collab-push is invoked
    Then the command prints "This command must be run from the collaboration branch (collab/v0.5-sprint)"
    And exits with code 1

#### Scenario: pl-collab-push Exits When No Active Session

    Given no file exists at .purlin/runtime/active_remote_session
    When /pl-collab-push is invoked
    Then the command prints "No active remote session"
    And exits with code 1

#### Scenario: pl-collab-push Aborts When Working Tree Is Dirty

    Given the current branch is collab/v0.5-sprint
    And an active remote session "v0.5-sprint" exists
    And the working tree has uncommitted changes outside .purlin/
    When /pl-collab-push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed

#### Scenario: pl-collab-push Blocked When Local Is BEHIND Remote

    Given the current branch is collab/v0.5-sprint with an active session "v0.5-sprint"
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    And local collab/v0.5-sprint has no commits not in origin/collab/v0.5-sprint
    When /pl-collab-push is invoked
    Then the command prints "Local collab/v0.5-sprint is BEHIND" and instructs to run /pl-collab-pull
    And exits with code 1

#### Scenario: pl-collab-push Blocked When Local Is DIVERGED

    Given the current branch is collab/v0.5-sprint with an active session "v0.5-sprint"
    And local collab/v0.5-sprint has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When /pl-collab-push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-collab-pull
    And exits with code 1

#### Scenario: pl-collab-push Succeeds When AHEAD

    Given the current branch is collab/v0.5-sprint with an active session "v0.5-sprint"
    And local collab/v0.5-sprint has 3 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local collab/v0.5-sprint
    When /pl-collab-push is invoked
    Then git push origin collab/v0.5-sprint is executed
    And the command reports "Pushed 3 commits"

#### Scenario: pl-collab-push Is No-Op When SAME

    Given the current branch is collab/v0.5-sprint with an active session "v0.5-sprint"
    And local collab/v0.5-sprint and origin/collab/v0.5-sprint point to the same commit
    When /pl-collab-push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed

### Manual Scenarios (Human Verification Required)

None.
