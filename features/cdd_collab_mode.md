# Feature: CDD Collab Mode

> Label: "Tool: CDD Collab Mode"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md

[TODO]

## 1. Overview

CDD Collab Mode is a dashboard mode activated automatically when the CDD server runs from a project root that has active git worktrees under `.worktrees/`. In Collab Mode, the WORKSPACE section of the dashboard extends to become "WORKSPACE & COLLABORATION", showing what each agent role session is doing and surfacing per-role pre-merge checklists.

---

## 2. Requirements

### 2.1 Detection Mechanism

- On each status refresh, `serve.py` runs `git worktree list --porcelain` from the project root.
- Collab Mode is active when: at least one worktree other than the main checkout is listed AND its path is under `.worktrees/` relative to the project root.
- When Collab Mode is not active, the WORKSPACE section behaves as before (no change).
- Detection is read-only. CDD never writes to worktree paths.

### 2.2 Role Mapping from Branch Name

Branch prefix determines role assignment:

- `spec/*` → Architect
- `impl/*` → Builder
- `qa/*` → QA
- Any other prefix → Unknown (shown as a worktree but displayed as role-unlabeled)

### 2.3 WORKSPACE & COLLABORATION Section

When Collab Mode is active, the WORKSPACE section becomes "WORKSPACE & COLLABORATION". It contains three sub-sections:

**Sessions sub-section:** A table listing all active worktrees:

| Role | Branch | Dirty? | Last Activity |
|------|--------|--------|---------------|
| Architect | spec/collab | 2 files | 45 min ago — feat(spec): add filtering scenarios |
| Builder | impl/collab | Clean | 12 min ago — feat(impl): implement CRUD handlers |
| QA | qa/collab | 1 file | just now — qa: record test discovery |

"Dirty?" shows file count when modified, "Clean" when clean. "Last Activity" shows relative timestamp + last commit subject.

**Pre-Merge Status sub-section:** Per-worktree handoff readiness:

- For each worktree, shows role, branch, and a readiness indicator.
- `Ready to merge` — all auto-evaluable handoff checklist items pass.
- `N items pending` — N items need attention; `[view checklist ->]` link text.

**Local (main) sub-section:** Current state of the main checkout (existing WORKSPACE content):

- Branch name, ahead/behind status.
- Clean/dirty state.
- Last commit summary.

### 2.4 Worktree State Reading

CDD reads each worktree's state using read-only git commands:

- `git worktree list --porcelain` — all worktree paths and HEAD commits.
- `git -C <path> rev-parse --abbrev-ref HEAD` — branch name per worktree.
- `git -C <path> status --porcelain` — dirty/clean per worktree.
- `git -C <path> log -1 --format='%h %s (%cr)'` — last commit per worktree.
- `git -C <path> log --grep='\[Ready for Verification\]' --format=%ct` — check for status commit.

CDD writes nothing to worktree paths. No interference with running agent sessions.

### 2.5 Pre-Merge Status Evaluation

For each worktree, CDD evaluates auto-checkable items from the handoff checklist:

- `purlin.handoff.git_clean` — checked via `git status --porcelain` output.
- `purlin.handoff.status_commit_made` (Builder only) — checked via grep on git log.
- `purlin.handoff.complete_commit_made` (QA only) — checked via grep on git log.

Items requiring human judgment (e.g., spec gate pass, visual spec complete) are shown as pending until the agent runs `/pl-handoff-check` and records results.

### 2.6 /status.json API Extension

When Collab Mode is active, the `/status.json` response includes additional fields:

```json
{
  "collab_mode": true,
  "worktrees": [
    {
      "path": ".worktrees/architect-session",
      "branch": "spec/collab",
      "role": "architect",
      "dirty": true,
      "file_count": 2,
      "last_commit": "abc1234 feat(spec): add filtering scenarios (45 min ago)",
      "handoff_ready": false,
      "handoff_pending_count": 1
    },
    {
      "path": ".worktrees/builder-session",
      "branch": "impl/collab",
      "role": "builder",
      "dirty": false,
      "file_count": 0,
      "last_commit": "def5678 feat(impl): implement CRUD handlers (12 min ago)",
      "handoff_ready": true,
      "handoff_pending_count": 0
    }
  ]
}
```

When Collab Mode is not active: `collab_mode` is false (or omitted) and `worktrees` is absent.

Fields per worktree entry:

- `path` — relative path from project root.
- `branch` — current branch name.
- `role` — `"architect"`, `"builder"`, `"qa"`, or `"unknown"`.
- `dirty` — true if any uncommitted changes.
- `file_count` — count of modified/staged files (0 when clean).
- `last_commit` — formatted string: `"<hash> <subject> (<relative-time>)"`.
- `handoff_ready` — true if all auto-evaluable handoff items pass.
- `handoff_pending_count` — count of pending items (0 when ready).

### 2.7 Visual Design

The WORKSPACE & COLLABORATION section uses the same Purlin CSS tokens as the rest of the dashboard. No new design tokens are introduced. The section heading changes from "WORKSPACE" to "WORKSPACE & COLLABORATION" when Collab Mode is active. Sub-section labels ("Sessions", "Pre-Merge Status", "Local (main)") use the same section header typography.

### 2.8 No Collab Mode During Main Checkout

When the CDD server is run from within a worktree (not the project root), Collab Mode is not available. The dashboard operates in standard mode. Only the project root has visibility into all worktrees.

### 2.9 Collab Session Controls

The dashboard exposes UI controls to start and stop Collab Sessions, complementing the CLI scripts in `tools/collab/`.

**Start Collab Session (when Collab Mode is inactive):**

- A "Start Collab Session" button appears as a footer action in the standard WORKSPACE section.
- Clicking the button directly triggers `POST /start-collab` with an empty body `{}`. No text input or form is shown.
- While the request is in flight, the 5-second auto-refresh timer MUST be paused to prevent the error message from being wiped before the user sees it. The timer is resumed after the response is received (success or error). This is the same guard pattern used by `rcPendingSave` in the release checklist.
- The server runs `tools/collab/setup_worktrees.sh --project-root <PROJECT_ROOT>` (no `--feature` argument).
- On success (`{ "status": "ok" }`): dashboard refreshes; WORKSPACE becomes WORKSPACE & COLLABORATION.
- On error: inline error message shown below the button.

**End Collab Session (when Collab Mode is active):**

- An "End Collab Session" button appears in the WORKSPACE & COLLABORATION section header.
- On click: dashboard sends `POST /end-collab` with body `{ "dry_run": true }`. The server runs `tools/collab/teardown_worktrees.sh --dry-run` and returns the safety status.
- The dashboard shows a modal based on the dry-run result:
  - **Dirty worktrees present:** Modal lists the dirty worktrees and their uncommitted files. Instructs the user to commit or stash before ending the session. Confirm button is disabled. No force path is offered.
  - **Unsynced commits present (no dirty):** Modal shows a warning listing unmerged branches and commit counts, with a note that branches survive worktree removal. User must check "I understand, the branches still exist" before the Confirm button is enabled.
  - **Clean state:** Simple confirmation dialog with Confirm and Cancel buttons.
- On confirm: dashboard sends `POST /end-collab` with body `{ "force": true }`. Server runs `tools/collab/teardown_worktrees.sh --force`.
- On success: dashboard refreshes; WORKSPACE & COLLABORATION becomes standard WORKSPACE.

**Server endpoints:**

- `POST /start-collab` — body: `{}` (empty; no `feature` field required or accepted) — runs `setup_worktrees.sh`, returns `{ "status": "ok" }` or `{ "error": "..." }`.
- `POST /end-collab` — body: `{ "dry_run": true }` or `{ "force": true }` — runs `teardown_worktrees.sh` with the appropriate flag. Returns safety status JSON for dry-run; returns `{ "status": "ok" }` for a force run.
- Both endpoints follow the same pattern as `/run-critic` in `serve.py`.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Collab Mode Inactive When No Worktrees

    Given git worktree list shows only the main checkout
    When an agent calls GET /status.json
    Then collab_mode is false or absent
    And no worktrees array is present in the response

#### Scenario: Collab Mode Active When Worktrees Detected

    Given a worktree exists at .worktrees/architect-session on branch spec/collab
    When an agent calls GET /status.json
    Then collab_mode is true
    And the worktrees array contains one entry with path ".worktrees/architect-session"
    And the entry has branch "spec/collab" and role "architect"

#### Scenario: Role Mapped from Branch Prefix

    Given worktrees on branches spec/feature-a, impl/feature-a, qa/feature-a
    When an agent calls GET /status.json
    Then the worktrees array contains entries with roles architect, builder, and qa respectively

#### Scenario: Unknown Role for Non-Standard Branch

    Given a worktree on branch hotfix/urgent-fix
    When an agent calls GET /status.json
    Then the worktree entry has role "unknown"

#### Scenario: Dirty State Detected

    Given a worktree at .worktrees/builder-session has uncommitted files
    When an agent calls GET /status.json
    Then the worktree entry has dirty true and file_count greater than 0

#### Scenario: Handoff Ready When Auto-Steps Pass

    Given a builder worktree with clean git status
    And tests/task_crud/tests.json exists with status PASS
    And a [Ready for Verification] commit is in the worktree log
    When an agent calls GET /status.json
    Then the builder worktree entry has handoff_ready true and handoff_pending_count 0

#### Scenario: Start Collab Creates Worktrees via Dashboard

    Given no worktrees exist under .worktrees/
    And the CDD server is running
    When a POST request is sent to /start-collab with body {}
    Then the server runs setup_worktrees.sh --project-root <PROJECT_ROOT>
    And the response contains { "status": "ok" }
    And .worktrees/architect-session, .worktrees/builder-session, .worktrees/qa-session are created

#### Scenario: End Collab Removes Worktrees via Dashboard (Clean State)

    Given worktrees exist at .worktrees/architect-session, .worktrees/builder-session, .worktrees/qa-session
    And all worktrees have clean git status
    And no worktree branches have commits ahead of main
    When a POST request is sent to /end-collab with body { "force": true }
    Then the server runs teardown_worktrees.sh --force
    And the response contains { "status": "ok" }
    And no worktrees remain under .worktrees/

### Manual Scenarios (Human Verification Required)

#### Scenario: Sessions Table Displays Worktree State

    Given the CDD server is running from the project root
    And three worktrees exist (architect-session, builder-session, qa-session)
    When the User opens the CDD dashboard
    Then the WORKSPACE & COLLABORATION section is visible
    And the Sessions sub-section shows a table with Role, Branch, Dirty, and Last Activity columns
    And each worktree appears as a row with correct role and branch information

#### Scenario: Pre-Merge Status Shows Ready Indicator

    Given a builder worktree has passed all auto-evaluable handoff steps
    When the User views the Pre-Merge Status sub-section
    Then the builder row shows a check mark and "Ready to merge"

#### Scenario: Pre-Merge Status Shows Pending Count

    Given an architect worktree has 2 handoff items pending
    When the User views the Pre-Merge Status sub-section
    Then the architect row shows "2 items pending" with a "view checklist ->" indicator

#### Scenario: Start Collab Button Visible in Standard WORKSPACE Mode

    Given no worktrees exist under .worktrees/
    When the User opens the CDD dashboard
    Then the WORKSPACE section shows a "Start Collab Session" button in the footer
    And clicking the button directly triggers the POST /start-collab request with no inline form

#### Scenario: End Collab Button Shows Safety Warning When Worktrees Are Dirty

    Given worktrees exist and at least one worktree has uncommitted changes
    When the User clicks the "End Collab Session" button
    Then a modal appears listing the dirty worktree and its uncommitted files
    And the modal instructs the user to commit or stash before ending the session
    And the Confirm button is disabled

---

## 4. Visual Specification

### Screen: CDD Dashboard — WORKSPACE & COLLABORATION Section

- **Reference:** N/A
- [ ] Section heading reads "WORKSPACE & COLLABORATION" when collab mode is active (vs "WORKSPACE" when not)
- [ ] "Sessions" sub-label is visible above the worktree table
- [ ] Sessions table has columns: Role, Branch, Dirty?, Last Activity
- [ ] Each active worktree appears as a row
- [ ] Role badges use same styling as status badges (no new colors needed)
- [ ] Dirty indicator shows file count (e.g., "2 files") or "Clean"
- [ ] Last Activity shows relative timestamp + last commit subject
- [ ] "Pre-Merge Status" sub-label is visible below the Sessions table
- [ ] Ready worktrees show a check mark ("Ready to merge")
- [ ] Pending worktrees show a circle indicator ("N items pending")
- [ ] "Local (main)" sub-label introduces the existing workspace content

### Screen: CDD Dashboard — Collab Session Controls

- **Reference:** N/A
- [ ] "Start Collab Session" button is visible in the WORKSPACE section footer when no worktrees are present
- [ ] "Start Collab Session" is a single button; clicking it directly sends the POST /start-collab request (no inline form or text input)
- [ ] "End Collab Session" button is visible in the WORKSPACE & COLLABORATION section header when collab is active
- [ ] End Collab dirty-state modal lists dirty worktree names and uncommitted file counts; Confirm button is disabled
- [ ] End Collab unsynced-state modal includes an "I understand, the branches still exist" checkbox; Confirm is disabled until checked
- [ ] End Collab clean-state modal shows a simple Confirm/Cancel dialog

---

## 5. Implementation Notes

The CDD dashboard is read-only with respect to worktree monitoring — it uses `git -C <path>` to query state without modifying anything, and Collab Mode detection happens on every `/status.json` call.

The `/start-collab` and `/end-collab` endpoints are intentional exceptions to the read-only pattern: they delegate to `tools/collab/setup_worktrees.sh` and `tools/collab/teardown_worktrees.sh` respectively. These endpoints are explicit write operations initiated by the user; they are not invoked automatically by the dashboard's status polling.

The Pre-Merge Status evaluation deliberately avoids running the full handoff checklist (which may have side effects or require user interaction). It only evaluates items that can be determined from git state alone.

**[CLARIFICATION]** The End Collab modal is implemented as a dedicated overlay element (`collab-modal-overlay`) rather than reusing the feature detail modal, since it has a different structure (checkbox, 3-state content, no tabs). The modal is populated by `showEndCollabModal()` based on the dry-run response JSON. (Severity: INFO)

**[CLARIFICATION]** The `POST /end-collab` endpoint without `dry_run` or `force` flags runs teardown without `--force`, which means dirty worktrees will block it (the script returns exit code 1). The dashboard always does a dry-run first before showing the modal, then sends `force: true` on confirm. (Severity: INFO)

**[CLARIFICATION]** The Critic's `parse_visual_spec()` regex (`^##\s+Visual\s+Specification`) does not match numbered section headers like `## 4. Visual Specification`. Acknowledged by Architect — `features/critic_tool.md` Section 2.13 updated to require numbered-prefix detection, and a new Gherkin scenario was added. Builder must update the regex in `parse_visual_spec()` and add a corresponding test case.

## User Testing Discoveries

### [BUG] Start Collab Session button has incorrect colors in dark mode (Discovered: 2026-02-22)
- **Scenario:** Visual Specification — Screen: CDD Dashboard — Collab Session Controls
- **Observed Behavior:** In dark mode, the "Start Collab Session" button renders with a light background and dark text, opposite of the correct dark-mode button style.
- **Expected Behavior:** Button should have a darker background with lighter text, matching the styling of other dashboard action buttons (e.g., "Run Critic"), consistent with the Purlin CSS token system (Section 2.7).
- **Action Required:** Builder
- **Status:** RESOLVED
