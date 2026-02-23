# Feature: Workflow Handoff Checklist

> Label: "Tool: Workflow Handoff Checklist"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

The Workflow Handoff Checklist system provides per-role pre-merge checklists that agents run before completing a lifecycle phase and merging their branch to `main`. It is architecturally parallel to the Release Checklist system, reusing the same step schema and resolver infrastructure. Agents invoke `/pl-work-push` to run the checklist and merge in one step.

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
*   `purlin.handoff.branch_naming` — current branch follows naming convention (`spec/*`, `build/*`, or `qa/*`)

**Architect-only steps (`roles: ["architect"]`):**

*   `purlin.handoff.spec_gate_pass` — all modified feature specs pass the Critic Spec Gate (architect=DONE)
*   `purlin.handoff.impl_notes_stub` — all new feature files have an Implementation Notes section or companion file stub
*   `purlin.handoff.visual_spec_complete` — if the feature has a Visual Specification section, all required fields are present

**Builder-only steps (`roles: ["builder"]`):**

*   `purlin.handoff.tests_pass` — `tests/<feature>/tests.json` exists with `status: "PASS"` for all modified features
*   `purlin.handoff.impl_notes_updated` — Implementation Notes section updated with any `[DEVIATION]` or `[DISCOVERY]` entries
*   `purlin.handoff.status_commit_made` — a `[Ready for Verification]` or `[Complete]` status commit exists for all implemented features

**QA-only steps (`roles: ["qa"]`):**

*   `purlin.handoff.scenarios_complete` — all manual scenarios for in-scope features have been attempted; scenarios blocked by an open BUG may be explicitly noted as deferred rather than run
*   `purlin.handoff.discoveries_addressed` — all discoveries found during this verification cycle are committed to the branch; OPEN status is acceptable (routes to Builder); FAIL only when observed bugs are uncommitted
*   `purlin.handoff.complete_commit_made` — a `[Complete]` commit exists for every in-scope feature that is fully clean; PASS when all in-scope features have open discoveries (nothing to complete yet)

### 2.6 Slash Commands

**`/pl-work-push`** (replaces `/pl-handoff-check`; available to all roles):

1. Infers the current role from the branch name (`spec/*` → architect, `build/*` → builder, `qa/*` → qa)
2. Runs `tools/handoff/run.sh` for the current role
3. If ALL steps PASS: merges the current branch into `main` using `git merge --ff-only <current-branch>` from the project root
4. If any steps FAIL or PENDING: prints the list of issues and does NOT merge
5. Safety check: verifies the main checkout (`PROJECT_ROOT`) is on `main` before merging; aborts with a clear error if not
6. Does NOT push to remote — that remains a separate explicit user action

**`/pl-work-pull`** (new; available to all roles):

1. Checks that the working tree is clean; aborts with message "Commit or stash changes before pulling" if dirty
2. Runs `git merge main` from within the worktree
3. Reports: N commits pulled, list of new/changed feature files
4. Use case: agent wants updated specs or code from main without pushing own work first

### 2.7 Integration with CDD Collab Mode

When CDD Collab Mode is active, the Pre-Merge Status panel reads each worktree's handoff checklist state. Items that can be auto-evaluated (git clean, `tests.json` exists, status commit present) are computed server-side. Items requiring human judgment are shown as "pending" until the agent runs `/pl-work-push` to confirm them.

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
When `/pl-work-push` is invoked without a `--role` argument,
Then the checklist runs with `role="qa"`,
And only QA-specific and shared steps are included.

#### Scenario: pl-work-push Merges Branch When All Checks Pass

    Given the current branch is build/collab
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch main
    When /pl-work-push is invoked
    Then git merge --ff-only build/collab is executed from PROJECT_ROOT
    And the command succeeds

#### Scenario: pl-work-push Blocks Merge When Handoff Checks Fail

    Given the current branch is build/collab
    And tools/handoff/run.sh exits with code 1
    When /pl-work-push is invoked
    Then the failing items are printed
    And no merge is executed

#### Scenario: pl-work-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-work-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed

#### Scenario: pl-work-pull Merges Main Into Worktree

    Given the current worktree is clean
    And main has 3 new commits not in the worktree
    When /pl-work-pull is invoked
    Then git merge main is executed
    And the output reports commits pulled and lists changed feature files

#### Scenario: pl-work-push Allows QA Merge When Discoveries Are Committed But Open

    Given the current branch is qa/collab
    And features/cdd_collab_mode.md has 3 OPEN entries in ## User Testing Discoveries
    And all discovery entries are committed to the branch
    And all manual scenarios have been attempted (failed ones have BUG discoveries)
    And no in-scope feature is fully clean (no [Complete] commit needed)
    When /pl-work-push is invoked
    Then discoveries_addressed evaluates as PASS
    And complete_commit_made evaluates as PASS
    And the branch is merged to main

### Manual Scenarios

None. All scenarios for this feature are fully automated.

## 4. Implementation Notes

The handoff checklist system reuses the resolver infrastructure from the release checklist. The key design principle is that handoff checklists are role-scoped (only show relevant steps) while the release checklist is comprehensive (all steps). The `roles` field on `global_steps.json` entries provides this filtering. The `run.sh` script is the CLI surface; `resolve.py` handles the merge of global + local steps with ordering and enable/disable.

*   **resolve.py changes:** Added `checklist_type` parameter and `roles` field passthrough. `checklist_type="handoff"` routes to `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`. The `_make_entry()` helper extracts step fields including `roles` (backward-compatible: release steps have `roles=None`). No logic changes to the resolution algorithm.
*   **run.py import strategy:** `resolve.py` is imported from the framework's `tools/release/` directory (sibling path relative to `tools/handoff/`), not from the project root. This allows the runner to work in any project root (including temp dirs in tests) while always finding the framework's resolver. Explicit `global_path`, `local_path`, `config_path` are computed from the `--project-root` argument and passed to `resolve_checklist()`.
*   **Step evaluation:** Steps with a `code` field are auto-evaluated via `subprocess.run()` with 30s timeout. Steps without `code` are reported as PENDING. Exit code 1 if any step is FAIL or PENDING; 0 only when all steps PASS.
*   **Branch inference:** `infer_role_from_branch()` maps `spec/*` → architect, `build/*` → builder, `qa/*` → qa. Returns None for unrecognized branches, causing the CLI to exit with an error message.
- **Branch naming:** `/pl-work-push` and `/pl-work-pull` infer role from branch using same prefix map as `serve.py` (`spec/*` → architect, `build/*` → builder, `qa/*` → qa). `infer_role_from_branch()` updated to map `build/*` → builder (was `impl/*`).
- **`--ff-only` rationale:** Fast-forward only merge prevents accidental merge commits on `main`. If the branch cannot be fast-forwarded, the user must rebase first.
- **PROJECT_ROOT detection:** `/pl-work-push` uses `PURLIN_PROJECT_ROOT` if set, falls back to `git worktree list --porcelain` to locate the main checkout path.
