# Feature: CDD Collab Mode

> Label: "Tool: CDD Collab Mode"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md

[Complete]

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

**Display labels in the Sessions table:** role values from the API are lowercase (`architect`, `builder`, `qa`, `unknown`). Displayed as: `architect` → "Architect", `builder` → "Builder", `qa` → "QA" (all caps, not "Qa"), `unknown` → "Unknown". This capitalization rule applies everywhere the role label is rendered in the Collaboration section.

### 2.3 Collaboration Section

When Collab Mode is active, the WORKSPACE section becomes "Collaboration". It contains two sub-sections:

**Sessions sub-section:** A table listing all active worktrees:

| Role | Branch | Main Diff | Modified |
|------|--------|-----------|----------|
| Architect | spec/collab | AHEAD | 2 Specs |
| Builder | build/collab | SAME | |
| QA | qa/collab | DIVERGED | 1 Specs |

"Main Diff" shows the sync state between the worktree's branch and main:
- `AHEAD` — only this branch has moved: it has commits not yet in main; main has no commits missing from this branch. Modified reflects files the branch changed since its common ancestor with main.
- `SAME` — branch and main are at identical commit positions. Modified will always be empty.
- `BEHIND` — only main has moved: it has commits not yet in this branch; this branch has no commits ahead of main. Run `/pl-work-pull` before pushing. Modified will always be empty.
- `DIVERGED` — both main and this branch have commits beyond their common ancestor. Run `/pl-work-pull` before pushing. Modified reflects files the branch changed since the common ancestor.

Combined interpretation: AHEAD + Modified = commits ready to merge; Modified lists the files the branch changed since the common ancestor. SAME + empty Modified = no work in progress, aligned with main. BEHIND + empty Modified = main has moved ahead; pull required before this branch can push. DIVERGED + Modified = both sides have moved; pull and resolve before pushing; Modified lists the files the branch changed since the common ancestor.

"Modified" shows files the branch changed since its common ancestor with main — derived from `git diff main...<branch> --name-only` (three-dot), not from uncommitted changes in the worktree. Modified is always empty when `main_diff` is `SAME` or `BEHIND`. Modified may be empty even when `main_diff` is `AHEAD` or `DIVERGED` if the branch's commits contain no file changes (e.g., `--allow-empty` status commits). When non-empty, it shows space-separated category counts in order: Specs (files under `features/`), Tests (files under `tests/`), Code/Other (all other files). Zero-count categories are omitted. Example: `"2 Specs"`, `"1 Tests 4 Code/Other"`, `"3 Specs 1 Tests 6 Code/Other"`. Files under `.purlin/` are excluded from all categories.

**Local (main) sub-section:** Current state of the main checkout (existing WORKSPACE content):

- Branch name, ahead/behind status.
- Clean/dirty state.
- Last commit summary.

When the main checkout has no uncommitted changes, the sub-section heading is exactly "Local (main)" with no additional annotations. Text such as "Ready for specs" or any other status label MUST NOT be appended when the checkout is clean.

Files under `.purlin/` do not constitute "dirty" state for the main checkout display — they are excluded from the clean/dirty determination. It is a process invariant that `.purlin/`-only commits should not appear on `main`; `.purlin/` is environment-specific configuration and must not be committed to the shared main branch.

### 2.4 Worktree State Reading

CDD reads each worktree's state using read-only git commands:

- `git worktree list --porcelain` — all worktree paths and HEAD commits.
- `git -C <path> rev-parse --abbrev-ref HEAD` — branch name per worktree.
- `git diff main...<branch> --name-only` — files the branch changed since its common ancestor with main (three-dot diff), run from the **project root** (same mechanism as `main_diff`). This is always empty for `SAME` and `BEHIND` states; may be empty for `AHEAD` or `DIVERGED` if the branch's commits touch no files. Output is one filename per line, parsed by path prefix to count per-category modified files:
  - Lines starting with `.purlin/` → **excluded entirely** (not counted in any category).
  - Lines starting with `features/` → Specs count.
  - Lines starting with `tests/` → Tests count.
  - All other lines → Code/Other count.
- `git -C <path> log -1 --format='%h %s (%cr)'` — last commit per worktree.
- `git -C <path> rev-list --count main..HEAD` → `commits_ahead` (int).
- Two `git log` range queries to determine `main_diff` — run from the **project root** (not via `git -C <worktree-path>`), using the worktree's branch name. Running from the project root is necessary because the CDD server has the full ref namespace and can evaluate `main` authoritatively; agents running inside a worktree may not reliably resolve `main` in all configurations.

  1. `git log <branch>..main --oneline` — commits on main not in branch (branch is behind).
  2. `git log main..<branch> --oneline` — commits on branch not in main (branch is ahead).

  Evaluation:
  - If query 1 is non-empty AND query 2 is non-empty → `main_diff: "DIVERGED"` (both main and branch have moved beyond their common ancestor; pull and resolve required)
  - If query 1 is non-empty AND query 2 is empty → `main_diff: "BEHIND"` (only main has moved; branch must pull before pushing)
  - If query 1 is empty AND query 2 is non-empty → `main_diff: "AHEAD"` (only branch has moved; ready to merge)
  - If both empty → `main_diff: "SAME"` (branch and main are at identical positions)

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
      "main_diff": "AHEAD",
      "commits_ahead": 3,
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
      "commits_ahead": 0,
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
- `main_diff` — four-state sync indicator. `"SAME"` if branch and main are at identical positions. `"AHEAD"` if only the branch has moved (commits not yet in main; ready to merge). `"BEHIND"` if only main has moved (branch must pull before pushing). `"DIVERGED"` if both main and branch have commits beyond their common ancestor (pull and resolve required). Computed via two `git log` range queries from the project root.
- `commits_ahead` — integer count of commits in this branch not yet in main. Always present (0 when none).
- `last_commit` — formatted string: `"<hash> <subject> (<relative-time>)"`.
- `modified` — object with integer sub-fields `specs`, `tests`, and `other` (all ≥ 0). Counts are derived from `git diff main...<branch> --name-only` (three-dot) output parsed by path prefix (run from project root). Always all-zero when `main_diff` is `"SAME"` or `"BEHIND"`. May be all-zero when `main_diff` is `"AHEAD"` or `"DIVERGED"` if the branch's commits contain no file changes. Files under `.purlin/` are excluded.

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

**Worktree Creation Config Initialization:**
- When `POST /start-collab` creates worktrees via `setup_worktrees.sh`, each new worktree must receive the live project root `.purlin/config.json` — not the git-committed version.
- Immediately after each `git worktree add` call completes, `setup_worktrees.sh` copies the project root `.purlin/config.json` into the new worktree's `.purlin/config.json`, overwriting the git-committed copy.
- This ensures agents launched in a new worktree start with the current dashboard-configured settings, not stale git-committed values.
- If the project root `.purlin/config.json` does not exist at copy time, the worktree's git-committed copy is used as-is (standard `git worktree add` behavior).

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

#### Scenario: Modified Non-Empty When Branch Is AHEAD Of Main

    Given a worktree at .worktrees/build-session is AHEAD of main with commits that modified files
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

#### Scenario: New Worktrees Initialized with Live Project Root Config

    Given the project root .purlin/config.json has startup_sequence true for the qa role
    And the git-committed .purlin/config.json has startup_sequence false for the qa role
    When a POST request is sent to /start-collab with body {}
    Then the qa-session worktree's .purlin/config.json has startup_sequence true for the qa role
    And the value matches the live project root config, not the git-committed version

#### Scenario: Modified Column Categorizes Files Changed Against Main by Type

    Given a worktree at .worktrees/architect-session on a branch AHEAD of main
    And the branch's commits modified two files under features/ and one file outside features/ and tests/ relative to main
    When an agent calls GET /status.json
    Then the worktree entry's modified field has specs=2, tests=0, other=1

#### Scenario: Main Diff BEHIND When Worktree Branch Is Missing Main Commits

    Given a worktree at .worktrees/architect-session on branch spec/collab
    And main has commits that are not in spec/collab
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "BEHIND"

#### Scenario: Main Diff AHEAD When Worktree Branch Has Commits Not In Main

    Given a worktree at .worktrees/architect-session on branch spec/collab
    And spec/collab has commits that are not in main
    And main has no commits that are missing from spec/collab
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "AHEAD"

#### Scenario: Main Diff SAME When Branch And Main Are Identical

    Given a worktree at .worktrees/builder-session on branch build/collab
    And build/collab and main point to the same commit
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "SAME"

#### Scenario: Main Diff DIVERGED When Both Main And Branch Have Commits Beyond Common Ancestor

    Given a worktree at .worktrees/builder-session on branch build/collab
    And build/collab has commits not in main
    And main has commits not in build/collab
    When an agent calls GET /status.json
    Then the worktree entry has main_diff "DIVERGED"

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
- [ ] Role column renders "QA" (all caps) for the qa role; "Architect", "Builder", "Unknown" for other roles
- [ ] Role badges use same styling as status badges (no new colors needed)
- [ ] Main Diff cell shows "SAME" in `--purlin-status-good` (green) when branch and main are at identical positions
- [ ] Main Diff cell shows "AHEAD" in `--purlin-status-todo` (yellow) when the branch has commits not yet in main
- [ ] Main Diff cell shows "BEHIND" in `--purlin-status-todo` (yellow) when only main has moved (branch must pull before pushing)
- [ ] Main Diff cell shows "DIVERGED" in `--purlin-status-warning` (orange) when both main and branch have commits beyond their common ancestor
- [ ] Modified cell is empty when main_diff is SAME or BEHIND
- [ ] Modified cell shows category counts (e.g., "2 Specs", "1 Tests 4 Code/Other") when main_diff is AHEAD or DIVERGED
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

**Main Diff computation:** The `main_diff` field is a four-state indicator (`SAME`, `AHEAD`, `BEHIND`, `DIVERGED`) computed at the project root using two `git log` range queries — not via `git -C <worktree-path>`. Running from the project root ensures `main` resolves correctly regardless of the worktree's internal git context. DIVERGED (both non-empty) takes full precedence; BEHIND and AHEAD are mutually exclusive pure-directional states. Agents running inside a worktree should use `/pl-work-pull` to determine their own sync state; the dashboard is the authoritative display.

**[CLARIFICATION]** The Critic's `parse_visual_spec()` regex (`^##\s+Visual\s+Specification`) does not match numbered section headers like `## 4. Visual Specification`. Acknowledged by Architect — `features/critic_tool.md` Section 2.13 updated to require numbered-prefix detection, and a new Gherkin scenario was added. Builder must update the regex in `parse_visual_spec()` and add a corresponding test case.

- `commits_ahead`: uses `git rev-list --count main..HEAD` in `_worktree_state()`.
- `last_commit`: uses `git log -1 --format='%h %s (%cr)'` in `_worktree_state()`.
- `ROLE_PREFIX_MAP` in `serve.py`: `'build': 'builder'` (already updated from `impl` in a prior session).
- `main_diff`: computed by `_compute_main_diff(branch)` running two `git log` range queries from PROJECT_ROOT (not per-worktree). Query 1: `git log <branch>..main --oneline` (behind check). Query 2: `git log main..<branch> --oneline` (ahead check). Returns "DIVERGED" if both non-empty, "BEHIND" if only query 1 non-empty, "AHEAD" if only query 2 non-empty, "SAME" if both empty.
- `modified`: computed via `git diff main...<branch> --name-only` (three-dot) run from PROJECT_ROOT (not per-worktree, same call site as `main_diff`). Three-dot diffs the branch against the common ancestor — always empty for SAME/BEHIND, reflects only branch-side changes for AHEAD/DIVERGED. Output is one filename per line; categorized by path prefix: `.purlin/` → excluded, `features/` → specs, `tests/` → tests, everything else → other. This replaces the previous `git status --porcelain` approach (which tracked uncommitted changes); the new semantic tracks committed changes vs main. The XY-column parsing concern from the old porcelain approach no longer applies. Note: AHEAD/DIVERGED may still have all-zero modified counts if the branch's commits are `--allow-empty` (spec invariant relaxed).
- Pre-Merge Status sub-section and `_worktree_handoff_status()` / `_read_feature_summary()` removed — spec no longer requires handoff checks on the dashboard.
- Agent config propagation: `_handle_config_agents()` writes updated config to all active worktree `.purlin/config.json` files after the project root write. Failures are collected as `warnings` in the response.

- `setup_worktrees.sh` config initialization: after each `git worktree add`, the script copies `$PROJECT_ROOT/.purlin/config.json` into the new worktree's `.purlin/config.json`, overwriting the git-committed copy. If the live config doesn't exist, the git-committed copy is used as-is.
- traceability_override: "Modified Non-Empty When Branch Is AHEAD Of Main" -> test_categorizes_by_path_prefix
- RESOLVED BUGs (2026-02-22/23): Start Collab and End Collab modal buttons used `btn` class (no CSS), fixed to `btn-critic`. Modified column zeroed on git lock contention — removed `check=True` from subprocess call. Dirty detection included `.purlin/` files — added exclusion filter to teardown script and API. Worktree config init now copies live project root `.purlin/config.json` after each `git worktree add`.

**[CLARIFICATION]** The AGENTS heading annotation ("applies across all local worktrees") is applied server-side in `generate_html()` rather than client-side via JS. Since the dashboard's 5-second refresh fetches fresh server-rendered HTML, this is functionally equivalent to the spec's "applied client-side after each poll" phrasing — the heading updates on every refresh cycle. (Severity: INFO)

- **BUG FIX: Modal button styling:** End Collab modal buttons (Confirm/Cancel) used `class="btn"` which has no CSS definition, causing them to fall back to browser defaults (light background in dark mode). Changed to `class="btn-critic"` to match all other dashboard buttons.
- **BUG FIX: Teardown .purlin/ exclusion:** `teardown_worktrees.sh` did not exclude `.purlin/` files from the dirty detection, counting auto-propagated `config.json` changes as "dirty". Added `grep -v '\.purlin/'` filter to both Phase 1 dirty detection and dry-run JSON output, matching the exclusion already present in `_worktree_state()` and `get_git_status()`.
- **Four-state main_diff + theme colors (2026-02-23):** Added DIVERGED state to `_compute_main_diff()` — both range queries non-empty returns "DIVERGED" instead of "BEHIND". Dashboard badge colors updated: SAME → `st-good` (green), AHEAD → `st-todo` (yellow), BEHIND → `st-todo` (yellow), DIVERGED → `st-disputed` (orange/`--purlin-status-warning`). Modified column now uses `git diff main..<branch> --name-only` from PROJECT_ROOT instead of `git status --porcelain` per-worktree — tracks committed changes vs main, not uncommitted changes. The XY-column parsing and lock contention concerns from the old porcelain approach no longer apply.

## User Testing Discoveries

### [BUG] AHEAD state with empty Modified when only --allow-empty commits exist (Discovered: 2026-02-23)
- **Scenario:** Sessions Table Displays Worktree State
- **Observed Behavior:** QA worktree shows `AHEAD` in Main Diff but the Modified column is empty. The branch has 2 commits ahead of main (both `--allow-empty` QA status commits), so `git diff main..qa/collab --name-only` returns nothing.
- **Expected Behavior:** Per Section 2.3 and 2.6, "Modified will always be non-empty when `main_diff` is `AHEAD` or `DIVERGED`." The spec invariant is violated when the only commits ahead of main are `--allow-empty` commits (QA status commits touch no files).
- **Action Required:** Architect
- **Status:** SPEC_UPDATED — Invariant relaxed: "Modified may be empty even when AHEAD or DIVERGED if the branch's commits contain no file changes." Sections 2.3, 2.4, and 2.6 updated. Builder must switch `git diff main..<branch>` to `git diff main...<branch>` (three-dot) — the two fixes share the same implementation change.

### [BUG] BEHIND state shows non-empty Modified due to wrong git diff semantics (Discovered: 2026-02-23)
- **Scenario:** Sessions Table Displays Worktree State
- **Observed Behavior:** Builder worktree shows `BEHIND` with "1 Specs" in the Modified column. After main was updated (by QA merging a discovery commit to `features/cdd_collab_mode.md`), build/collab moved to BEHIND and the Modified column showed the file that MAIN changed — not anything the builder branch changed.
- **Expected Behavior:** Per Section 2.3, "Modified will always be empty when `main_diff` is `SAME` or `BEHIND`." Root cause: the spec specifies `git diff main..<branch> --name-only` (two-dot), but two-dot git diff is a simple diff between two tips — it shows ALL file differences in both directions. For a BEHIND branch, this shows files that main added, not files the branch changed. The correct command is `git diff main...<branch> --name-only` (three-dot), which shows only what the branch changed from the common ancestor (empty for BEHIND, matching the stated invariant).
- **Action Required:** Architect
- **Status:** SPEC_UPDATED — All references to `git diff main..<branch>` updated to `git diff main...<branch>` (three-dot) in Sections 2.3, 2.4, and 2.6. Builder must update the implementation accordingly.

### [SPEC_DISPUTE] "Modified" column name is misleading — suggest renaming to "Differences" (Discovered: 2026-02-23)
- **Scenario:** Sessions Table Displays Worktree State
- **Observed Behavior:** The "Modified" column heading implies files the branch modified, but in practice (due to the git diff semantics bug above) it shows files that differ between the branch and main in either direction. A BEHIND branch showing files that main changed looks wrong under the "Modified" label.
- **Expected Behavior:** User proposes renaming the column to "Differences" to better communicate that it shows files that differ between this branch and main — not exclusively files the branch itself changed.
- **Action Required:** Architect
- **Status:** RESOLVED — Reaffirmed. The "Modified" label is accurate once the three-dot fix (BUG above) is applied: the column exclusively shows files the branch changed since its common ancestor with main — never files that main changed. "Differences" implies bidirectionality, which the column does not have. "Modified" remains the correct label.
