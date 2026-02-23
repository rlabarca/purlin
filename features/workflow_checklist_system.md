# Feature: Workflow Handoff Checklist

> Label: "Tool: Workflow Handoff Checklist"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

The Workflow Handoff Checklist system provides per-role pre-merge checklists that agents run before completing a lifecycle phase and merging their branch to `main`. It is architecturally parallel to the Release Checklist system, reusing the same step schema and resolver infrastructure. Agents invoke `/pl-handoff-check` before ending a session on a lifecycle branch.

## 2. Requirements

### 2.1 Step Schema

The handoff step schema extends the release checklist step schema with one additional field: `roles`.

```json
{
  "id": "purlin.handoff.git_clean",
  "friendly_name": "Git Working Directory Clean",
  "description": "No uncommitted changes in the worktree",
  "code": "git diff --exit-code && git diff --cached --exit-code",
  "agent_instructions": "Run git status. If any files are staged or modified, commit or stash them before proceeding.",
  "roles": ["all"]
}
```

The `roles` field values:

*   `["all"]` — appears in all three role checklists AND the release checklist
*   `["architect"]`, `["builder"]`, `["qa"]` — role-specific
*   Absent or null — applies to the current checklist type only (no cross-list sharing)

### 2.2 File Structure

```
tools/handoff/
  global_steps.json          ← framework handoff steps (tagged by role)
  run.sh                     ← CLI entry point: --role <architect|builder|qa>
.purlin/handoff/
  local_steps.json           ← project-specific handoff steps (optional)
  architect/config.json      ← ordering + enable/disable for Architect role
  builder/config.json        ← for Builder role
  qa/config.json             ← for QA role
```

### 2.3 Resolver Reuse

`tools/release/resolve.py` is used to resolve steps. A `checklist_type` parameter routes to the correct file paths:

*   `checklist_type="handoff"` → reads `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`
*   `checklist_type="release"` → current behavior (unchanged)

No logic changes to `resolve.py` are required — only path routing based on the new parameter.

### 2.4 CLI Interface

`tools/handoff/run.sh --role <architect|builder|qa>`

Behavior:

1.  Reads `PURLIN_PROJECT_ROOT` to find `.purlin/handoff/<role>/config.json`
2.  Resolves the ordered, enabled step list for the given role via `resolve.py`
3.  For each step: displays the step name + `agent_instructions`; auto-evaluates the `code` field if present; reports PASS/FAIL; presents items requiring human judgment as prompts
4.  On completion, prints a summary: N passed, M pending
5.  If any item is FAIL or PENDING, exits with code 1; if all pass, exits with code 0

### 2.5 Sample Handoff Steps (global_steps.json)

**Shared steps (`roles: ["all"]`):**

*   `purlin.handoff.git_clean` — working directory has no uncommitted changes
*   `purlin.handoff.run_critic` — Critic report is current (run `tools/cdd/status.sh`)
*   `purlin.handoff.branch_naming` — current branch follows naming convention (`spec/*`, `impl/*`, or `qa/*`)

**Architect-only steps (`roles: ["architect"]`):**

*   `purlin.handoff.spec_gate_pass` — all modified feature specs pass the Critic Spec Gate (architect=DONE)
*   `purlin.handoff.impl_notes_stub` — all new feature files have an Implementation Notes section or companion file stub
*   `purlin.handoff.visual_spec_complete` — if the feature has a Visual Specification section, all required fields are present

**Builder-only steps (`roles: ["builder"]`):**

*   `purlin.handoff.tests_pass` — `tests/<feature>/tests.json` exists with `status: "PASS"` for all modified features
*   `purlin.handoff.impl_notes_updated` — Implementation Notes section updated with any `[DEVIATION]` or `[DISCOVERY]` entries
*   `purlin.handoff.status_commit_made` — a `[Ready for Verification]` or `[Complete]` status commit exists for all implemented features

**QA-only steps (`roles: ["qa"]`):**

*   `purlin.handoff.scenarios_complete` — all manual scenarios for in-scope features have been verified (PASS or recorded FAIL)
*   `purlin.handoff.discoveries_addressed` — all OPEN discoveries have been recorded and committed
*   `purlin.handoff.complete_commit_made` — a `[Complete]` commit exists for all clean features (zero discoveries)

### 2.6 Slash Command

`/pl-handoff-check` — available to all roles; runs the handoff checklist for the current role. The role is inferred from the current branch name (`spec/*` → architect, `impl/*` → builder, `qa/*` → qa). Falls back to asking the user to specify the role if the branch does not match a known pattern.

### 2.7 Integration with CDD Collab Mode

When CDD Collab Mode is active, the Pre-Merge Status panel reads each worktree's handoff checklist state. Items that can be auto-evaluated (git clean, `tests.json` exists, status commit present) are computed server-side. Items requiring human judgment are shown as "pending" until the user confirms them via `/pl-handoff-check`.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Handoff CLI Filters Steps by Role
Given the handoff `global_steps.json` contains steps with `roles: ["all"]`, `["architect"]`, `["builder"]`, and `["qa"]`,
When `run.sh --role architect` is invoked,
Then only steps with `roles: ["all"]` or `["architect"]` are included in the checklist,
And steps with `roles: ["builder"]` or `["qa"]` are excluded.

#### Scenario: Handoff CLI Passes When All Auto-Steps Pass
Given the current branch is `spec/task-crud`,
And the working directory is clean,
And all modified features pass the Critic Spec Gate,
When `run.sh --role architect` is invoked,
Then the CLI exits with code 0,
And prints a summary with all steps PASS.

#### Scenario: Handoff CLI Exits 1 When Any Step Fails
Given the current branch is `impl/task-crud`,
And `tests/task_crud/tests.json` does not exist,
When `run.sh --role builder` is invoked,
Then the CLI exits with code 1,
And reports the failing step (`purlin.handoff.tests_pass`) as FAIL.

#### Scenario: Role Inferred from Branch Name
Given the current branch is `qa/task-filtering`,
When `/pl-handoff-check` is invoked without a `--role` argument,
Then the checklist runs with `role="qa"`,
And only QA-specific and shared steps are included.

### Manual Scenarios

None. All scenarios for this feature are fully automated.

## 4. Implementation Notes

The handoff checklist system reuses the resolver infrastructure from the release checklist. The key design principle is that handoff checklists are role-scoped (only show relevant steps) while the release checklist is comprehensive (all steps). The `roles` field on `global_steps.json` entries provides this filtering. The `run.sh` script is the CLI surface; `resolve.py` handles the merge of global + local steps with ordering and enable/disable.
