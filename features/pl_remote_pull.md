# Feature: Remote Pull

> Label: "/pl-remote-pull Remote Pull"
> Category: "Agent Skills"
> Prerequisite: features/policy_branch_collab.md

[TODO]

## 1. Overview

The `/pl-remote-pull` skill pulls the remote collaboration branch into the local collaboration branch via merge. It operates in two modes depending on how it is invoked:

- **No-argument mode:** Resolves the collaboration branch per `policy_branch_collab.md` Section 2.4. If `.purlin/runtime/active_branch` is present and non-empty, uses that value (collaboration mode). If absent or empty, defaults to `main` (direct mode). Must be checked out on the resolved collaboration branch.
- **Explicit-branch mode** (e.g., `/pl-remote-pull RC0.8.0`): Uses the argument as the branch name directly. Runs from any branch (typically `main`). Skips Steps 0-1.

Merge (not rebase) is used because the collaboration branch is a shared integration branch -- rebasing rewrites commits other contributors' copies or the remote already have.

---

## 2. Requirements

### 2.1 Branch Collaboration Setup

No manual config editing is required. Branches are created and managed through the CDD dashboard. The active branch is stored in `.purlin/runtime/active_branch` (gitignored, per-machine).

Optional config override in `.purlin/config.json`:

```json
{ "branch_collab": { "remote": "origin", "auto_fetch_interval": 300 } }
```

Both fields have defaults and the entire block is optional. Backward compatibility: read `remote_collab` if `branch_collab` absent.

### 2.2 Collaboration Branch Resolution (no-argument mode only)

**Skip this step** when a branch argument was provided -- use the argument as `<branch>` and proceed directly to Step 2.4.

Read `.purlin/runtime/active_branch`:

1. If present and non-empty: collaboration branch = that value.
2. If absent or empty: collaboration branch = `main`.

This replaces the former "Branch Guard" that aborted when no active branch existed.

### 2.3 Collaboration Branch Guard (no-argument mode only)

**Skip this step** when a branch argument was provided.

```
git rev-parse --abbrev-ref HEAD
```

If the result does not match the resolved collaboration branch:

- **Active branch exists:** abort with "This command must be run from the collaboration branch (<branch>). Current branch: <current>."
- **No active branch (direct mode):** abort with "No active collaboration branch. On `main`, /pl-remote-pull pulls main directly. Current branch: <current>. Switch to main or use the CDD dashboard to create a collaboration branch."

### 2.4 Remote Guard

After the branch guard passes (or is skipped in explicit-branch mode), check for configured remotes:

```
git remote -v
```

If no remotes exist, print: "No git remote configured. Run `/pl-remote-push` to set up a remote first." and exit with code 1.

### 2.5 Shared Preconditions

- Read remote from `branch_collab.remote` in `.purlin/config.json`, default `"origin"` if absent. Fallback to `remote_collab.remote`.
- Working tree clean (git status check, excluding `.purlin/` files per collaboration policy).

### 2.6 First-Pull Safety Confirmation

On the first pull from a remote+branch pair, detected by checking whether the local branch has any merge-base with the remote tracking branch (`git merge-base <branch> <remote>/<branch>` fails), display a confirmation prompt:

```
First pull from this remote. Please confirm:
  Remote:   <name> (<url>)
  Branch:   <branch>
  Incoming: <N> commit(s) will be merged

Proceed? [Y/n]
```

If the user declines, abort without merging. Subsequent pulls from the same remote+branch (where a merge-base exists) skip this confirmation.

### 2.7 Pull Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log <remote>/<branch>..<branch> --oneline` (ahead), `git log <branch>..<remote>/<branch> --oneline` (behind). In explicit-branch mode, replace `<branch>` with `HEAD` per the ref substitution rule.
3. **SAME**: "Local <branch> is already in sync with remote." Exit 0.
4. **AHEAD**: "Local <branch> is AHEAD by N commits. Nothing to pull -- run `/pl-remote-push` when ready." Exit 0.
5. **BEHIND**: `git merge --ff-only <remote>/<branch>`. Report "Fast-forwarded local <branch> by M commits from `<remote>/<branch>`." On ff-failure (race condition): "Fast-forward failed -- re-run `/pl-remote-pull`." Exit 1.
6. **DIVERGED**: Print pre-merge context (`git log <branch>..<remote>/<branch> --stat --oneline`). Run `git merge <remote>/<branch>`. On conflict: print per-file conflict context (commits from each side that touched each conflicting file); provide resolution instructions (`git add` + `git merge --continue` or `git merge --abort`); exit 1.

### 2.8 Post-Merge Digest Generation

After a successful merge (BEHIND fast-forward or DIVERGED clean merge), auto-generate the "What's Different?" digest. This step is informational and does not block or fail the pull.

1. Run the generation script: `bash <tools_root>/collab/generate_whats_different.sh <branch>`
2. Read the generated file at `features/digests/whats-different.md` and display its content inline.
3. If the script fails or the file is not written, print a warning and continue.

**Skip this step** when the merge result is SAME, AHEAD, or DIVERGED-with-conflicts.

### 2.9 FORBIDDEN Pattern Enforcement

The command MUST NOT execute any operation that violates the FORBIDDEN patterns in `policy_branch_collab.md` Section 4:

- MUST NOT rebase the collaboration branch. Uses `git merge` exclusively (consistent with policy Section 2.8).
- MUST NOT push to any branch. This is a pull-only command.
- MUST NOT auto-resolve merge conflicts. Conflict resolution is a human responsibility per policy Section 2.8.
- In no-argument mode, MUST NOT proceed when the current branch does not match the resolved collaboration branch (enforced by the Collaboration Branch Guard in Section 2.3).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-remote-pull Resolves To Main When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And a remote "origin" is configured
    And origin/main has 3 commits not in local main
    When /pl-remote-pull is invoked
    Then the collaboration branch resolves to main
    And git merge --ff-only origin/main is executed
    And the command reports "Fast-forwarded local main by 3 commits"

#### Scenario: pl-remote-pull Rejects Non-Main Branch When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is hotfix/urgent
    When /pl-remote-pull is invoked
    Then the command prints "No active collaboration branch"
    And the command prints "Switch to main"
    And exits with code 1

#### Scenario: pl-remote-pull Prints Helpful Message When No Remote Configured

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And no git remotes are configured
    When /pl-remote-pull is invoked
    Then the command prints "No git remote configured. Run /pl-remote-push to set up a remote first."
    And exits with code 1

#### Scenario: pl-remote-pull First Pull Shows Safety Confirmation

    Given the current branch is main
    And a remote "origin" is configured with URL "git@github.com:user/repo.git"
    And local main has no merge-base with origin/main
    And origin/main has 4 commits
    When /pl-remote-pull is invoked
    Then the command displays remote name "origin", URL, branch "main", and "4 commit(s)"
    And waits for user confirmation before merging

#### Scenario: pl-remote-pull First Pull Aborted When User Declines

    Given the current branch is main
    And a remote "origin" is configured
    And local main has no merge-base with origin/main
    When /pl-remote-pull is invoked
    And the user declines the first-pull safety prompt
    Then no git merge is executed
    And exits with code 1

#### Scenario: pl-remote-pull Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-pull is invoked
    Then the command prints "This command must be run from the collaboration branch"
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
