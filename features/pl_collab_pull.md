# Feature: Collab Pull

> Label: "/pl-collab-pull: Collab Pull"
> Category: "Agent Skills"
> Prerequisite: features/policy_remote_collab.md

[TODO]

## 1. Overview

The `/pl-collab-pull` skill pulls the remote collaboration branch into local `main` via merge. It is available only from the main checkout (not from isolated worktrees). The target branch is derived from the active remote session.

Merge (not rebase) is used because local `main` is a shared integration branch — rebasing rewrites commits other contributors' copies or the remote already have. This differs from `/pl-local-pull` which uses rebase on personal isolation branches.

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

### 2.5 Pull Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log origin/<branch>..main --oneline` (ahead), `git log main..origin/<branch> --oneline` (behind)
3. **SAME**: "Local main is already in sync with remote." Exit 0.
4. **AHEAD**: "Local main is AHEAD by N commits. Nothing to pull — run `/pl-collab-push` when ready." Exit 0.
5. **BEHIND**: `git merge --ff-only origin/<branch>`. Report "Fast-forwarded local main by M commits from `<remote>/<branch>`." On ff-failure (race condition): "Fast-forward failed — re-run `/pl-collab-pull`." Exit 1.
6. **DIVERGED**: Print pre-merge context (`git log main..origin/<branch> --stat --oneline`). Run `git merge origin/<branch>`. On conflict: print per-file conflict context (commits from each side that touched each conflicting file); provide resolution instructions (`git add` + `git merge --continue` or `git merge --abort`); exit 1.

### 2.6 No Cascade to Isolated Teams

After `/pl-collab-pull` updates main, any active isolations that are BEHIND will show `BEHIND` in the ISOLATED TEAMS section and sync themselves via `/pl-local-pull` when ready. Each isolation controls its own branch.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-collab-pull Exits When Current Branch Is Not Main

    Given the current branch is isolated/feat1
    When /pl-collab-pull is invoked
    Then the command prints "This command is only valid from the main checkout"
    And exits with code 1

#### Scenario: pl-collab-pull Exits When No Active Session

    Given the current branch is main
    And .purlin/runtime/active_remote_session is absent
    When /pl-collab-pull is invoked
    Then the command prints "No active remote session"
    And exits with code 1

#### Scenario: pl-collab-pull Aborts When Working Tree Is Dirty

    Given the current branch is main
    And an active remote session exists
    And the working tree has uncommitted changes outside .purlin/
    When /pl-collab-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed

#### Scenario: pl-collab-pull Fast-Forwards Main When BEHIND

    Given the current branch is main with an active session "v0.5-sprint"
    And origin/collab/v0.5-sprint has 3 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When /pl-collab-pull is invoked
    Then git merge --ff-only origin/collab/v0.5-sprint is executed
    And the command reports "Fast-forwarded local main by 3 commits"

#### Scenario: pl-collab-pull Creates Merge Commit When DIVERGED No Conflicts

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And the changes do not conflict
    When /pl-collab-pull is invoked
    Then git merge origin/collab/v0.5-sprint creates a merge commit
    And the command reports success

#### Scenario: pl-collab-pull Exits On Conflict With Per-File Context

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint have conflicting changes to features/foo.md
    When /pl-collab-pull is invoked
    Then git merge origin/collab/v0.5-sprint halts with conflicts
    And the command prints commits from each side that touched features/foo.md
    And provides instructions for git add and git merge --continue or git merge --abort
    And exits with code 1

#### Scenario: pl-collab-pull Is No-Op When AHEAD

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 2 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local main
    When /pl-collab-pull is invoked
    Then the command prints "Local main is AHEAD by 2 commits. Nothing to pull"
    And no git merge is executed

#### Scenario: pl-collab-pull Is No-Op When SAME

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint point to the same commit
    When /pl-collab-pull is invoked
    Then the command prints "Local main is already in sync with remote"
    And no git merge is executed

#### Scenario: pl-collab-pull Does Not Cascade To Isolated Team Worktrees

    Given the current branch is main with an active session "v0.5-sprint"
    And an isolated worktree exists at .worktrees/feat1
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When /pl-collab-pull is invoked and fast-forwards main
    Then the isolated worktree at .worktrees/feat1 is not modified
    And .worktrees/feat1 shows BEHIND in subsequent status checks

### Manual Scenarios (Human Verification Required)

None.
