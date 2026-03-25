# Feature: Purlin Worktree Concurrency

> Label: "Install, Update & Scripts: Purlin Worktree Concurrency"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

Multiple Purlin agents can run concurrently by using git worktrees for isolation. Each agent launched with `--worktree` gets its own copy of the repository, works independently, and merges back when done. A SessionEnd hook (`merge-worktrees.sh`) ensures worktrees are merged even on Ctrl+C exit. The `/pl-merge` skill provides explicit merge-back control. Worktrees are a local parallelism mechanism; remote collaboration uses `pl-push`/`pl-pull` after local merges.

---

## 2. Requirements

### 2.1 Worktree Creation

- `--worktree` flag MUST create a git worktree under `.purlin/worktrees/` with branch name `purlin-<mode>-<timestamp>`.
- The agent MUST operate entirely within the worktree directory.
- `PURLIN_PROJECT_ROOT` MUST be set to the worktree path.
- `.purlin/worktrees/` MUST be listed in `.gitignore` to prevent worktree contents from being accidentally committed to the main repo.

### 2.2 Merge-Back Protocol

- `/pl-merge` MUST commit any pending work in the worktree.
- `/pl-merge` MUST merge the worktree branch back to the source branch.
- On merge conflict with safe files (`.purlin/delivery_plan.md`, `.purlin/cache/*`): auto-resolve by keeping main's version.
- On merge conflict with code or spec files: present the conflict to the user.
- After successful merge: remove worktree and delete branch.
- `.purlin_worktree_label` MUST NOT be committed into the worktree branch. It MUST be excluded from auto-commit (via `.gitignore`) so it does not propagate to the target branch on merge.

### 2.3 SessionEnd Hook

- `tools/hooks/merge-worktrees.sh` MUST be registered as a `SessionEnd` hook in `.claude/settings.json`. The hook is always registered (not dynamically added by `pl-run.sh`) — it is a safe no-op when not running in a worktree.
- The hook MUST fire on all exit types including Ctrl+C (`prompt_input_exit`).
- The hook MUST auto-commit pending changes before merge, including both tracked modifications and untracked files (`git ls-files --others --exclude-standard`).
- The hook MUST NOT use `set -e`. Intermediate failures (e.g., `git add`) must not prevent the merge attempt from being reached. All git commands in the auto-commit block MUST use `|| true` for resilience.
- The hook MUST only process branches matching `purlin-*` pattern.
- On merge conflict: abort merge and preserve worktree with instructions for manual resolution.
- The hook MUST exit 0 in all cases (never block agent exit).

### 2.4 Stale Worktree Detection

- On init.sh refresh: scan `.purlin/worktrees/` and remove invalid worktrees.
- On agent startup: if stale worktrees exist (older than 24h with no recent commits), warn the user.
- `/pl-resume` MUST detect and offer to resume or clean up abandoned worktrees.

### 2.5 Concurrent Session Safety

- Multiple worktree agents MUST NOT share the same worktree directory.
- Branch names MUST include timestamp for uniqueness.
- Merge-back is sequential (one at a time to avoid cascading conflicts).

---

## 3. Scenarios

### Unit Tests

#### Scenario: Worktree branch naming convention

    Given pl-run.sh invoked with --worktree --mode engineer
    When the worktree is created
    Then the branch name matches pattern "purlin-engineer-YYYYMMDD-HHMMSS"

#### Scenario: Worktree directory location

    Given pl-run.sh invoked with --worktree
    When the worktree is created
    Then the worktree directory is under .purlin/worktrees/

#### Scenario: SessionEnd hook skips non-purlin branches

    Given the agent is on a branch named "feature/login"
    When the SessionEnd hook fires
    Then no merge is attempted
    And exit code is 0

#### Scenario: SessionEnd hook auto-commits pending work

    Given the agent is in a purlin worktree with uncommitted changes
    When the SessionEnd hook fires
    Then changes are committed with message "chore: auto-commit on session exit"

#### Scenario: SessionEnd hook auto-commits untracked files

    Given the agent is in a purlin worktree with new untracked files
    When the SessionEnd hook fires
    Then the untracked files are added, committed, and merged to the source branch

#### Scenario: SessionEnd hook handles merge conflict gracefully

    Given the agent is in a purlin worktree
    And the source branch has diverged with conflicting changes
    When the SessionEnd hook fires
    Then the merge is aborted
    And the worktree is preserved
    And instructions for manual resolution are printed to stderr
    And exit code is 0

#### Scenario: Stale worktree cleanup on refresh

    Given .purlin/worktrees/ contains a directory not listed by git worktree list
    When init.sh runs with --refresh
    Then the stale worktree directory is removed

#### Scenario: pl-merge cleans up worktree after successful merge

    Given the agent is in a purlin worktree with committed work
    When /pl-merge is invoked
    Then the worktree branch is merged to the source branch
    And the worktree directory is removed
    And the worktree branch is deleted

### QA Scenarios

#### Scenario: Safe file auto-resolution during merge @auto

    Given a worktree with changes to both src/app.py and .purlin/cache/scan.json
    And the source branch also changed .purlin/cache/scan.json
    When /pl-merge is invoked
    Then .purlin/cache/scan.json conflict is auto-resolved (keep main)
    And src/app.py merges cleanly

#### Scenario: Concurrent worktrees do not share directories @auto

    Given two pl-run.sh processes both invoked with --worktree --mode engineer
    When both create worktrees
    Then each has a unique branch name
    And each operates in a separate directory

## Regression Guidance
- Verify merge-worktrees.sh is registered as a SessionEnd hook in .claude/settings.json
- Verify merge hook merges worktree branch back to main and cleans up (branch + directory removed)
- Verify merge hook auto-commits both tracked changes and untracked files before merging
- Verify merge hook is a no-op when not in a worktree (safe to run on every session exit)
- Verify merge hook skips non-purlin branches (e.g., feature/* branches in sub-agent worktrees)
- Verify merge hook preserves worktree and aborts cleanly on merge conflict, with resolution instructions
- Verify .purlin/worktrees/ is in .gitignore
- Verify worktree creation fails gracefully if .purlin/worktrees/ is not writable
- Verify merge-back preserves all commits (not squashing)
- Verify hook does not corrupt main branch on partial merge failure
