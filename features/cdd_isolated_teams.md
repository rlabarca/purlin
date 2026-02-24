# Feature: CDD Isolated Teams Mode

> Label: "Tool: CDD Isolated Teams Mode"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md

[TODO]

## 1. Overview

CDD Isolated Teams Mode is activated automatically when the CDD server detects active named isolated teams (git worktrees under `.worktrees/`) in the project root. The dashboard always renders a standalone ISOLATED TEAMS section, positioned below the WORKSPACE section at the same visual level. When Isolated Teams Mode is active, that section is populated with a Sessions table showing each named isolated team's branch, sync state, and in-flight changes relative to `main`.

---

## 2. Requirements

### 2.1 Detection Mechanism

- On each status refresh, `serve.py` runs `git worktree list --porcelain` from the project root.
- Isolated Teams Mode is active when: at least one worktree other than the main checkout is listed AND its path is under `.worktrees/` relative to the project root.
- When Isolated Teams Mode is not active, the ISOLATED TEAMS section renders with no Sessions table rows; only the creation row is shown.
- Detection is read-only. CDD never writes to worktree paths.
- Detection governs the `/status.json` API fields (`isolations_active`, `worktrees`), the Agent Config heading annotation (Section 2.9), and config propagation behavior (Section 2.9). The ISOLATED TEAMS section is always rendered in the dashboard, regardless of detection state — see Section 2.3.

### 2.2 Isolation Name from Worktree Path

- The isolation name is parsed from the worktree path: `.worktrees/<name>/` → name is `<name>`.
- No role is inferred from the branch name. The `_role_from_branch()` function is removed.
- Any branch name is valid. The branch is displayed as-is; the name cell shows the parsed isolation name.

### 2.3 Dashboard Section Layout

The dashboard sidebar/content area contains four top-level collapsible sections in this order: ACTIVE, COMPLETE, WORKSPACE, ISOLATED TEAMS. WORKSPACE and ISOLATED TEAMS are peers — they appear at the same indent level, one after the other. ISOLATED TEAMS is never nested inside WORKSPACE.

**WORKSPACE section:**
- Collapsible heading labeled "WORKSPACE".
- When expanded, shows the Local (main) git status content: branch name, ahead/behind status, clean/dirty state, and last commit summary.
- When collapsed, shows just the section heading.
- When the main checkout has no uncommitted changes, the expanded content carries no additional annotations. Text such as "Ready for specs" MUST NOT be appended when the checkout is clean.
- Files under `.purlin/` are excluded from the clean/dirty determination.

**ISOLATED TEAMS section:**
- Collapsible heading labeled "ISOLATED TEAMS", positioned directly below the WORKSPACE section at the same visual indent level.
- Always rendered, regardless of whether any worktrees are active.

**ISOLATED TEAMS heading collapse behavior:**

- **Collapsed, no active worktrees:** The heading label reads "ISOLATED TEAMS" with no annotation.
- **Collapsed, N active worktrees:** The heading label reads "N Isolated Teams" (e.g., "2 Isolated Teams") in the normal section heading color (`--purlin-muted`). The heading text MUST NOT change color based on worktree severity state — it always renders in the same color as any other collapsed section heading.

**ISOLATED TEAMS section expanded content (in order):**

1. **Creation row:** Always the first item when the section is expanded. Never hidden, regardless of whether any worktrees are active. See Section 2.8 for full creation controls detail.

2. **Sessions table:** A table listing all active worktrees, appearing below the creation row. When no worktrees are active, only the creation row is shown.

   | Name | Branch | Main Diff | Modified |
   |------|--------|-----------|----------|
   | feat1 | isolated/feat1 | AHEAD | 2 Specs |
   | ui | isolated/ui | SAME | |

   Each row also has a "Kill" button (see Section 2.8).

**Main Diff** shows the sync state between the worktree's branch and main:
- `AHEAD` — only this branch has moved: it has commits not yet in main; main has no commits missing from this branch. Modified reflects files the branch changed since its common ancestor with main.
- `SAME` — branch and main are at identical commit positions. Modified will always be empty.
- `BEHIND` — only main has moved: it has commits not yet in this branch; this branch has no commits ahead of main. Run `/pl-local-pull` before pushing. Modified will always be empty.
- `DIVERGED` — both main and this branch have commits beyond their common ancestor. Run `/pl-local-pull` before pushing. Modified reflects files the branch changed since the common ancestor.

**Modified** shows files the branch changed since its common ancestor with main — derived from `git diff main...<branch> --name-only` (three-dot), not from uncommitted changes in the worktree. Modified is always empty when `main_diff` is `SAME` or `BEHIND`. Modified may be empty even when `main_diff` is `AHEAD` or `DIVERGED` if the branch's commits contain no file changes (e.g., `--allow-empty` status commits). When non-empty, it shows space-separated category counts in order: Specs (files under `features/`), Tests (files under `tests/`), Code/Other (all other files). Zero-count categories are omitted. Example: `"2 Specs"`, `"1 Tests 4 Code/Other"`, `"3 Specs 1 Tests 6 Code/Other"`. Files under `.purlin/` are excluded from all categories.

### 2.4 Worktree State Reading

CDD reads each worktree's state using read-only git commands:

- `git worktree list --porcelain` — all worktree paths and HEAD commits.
- `git -C <path> rev-parse --abbrev-ref HEAD` — branch name per worktree.
- `git diff main...<branch> --name-only` — files the branch changed since its common ancestor with main (three-dot diff), run from the **project root**. This is always empty for `SAME` and `BEHIND` states; may be empty for `AHEAD` or `DIVERGED` if the branch's commits touch no files. Output is one filename per line, parsed by path prefix to count per-category modified files:
  - Lines starting with `.purlin/` → **excluded entirely** (not counted in any category).
  - Lines starting with `features/` → Specs count.
  - Lines starting with `tests/` → Tests count.
  - All other lines → Code/Other count.
- `git -C <path> log -1 --format='%h %s (%cr)'` — last commit per worktree.
- `git -C <path> rev-list --count main..HEAD` → `commits_ahead` (int).
- Two `git log` range queries to determine `main_diff` — run from the **project root** (not via `git -C <worktree-path>`), using the worktree's branch name:

  1. `git log <branch>..main --oneline` — commits on main not in branch (branch is behind).
  2. `git log main..<branch> --oneline` — commits on branch not in main (branch is ahead).

  Evaluation:
  - If query 1 is non-empty AND query 2 is non-empty → `main_diff: "DIVERGED"`
  - If query 1 is non-empty AND query 2 is empty → `main_diff: "BEHIND"`
  - If query 1 is empty AND query 2 is non-empty → `main_diff: "AHEAD"`
  - If both empty → `main_diff: "SAME"`

CDD writes nothing to worktree paths. No interference with running agent sessions.

### 2.5 /status.json API Extension

When Isolated Teams Mode is active, the `/status.json` response includes additional fields:

```json
{
  "isolations_active": true,
  "worktrees": [
    {
      "name": "feat1",
      "path": ".worktrees/feat1",
      "branch": "isolated/feat1",
      "main_diff": "AHEAD",
      "commits_ahead": 3,
      "last_commit": "abc1234 feat: add filtering scenarios (45 min ago)",
      "modified": {
        "specs": 2,
        "tests": 0,
        "other": 1
      },
      "delivery_phase": {
        "current": 2,
        "total": 3
      }
    },
    {
      "name": "ui",
      "path": ".worktrees/ui",
      "branch": "isolated/ui",
      "main_diff": "SAME",
      "commits_ahead": 0,
      "last_commit": "def5678 feat(ui): implement dashboard component (12 min ago)",
      "modified": {
        "specs": 0,
        "tests": 0,
        "other": 0
      }
    }
  ]
}
```

When Isolated Teams Mode is not active: `isolations_active` is false (or omitted) and `worktrees` is absent.

Fields per worktree entry:

- `name` — isolation name, parsed from worktree path (e.g., `.worktrees/feat1` → `"feat1"`).
- `path` — relative path from project root.
- `branch` — current branch name.
- `main_diff` — four-state sync indicator (`"SAME"`, `"AHEAD"`, `"BEHIND"`, `"DIVERGED"`). Computed via two `git log` range queries from the project root.
- `commits_ahead` — integer count of commits in this branch not yet in main. Always present (0 when none).
- `last_commit` — formatted string: `"<hash> <subject> (<relative-time>)"`.
- `modified` — object with integer sub-fields `specs`, `tests`, and `other` (all ≥ 0). Derived from `git diff main...<branch> --name-only` (three-dot) run from project root. Files under `.purlin/` are excluded.
- `delivery_phase` — optional object with `current` (int) and `total` (int). Present only when the worktree's `.purlin/cache/delivery_plan.md` exists and has an IN_PROGRESS phase. Absent when no delivery plan exists or all phases are COMPLETE.

### 2.6 Visual Design

The ISOLATED TEAMS section uses the same Purlin CSS tokens as the rest of the dashboard. No new design tokens are introduced. WORKSPACE and ISOLATED TEAMS are peer sections: both use identical section heading styling (same typography, same toggle affordance, same indent level). The WORKSPACE heading is unchanged regardless of Isolated Teams Mode state.

### 2.7 No Isolated Teams Mode During Main Checkout

When the CDD server is run from within a worktree (not the project root), Isolated Teams Mode is not available. The dashboard operates in standard mode. Only the project root has visibility into all worktrees.

### 2.8 New Isolation Controls

The dashboard exposes UI controls to create and remove isolations, complementing the CLI scripts in `tools/collab/`.

**Creation Row (always the first item in the expanded Isolated Teams sub-section):**

- The row is prepended with the label "Create An Isolated Team".
- The label is followed by a text input (max 12 characters, validated) and a "Create" button.
- The creation row is never hidden — it is visible whether or not any worktrees are active, and it always appears above the Sessions table.
- **Input value persistence:** The name input value is preserved across auto-refreshes. The dashboard JavaScript saves the input's current value to a module-level variable before each DOM update and restores it immediately after. The user's in-progress text is never wiped by the 5-second polling cycle.
- **Input visual style:** The name text input uses the same color scheme as the dashboard header's search/filter input: `--purlin-surface` background, `--purlin-border` border, `--purlin-dim` placeholder text color, and `--purlin-primary` foreground text color. This ensures consistent theme adaptation between Blueprint (dark) and Architect (light) modes.
- Client-side validation: name must match `[a-zA-Z0-9_-]+` and be ≤12 characters. The Create button is disabled until the name is valid.
- The name input MUST include `autocapitalize="none"` and `autocorrect="off"` HTML attributes to suppress browser auto-capitalization and autocorrect on mobile and desktop browsers.
- Clicking Create sends `POST /isolate/create` with body `{ "name": "<name>" }`.
- While the request is in flight, the 5-second auto-refresh timer MUST be paused to prevent the error message from being wiped before the user sees it. The timer is resumed after the response is received (success or error).
- The server runs `tools/collab/create_isolation.sh <name> --project-root <PROJECT_ROOT>`.
- On success (`{ "status": "ok" }`): dashboard refreshes; new isolation appears in the Sessions table. The input is cleared on success.
- On error: inline error message shown below the input.

**Kill button (per-row, Sessions table):**

- Each row in the Sessions table has a "Kill" button.
- On click: dashboard sends `POST /isolate/kill` with body `{ "name": "<name>", "dry_run": true }`. The server runs `kill_isolation.sh <name> --dry-run` and returns the safety status.
- The dashboard shows a modal based on the dry-run result:
  - **Dirty worktree:** Modal lists the dirty files. Instructs the user to commit or stash first. Confirm button is disabled. No force path is offered.
  - **Unsynced commits (no dirty):** Modal shows a warning with the unmerged branch name and commit count. User must check "I understand, the branch still exists" before the Confirm button is enabled.
  - **Clean state:** Simple confirmation dialog with Confirm and Cancel buttons.
- On confirm: dashboard sends `POST /isolate/kill` with body `{ "name": "<name>", "force": true }`. Server runs `kill_isolation.sh <name> --force`.
- On success: dashboard refreshes; isolation row disappears from the Sessions table.

**Server endpoints:**

- `POST /isolate/create` — body: `{ "name": "<name>" }` — validates name server-side, runs `create_isolation.sh <name>`, returns `{ "status": "ok" }` or `{ "error": "..." }`.
- `POST /isolate/kill` — body: `{ "name": "<name>", "dry_run": true }` or `{ "name": "<name>", "force": true }` — runs `kill_isolation.sh <name>` with the appropriate flag. Returns safety status JSON for dry-run; returns `{ "status": "ok" }` for a force run.
- Both endpoints follow the same pattern as `/run-critic` in `serve.py`.

### 2.9 Agent Config Propagation

Agent configs in `.purlin/config.json` apply to ALL local instances of each agent role — not just the agent launched from the project root. In Isolated Teams Mode, worktrees each hold their own committed copy of `.purlin/config.json`. Changes made via the dashboard must be propagated to every active isolation so that all agent sessions reflect the new settings.

**Agent Config Section Heading:**
- When Isolated Teams Mode is active, the Agent Config section heading displays the annotation "(applies across all local isolations)" appended to the title.
- Applied server-side in `generate_html()`. Since the dashboard refreshes every 5 seconds, the heading updates on every refresh cycle.

**Save Propagation:**
- `POST /config/agents` writes to the project root `.purlin/config.json` first.
- If Isolated Teams Mode is active, the handler also writes the same updated config to each active worktree's `.purlin/config.json`.
- **Propagated write uses full config:** The value written to each worktree MUST be the complete `current` config object (all top-level keys: `cdd_port`, `tools_root`, `models`, `agents`, etc.) — not just the `agents` subtree. The worktree config MUST NOT be reduced to a partial structure as a result of propagation.
- **Propagated write uses merge semantics:** The propagation reads each worktree's existing `.purlin/config.json`, merges the updated `agents` object into it, and writes back the full merged result. If a worktree's config cannot be read, the project root's full `current` config is written as the fallback.
- Propagation is best-effort per-worktree: a failure to write one worktree is logged server-side and included in the response as `{ "warnings": ["..."] }`, but does not roll back the project root write or block the response.
- Worktree list determined by `get_isolation_worktrees()` — no new detection mechanism.
- This is a push model: agents in worktrees do NOT search up the directory tree for a parent config. Each worktree reads its own `.purlin/config.json` only.

### 2.10 Delivery Phase Badge

Each worktree row in the Sessions table MAY display an orange `(Phase N/M)` badge in the Name cell.

**Detection:**
- After reading the worktree's state, the server checks for `.purlin/cache/delivery_plan.md` in the worktree directory (read-only stat only).
- If the file exists, the server reads it and parses the current IN_PROGRESS phase number (N) and total phase count (M).
- If an IN_PROGRESS phase is found: the `delivery_phase: { current: N, total: M }` field is added to the worktree's status entry.
- If no delivery plan exists, or all phases are COMPLETE, the field is absent from the status entry.

**Display:**
- When `delivery_phase` is present in the worktree entry, the Name cell renders: `<name> (Phase N/M)`.
- The `(Phase N/M)` annotation uses the same orange color (`--purlin-status-warning`) as the ACTIVE section header's phase annotation.
- No badge is shown when `delivery_phase` is absent.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Isolations Inactive When No Worktrees

    Given git worktree list shows only the main checkout
    When an agent calls GET /status.json
    Then isolations_active is false or absent
    And no worktrees array is present in the response

#### Scenario: Isolations Active When Worktrees Detected

    Given a worktree exists at .worktrees/feat1 on branch isolated/feat1
    When an agent calls GET /status.json
    Then isolations_active is true
    And the worktrees array contains one entry with name "feat1"
    And the entry has path ".worktrees/feat1" and branch "isolated/feat1"
    And the entry has no role field

#### Scenario: Isolation Name Parsed from Worktree Path

    Given a worktree at .worktrees/ui on branch isolated/ui
    When an agent calls GET /status.json
    Then the worktree entry has name "ui"

#### Scenario: Non-Isolated Branch Worktrees Detected Without Role Assignment

    Given a worktree at .worktrees/hotfix on branch hotfix/urgent
    When an agent calls GET /status.json
    Then the worktree entry has name "hotfix" and branch "hotfix/urgent"
    And no role field is present in the entry

#### Scenario: Modified Non-Empty When Branch Is AHEAD Of Main

    Given a worktree at .worktrees/feat1 is AHEAD of main with commits that modified files
    When an agent calls GET /status.json
    Then the worktree entry's modified object has at least one non-zero field (specs, tests, or other)

#### Scenario: Commits Ahead Reported When Worktree Branch Is Ahead Of Main

    Given a worktree at .worktrees/feat1 has 3 commits not yet merged to main
    When an agent calls GET /status.json
    Then the worktree entry has commits_ahead equal to 3

#### Scenario: Create Isolation via Dashboard

    Given no worktree exists at .worktrees/feat1
    And the CDD server is running
    When a POST request is sent to /isolate/create with body {"name": "feat1"}
    Then the server runs create_isolation.sh feat1 --project-root <PROJECT_ROOT>
    And the response contains { "status": "ok" }
    And .worktrees/feat1/ is created on branch isolated/feat1

#### Scenario: Create Isolation Rejected When Name Is Invalid

    Given the CDD server is running
    When a POST request is sent to /isolate/create with body {"name": "toolongname123"}
    Then the server returns { "error": "..." }
    And no worktree is created

#### Scenario: Kill Isolation via Dashboard (Clean State)

    Given a worktree exists at .worktrees/feat1 with no uncommitted changes and no unmerged commits
    When a POST request is sent to /isolate/kill with body {"name": "feat1", "force": true}
    Then the server runs kill_isolation.sh feat1 --force
    And the response contains { "status": "ok" }
    And no worktree remains at .worktrees/feat1

#### Scenario: Kill Isolation Dry Run Returns Safety Status

    Given a worktree at .worktrees/feat1 has uncommitted changes
    When a POST request is sent to /isolate/kill with body {"name": "feat1", "dry_run": true}
    Then the server runs kill_isolation.sh feat1 --dry-run
    And the response contains dirty: true and dirty_files listing the changed files
    And no worktree is removed

#### Scenario: Agent Config Save Propagates to All Active Isolations

    Given isolations_active is true with two worktrees: .worktrees/feat1 and .worktrees/ui
    When a POST request is sent to /config/agents with updated model and startup_sequence values
    Then the project root .purlin/config.json reflects the new values
    And .worktrees/feat1/.purlin/config.json reflects the new values
    And .worktrees/ui/.purlin/config.json reflects the new values

#### Scenario: Modified Column Categorizes Files Changed Against Main by Type

    Given a worktree at .worktrees/feat1 on a branch AHEAD of main
    And the branch's commits modified two files under features/ and one file outside features/ and tests/
    When an agent calls GET /status.json
    Then the worktree entry's modified field has specs=2, tests=0, other=1

#### Scenario: Main Diff BEHIND When Worktree Branch Is Missing Main Commits

    Given a worktree at .worktrees/feat1 on branch isolated/feat1
    And main has commits that are not in isolated/feat1
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "BEHIND"

#### Scenario: Main Diff AHEAD When Worktree Branch Has Commits Not In Main

    Given a worktree at .worktrees/feat1 on branch isolated/feat1
    And isolated/feat1 has commits that are not in main
    And main has no commits that are missing from isolated/feat1
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "AHEAD"

#### Scenario: Main Diff SAME When Branch And Main Are Identical

    Given a worktree at .worktrees/ui on branch isolated/ui
    And isolated/ui and main point to the same commit
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "SAME"

#### Scenario: Main Diff DIVERGED When Both Main And Branch Have Commits Beyond Common Ancestor

    Given a worktree at .worktrees/feat1 on branch isolated/feat1
    And isolated/feat1 has commits not in main
    And main has commits not in isolated/feat1
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "DIVERGED"

#### Scenario: Delivery Phase Badge Present When Delivery Plan Has Active Phase

    Given a worktree at .worktrees/feat1 has .purlin/cache/delivery_plan.md
    And the delivery plan has Phase 2 as IN_PROGRESS out of 3 total phases
    When an agent calls GET /status.json
    Then the worktree entry has delivery_phase.current equal to 2
    And delivery_phase.total equal to 3

#### Scenario: Delivery Phase Badge Absent When No Delivery Plan

    Given a worktree at .worktrees/ui has no .purlin/cache/delivery_plan.md
    When an agent calls GET /status.json
    Then the worktree entry has no delivery_phase field

### Manual Scenarios (Human Verification Required)

#### Scenario: Sessions Table Displays Named Isolations

    Given the CDD server is running from the project root
    And two worktrees exist (.worktrees/feat1 and .worktrees/ui)
    When the User opens the CDD dashboard
    Then the Isolated Teams section is visible
    And the Sessions sub-section shows a table with Name, Branch, Main Diff, and Modified columns
    And each worktree appears as a row with its isolation name and branch
    And no Role column is present

#### Scenario: New Isolation Input Creates Named Worktree

    Given the CDD dashboard is open
    And the New Isolation input is visible in the section footer
    When the User types "feat2" into the input and clicks Create
    Then a new row appears in the Sessions table with name "feat2"
    And .worktrees/feat2/ exists in the project root

#### Scenario: New Isolation Input Rejects Invalid Names

    Given the CDD dashboard is open
    When the User types "toolongname123" (14 chars) into the New Isolation input
    Then the Create button remains disabled
    And an inline validation message is shown

#### Scenario: Kill Button Shows Safety Modal for Named Worktree

    Given a worktree at .worktrees/feat1 has uncommitted changes
    When the User clicks the Kill button on the feat1 row
    Then a modal appears listing the uncommitted files
    And the modal instructs the user to commit or stash before killing
    And the Confirm button is disabled

#### Scenario: Delivery Phase Badge Visible in Worktree Row

    Given a worktree at .worktrees/feat1 has an active delivery plan at Phase 1 of 2
    When the User views the Sessions table
    Then the feat1 row's Name cell shows "feat1 (Phase 1/2)"
    And the badge text is rendered in orange (--purlin-status-warning)

#### Scenario: Isolated Teams Sub-heading Collapsed With No Active Worktrees

    Given the CDD dashboard is open
    And no worktrees are active under .worktrees/
    When the User collapses the Isolated Teams sub-heading
    Then the collapsed label reads "ISOLATED TEAMS" with no annotation

#### Scenario: Isolated Teams Sub-heading Shows Count When Collapsed With Active Worktrees

    Given the CDD dashboard is open
    And two worktrees are active: one with main_diff DIVERGED and one with main_diff AHEAD
    When the User collapses the Isolated Teams sub-heading
    Then the collapsed label reads "2 Isolated Teams"
    And the label color is the normal section heading color (--purlin-muted), not orange or any severity color

#### Scenario: Creation Row Always Visible When Sub-section Is Expanded With No Agents

    Given the CDD dashboard is open
    And the Isolated Teams sub-section is expanded
    And no worktrees are active
    When the User views the Isolated Teams section content
    Then the creation row "Create An Isolated Team [input] [Create]" is visible
    And no Sessions table rows are shown

#### Scenario: Name Input Preserved Across Auto-refresh

    Given the CDD dashboard is open
    And the User has typed "feat3" into the name input
    When the 5-second auto-refresh cycle triggers a DOM update
    Then the name input still contains "feat3"
    And the Create button state is unchanged

#### Scenario: Name Input Focus Restored After Auto-refresh

    Given the CDD dashboard is open
    And the User has clicked into the name input and typed "feat3"
    When the 5-second auto-refresh cycle triggers a DOM update
    Then the name input still contains "feat3"
    And the name input retains keyboard focus without requiring a click to resume typing

---

## 4. Visual Specification

### Screen: CDD Dashboard — Isolated Teams Section

- **Reference:** N/A
- [ ] WORKSPACE section heading is unchanged regardless of Isolated Teams Mode state
- [ ] ISOLATED TEAMS section appears directly below the WORKSPACE section at the same indent level (peer sections, not nested)
- [ ] ISOLATED TEAMS section uses the same collapsible heading style as WORKSPACE
- [ ] Collapsed heading with no active worktrees reads "ISOLATED TEAMS" with no annotation
- [ ] Collapsed heading with N active worktrees reads "N Isolated Teams" (e.g., "2 Isolated Teams") in the normal section heading color (`--purlin-muted`) — NOT colored by worktree severity state
- [ ] When expanded, the creation row "Create An Isolated Team [input] [Create]" is always the first item
- [ ] Sessions table appears below the creation row
- [ ] Sessions table has columns: Name, Branch, Main Diff, Modified (no Role column)
- [ ] Each active worktree appears as a row
- [ ] Each row has a "Kill" button aligned to the right
- [ ] Main Diff cell shows "SAME" in `--purlin-status-good` (green)
- [ ] Main Diff cell shows "AHEAD" in `--purlin-status-todo` (yellow)
- [ ] Main Diff cell shows "BEHIND" in `--purlin-status-todo` (yellow)
- [ ] Main Diff cell shows "DIVERGED" in `--purlin-status-warning` (orange)
- [ ] Modified cell is empty when main_diff is SAME or BEHIND
- [ ] Modified cell shows category counts (e.g., "2 Specs", "1 Tests 4 Code/Other") when AHEAD or DIVERGED
- [ ] When delivery_phase is present, Name cell shows "name (Phase N/M)" with orange badge text

### Screen: CDD Dashboard — Isolation Controls

- **Reference:** N/A
- [ ] The creation row ("Create An Isolated Team [input] [Create]") is always the first item when the ISOLATED TEAMS section is expanded, regardless of whether any worktrees are active
- [ ] The creation row has sufficient top padding that a focused input's focus ring is fully visible and does not clip under any section header or divider element
- [ ] The name input uses the same color scheme as the header filter box: `--purlin-surface` background, `--purlin-border` border, `--purlin-dim` placeholder, `--purlin-primary` text color
- [ ] The name input does not auto-capitalize on first keystroke (no browser autocapitalize behavior)
- [ ] The text input preserves its value across auto-refreshes (typing a name and waiting for the 5-second cycle does not erase the text)
- [ ] The Create button is disabled when the input is empty or contains an invalid name
- [ ] An inline validation message appears for names that are too long or contain invalid characters
- [ ] Clicking Create while valid sends the request and shows a success or error response
- [ ] On success, the name input is cleared
- [ ] Each Sessions row has a "Kill" button; clicking it triggers the dry-run safety check modal
- [ ] Kill dirty-state modal lists dirty files; Confirm button is disabled
- [ ] Kill unsynced-state modal includes "I understand, the branch still exists" checkbox; Confirm disabled until checked
- [ ] Kill clean-state modal shows a simple Confirm/Cancel dialog
- [ ] Agent Config section heading reads "Agent Config (applies across all local isolations)" when isolated teams mode is active
- [ ] Agent Config section heading reads "Agent Config" (no annotation) when isolated teams mode is inactive

---

## 5. Implementation Notes
See [cdd_isolated_teams.impl.md](cdd_isolated_teams.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.

## User Testing Discoveries

### [BUG] pl-local-push/pull not shown in isolation startup table; appear in autocomplete on main (Discovered: 2026-02-23)
- **Scenario:** NONE (no scenario covers agent command vocabulary in isolation vs. main context)
- **Observed Behavior:** (1) When an agent is launched inside an isolated worktree, `pl-local-push` and `pl-local-pull` do not appear in the printed startup command table (Section 3.0 of role instructions), even though Section 8 of QA_BASE lists them as authorized isolation commands. (2) Both skills appear in Claude Code autocomplete regardless of context — they are suggested even when the agent is running on the main branch where they have no applicable purpose.
- **Expected Behavior:** `pl-local-push` and `pl-local-pull` should appear in the startup command table when the agent is running inside an isolated worktree. They should not be surfaced (via autocomplete or command table) to agents running on the main branch.
- **Action Required:** Architect
- **Status:** RESOLVED — Added `pl-local-push` and `pl-local-pull` to the startup command table in ARCHITECT_BASE.md, BUILDER_BASE.md, and QA_BASE.md. Autocomplete visibility on main is a platform limitation outside instruction-file control.

### [INTENT_DRIFT] Name input loses focus on auto-refresh (Discovered: 2026-02-23)
- **Scenario:** Scenario: Name Input Preserved Across Auto-refresh
- **Observed Behavior:** The name input loses keyboard focus when the 5-second auto-refresh cycle fires a DOM update, even though the typed value is correctly preserved. The user must click back into the field to resume typing.
- **Expected Behavior:** The spec says to preserve the input value across refreshes, but the intent is clearly to preserve the full in-progress state — including focus. After a DOM update, focus should be restored to the input if it was focused before the refresh.
- **Action Required:** Builder
- **Status:** RESOLVED — Focus restoration implemented: `refreshStatus()` now saves `document.activeElement === isoInput` before DOM refresh and calls `restoredInput.focus()` after value restore.

### [DISCOVERY] Name input focus highlight clips under header; creation row needs more padding (Discovered: 2026-02-23)
- **Scenario:** NONE
- **Observed Behavior:** When the name input is focused/selected, its focus highlight ring clips beneath the section header dividing line. The creation row has insufficient vertical padding, causing the focused input to visually overlap with the header above it.
- **Expected Behavior:** The creation row should have enough top padding that a focused input's highlight ring is fully visible and does not clip under any header or divider element. No scenario or visual spec checklist item currently covers row padding or focus ring visibility.
- **Action Required:** Builder
- **Status:** RESOLVED — Added `padding-top:4px` to the creation row container div, providing clearance for the input focus ring.

### [SPEC_DISPUTE] 8-character isolation name limit is too restrictive; user wants 12 (Discovered: 2026-02-23)
- **Scenario:** Scenario: New Isolation Input Rejects Invalid Names (SUSPENDED)
- **Observed Behavior:** The name input enforces an 8-character maximum, rejecting names longer than 8 characters (e.g., "toolong12" at 9 chars is rejected).
- **Expected Behavior:** User believes the limit should be 12 characters to allow more meaningful isolation names.
- **Action Required:** Builder
- **Status:** RESOLVED — Updated to 12-char limit in: HTML `maxlength`, JS `validateIsolationName()`, hint text, and `create_isolation.sh` server-side validation.
