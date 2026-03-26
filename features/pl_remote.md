# Feature: /pl-remote Branch Collaboration

> Label: "/pl-remote Branch Collaboration"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_agent_launcher.md
> Prerequisite: features/policy_branch_collab.md

## 1. Overview

The `/pl-remote` skill is the single entry point for branch collaboration operations. It provides four subcommands — `push`, `pull`, `add`, and `branch` — that manage remote configuration, branch lifecycle, and synchronization between machines. Push and pull resolve the collaboration branch from `.purlin/runtime/active_branch` (defaulting to `main` when absent), enforce safety preconditions, and operate within the sync-state model defined in `policy_branch_collab.md`. Branch manages the collaboration branch lifecycle (create, join, leave, list). Add handles remote configuration with guided setup, SSH key management, and connectivity verification.

---

## 2. Requirements

### 2.1 Invocation Syntax

```
/pl-remote push                                — Push collaboration branch to remote
/pl-remote pull [<branch>]                     — Pull remote branch into local
/pl-remote add [<url>] [--name <remote-name>]  — Configure a git remote
/pl-remote branch create <name>                — Create and switch to a collaboration branch
/pl-remote branch join <name>                  — Switch to an existing collaboration branch
/pl-remote branch leave                        — Return to main and clear active branch
/pl-remote branch list                         — List available collaboration branches
```

- **No subcommand or invalid subcommand:** Print usage summary with the four subcommands and exit. Do NOT guess intent.
- **Legacy agent routing:** Legacy agents use `/pl-remote-push`, `/pl-remote-pull`, `/pl-remote-add` instead.

### 2.2 Consolidation

- Old skill files (`pl-remote-push.md`, `pl-remote-pull.md`, `pl-remote-add.md`) have been tombstoned.
- The consolidated skill MUST handle all four subcommands.

### 2.3 Contextual Next-Step Guidance

Every subcommand exit point — success, error, or no-op — MUST suggest the logical next action. Users should never hit a dead end. The guidance chain forms a discoverable onboarding path:

| Exit Point | Suggested Next Step |
|------------|-------------------|
| `add` success | `/pl-remote branch create <name>` or `/pl-remote push` |
| `branch create` success | `/pl-remote push` and `/pl-remote pull` to sync |
| `branch join` success | `/pl-remote push` and `/pl-remote pull` to sync |
| `branch leave` success | `/pl-remote branch join <name>` to rejoin |
| `branch list` (no branches) | `/pl-remote branch create <name>` to start one |
| `push` / `pull` — no remote | `/pl-remote add` to configure a remote |
| `push` / `pull` — no active branch, wrong branch | `/pl-remote branch create <name>` or switch to main |
| `push` — BEHIND/DIVERGED | `/pl-remote pull` before pushing |
| `pull` — AHEAD | `/pl-remote push` when ready |
| No subcommand / invalid | Print full usage with all four subcommands |

This table is normative — each message MUST include the suggested command. The user should be able to go from zero (no remote, no branch) to collaborating by following the suggestions.

### 2.4 Config Reading

Read remote name from `.purlin/config.json`:

1. Check `branch_collab.remote`.
2. If absent, fall back to `remote_collab.remote`.
3. If both absent, default to `"origin"`.

This resolution order applies to ALL subcommands and to the extraction tool (`tools/collab/extract_whats_different.py`).

### 2.5 Collaboration Branch Resolution

Per `policy_branch_collab.md` Section 2.4:

1. Read `.purlin/runtime/active_branch`.
2. If present and non-empty: collaboration branch = that value.
3. If absent or empty: collaboration branch = `main`.

Push and pull (no-argument mode) both resolve the collaboration branch this way.

### 2.6 Collaboration Branch Guard (push and pull no-argument mode)

```
git rev-parse --abbrev-ref HEAD
```

If the current branch does not match the resolved collaboration branch:

- **Active branch exists:** Abort: `"This command must be run from the collaboration branch (<branch>). Current branch: <current>."`
- **No active branch (direct mode):** Abort: `"No active collaboration branch. On main, /pl-remote <push|pull> operates on main directly. Current branch: <current>. Switch to main or create a collaboration branch with /pl-remote branch create <name>."`

### 2.7 Remote Guard (all subcommands except add)

```
git remote -v
```

If no remotes exist: `"No git remote configured. Run /pl-remote add to set up a remote first."` Exit 1.

### 2.8 Working Tree Check (push and pull)

Run `git status --porcelain`. If any staged or unstaged modifications exist to tracked files outside `.purlin/`:

- Push: `"Commit or stash changes before pushing."` Exit 1.
- Pull: `"Commit or stash changes before pulling."` Exit 1.

Untracked files are ignored. Changes inside `.purlin/` are exempt per `policy_branch_collab.md` Section 2.10.

---

### 2.10 Subcommand: push

Push the local collaboration branch to the remote.

#### 2.10.1 Preconditions

Execute in order: Collaboration Branch Resolution (2.5) → Branch Guard (2.6) → Remote Guard (2.7) → Working Tree Check (2.8) → Config Reading (2.4).

#### 2.10.2 First-Push Safety Confirmation

Detected by `git rev-parse --verify <remote>/<branch>` failing (no remote tracking ref). Display:

```
First push to this remote. Please confirm:
  Remote:  <name> (<url>)
  Branch:  <branch>
  Commits: <N> commit(s) will be pushed

Proceed? [Y/n]
```

If declined, abort without pushing. Subsequent pushes (where the remote tracking ref exists) skip this confirmation.

#### 2.10.3 Sync State Logic

1. `git fetch <remote>`
2. Two-range query:
   - Ahead: `git log <remote>/<branch>..<branch> --oneline`
   - Behind: `git log <branch>..<remote>/<branch> --oneline`
3. **SAME:** `"Already in sync. Nothing to push."` Exit 0.
4. **BEHIND:** `"Local <branch> is BEHIND <remote>/<branch> by M commits. Run /pl-remote pull before pushing."` Exit 1.
5. **DIVERGED:** Print incoming commits from remote. Instruct to run `/pl-remote pull`. Exit 1.
6. **AHEAD:** Execute `git push <remote> <branch>`. Report `"Pushed N commits to <remote>/<branch>."` On push failure: print git error, exit 1.

If the remote tracking ref does not exist (first push), treat as AHEAD. The first-push safety confirmation (2.10.2) applies before the actual push.

#### 2.10.4 FORBIDDEN Patterns

- MUST NOT `git push --force` to any branch.
- MUST NOT push to a branch that does not match the resolved collaboration branch.
- User-provided input MUST be validated against shell injection.

---

### 2.20 Subcommand: pull

Pull the remote collaboration branch into the local branch via merge.

#### 2.20.1 Modes

- **No-argument mode:** Resolve collaboration branch per Section 2.5. Execute Branch Guard (2.6) → Remote Guard (2.7) → Working Tree Check (2.8) → Config Reading (2.4).
- **Explicit-branch mode** (`/pl-remote pull RC0.8.0`): Use the argument as `<branch>` directly. Skip Branch Resolution and Branch Guard. Execute Remote Guard (2.7) → Working Tree Check (2.8) → Config Reading (2.4). Runs from any branch (typically `main`).

#### 2.20.2 First-Pull Safety Confirmation

Detected by `git merge-base <branch> <remote>/<branch>` failing (no common ancestor). Display:

```
First pull from this remote. Please confirm:
  Remote:   <name> (<url>)
  Branch:   <branch>
  Incoming: <N> commit(s) will be merged

Proceed? [Y/n]
```

If declined, abort without merging. Subsequent pulls (where a merge-base exists) skip this confirmation.

#### 2.20.3 Sync State Logic

1. `git fetch <remote>`
2. Two-range query (in explicit-branch mode, replace `<branch>` with `HEAD` for the local side):
   - Ahead: `git log <remote>/<branch>..<branch> --oneline`
   - Behind: `git log <branch>..<remote>/<branch> --oneline`
3. **SAME:** `"Local <branch> is already in sync with remote."` Exit 0.
4. **AHEAD:** `"Local <branch> is AHEAD by N commits. Nothing to pull — run /pl-remote push when ready."` Exit 0.
5. **BEHIND:** `git merge --ff-only <remote>/<branch>`. Report `"Fast-forwarded local <branch> by M commits from <remote>/<branch>."` On ff-failure (race condition): `"Fast-forward failed — re-run /pl-remote pull."` Exit 1.
6. **DIVERGED:** Print pre-merge context (`git log <branch>..<remote>/<branch> --stat --oneline`). Run `git merge <remote>/<branch>`. On conflict: print per-file conflict context (commits from each side that touched each conflicting file); provide resolution instructions (`git add` + `git merge --continue` or `git merge --abort`); exit 1.

#### 2.20.4 Post-Merge Digest Generation

After a successful merge (BEHIND fast-forward or DIVERGED clean merge), auto-generate the "What's Different?" digest:

1. Run: `bash <tools_root>/collab/generate_whats_different.sh <branch>`
2. Read `features/digests/whats-different.md` and display inline.
3. If the script fails or the file is not written, print a warning and continue. The digest is informational — it does NOT block or fail the pull.

Skip this step when the merge result is SAME, AHEAD, or DIVERGED-with-conflicts.

#### 2.20.5 FORBIDDEN Patterns

- MUST NOT rebase the collaboration branch. Uses `git merge` exclusively.
- MUST NOT push to any branch. This is a pull-only subcommand.
- MUST NOT auto-resolve merge conflicts. Conflict resolution is a human responsibility.
- In no-argument mode, MUST NOT proceed when the current branch does not match the resolved collaboration branch.

---

### 2.30 Subcommand: add

Configure a git remote. This is a configuration-only command — no push or pull operations.

#### 2.30.1 Invocation

```
/pl-remote add [<url>] [--name <remote-name>]
```

- `<url>` (optional): If provided, skip the help banner and URL prompt.
- `--name <remote-name>` (optional): If provided, skip the name prompt. Default: `"origin"`.
- No branch guard. No dirty check. No working tree inspection.

#### 2.30.2 Mode 1: No Remotes Configured (Guided Setup)

When `git remote -v` returns empty:

1. If no `<url>` argument, print the help banner (2.30.3) and run hosting hints scan (2.30.4).
2. Prompt for URL (2.30.5) — or use `<url>` argument if provided.
3. Prompt for remote name (2.30.6) — or use `--name` argument if provided.
4. Execute `git remote add <name> <url>`.
5. Verify connectivity (2.30.7).
6. Print success output (2.30.8).

#### 2.30.3 Help Banner

Displayed when invoked without a `<url>` argument and no remotes are configured:

```
/pl-remote add — Configure a git remote for this project

This connects your project to a remote repository so you can
push, pull, and collaborate on branches with /pl-remote.

Supported URL formats:
  git@github.com:user/repo.git     (SSH)
  https://github.com/user/repo.git (HTTPS)
  ssh://git@host/path/repo.git     (SSH URL)
  /path/to/bare/repo.git           (local)
```

If hosting hints are detected (2.30.4), append them below the format list.

#### 2.30.4 Hosting Hints Scan

Scan for hosting-provider hints:

- Check `~/.ssh/config` for configured hosts (e.g., `github.com`, `gitlab.com`, `bitbucket.org`).
- Check git credential helpers via `git config --global --get-regexp credential`.
- Check for hosting CLIs: `gh` (GitHub), `glab` (GitLab).

Present findings as informational suggestions (e.g., `"Detected: github.com (SSH key)"`). Do not auto-select any host.

#### 2.30.5 URL Prompt, Normalization, and Validation

- If `<url>` argument was provided, skip the prompt and validate directly.
- Otherwise prompt: `"Enter a git remote URL (SSH or HTTPS — any git-compatible host). You can paste a browser URL too."`
- Accept any valid git URL format: `git@host:user/repo.git`, `https://host/user/repo.git`, `ssh://...`, or local paths.
- **Browser URL normalization:** If the user pastes a browser URL (e.g., `https://bitbucket.org/team/repo/src/main/` or `https://github.com/user/repo/tree/main`):
  1. Strip trailing path segments after the repo name (`/src/main/`, `/tree/main`, `/blob/...`, etc.).
  2. Append `.git` if not present.
  3. Convert to SSH format: `git@<host>:<owner>/<repo>.git`.
  4. Show and confirm: `"Normalized to: git@bitbucket.org:team/repo.git — use this? [Y/n]"`
  5. If declined, prompt for manual entry.

#### 2.30.6 Remote Name Prompt

- If `--name` argument was provided, skip the prompt.
- Otherwise, prompt for the remote name with default `"origin"`.

#### 2.30.7 Mode 2: Remote(s) Already Configured

When `git remote -v` returns one or more remotes:

1. Display current remote(s): name and URL for each.
2. If both `<url>` and `--name` arguments are provided:
   - Named remote exists: `git remote set-url <name> <url>`.
   - Named remote does not exist: `git remote add <name> <url>`.
3. If arguments are not provided, present options:
   - **Change URL:** Numbered list of remotes. Prompt: `"Which remote to update?"` Default: `"origin"` if it exists. Then prompt for new URL. Execute `git remote set-url <name> <new-url>`.
   - **Add additional remote:** Prompt for name (must not conflict) and URL. Execute `git remote add <name> <url>`.
4. Verify connectivity (2.30.8).
5. Print success output (2.30.9).

#### 2.30.8 Connectivity Verification

Run `git ls-remote <name>`.

- **Success:** Proceed to success output.
- **Failure — classify error:**
  1. **SSH auth failure** (stderr contains "Permission denied", "publickey"): Proceed to SSH Key Setup Flow (2.30.8.1).
  2. **HTTPS auth failure** (stderr contains "403", "authentication"): Suggest switching to SSH (offer URL conversion) or setting up a credential helper.
  3. **Network failure** (stderr contains "Could not resolve host", "Network is unreachable"): Offer URL correction.
  4. **Rollback on decline:**
     - Remote was **newly added** (`git remote add`): remove via `git remote remove <name>`.
     - Remote **already existed** (`git remote set-url`): restore previous URL via `git remote set-url <name> <old-url>`. The old URL MUST be captured before attempting set-url.
     - Exit 1.

#### 2.30.8.1 SSH Key Setup Flow

When SSH authentication fails, handle the entire setup. The user should only need to copy-paste one public key into their host's web UI.

**Step 1 — Check for existing keys:**
- Read `~/.ssh/` for existing key files (`id_ed25519`, `id_rsa`, `id_ecdsa`, and `.pub` counterparts).
- If a suitable key exists, skip to Step 3.

**Step 2 — Generate a new key (if none found):**
- `mkdir -p ~/.ssh && chmod 700 ~/.ssh` if needed.
- `ssh-keygen -t ed25519 -C "<user.email from git config>" -f ~/.ssh/id_ed25519 -N ""`
- The skill runs this directly — do NOT ask the user to run commands.

**Step 3 — Ensure the host is in known_hosts:**
- `ssh-keyscan <host> >> ~/.ssh/known_hosts 2>/dev/null`

**Step 4 — Display the public key:**
- Read and display `~/.ssh/id_ed25519.pub` (or whichever key was found/generated).
- Print hosting-provider-specific URL for adding SSH keys:
  - `github.com` → `https://github.com/settings/keys`
  - `bitbucket.org` → `https://bitbucket.org/account/settings/ssh-keys/`
  - `gitlab.com` → `https://gitlab.com/-/user_settings/ssh_keys`
  - Other → `"Add this public key to your SSH keys on <host>"`
- Format: `"Copy this key and add it at <url>:\n\n<key contents>\n\nPress Enter when done."`

**Step 5 — Wait and re-verify:**
- After user confirms, re-run `git ls-remote <name>`.
- Success: proceed to success output.
- Failure: report error, offer retry or rollback.

**Constraints:**
- MUST NOT ask the user to run terminal commands.
- MUST NOT overwrite existing SSH keys without asking.
- If `id_ed25519` exists but auth still fails, skip to Step 4 (display existing key for user to add).

#### 2.30.9 Success Output

```
Remote configured:
  Name:   <name>
  URL:    <url>
  Status: Connected

Next steps:
  /pl-remote branch create <name>   Start a collaboration branch
  /pl-remote push                   Push current branch to remote
```

#### 2.30.10 Config Sync

After a successful add or set-url, check whether the remote name matches `branch_collab.remote` in config (per Section 2.4 resolution order).

- Name matches config (or is `"origin"` and no config override): no action.
- Name does NOT match and is the **only** remote: Prompt: `"Remote <name> is not the default (origin). Should /pl-remote push and /pl-remote pull use <name> as the default remote? [Y/n]"` If yes, write `branch_collab.remote` to `.purlin/config.json`.
- Multiple remotes: Inform which remote push/pull will use. Suggest updating config to change the default.

#### 2.30.11 FORBIDDEN Patterns

- MUST NOT execute any push or pull operations. Configuration-only command.
- MUST NOT delete existing remotes unless rolling back a **newly added** remote after a failed connectivity check. For existing remotes where set-url was used, rollback restores the old URL — never removes.
- User-provided remote names and URLs MUST be properly quoted to prevent shell injection.

---

### 2.40 Subcommand: branch

Manage the collaboration branch lifecycle — creating, joining, leaving, and listing collaboration branches.

#### 2.40.1 Invocation

```
/pl-remote branch create <name>   — Create and switch to a collaboration branch
/pl-remote branch join <name>     — Switch to an existing remote branch
/pl-remote branch leave           — Return to main and clear active branch
/pl-remote branch list            — List available collaboration branches
/pl-remote branch                 — (no sub-subcommand) Print branch subcommand usage
```

#### 2.40.2 branch create

Create a new collaboration branch from the current HEAD and push it to the remote.

**Preconditions:**
- Remote Guard (2.6): a remote must be configured.
- Working Tree Check (2.7): working tree must be clean.
- Must be on `main` (creating branches from other collaboration branches is not supported).
- Branch name must not already exist locally or on the remote.

**Steps:**
1. `git checkout -b <name>` — create and switch to the new branch.
2. `git push -u <remote> <name>` — push to remote so other collaborators can discover it.
3. Write `<name>` to `.purlin/runtime/active_branch`.
4. Store `main` in `.purlin/runtime/branch_collab_base` (the branch to return to on leave).

**Output:**
```
Created collaboration branch: <name>
  Pushed to: <remote>/<name>
  Active branch set. Use /pl-remote push and /pl-remote pull to sync.
  Use /pl-remote branch leave to return to main.
```

#### 2.40.3 branch join

Switch to an existing collaboration branch that is already on the remote.

**Preconditions:**
- Remote Guard (2.6).
- Working Tree Check (2.7).
- `git fetch <remote>` — refresh remote state.
- Branch must exist on the remote (`git rev-parse --verify <remote>/<name>`).

**Steps:**
1. If the branch exists locally: `git checkout <name>` and `git merge --ff-only <remote>/<name>` to catch up.
2. If the branch does not exist locally: `git checkout -b <name> <remote>/<name>` — create local tracking branch.
3. Write `<name>` to `.purlin/runtime/active_branch`.
4. Store the current branch in `.purlin/runtime/branch_collab_base`.

**Output:**
```
Joined collaboration branch: <name>
  Tracking: <remote>/<name>
  Local branch is up to date.
  Use /pl-remote push and /pl-remote pull to sync.
```

#### 2.40.4 branch leave

Return to the base branch and clear the active branch state.

**Preconditions:**
- Working Tree Check (2.7).
- An active branch must exist (`.purlin/runtime/active_branch` is non-empty). If no active branch: `"No active collaboration branch. Nothing to leave."` Exit 0.

**Steps:**
1. Read the base branch from `.purlin/runtime/branch_collab_base` (default: `main` if absent).
2. `git checkout <base>`.
3. Clear `.purlin/runtime/active_branch` (truncate to empty).
4. Delete `.purlin/runtime/branch_collab_base`.

**Output:**
```
Left collaboration branch: <name>
  Returned to: <base>
  The branch still exists locally and on the remote.
  Use /pl-remote branch join <name> to rejoin.
```

Does NOT delete the branch. The branch remains joinable by this machine or other collaborators.

#### 2.40.5 branch list

List collaboration branches available on the remote.

**Steps:**
1. `git fetch <remote>` — refresh remote state.
2. `git branch -r` — list remote branches, filter out `HEAD`, `main`, `master`.
3. Read `.purlin/runtime/active_branch` to identify the currently active branch (if any).

**Output:**
```
Collaboration branches on <remote>:
  * <active-branch>  (active)
    <other-branch-1>
    <other-branch-2>

Use /pl-remote branch join <name> to switch branches.
```

If no collaboration branches exist: `"No collaboration branches on <remote>. Use /pl-remote branch create <name> to start one."`

#### 2.40.6 FORBIDDEN Patterns

- `branch create` MUST NOT create from a non-main branch.
- `branch leave` MUST NOT delete the branch (local or remote).
- `branch join` MUST NOT force-checkout when the working tree is dirty.
- Branch names are user input — validate and quote to prevent shell injection.

---

## 3. Scenarios

### Unit Tests

<!-- branch scenarios -->

#### Scenario: branch create Creates And Pushes New Branch

    Given the current branch is main
    And a remote "origin" is configured
    And the working tree is clean
    When /pl-remote branch create feature/collab is invoked
    Then git checkout -b feature/collab is executed
    And git push -u origin feature/collab is executed
    And .purlin/runtime/active_branch contains "feature/collab"
    And the command prints "Created collaboration branch: feature/collab"

#### Scenario: branch create Rejects When Not On Main

    Given the current branch is feature/other
    When /pl-remote branch create feature/collab is invoked
    Then the command prints that branch creation must be from main
    And exits with code 1

#### Scenario: branch create Rejects Existing Branch Name

    Given the current branch is main
    And a remote branch "origin/feature/collab" already exists
    When /pl-remote branch create feature/collab is invoked
    Then the command prints that the branch already exists
    And exits with code 1

#### Scenario: branch create Rejects When No Remote

    Given no git remotes are configured
    When /pl-remote branch create feature/collab is invoked
    Then the command prints "No git remote configured. Run /pl-remote add to set up a remote first."
    And exits with code 1

#### Scenario: branch join Switches To Existing Remote Branch

    Given the current branch is main
    And a remote "origin" is configured
    And origin/feature/collab exists
    And feature/collab does not exist locally
    When /pl-remote branch join feature/collab is invoked
    Then git checkout -b feature/collab origin/feature/collab is executed
    And .purlin/runtime/active_branch contains "feature/collab"
    And the command prints "Joined collaboration branch: feature/collab"

#### Scenario: branch join Fast-Forwards Local Branch

    Given the current branch is main
    And feature/collab exists locally
    And origin/feature/collab has 2 commits ahead of local feature/collab
    When /pl-remote branch join feature/collab is invoked
    Then git checkout feature/collab is executed
    And git merge --ff-only origin/feature/collab is executed
    And .purlin/runtime/active_branch contains "feature/collab"

#### Scenario: branch join Rejects Nonexistent Remote Branch

    Given the current branch is main
    And a remote "origin" is configured
    And origin/feature/nonexistent does not exist
    When /pl-remote branch join feature/nonexistent is invoked
    Then the command prints that the branch does not exist on the remote
    And suggests /pl-remote branch create or /pl-remote branch list
    And exits with code 1

#### Scenario: branch leave Returns To Main

    Given the current branch is feature/collab
    And .purlin/runtime/active_branch contains "feature/collab"
    And .purlin/runtime/branch_collab_base contains "main"
    When /pl-remote branch leave is invoked
    Then git checkout main is executed
    And .purlin/runtime/active_branch is empty
    And .purlin/runtime/branch_collab_base is deleted
    And the command prints "Left collaboration branch: feature/collab"

#### Scenario: branch leave Is No-Op When No Active Branch

    Given .purlin/runtime/active_branch is empty or absent
    When /pl-remote branch leave is invoked
    Then the command prints "No active collaboration branch. Nothing to leave."
    And exits with code 0

#### Scenario: branch leave Does Not Delete The Branch

    Given the current branch is feature/collab
    And .purlin/runtime/active_branch contains "feature/collab"
    When /pl-remote branch leave is invoked
    Then no git branch -d or git push --delete is executed
    And the branch still exists locally and on the remote

#### Scenario: branch list Shows Remote Branches

    Given a remote "origin" is configured
    And origin has branches feature/collab and feature/auth
    And .purlin/runtime/active_branch contains "feature/collab"
    When /pl-remote branch list is invoked
    Then the output shows feature/collab marked as active
    And the output shows feature/auth
    And main and master are not listed

#### Scenario: branch list Shows Empty Message When No Branches

    Given a remote "origin" is configured
    And origin has no branches other than main
    When /pl-remote branch list is invoked
    Then the command prints "No collaboration branches on origin"
    And suggests /pl-remote branch create

<!-- push scenarios -->

### Unit Tests

<!-- push scenarios -->

#### Scenario: push Resolves To Main When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And a remote "origin" is configured
    And local main has 2 commits not in origin/main
    When /pl-remote push is invoked
    Then the collaboration branch resolves to main
    And git push origin main is executed
    And the command reports "Pushed 2 commits"

#### Scenario: push Rejects Non-Main Branch When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is hotfix/urgent
    When /pl-remote push is invoked
    Then the command prints "No active collaboration branch"
    And the command prints "Switch to main"
    And exits with code 1

#### Scenario: push Exits With Guidance When No Remote Configured

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And no git remotes are configured
    When /pl-remote push is invoked
    Then the command prints "No git remote configured. Run /pl-remote add to set up a remote first."
    And exits with code 1

#### Scenario: push First Push Shows Safety Confirmation

    Given the current branch is main
    And a remote "origin" is configured with URL "git@github.com:user/repo.git"
    And origin/main does not exist (no remote tracking ref)
    And local main has 3 commits
    When /pl-remote push is invoked
    Then the command displays remote name "origin", URL, branch "main", and "3 commit(s)"
    And waits for user confirmation before pushing

#### Scenario: push First Push To Empty Remote Succeeds

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main does not exist (no remote tracking ref)
    And local main has 5 commits
    When /pl-remote push is invoked
    And the user confirms the first-push safety prompt
    Then git push origin main is executed
    And the command reports "Pushed 5 commits"

#### Scenario: push First Push Aborted When User Declines

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main does not exist (no remote tracking ref)
    When /pl-remote push is invoked
    And the user declines the first-push safety prompt
    Then no git push is executed
    And exits with code 1

#### Scenario: push Subsequent Push Skips Confirmation

    Given the current branch is main
    And a remote "origin" is configured
    And origin/main exists (remote tracking ref is present)
    And local main has 2 commits not in origin/main
    When /pl-remote push is invoked
    Then no safety confirmation is displayed
    And git push origin main is executed

#### Scenario: push Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote push is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1

#### Scenario: push Exits When On Wrong Branch

    Given the current branch is hotfix/urgent
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote push is invoked
    Then the command prints "This command must be run from the collaboration branch (feature/auth)"
    And exits with code 1

#### Scenario: push Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed

#### Scenario: push Blocked When Local Is BEHIND Remote

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote push is invoked
    Then the command prints "Local feature/auth is BEHIND" and instructs to run /pl-remote pull
    And exits with code 1

#### Scenario: push Blocked When Local Is DIVERGED

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    When /pl-remote push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-remote pull
    And exits with code 1

#### Scenario: push Succeeds When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote push is invoked
    Then git push origin feature/auth is executed
    And the command reports "Pushed 3 commits"

#### Scenario: push Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed

<!-- pull scenarios -->

#### Scenario: pull Resolves To Main When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And a remote "origin" is configured
    And origin/main has 3 commits not in local main
    When /pl-remote pull is invoked
    Then the collaboration branch resolves to main
    And git merge --ff-only origin/main is executed
    And the command reports "Fast-forwarded local main by 3 commits"

#### Scenario: pull Rejects Non-Main Branch When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is hotfix/urgent
    When /pl-remote pull is invoked
    Then the command prints "No active collaboration branch"
    And the command prints "Switch to main"
    And exits with code 1

#### Scenario: pull Exits With Guidance When No Remote Configured

    Given no file exists at .purlin/runtime/active_branch
    And the current branch is main
    And no git remotes are configured
    When /pl-remote pull is invoked
    Then the command prints "No git remote configured. Run /pl-remote add to set up a remote first."
    And exits with code 1

#### Scenario: pull First Pull Shows Safety Confirmation

    Given the current branch is main
    And a remote "origin" is configured with URL "git@github.com:user/repo.git"
    And local main has no merge-base with origin/main
    And origin/main has 4 commits
    When /pl-remote pull is invoked
    Then the command displays remote name "origin", URL, branch "main", and "4 commit(s)"
    And waits for user confirmation before merging

#### Scenario: pull First Pull Aborted When User Declines

    Given the current branch is main
    And a remote "origin" is configured
    And local main has no merge-base with origin/main
    When /pl-remote pull is invoked
    And the user declines the first-pull safety prompt
    Then no git merge is executed
    And exits with code 1

#### Scenario: pull Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote pull is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1

#### Scenario: pull Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed

#### Scenario: pull Fast-Forwards When BEHIND

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 3 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote pull is invoked
    Then git merge --ff-only origin/feature/auth is executed
    And the command reports "Fast-forwarded local feature/auth by 3 commits"

#### Scenario: pull Creates Merge Commit When DIVERGED No Conflicts

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    And the changes do not conflict
    When /pl-remote pull is invoked
    Then git merge origin/feature/auth creates a merge commit
    And the command reports success

#### Scenario: pull Exits On Conflict With Per-File Context

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth have conflicting changes to features/foo.md
    When /pl-remote pull is invoked
    Then git merge origin/feature/auth halts with conflicts
    And the command prints commits from each side that touched features/foo.md
    And provides instructions for git add and git merge --continue or git merge --abort
    And exits with code 1

#### Scenario: pull Is No-Op When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 2 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote pull is invoked
    Then the command prints "Local feature/auth is AHEAD by 2 commits. Nothing to pull"
    And no git merge is executed

#### Scenario: pull Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote pull is invoked
    Then the command prints "Local feature/auth is already in sync with remote"
    And no git merge is executed

#### Scenario: pull Generates Digest After Successful Merge

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 3 commits not in local feature/auth
    When /pl-remote pull is invoked and the fast-forward succeeds
    Then the command runs generate_whats_different.sh for the branch
    And the digest output is displayed inline
    And if the digest script fails the pull still reports success with a warning

#### Scenario: pull Explicit Branch Skips Branch Guard

    Given the current branch is main
    And a remote "origin" is configured
    And origin/RC0.8.0 has 5 commits not in local main
    When /pl-remote pull RC0.8.0 is invoked
    Then no branch guard check is performed
    And git merge origin/RC0.8.0 is executed from main

<!-- add scenarios -->

#### Scenario: add Prints Help Banner When No Args And No Remote

    Given no git remotes are configured
    When /pl-remote add is invoked with no arguments
    Then the command prints a help banner containing "Configure a git remote"
    And the banner lists supported URL formats including SSH and HTTPS examples
    And the command prompts for a git remote URL

#### Scenario: add Guides Setup When No Remote Exists

    Given no git remotes are configured
    And the user provides URL "git@github.com:user/repo.git" when prompted
    And the user accepts the default remote name "origin"
    When /pl-remote add completes the guided setup
    Then git remote add origin git@github.com:user/repo.git is executed
    And git ls-remote origin is executed to verify connectivity
    And the command prints "Remote configured" with name "origin" and the URL

#### Scenario: add Shows Hosting Hints When Available

    Given no git remotes are configured
    And ~/.ssh/config contains a Host entry for github.com
    When /pl-remote add is invoked with no arguments
    Then the command displays "Detected: github.com (SSH key)" as an informational hint
    And does not auto-select any host

#### Scenario: add Skips Banner When URL Argument Provided

    Given no git remotes are configured
    When /pl-remote add git@github.com:user/repo.git is invoked
    Then the command does not print the help banner
    And prompts for remote name (default "origin")
    And executes git remote add with the provided URL

#### Scenario: add Accepts Both URL And Name Arguments

    Given no git remotes are configured
    When /pl-remote add git@github.com:user/repo.git --name upstream is invoked
    Then the command skips both prompts
    And executes git remote add upstream git@github.com:user/repo.git
    And verifies connectivity via git ls-remote upstream

#### Scenario: add Shows Existing Remotes When Remote Already Configured

    Given a remote "origin" is configured with URL "git@github.com:user/repo.git"
    When /pl-remote add is invoked with no arguments
    Then the command displays the existing remote name "origin" and its URL
    And offers to change the URL or add an additional remote

#### Scenario: add Changes URL When Named Remote Exists And URL Provided

    Given a remote "origin" is configured with URL "git@github.com:user/old-repo.git"
    When /pl-remote add git@github.com:user/new-repo.git --name origin is invoked
    Then the command executes git remote set-url origin git@github.com:user/new-repo.git
    And verifies connectivity via git ls-remote origin
    And prints "Remote configured" with the new URL

#### Scenario: add Adds New Remote When Named Remote Does Not Exist

    Given a remote "origin" is configured
    When /pl-remote add git@github.com:user/fork.git --name upstream is invoked
    Then the command executes git remote add upstream git@github.com:user/fork.git
    And verifies connectivity via git ls-remote upstream

#### Scenario: add Reports Connectivity Failure And Classifies Error

    Given no git remotes are configured
    And the user provides a URL with an SSH auth failure
    When the remote is added via git remote add
    Then git ls-remote fails
    And the command suggests checking SSH keys or credentials
    And offers the user a chance to correct the URL

#### Scenario: add Rolls Back New Remote On Declined Correction

    Given no git remotes are configured
    And the user provides an unreachable URL
    When git ls-remote fails and the user declines to correct
    Then the command executes git remote remove to clean up the failed add
    And exits with code 1

#### Scenario: add Restores Old URL On Set-Url Failure

    Given a remote "origin" is configured with URL "git@github.com:user/old-repo.git"
    When /pl-remote add git@bad-host:user/repo.git --name origin is invoked
    And git ls-remote fails and the user declines to correct
    Then the command restores the original URL "git@github.com:user/old-repo.git"
    And does not remove the remote

#### Scenario: add Normalizes Browser URL to SSH

    Given no git remotes are configured
    When /pl-remote add https://bitbucket.org/team/repo/src/main/ is invoked
    Then the command normalizes to "git@bitbucket.org:team/repo.git"
    And asks the user to confirm the normalized URL
    When the user confirms
    Then git remote add origin git@bitbucket.org:team/repo.git is executed

#### Scenario: add Sets Up SSH Key On Auth Failure

    Given no git remotes are configured
    And no SSH key exists at ~/.ssh/id_ed25519
    When /pl-remote add git@bitbucket.org:team/repo.git is invoked
    And git ls-remote fails with "Permission denied (publickey)"
    Then the command generates an SSH key via ssh-keygen (no user commands)
    And runs ssh-keyscan to add the host to known_hosts
    And displays the public key contents
    And prints the Bitbucket SSH key settings URL
    And waits for the user to confirm the key was added
    When the user confirms
    Then the command re-runs git ls-remote and succeeds

#### Scenario: add Uses Existing SSH Key When Available

    Given no git remotes are configured
    And ~/.ssh/id_ed25519.pub exists
    When /pl-remote add git@github.com:user/repo.git is invoked
    And git ls-remote fails with "Permission denied (publickey)"
    Then the command does NOT generate a new key
    And displays the existing public key contents
    And prints the GitHub SSH key settings URL
    And waits for the user to confirm

#### Scenario: add Does Not Require Branch Guard

    Given an active branch "feature/auth" in .purlin/runtime/active_branch
    And the current branch is main
    When /pl-remote add is invoked
    Then the command does not check the current branch
    And proceeds with remote configuration

#### Scenario: add Does Not Require Clean Working Tree

    Given the working tree has uncommitted changes
    When /pl-remote add is invoked
    Then the command does not check working tree status
    And proceeds with remote configuration

#### Scenario: add Does Not Push Or Pull

    Given no git remotes are configured
    When /pl-remote add is invoked and the remote is successfully added
    Then no git push or git pull is executed
    And the command exits after printing the success summary

#### Scenario: add Prompts Config Sync When Non-Origin Name Is Only Remote

    Given no git remotes are configured
    When /pl-remote add git@github.com:user/repo.git --name upstream is invoked
    And connectivity verification succeeds
    Then the command prompts whether push/pull should use "upstream" as the default
    And if user confirms, branch_collab.remote is set to "upstream" in .purlin/config.json

#### Scenario: add Skips Config Sync When Name Is Origin

    Given no git remotes are configured
    When /pl-remote add git@github.com:user/repo.git --name origin is invoked
    And connectivity verification succeeds
    Then the command does not prompt about config sync
    And .purlin/config.json is not modified

<!-- shared scenarios -->

#### Scenario: Invalid Subcommand Prints Usage

    Given /pl-remote is invoked with argument "foo"
    When the command parses the subcommand
    Then the command prints usage with the four valid subcommands (push, pull, add, branch)
    And exits without performing any git operations

#### Scenario: No Subcommand Prints Usage

    Given /pl-remote is invoked with no arguments
    When the command parses the subcommand
    Then the command prints usage with the four valid subcommands (push, pull, add, branch)
    And exits without performing any git operations

#### Scenario: Config Reads branch_collab Before remote_collab

    Given .purlin/config.json contains branch_collab.remote = "upstream"
    And .purlin/config.json also contains remote_collab.remote = "origin"
    When any /pl-remote subcommand resolves the remote name
    Then "upstream" is used (branch_collab takes precedence)

<!-- onboarding / next-step guidance scenarios -->

#### Scenario: add Success Suggests Next Steps

    Given no git remotes are configured
    When /pl-remote add completes successfully
    Then the success output includes "/pl-remote branch create" as a suggested next step
    And the success output includes "/pl-remote push" as a suggested next step

#### Scenario: push No Remote Suggests add

    Given no git remotes are configured
    When /pl-remote push is invoked
    Then the error message includes "/pl-remote add"

#### Scenario: branch create Success Suggests push and pull

    Given /pl-remote branch create completes successfully
    When the success output is displayed
    Then it includes "/pl-remote push" and "/pl-remote pull" as next steps
    And it includes "/pl-remote branch leave" to return to main

#### Scenario: branch list Empty Suggests create

    Given no collaboration branches exist on the remote
    When /pl-remote branch list is invoked
    Then the output includes "/pl-remote branch create <name>" as a suggestion

### Manual Scenarios (Human Verification Required)

None.
