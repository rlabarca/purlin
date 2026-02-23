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

- **Location:** Project root (executable, `chmod +x`).
- **Purpose:** One-time setup that creates three git worktrees under `.worktrees/`.
- **Behavior:**
  1. Check that `.worktrees/` is gitignored; if not, warn and exit.
  2. Accept an optional `--feature <name>` argument to name the lifecycle branches. Default: `feature`.
  3. Create branch `spec/<feature>` and worktree at `.worktrees/architect-session/` (if not already present).
  4. Create branch `impl/<feature>` and worktree at `.worktrees/builder-session/` (if not already present).
  5. Create branch `qa/<feature>` and worktree at `.worktrees/qa-session/` (if not already present).
  6. All three branches start from the current `HEAD` of `main`.
  7. Print a summary of what was created and the next-steps instructions.
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
2. Architect completes spec work, runs `/pl-handoff-check`, merges `spec/<feature>` to `main`.
3. Builder session: `cd .worktrees/builder-session && git merge main` (to get spec commits), then `bash run_builder.sh`.
4. Builder completes, runs `/pl-handoff-check`, merges `impl/<feature>` to `main`.
5. QA session: `cd .worktrees/qa-session && git merge main` (to get impl commits), then `bash run_qa.sh`.
6. QA completes, runs `/pl-handoff-check`, merges `qa/<feature>` to `main`.

### 2.4 Worktree Isolation Invariants

- Each worktree has its own `.purlin/cache/` and `.purlin/runtime/` (generated, gitignored).
- Each worktree has its own `CRITIC_REPORT.md` (generated, gitignored).
- `features/` content differs per worktree (different branch checkouts).
- `tests/` content differs per worktree.
- The only shared state between worktrees is the git object database (commits, branches).

### 2.5 Cleanup

- When all phases are complete and merged to `main`, worktrees can be removed: `git worktree remove .worktrees/<role>-session`.
- The branches (`spec/*`, `impl/*`, `qa/*`) can be deleted after merge: `git branch -d spec/<feature>`.
- The `.worktrees/` directory itself should be removed when empty.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: setup_worktrees Creates Three Worktrees

    Given the project root has no worktrees under .worktrees/
    And .worktrees/ is gitignored
    When setup_worktrees.sh --feature task-crud is run
    Then .worktrees/architect-session/ is created on branch spec/task-crud
    And .worktrees/builder-session/ is created on branch impl/task-crud
    And .worktrees/qa-session/ is created on branch qa/task-crud
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

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Implementation Notes

The `setup_worktrees.sh` approach avoids modifying the main checkout during setup. All three branches are created from `HEAD` of `main`. The key insight: when a launcher script does `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)`, running from within a worktree makes `$SCRIPT_DIR` the worktree root — which is exactly what `PURLIN_PROJECT_ROOT` should be. No special worktree-aware logic is needed in the launchers.

The `.worktrees/` directory convention (under `.worktrees/`, gitignored) is important for CDD Collab Mode detection — `serve.py` specifically looks for worktrees under this path to activate Collab Mode.
