# Feature: Workflow Handoff Checklist

> Label: "Handoff Checklist System"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/release_checklist_core.md

[TODO]

## 1. Overview

The Workflow Handoff Checklist system provides a generic pre-merge checklist that agents run before completing their isolation session and merging their branch to `main`. It is architecturally parallel to the Release Checklist system, reusing the same step schema and resolver infrastructure. The `/pl-local-push` skill invokes this checklist as a prerequisite to merging.

No role is assumed. The checklist steps are generic and apply equally to any agent (Architect, Builder, QA) running in any named isolation.

---

## 2. Requirements

### 2.1 Step Schema

The handoff step schema is identical to the release checklist step schema. The `roles` field is removed — all steps apply to all agents:

```json
{
  "id": "purlin.handoff.git_clean",
  "friendly_name": "Git Working Directory Clean",
  "description": "No uncommitted changes in the worktree (excluding .purlin/)",
  "code": "git diff --exit-code -- ':!.purlin/' && git diff --cached --exit-code -- ':!.purlin/'",
  "agent_instructions": "Run git status. If any files are staged or modified (outside .purlin/), commit or stash them before proceeding. .purlin/ config files are excluded — they are ephemeral in worktrees and must not be committed."
}
```

### 2.2 File Structure

```
tools/handoff/
  global_steps.json          <- framework handoff steps (generic, no role filtering)
  run.sh                     <- CLI entry point
.purlin/handoff/
  local_steps.json           <- project-specific handoff steps (optional)
  config.json                <- ordering + enable/disable
```

### 2.3 Resolver Reuse

`tools/release/resolve.py` is used to resolve steps. A `checklist_type` parameter routes to the correct file paths:

*   `checklist_type="handoff"` -> reads `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`
*   `checklist_type="release"` -> current behavior (unchanged)

No logic changes to `resolve.py` are required — only path routing based on the new parameter.

### 2.4 CLI Interface

`tools/handoff/run.sh`

Behavior:

1. Reads `PURLIN_PROJECT_ROOT` to find `.purlin/handoff/config.json`
2. Resolves the ordered, enabled step list via `resolve.py`
3. For each step: displays the step name + `agent_instructions`; auto-evaluates the `code` field if present; reports PASS/FAIL; presents items requiring human judgment as prompts
4. On completion, prints a summary: N passed, M pending
5. If any item is FAIL or PENDING, exits with code 1; if all pass, exits with code 0

### 2.5 Handoff Steps (global_steps.json)

*   `purlin.handoff.git_clean` — working directory has no uncommitted changes (excludes `.purlin/`)
*   `purlin.handoff.critic_report` — Critic report is current (run `tools/cdd/status.sh`)

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Handoff CLI Passes When All Auto-Steps Pass

    Given the current worktree is on branch isolated/feat1
    And the working directory is clean
    And the critic report is current
    When run.sh is invoked
    Then the CLI exits with code 0
    And prints a summary with all steps PASS

#### Scenario: Handoff CLI Exits 1 When Any Step Fails

    Given the working directory has uncommitted changes
    When run.sh is invoked
    Then the CLI exits with code 1
    And reports the failing step (purlin.handoff.git_clean) as FAIL

### Manual Scenarios (Human Verification Required)

None.
