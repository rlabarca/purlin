# Feature: Remote Push

> Label: "/pl-remote-push Remote Push"
> Category: "Agent Skills"
> Prerequisite: features/policy_branch_collab.md

[TODO]

## 1. Overview

The `/pl-remote-push` skill pushes the local collaboration branch to the remote. It operates in three modes depending on project state:

- **Mode 1 -- No remote configured:** Guides the user through adding a git remote, then pushes.
- **Mode 2 -- Direct mode (no active branch):** Collaboration branch resolves to `main`. Pushes `main` to the remote.
- **Mode 3 -- Collaboration mode (active branch):** Pushes the active collaboration branch to the same-named remote branch.

The collaboration branch is resolved per `policy_branch_collab.md` Section 2.4: read `.purlin/runtime/active_branch`; if present and non-empty, use that value; otherwise default to `main`.

---

## 2. Requirements

### 2.1 Branch Collaboration Setup

No manual config editing is required. Branches are created and managed through the CDD dashboard. The active branch is stored in `.purlin/runtime/active_branch` (gitignored, per-machine).

Optional config override in `.purlin/config.json`:

```json
{ "branch_collab": { "remote": "origin", "auto_fetch_interval": 300 } }
```

Both fields have defaults and the entire block is optional. Backward compatibility: read `remote_collab` if `branch_collab` absent.

### 2.2 Collaboration Branch Resolution

Read `.purlin/runtime/active_branch`:

1. If present and non-empty: collaboration branch = that value.
2. If absent or empty: collaboration branch = `main`.

This replaces the former "Branch Guard" that aborted when no active branch existed.

### 2.3 Collaboration Branch Guard

```
git rev-parse --abbrev-ref HEAD
```

If the result does not match the resolved collaboration branch:

- **Active branch exists:** abort with "This command must be run from the collaboration branch (<branch>). Current branch: <current>."
- **No active branch (direct mode):** abort with "No active collaboration branch. On `main`, /pl-remote-push pushes main directly. Current branch: <current>. Switch to main or use the CDD dashboard to create a collaboration branch."

### 2.4 Remote Guard

After the branch guard passes, check for configured remotes:

```
git remote -v
```

If no remotes exist, guide the user through setup:

1. Check `gh` CLI availability (`command -v gh`).
2. If `gh` available: offer two options -- "Create a new GitHub repository" (`gh repo create`) or "Add an existing remote URL".
3. If `gh` unavailable: prompt for remote URL and name (default "origin").
4. Execute `git remote add <name> <url>` (or `gh repo create`).
5. Proceed to push.

### 2.5 Shared Preconditions

- Read remote from `branch_collab.remote` in `.purlin/config.json`, default `"origin"` if absent. Fallback to `remote_collab.remote`.
- Working tree clean (git status check, excluding `.purlin/` files per collaboration policy).

### 2.6 First-Push Safety Confirmation

On the first push to a remote+branch pair, detected by `git rev-parse --verify <remote>/<branch>` failing (no remote tracking ref exists), display a confirmation prompt:

```
First push to this remote. Please confirm:
  Remote:  <name> (<url>)
  Branch:  <branch>
  Commits: <N> commit(s) will be pushed

Proceed? [Y/n]
```

If the user declines, abort without pushing. Subsequent pushes to the same remote+branch (where the remote tracking ref exists) skip this confirmation.

### 2.7 Push Behavior

Steps (after preconditions pass):

1. `git fetch <remote>`
2. Two-range query: `git log <remote>/<branch>..<branch> --oneline` (ahead), `git log <branch>..<remote>/<branch> --oneline` (behind)
3. **SAME**: "Already in sync. Nothing to push." Exit 0.
4. **BEHIND**: "Local <branch> is BEHIND `<remote>/<branch>` by M commits. Run `/pl-remote-pull` before pushing." Exit 1.
5. **DIVERGED**: Print incoming commits. Instruct `/pl-remote-pull`. Exit 1.
6. **AHEAD**: `git push <remote> <branch>`. Report "Pushed N commits to `<remote>/<branch>`." On push failure: print git error, exit 1.

If the remote tracking ref does not exist (first push), treat as AHEAD with ahead = all commits on `<branch>`. The first-push safety confirmation (2.6) applies before the actual push.

### 2.8 FORBIDDEN Pattern Enforcement

The command MUST NOT execute any operation that violates the FORBIDDEN patterns in `policy_branch_collab.md` Section 4:

- MUST NOT `git push --force` to any branch. If push fails due to non-fast-forward, report the error and instruct `/pl-remote-pull`.
- MUST NOT push to a branch that does not match the resolved collaboration branch (enforced by the Collaboration Branch Guard in Section 2.3).
- User-provided input (remote names, branch names) MUST be validated against shell injection. Branch names are resolved from `.purlin/runtime/active_branch` or defaulted to `main` — never from unchecked user input passed directly to git commands.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-remote-push Resolves To Main When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And a remote "origin" is configured
    And local main has 2 commits not in origin/main
    When /pl-remote-push is invoked
    Then the collaboration branch resolves to main
    And git push origin main is executed
    And the command reports "Pushed 2 commits"

#### Scenario: pl-remote-push Rejects Non-Main Branch When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is hotfix/urgent
    When /pl-remote-push is invoked
    Then the command prints "No active collaboration branch"
    And the command prints "Switch to main"
    And exits with code 1

#### Scenario: pl-remote-push Detects No Remote And Prompts For Setup

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And no git remotes are configured
    When /pl-remote-push is invoked
    Then the command detects no remotes via git remote -v
    And prompts the user to add a remote

#### Scenario: pl-remote-push Offers gh Repo Create When gh CLI Available

    Given no git remotes are configured
    And the current branch is main
    And the gh CLI is available
    When /pl-remote-push is invoked and detects no remotes
    Then the command offers "Create a new GitHub repository" as an option
    And offers "Add an existing remote URL" as an option

#### Scenario: pl-remote-push First Push To Empty Remote Succeeds

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main does not exist (no remote tracking ref)
    And local main has 5 commits
    When /pl-remote-push is invoked
    And the user confirms the first-push safety prompt
    Then git push origin main is executed
    And the command reports "Pushed 5 commits"

#### Scenario: pl-remote-push First Push Shows Safety Confirmation

    Given the current branch is main
    And a remote "origin" is configured with URL "git@github.com:user/repo.git"
    And origin/main does not exist (no remote tracking ref)
    And local main has 3 commits
    When /pl-remote-push is invoked
    Then the command displays remote name "origin", URL, branch "main", and "3 commit(s)"
    And waits for user confirmation before pushing

#### Scenario: pl-remote-push First Push Aborted When User Declines

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main does not exist (no remote tracking ref)
    When /pl-remote-push is invoked
    And the user declines the first-push safety prompt
    Then no git push is executed
    And exits with code 1

#### Scenario: pl-remote-push Subsequent Push Skips Confirmation

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main exists (remote tracking ref is present)
    And local main has 2 commits not in origin/main
    When /pl-remote-push is invoked
    Then no safety confirmation is displayed
    And git push origin main is executed

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
