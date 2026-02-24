# Feature: Multi-User Agent Launchers

> Label: "Tool: Multi-User Agent Launchers"
> Category: "Install, Update & Scripts"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

When multiple agents work concurrently using git worktrees, each session requires its launcher scripts to export `PURLIN_PROJECT_ROOT` pointing to the worktree directory, not the project root. This feature covers the `setup_worktrees.sh` script that creates the worktree structure, and the conventions for worktree-aware launcher scripts.

This feature extends (does not replace) `agent_launchers_common.md`. The standalone launchers (`run_architect.sh`, etc.) already export `PURLIN_PROJECT_ROOT`; this feature covers the setup tooling and the worktree-specific session launch pattern.

---

## 2. Requirements

### 2.1 setup_worktrees.sh

- **Location:** `tools/collab/setup_worktrees.sh` (framework-delivered via submodule).
- **Consumer invocation:** `bash purlin/tools/collab/setup_worktrees.sh`
- **Purpose:** One-time setup that creates three git worktrees under `.worktrees/`.
- **Behavior:**
  1. Check that `.worktrees/` is gitignored; if not, warn and exit.
  2. Accept an optional `--project-root <path>` argument; defaults to CWD.
  3. Create branch `spec/collab` and worktree at `.worktrees/architect-session/` (if not already present).
  4. Create branch `build/collab` and worktree at `.worktrees/build-session/` (if not already present).
  5. Create branch `qa/collab` and worktree at `.worktrees/qa-session/` (if not already present).
  6. All three branches start from the current `HEAD` of `main`.
  7. **Worktree Command Deduplication:** After each `git worktree add`, remove `.claude/commands/` from the newly created worktree directory. The worktree lives inside the main repo directory tree; Claude Code climbs the directory tree and discovers the main repo's `.claude/commands/` automatically. The per-worktree copy is redundant and causes all `/pl-*` slash commands to appear multiple times in the Claude Code completion UI. This deletion is safe: no agent functionality depends on the worktree having its own copy of the commands directory.
  8. Print a summary of what was created and the next-steps instructions.
- **Idempotency:** Running `setup_worktrees.sh` again when worktrees already exist MUST print a status message and exit cleanly (no duplicate worktrees).

### 2.2 Worktree Session Launchers

The standard launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) already export `PURLIN_PROJECT_ROOT="$SCRIPT_DIR"`. When run from within a worktree, `$SCRIPT_DIR` resolves to the worktree directory — which is the correct value. No modification to the launcher scripts is required; the existing behavior is correct.

**Verification:** A worktree launched with `PURLIN_PROJECT_ROOT` set to the worktree path will:

- Scan `features/` relative to the worktree (sees the worktree's branch checkout of features/).
- Write `.purlin/cache/` and `.purlin/runtime/` relative to the worktree (isolated from other sessions).
- Write `CRITIC_REPORT.md` to the worktree root (isolated).

### 2.3 Branch Lifecycle Protocol

After setup:

1. Architect session: `cd .worktrees/architect-session && bash run_architect.sh`
2. Architect completes spec work, runs `/pl-work-push`, merges `spec/collab` to `main`.
3. Builder session: `cd .worktrees/build-session && git merge main` (to get spec commits), then `bash run_builder.sh`.
4. Builder completes, runs `/pl-work-push`, merges `build/collab` to `main`.
5. QA session: `cd .worktrees/qa-session && git merge main` (to get impl commits), then `bash run_qa.sh`.
6. QA completes, runs `/pl-work-push`, merges `qa/collab` to `main`.

### 2.4 Worktree Isolation Invariants

- Each worktree has its own `.purlin/cache/` and `.purlin/runtime/` (generated, gitignored).
- Each worktree has its own `CRITIC_REPORT.md` (generated, gitignored).
- `features/` content differs per worktree (different branch checkouts).
- `tests/` content differs per worktree.
- The only shared state between worktrees is the git object database (commits, branches).

### 2.5 Cleanup

- When all phases are complete and merged to `main`, use `tools/collab/teardown_worktrees.sh` to remove worktrees safely (see Section 2.6).
- Consumer invocation: `bash purlin/tools/collab/teardown_worktrees.sh`
- The branches (`spec/collab`, `build/collab`, `qa/collab`) can be deleted after merge: `git branch -d spec/collab`.

### 2.6 teardown_worktrees.sh

- **Location:** `tools/collab/teardown_worktrees.sh` (framework-delivered via submodule).
- **Consumer invocation:** `bash purlin/tools/collab/teardown_worktrees.sh`
- **Purpose:** Safely remove all worktrees under `.worktrees/`, with pre-removal safety checks.

**Safety conditions (two distinct levels):**

**HARD BLOCK — uncommitted/staged changes (dirty state):**

- Detected via: `git -C <path> status --porcelain` returns output.
- These changes would be permanently lost if the worktree is removed.
- Script exits with code 1, lists the dirty files, and instructs the user to commit or stash first.
- Only bypassed with `--force`. The dashboard End Collab modal does NOT offer a force path for dirty worktrees — it instructs the user to commit or stash first.

**WARN + ALLOW — commits not yet merged to `main` (unsynced):**

- Detected via: `git -C <path> log main..HEAD --oneline` returns commits.
- The commits are NOT at risk — removing a worktree does not delete its branch. The branch survives and can be re-added with `git worktree add`.
- Script prints a warning listing unmerged branches and their commit counts, then proceeds without user input.
- The dashboard modal surfaces this warning prominently with an "I understand, the branches still exist" checkbox before enabling Confirm.

**Behavior sequence:**

1. For each worktree under `.worktrees/`: check dirty (hard block), then unsynced (soft warn).
2. If any dirty: exit code 1, list files, instruct user to commit/stash first.
3. If any unsynced (but none dirty): list branches + commit counts with a warning, then proceed.
4. Remove each worktree: `git worktree remove .worktrees/<role>-session`.
5. Remove `.worktrees/` directory if empty.

**Flags:**

- `--force`: Bypasses the HARD BLOCK dirty check. Use only after confirming data loss is acceptable.
- `--dry-run`: Reports safety status without removing anything. Used by the dashboard to populate the End Collab modal.
- `--project-root <path>`: Defaults to CWD.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: setup_worktrees Creates Three Worktrees

    Given the project root has no worktrees under .worktrees/
    And .worktrees/ is gitignored
    When setup_worktrees.sh is run
    Then .worktrees/architect-session/ is created on branch spec/collab
    And .worktrees/build-session/ is created on branch build/collab
    And .worktrees/qa-session/ is created on branch qa/collab
    And all three branches start from the same HEAD as main

#### Scenario: setup_worktrees Is Idempotent

    Given .worktrees/architect-session already exists
    When setup_worktrees.sh is run again
    Then the script prints a status message and exits cleanly
    And no duplicate worktrees or branches are created

#### Scenario: PURLIN_PROJECT_ROOT Resolves to Worktree Path

    Given the user runs run_architect.sh from .worktrees/architect-session/
    When the launcher script executes
    Then PURLIN_PROJECT_ROOT is exported as the absolute path of the worktree directory
    And features/ scanning targets the worktree's features/ directory
    And .purlin/cache/ writes target the worktree's .purlin/cache/

#### Scenario: setup_worktrees Removes .claude/commands/ From Each Worktree

    Given the project root has no worktrees under .worktrees/
    And .worktrees/ is gitignored
    When setup_worktrees.sh is run
    Then .worktrees/architect-session/.claude/commands/ does not exist
    And .worktrees/build-session/.claude/commands/ does not exist
    And .worktrees/qa-session/.claude/commands/ does not exist
    And .claude/commands/ at the project root still exists with all command files

#### Scenario: Teardown Is Blocked When Worktree Has Uncommitted Changes

    Given .worktrees/build-session exists and has uncommitted file changes
    When teardown_worktrees.sh is run without --force
    Then the script exits with code 1
    And the output lists the dirty files in build-session
    And no worktrees are removed

#### Scenario: Teardown Proceeds with Warning When Branch Has Unmerged Commits

    Given .worktrees/build-session exists with 3 commits not yet merged to main
    And the worktree has no uncommitted changes
    When teardown_worktrees.sh is run
    Then the script prints a warning listing the unmerged branch and commit count
    And the worktree is removed
    And the build/collab branch still exists in the git repository

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Implementation Notes

The `setup_worktrees.sh` approach avoids modifying the main checkout during setup. All three branches are created from `HEAD` of `main`. The key insight: when a launcher script does `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)`, running from within a worktree makes `$SCRIPT_DIR` the worktree root — which is exactly what `PURLIN_PROJECT_ROOT` should be. No special worktree-aware logic is needed in the launchers.

The `.worktrees/` directory convention (under `.worktrees/`, gitignored) is important for CDD Collab Mode detection — `serve.py` specifically looks for worktrees under this path to activate Collab Mode.

**[CLARIFICATION]** Both scripts use `--project-root` defaulting to CWD and all git operations use `git -C "$PROJECT_ROOT"` for consistency. The `teardown_worktrees.sh` `--dry-run` mode outputs JSON (matching what `/end-collab` dry-run endpoint returns to the dashboard modal). (Severity: INFO)

**[CLARIFICATION]** `teardown_worktrees.sh` uses `git worktree remove --force` for each session to handle both clean and force-mode removals uniformly. The `--force` flag on the script controls whether the dirty-state safety check is bypassed; the `--force` on `git worktree remove` is always used to avoid interactive prompts. (Severity: INFO)
