# Feature: Local Push

> Label: "/pl-local-push: Local Push"
> Category: "Agent Skills"
> Prerequisite: features/workflow_checklist_system.md
> Prerequisite: features/policy_collaboration.md

[TODO]

## 1. Overview

The `/pl-local-push` skill runs the handoff checklist and merges the current isolation branch into `main` in one step. It is available only inside an isolated worktree — the command file is placed in the worktree's `.claude/commands/` by `create_isolation.sh` and does not exist in the project root.

No role is assumed. Any agent (Architect, Builder, QA) running in any named isolation can invoke it.

---

## 2. Requirements

### 2.1 Pre-Flight Sync Check

Before running the handoff checklist, the command computes N (commits behind main) and M (commits ahead of main):

*   **BEHIND (N>0, M=0):** Auto-rebases onto main (fast-forward, no conflict risk) before running checklist.
*   **DIVERGED (N>0, M>0):** Blocks immediately — prints the incoming main commits and instructs the agent to run `/pl-local-pull` first. Does NOT proceed to the handoff checklist.

### 2.2 Handoff Checklist Execution

Runs `tools/handoff/run.sh` (see `features/workflow_checklist_system.md` for the checklist infrastructure).

### 2.3 Merge Behavior

*   If ALL steps PASS: merges the current branch into `main` using `git merge --ff-only <current-branch>` from the project root.
*   If any steps FAIL or PENDING: prints the list of issues and does NOT merge.

### 2.4 Safety Checks

*   Verifies the main checkout (`PROJECT_ROOT`) is on `main` before merging; aborts with a clear error if not.
*   Does NOT push to remote — that remains a separate explicit user action.

### 2.5 Physical Command Placement

`pl-local-push.md` is placed ONLY in the worktree's `.claude/commands/` directory (by `create_isolation.sh`). It is NOT present in the project root's `.claude/commands/` directory. This physical placement enforces that the command is only available inside an isolated worktree session — there is no need for a runtime "are we in a worktree" guard.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: pl-local-push Merges Branch When All Checks Pass

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch main
    When /pl-local-push is invoked
    Then git merge --ff-only isolated/feat1 is executed from PROJECT_ROOT
    And the command succeeds

#### Scenario: pl-local-push Blocks Merge When Handoff Checks Fail

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 1
    When /pl-local-push is invoked
    Then the failing items are printed
    And no merge is executed

#### Scenario: pl-local-push Blocks When Branch Is DIVERGED

    Given the current worktree branch has commits not in main
    And main has commits not in the worktree branch
    When /pl-local-push is invoked
    Then the command prints the DIVERGED state and lists incoming main commits
    And the handoff checklist is NOT run
    And no merge is executed
    And the agent is instructed to run /pl-local-pull first

### Manual Scenarios (Human Verification Required)

None.
