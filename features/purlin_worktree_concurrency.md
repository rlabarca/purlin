# Feature: Purlin Worktree Concurrency

> Label: "Tool: Purlin Worktree Concurrency"
> Category: "Framework Core"
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
- On merge conflict: abort merge, preserve worktree, and write a merge-pending breadcrumb (see 2.8). Then set the iTerm badge to `MERGE FAILED` so the dead terminal tab visually signals the problem. Print a prominent warning to stderr.
- The hook MUST exit 0 in all cases (never block agent exit).

### 2.4 Session Lock

On worktree creation, the launcher MUST write `.purlin_session.lock` in the worktree root:

```json
{
  "pid": 12345,
  "started": "2026-03-25T18:00:00Z",
  "mode": "engineer",
  "label": "W1"
}
```

- Written by `pl-run.sh` immediately after `git worktree add`.
- Deleted by the SessionEnd hook after successful merge, or by `/pl-merge` after cleanup.
- `.purlin_session.lock` MUST be gitignored (per-machine runtime artifact, not committed).
- One agent per worktree. The lock establishes ownership.

**Liveness check:** `kill -0 $PID`. If the process is not running, the lock is stale (agent crashed or exited without merging).

### 2.5 Stale Worktree Detection

Stale detection uses PID liveness from the session lock (Section 2.4), not commit age:

- **Lock exists + PID alive** → active. Leave alone.
- **Lock exists + PID dead** → stale. Agent crashed or exited without merging. Offer merge or discard.
- **No lock file** → orphaned. Old worktree with no session tracking. Offer cleanup.

On agent startup (via `/pl-resume`): report stale and orphaned worktrees with uncommitted work summary.
On `init.sh --refresh`: remove invalid worktree entries (worktree directory no longer exists).

### 2.6 Merge Serialization

When two worktrees merge back to main concurrently, they can race. Merge operations MUST be serialized:

- Before merging to main, acquire `.purlin/cache/merge.lock` (write PID + timestamp).
- If lock exists and PID is alive: print `"Merge blocked: another worktree is merging to main. Retrying..."` and retry after 2s, up to 3 times.
- If retries exhausted: abort merge, write breadcrumb (same as conflict handling in Section 2.8), and exit.
- Delete merge lock after merge completes (success or failure).
- Applies to both `/pl-merge` and the SessionEnd hook.
- Stale merge locks (PID dead) are silently removed before acquiring.

### 2.7 Concurrent Session Safety

- One agent per worktree. Multiple agents MUST NOT share the same worktree directory.
- Branch names MUST include timestamp for uniqueness.
- Merge-back is serialized via the merge lock (Section 2.6).

### 2.8 Merge Failure Signaling

When the SessionEnd hook (2.3) or `/pl-merge` encounters a merge conflict that cannot be auto-resolved:

- The hook MUST write a breadcrumb file to `.purlin/cache/merge_pending/<branch>.json` in the **main working directory** (not the worktree). The directory MUST be created if absent.
- The breadcrumb MUST contain:
  ```json
  {
    "branch": "purlin-engineer-20260325-143022",
    "worktree_path": "/path/to/.purlin/worktrees/...",
    "source_branch": "main",
    "failed_at": "2026-03-25T14:35:00Z",
    "reason": "conflict"
  }
  ```
- One file per failed merge. Multiple concurrent failures each leave their own breadcrumb.
- The hook MUST set the iTerm badge to `MERGE FAILED` after writing the breadcrumb, by calling `set_iterm_badge "MERGE FAILED"` (sourced from `identity.sh`). This persists on the terminal tab after the session ends, providing a visual indicator even if the user doesn't read stderr.
- The hook MUST print a prominent multi-line warning to stderr:
  ```
  ╔══════════════════════════════════════════════════╗
  ║  MERGE FAILED — worktree preserved              ║
  ║  Branch: purlin-engineer-20260325-143022         ║
  ║  Next Purlin session will recover automatically. ║
  ╚══════════════════════════════════════════════════╝
  ```
- On successful merge, the hook MUST NOT write a breadcrumb. If a breadcrumb exists from a previous failed attempt of the same branch, the hook MUST delete it.

### 2.9 Startup Merge Recovery

On every Purlin agent startup, **before** `scan.sh` and **before** mode activation:

- PURLIN_BASE.md Section 6 MUST include a **brief gate** as step 6.1a (before 6.1): glob `.purlin/cache/merge_pending/*.json`; if any exist, run `/pl-resume merge-recovery` before continuing. This MUST be 1-2 lines in the instruction file — no inline protocol. The detailed recovery logic lives in `/pl-resume`.
- This gate is **unconditional** — it runs regardless of CLI flags (`--auto-build`, `--mode`, etc.). The user cannot accidentally bypass it.

The `/pl-resume` skill MUST implement a `merge-recovery` subcommand (also invocable as an early step in normal `/pl-resume` restore flow):

1. Read all breadcrumbs from `.purlin/cache/merge_pending/*.json`.
2. Display each pending merge with branch name, age, and worktree path.
3. For each pending merge, attempt `git merge <branch>`:
   - If the merge succeeds: clean up worktree, delete branch, remove breadcrumb, report success.
   - If the merge conflicts: present the conflicts to the user and offer LLM-assisted resolution. The agent can read the conflicting files, understand the intent from both sides, and propose a resolution.
   - The user may defer resolution ("skip for now") — the breadcrumb stays, and startup continues with a warning banner: "Deferred merge: `<branch>` — unmerged work exists."
4. Only after all breadcrumbs are resolved or explicitly deferred, return control to the startup protocol.

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

#### Scenario: SessionEnd hook writes breadcrumb on merge conflict

    Given the agent is in a purlin worktree on branch "purlin-engineer-20260325-143022"
    And the source branch has diverged with conflicting changes
    When the SessionEnd hook fires
    Then the merge is aborted
    And the worktree is preserved
    And .purlin/cache/merge_pending/purlin-engineer-20260325-143022.json exists in the main directory
    And the breadcrumb contains the branch name, worktree path, source branch, timestamp, and reason
    And the iTerm badge is set to "MERGE FAILED"
    And a prominent warning is printed to stderr
    And exit code is 0

#### Scenario: Successful merge removes stale breadcrumb

    Given .purlin/cache/merge_pending/purlin-engineer-20260325-143022.json exists from a prior failure
    And the conflict has since been resolved
    When the SessionEnd hook fires for the same branch and merge succeeds
    Then the breadcrumb file is deleted
    And the worktree and branch are cleaned up normally

#### Scenario: Startup intercepts pending merge before scan

    Given .purlin/cache/merge_pending/purlin-engineer-20260325-143022.json exists
    When pl-run.sh is invoked with --auto-build
    Then the agent displays the pending merge before running scan.sh
    And the agent attempts to merge purlin-engineer-20260325-143022
    And scan.sh does not run until the merge is resolved or deferred

#### Scenario: Startup merge recovery succeeds cleanly

    Given .purlin/cache/merge_pending/purlin-engineer-20260325-143022.json exists
    And the worktree branch merges cleanly into main
    When the startup merge recovery runs
    Then the merge succeeds
    And the worktree is removed
    And the branch is deleted
    And the breadcrumb file is deleted
    And normal startup continues

#### Scenario: User defers merge recovery at startup

    Given .purlin/cache/merge_pending/purlin-engineer-20260325-143022.json exists
    And the merge has conflicts
    When the user chooses to defer resolution
    Then the breadcrumb file is preserved
    And a warning banner is displayed for the remainder of the session
    And normal startup continues

#### Scenario: Session lock written on worktree creation

    Given pl-run.sh invoked with --worktree --mode engineer
    When the worktree is created
    Then .purlin_session.lock exists in the worktree root
    And the lock contains the current PID, mode "engineer", and ISO timestamp

#### Scenario: Session lock deleted after successful merge

    Given the agent is in a purlin worktree with .purlin_session.lock
    When /pl-merge succeeds
    Then .purlin_session.lock no longer exists in the worktree
    And the worktree directory is removed

#### Scenario: Stale worktree detected via PID check

    Given .purlin/worktrees/purlin-pm-20260325/ has .purlin_session.lock with PID 99999
    And PID 99999 is not running
    When /pl-resume runs on startup
    Then the worktree is reported as stale
    And the user is offered to merge or discard

#### Scenario: Merge lock serializes concurrent merges

    Given two worktrees W1 and W2 both attempt /pl-merge simultaneously
    When W1 acquires .purlin/cache/merge.lock first
    Then W2 prints "Merge blocked: another worktree is merging to main"
    And W2 retries after 2 seconds
    And both merges eventually complete

#### Scenario: Stale merge lock is cleaned up

    Given .purlin/cache/merge.lock exists with PID 99999
    And PID 99999 is not running
    When a worktree attempts to merge
    Then the stale lock is removed
    And the merge proceeds normally

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
- Verify merge hook writes breadcrumb to .purlin/cache/merge_pending/ on conflict
- Verify merge hook sets badge to MERGE FAILED on conflict
- Verify merge hook deletes stale breadcrumb on successful merge of previously-failed branch
- Verify .purlin/worktrees/ is in .gitignore
- Verify worktree creation fails gracefully if .purlin/worktrees/ is not writable
- Verify merge-back preserves all commits (not squashing)
- Verify hook does not corrupt main branch on partial merge failure
- Verify startup merge recovery runs before scan.sh regardless of CLI flags
- Verify startup merge recovery resolves or defers all pending breadcrumbs before proceeding
- Verify deferred merges show a warning banner for the session duration
