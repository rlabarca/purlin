# Feature: CDD Collab Mode

> Label: "Tool: CDD Collab Mode"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md

[TODO]

## 1. Overview

CDD Collab Mode is a dashboard mode activated automatically when the CDD server runs from a project root that has active git worktrees under `.worktrees/`. In Collab Mode, the Workspace section of the dashboard becomes "Collaboration", showing what each agent role session is doing.

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
- `build/*` → Builder
- `qa/*` → QA
- Any other prefix → Unknown (shown as a worktree but displayed as role-unlabeled)

### 2.3 Collaboration Section

When Collab Mode is active, the WORKSPACE section becomes "Collaboration". It contains two sub-sections:

**Sessions sub-section:** A table listing all active worktrees:

| Role | Branch | Main Diff | Modified |
|------|--------|-----------|----------|
| Architect | spec/collab | BEHIND | 2 Specs 1 Code/Other |
| Builder | build/collab | SAME | |
| QA | qa/collab | SAME | 1 Tests |

"Main Diff" shows whether the worktree's branch has all commits from main:
- `SAME` — no commits on main are missing from this worktree's branch; the branch may additionally be ahead.
- `BEHIND` — one or more commits exist on main that are not in this worktree's branch. Run `/pl-work-pull` before pushing.

Combined interpretation: SAME + empty Modified = aligned with main. SAME + non-empty Modified = new committed or uncommitted work ready to push. BEHIND = sync with main required before this worktree can push.

"Modified" is empty when the worktree is clean. When uncommitted changes exist, it shows space-separated category counts in order: Specs (files under `features/`), Tests (files under `tests/`), Code/Other (all other files). Zero-count categories are omitted. Example: `"2 Specs"`, `"1 Tests 4 Code/Other"`, `"3 Specs 1 Tests 6 Code/Other"`.

**Local (main) sub-section:** Current state of the main checkout (existing WORKSPACE content):

- Branch name, ahead/behind status.
- Clean/dirty state.
- Last commit summary.

### 2.4 Worktree State Reading

CDD reads each worktree's state using read-only git commands:

- `git worktree list --porcelain` — all worktree paths and HEAD commits.
- `git -C <path> rev-parse --abbrev-ref HEAD` — branch name per worktree.
- `git -C <path> status --porcelain` — modified/staged/untracked files per worktree. Output is parsed by path prefix to count per-category modified files:
  - Lines where the file path (columns 4+) starts with `features/` → Specs count.
  - Lines where the file path starts with `tests/` → Tests count.
  - All other modified/staged/untracked lines → Code/Other count.
- `git -C <path> log -1 --format='%h %s (%cr)'` — last commit per worktree.
- `git -C <path> rev-list --count main..HEAD` → `commits_ahead` (int).
- `git log <worktree-branch>..main --oneline` — determine whether the worktree branch is behind main.

  Run from the **project root** (not via `git -C <worktree-path>`), using the worktree's branch name as the range start. This is necessary because the CDD server has the full ref namespace and can evaluate `main` authoritatively. Agents running inside a worktree may not reliably resolve `main` in all configurations.

  - If output is non-empty → `main_diff: "BEHIND"`
  - If output is empty → `main_diff: "SAME"`

CDD writes nothing to worktree paths. No interference with running agent sessions.
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
      "main_diff": "BEHIND",
      "commits_ahead": 0,
      "last_commit": "abc1234 feat(spec): add filtering scenarios (45 min ago)",
      "modified": {
        "specs": 2,
        "tests": 0,
        "other": 1
      }
    },
    {
      "path": ".worktrees/builder-session",
      "branch": "build/collab",
      "role": "builder",
      "main_diff": "SAME",
      "commits_ahead": 3,
      "last_commit": "def5678 feat(build): implement CRUD handlers (12 min ago)",
      "modified": {
        "specs": 0,
        "tests": 0,
        "other": 0
      }
    }
  ]
}
```

When Collab Mode is not active: `collab_mode` is false (or omitted) and `worktrees` is absent.

Fields per worktree entry:

- `path` — relative path from project root.
- `branch` — current branch name.
- `role` — `"architect"`, `"builder"`, `"qa"`, or `"unknown"`.
- `main_diff` — `"SAME"` if no commits on main are missing from this worktree's branch; `"BEHIND"` otherwise. Computed via `git log <branch>..main --oneline` from the project root.
- `commits_ahead` — integer count of commits in this branch not yet in main. Always present (0 when none).
- `last_commit` — formatted string: `"<hash> <subject> (<relative-time>)"`.
- `modified` — object with integer sub-fields `specs`, `tests`, and `other` (all ≥ 0). A worktree is clean when all three are zero. Counts are derived from `git status --porcelain` output parsed by path prefix.

### 2.7 Visual Design

The Collaboration section uses the same Purlin CSS tokens as the rest of the dashboard. No new design tokens are introduced. The section heading changes from "Workspace" to "Collaboration" when Collab Mode is active. Sub-section labels ("Sessions", "Local (main)") use the same section header typography.

### 2.8 No Collab Mode During Main Checkout

When the CDD server is run from within a worktree (not the project root), Collab Mode is not available. The dashboard operates in standard mode. Only the project root has visibility into all worktrees.

### 2.9 Collab Session Controls

The dashboard exposes UI controls to start and stop Collab Sessions, complementing the CLI scripts in `tools/collab/`.

**Start Collab Session (when Collab Mode is inactive):**

- A "Start Collab Session" button appears as a footer action in the standard Workspace section.
- Clicking the button directly triggers `POST /start-collab` with an empty body `{}`. No text input or form is shown.
- While the request is in flight, the 5-second auto-refresh timer MUST be paused to prevent the error message from being wiped before the user sees it. The timer is resumed after the response is received (success or error). This is the same guard pattern used by `rcPendingSave` in the release checklist.
- The server runs `tools/collab/setup_worktrees.sh --project-root <PROJECT_ROOT>` (no `--feature` argument).
- On success (`{ "status": "ok" }`): dashboard refreshes; Workspace becomes Collaboration.
- On error: inline error message shown below the button.

**End Collab Session (when Collab Mode is active):**

- An "End Collab Session" button appears in the Collaboration section header.
- On click: dashboard sends `POST /end-collab` with body `{ "dry_run": true }`. The server runs `tools/collab/teardown_worktrees.sh --dry-run` and returns the safety status.
- The dashboard shows a modal based on the dry-run result:
  - **Dirty worktrees present:** Modal lists the dirty worktrees and their uncommitted files. Instructs the user to commit or stash before ending the session. Confirm button is disabled. No force path is offered.
  - **Unsynced commits present (no dirty):** Modal shows a warning listing unmerged branches and commit counts, with a note that branches survive worktree removal. User must check "I understand, the branches still exist" before the Confirm button is enabled.
  - **Clean state:** Simple confirmation dialog with Confirm and Cancel buttons.
- On confirm: dashboard sends `POST /end-collab` with body `{ "force": true }`. Server runs `tools/collab/teardown_worktrees.sh --force`.
- On success: dashboard refreshes; Collaboration becomes standard Workspace.

**Server endpoints:**

- `POST /start-collab` — body: `{}` (empty; no `feature` field required or accepted) — runs `setup_worktrees.sh`, returns `{ "status": "ok" }` or `{ "error": "..." }`.
- `POST /end-collab` — body: `{ "dry_run": true }` or `{ "force": true }` — runs `teardown_worktrees.sh` with the appropriate flag. Returns safety status JSON for dry-run; returns `{ "status": "ok" }` for a force run.
- Both endpoints follow the same pattern as `/run-critic` in `serve.py`.

### 2.10 Agent Config Propagation in Collab Mode

Agent configs in `.purlin/config.json` apply to ALL local instances of each agent role — not just the agent launched from the project root. In Collab Mode, worktrees each hold their own committed copy of `.purlin/config.json`. Changes made via the dashboard must be propagated to every active worktree so that all agent sessions reflect the new settings.

**AGENTS Section Heading:**
- When Collab Mode is active, the AGENTS section heading displays the annotation "(applies across all local worktrees)" appended to the title.
- Applied client-side: after each `/status.json` poll, if `collab_mode` is true, the heading reads "AGENTS (applies across all local worktrees)". When collab mode is inactive, the heading reads "AGENTS" with no annotation.

**Save Propagation:**
- `POST /config/agents` writes to the project root `.purlin/config.json` first.
- If Collab Mode is active, the handler also writes the same updated config to each active worktree's `.purlin/config.json`.
- Propagation is best-effort per-worktree: a failure to write one worktree is logged server-side and included in the response as `{ "warnings": ["..."] }`, but does not roll back the project root write or block the response.
- Worktree list determined by `get_collab_worktrees()` — no new detection mechanism.
- This is a push model: agents in worktrees do NOT search up the directory tree for a parent config. Each worktree reads its own `.purlin/config.json` only.

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

    Given worktrees on branches spec/feature-a, build/feature-a, qa/feature-a
    When an agent calls GET /status.json
    Then the worktrees array contains entries with roles architect, builder, and qa respectively

#### Scenario: Unknown Role for Non-Standard Branch

    Given a worktree on branch hotfix/urgent-fix
    When an agent calls GET /status.json
    Then the worktree entry has role "unknown"

#### Scenario: Dirty State Detected

    Given a worktree at .worktrees/build-session has uncommitted files
    When an agent calls GET /status.json
    Then the worktree entry's modified object has at least one non-zero field (specs, tests, or other)

#### Scenario: Commits Ahead Reported When Worktree Branch Is Ahead Of Main

    Given a worktree at .worktrees/builder-session has 3 commits not yet merged to main
    When an agent calls GET /status.json
    Then the worktree entry has commits_ahead equal to 3

#### Scenario: Start Collab Creates Worktrees via Dashboard

    Given no worktrees exist under .worktrees/
    And the CDD server is running
    When a POST request is sent to /start-collab with body {}
    Then the server runs setup_worktrees.sh --project-root <PROJECT_ROOT>
    And the response contains { "status": "ok" }
    And .worktrees/architect-session, .worktrees/build-session, .worktrees/qa-session are created

#### Scenario: End Collab Removes Worktrees via Dashboard (Clean State)

    Given worktrees exist at .worktrees/architect-session, .worktrees/build-session, .worktrees/qa-session
    And all worktrees have clean git status
    And no worktree branches have commits ahead of main
    When a POST request is sent to /end-collab with body { "force": true }
    Then the server runs teardown_worktrees.sh --force
    And the response contains { "status": "ok" }
    And no worktrees remain under .worktrees/

#### Scenario: Agent Config Save Propagates to All Active Worktrees

    Given collab mode is active with two worktrees: architect-session and builder-session
    When a POST request is sent to /config/agents with updated model and startup_sequence values
    Then the project root .purlin/config.json reflects the new values
    And .worktrees/architect-session/.purlin/config.json reflects the new values
    And .worktrees/builder-session/.purlin/config.json reflects the new values

#### Scenario: Modified Column Categorizes Uncommitted Files by Type

    Given a worktree at .worktrees/architect-session has two modified files under features/
    And one modified file outside features/ and tests/
    When an agent calls GET /status.json
    Then the worktree entry's modified field has specs=2, tests=0, other=1

#### Scenario: Main Diff BEHIND When Worktree Branch Is Missing Main Commits

    Given a worktree at .worktrees/architect-session on branch spec/collab
    And main has commits that are not in spec/collab
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "BEHIND"

#### Scenario: Main Diff SAME When Worktree Branch Has All Main Commits

    Given a worktree at .worktrees/builder-session on branch build/collab
    And build/collab has all commits that are in main (may also be ahead)
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "SAME"

### Manual Scenarios (Human Verification Required)

#### Scenario: Sessions Table Displays Worktree State

    Given the CDD server is running from the project root
    And three worktrees exist (architect-session, build-session, qa-session)
    When the User opens the CDD dashboard
    Then the Collaboration section is visible
    And the Sessions sub-section shows a table with Role, Branch, Main Diff, and Modified columns
    And each worktree appears as a row with correct role and branch information

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

### Screen: CDD Dashboard — Collaboration Section

- **Reference:** N/A
- [ ] Section heading reads "Collaboration" when collab mode is active (vs "Workspace" when not)
- [ ] "Sessions" sub-label is visible above the worktree table
- [ ] Sessions table has columns: Role, Branch, Main Diff, Modified
- [ ] Each active worktree appears as a row
- [ ] Role badges use same styling as status badges (no new colors needed)
- [ ] Main Diff cell shows "BEHIND" (styled as a warning badge) when the worktree branch is missing commits from main
- [ ] Main Diff cell shows "SAME" (neutral/muted style) when the worktree branch has all of main's commits
- [ ] Modified cell is empty when worktree is clean
- [ ] Modified cell shows category counts (e.g., "2 Specs", "1 Tests 4 Code/Other") when dirty
- [ ] Multiple categories appear in order: Specs, Tests, Code/Other; zero-count categories omitted
- [ ] "Local (main)" sub-label introduces the existing workspace content

### Screen: CDD Dashboard — Collab Session Controls

- **Reference:** N/A
- [ ] "Start Collab Session" button is visible in the Workspace section footer when no worktrees are present
- [ ] "Start Collab Session" is a single button; clicking it directly sends the POST /start-collab request (no inline form or text input)
- [ ] "End Collab Session" button is visible in the Collaboration section header when collab is active
- [ ] End Collab dirty-state modal lists dirty worktree names and uncommitted file counts; Confirm button is disabled
- [ ] End Collab unsynced-state modal includes an "I understand, the branches still exist" checkbox; Confirm is disabled until checked
- [ ] End Collab clean-state modal shows a simple Confirm/Cancel dialog
- [ ] AGENTS section heading reads "AGENTS (applies across all local worktrees)" when collab mode is active
- [ ] AGENTS section heading reads "AGENTS" (no annotation) when collab mode is inactive

---

## 5. Implementation Notes

The CDD dashboard is read-only with respect to worktree monitoring — it uses `git -C <path>` to query state without modifying anything, and Collab Mode detection happens on every `/status.json` call.

The `/start-collab` and `/end-collab` endpoints are intentional exceptions to the read-only pattern: they delegate to `tools/collab/setup_worktrees.sh` and `tools/collab/teardown_worktrees.sh` respectively. These endpoints are explicit write operations initiated by the user; they are not invoked automatically by the dashboard's status polling.

**[CLARIFICATION]** The End Collab modal is implemented as a dedicated overlay element (`collab-modal-overlay`) rather than reusing the feature detail modal, since it has a different structure (checkbox, 3-state content, no tabs). The modal is populated by `showEndCollabModal()` based on the dry-run response JSON. (Severity: INFO)

**[CLARIFICATION]** The `POST /end-collab` endpoint without `dry_run` or `force` flags runs teardown without `--force`, which means dirty worktrees will block it (the script returns exit code 1). The dashboard always does a dry-run first before showing the modal, then sends `force: true` on confirm. (Severity: INFO)

**Main Diff computation:** The `main_diff` field is computed at the project root — `git log <branch>..main --oneline` — not via `git -C <worktree-path>`. This ensures `main` resolves correctly regardless of the worktree's internal git context. Agents running inside a worktree should use `/pl-work-pull` to determine their own sync state; the dashboard is the authoritative display.

**[CLARIFICATION]** The Critic's `parse_visual_spec()` regex (`^##\s+Visual\s+Specification`) does not match numbered section headers like `## 4. Visual Specification`. Acknowledged by Architect — `features/critic_tool.md` Section 2.13 updated to require numbered-prefix detection, and a new Gherkin scenario was added. Builder must update the regex in `parse_visual_spec()` and add a corresponding test case.

- `commits_ahead`: uses `git rev-list --count main..HEAD` in `_worktree_state()`.
- `last_commit`: uses `git log -1 --format='%h %s (%cr)'` in `_worktree_state()`.
- `ROLE_PREFIX_MAP` in `serve.py`: `'build': 'builder'` (already updated from `impl` in a prior session).
- `main_diff`: computed by `_compute_main_diff(branch)` running `git log <branch>..main --oneline` from PROJECT_ROOT (not per-worktree). Returns "SAME" or "BEHIND".
- `modified`: `_worktree_state()` reads raw `git status --porcelain` output (not through `_wt_cmd` which strips leading whitespace) and categorizes by path prefix: `features/` → specs, `tests/` → tests, everything else → other.
- Pre-Merge Status sub-section and `_worktree_handoff_status()` / `_read_feature_summary()` removed — spec no longer requires handoff checks on the dashboard.
- Agent config propagation: `_handle_config_agents()` writes updated config to all active worktree `.purlin/config.json` files after the project root write. Failures are collected as `warnings` in the response.

**[CLARIFICATION]** The AGENTS heading annotation ("applies across all local worktrees") is applied server-side in `generate_html()` rather than client-side via JS. Since the dashboard's 5-second refresh fetches fresh server-rendered HTML, this is functionally equivalent to the spec's "applied client-side after each poll" phrasing — the heading updates on every refresh cycle. (Severity: INFO)

**[CLARIFICATION]** The `git status --porcelain` output is now read with raw `result.stdout` (no `.strip()`) to preserve the position-dependent XY status columns. The previous approach of using `_wt_cmd()` (which strips the entire output) would corrupt the first line's status columns, causing incorrect file categorization. (Severity: INFO)

## User Testing Discoveries

### [BUG] Start Collab Session button has incorrect colors in dark mode (Discovered: 2026-02-22)
- **Scenario:** Visual Specification — Screen: CDD Dashboard — Collab Session Controls
- **Observed Behavior:** In dark mode, the "Start Collab Session" button renders with a light background and dark text, opposite of the correct dark-mode button style.
- **Expected Behavior:** Button should have a darker background with lighter text, matching the styling of other dashboard action buttons (e.g., "Run Critic"), consistent with the Purlin CSS token system (Section 2.7).
- **Action Required:** Builder
- **Status:** RESOLVED
