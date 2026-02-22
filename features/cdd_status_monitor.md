# Feature: CDD Status Monitor

> Label: "Tool: CDD Monitor"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/design_visual_standards.md


## 1. Overview
The CDD Dashboard is the web interface for human review of the Continuous Design-Driven project state. It displays feature lifecycle and role status tables, served from a single port with a shared header, theme system, and search/filter. The dashboard also provides a canonical JSON API and CLI tool for agent consumption.

## 2. Requirements

### 2.1 Feature Scanning
*   **Path Awareness:** The monitor must scan the project's `features/` directory for all feature files.
*   **Status Detection:** Status is derived from a combination of file modification timestamps (for [TODO] detection) and source control history/tags.
*   **Discovery-Aware Lifecycle Preservation:** When a feature file is modified after a status commit, the monitor MUST check whether the modification is limited to the `## User Testing Discoveries` section. If the spec content above that section is identical to the content at the status commit, the lifecycle state is preserved (COMPLETE or TESTING). This prevents QA housekeeping (pruning resolved discoveries) from triggering a false lifecycle reset to TODO.

### 2.2 UI & Layout

#### 2.2.1 Dashboard Shell

*   **Header:** A two-row header bar (per Section 2.9) is always visible. Row 1 contains the logo, title, timestamp, and theme toggle. Row 2 contains the view mode toggle buttons, Run Critic button, and the search box. A subtle border separates the two rows.
*   **Content Area:** Below the header, the content area renders either the Status view or the SW Map view.
*   **URL Hash Routing:** The URL hash MUST reflect the active view at all times. Switching to the Status view sets the hash to `#status`. Switching to the SW Map view sets the hash to `#map`. On page load, the dashboard MUST read the current URL hash and activate the corresponding view (`#map` activates SW Map; any other value or no hash defaults to Status). Browser back/forward navigation MUST switch views via the `hashchange` event.

#### 2.2.2 Status View
The Status view is the default view (`/#status`).

*   **Role-Based Columns:** The dashboard MUST render features in a table with the following columns:
    *   **Feature** -- The feature filename.
    *   **Architect** -- The Architect role status badge.
    *   **Builder** -- The Builder role status badge.
    *   **QA** -- The QA role status badge.
*   **Column Alignment:** Status column headers (Architect, Builder, QA) MUST be centered. The Feature column header MUST be left-justified.
*   **Three Collapsible Sections:** Features are displayed in three collapsible sections:
    *   **Active** -- Any feature where at least one role is not fully satisfied (i.e., not all of: Architect=DONE, Builder=DONE, QA=CLEAN or N/A).
    *   **Complete** -- All roles fully satisfied. Capped at 10 most recent entries.
    *   **Workspace** -- Git status and last commit information.
*   **Section Collapse/Expand Behavior:**
    *   Each section heading has a chevron indicator: right-pointing when collapsed, down-pointing when expanded.
    *   Clicking the section heading toggles between collapsed and expanded.
    *   **Collapsed Summary (Active/Complete):** When collapsed, the section heading displays a summary badge:
        - `DONE` (green) if all features in the section have all roles satisfied.
        - `??` (dim) if the section is empty.
        - `TODO` (yellow) if any feature has a TODO state without any FAIL/WARN states.
        - Most severe status badge otherwise (FAIL > INFEASIBLE > DISPUTED > TODO).
    *   **Collapsed Summary (Workspace):** When collapsed, displays "Clean State" or a brief status indicator.
    *   **Default State:** Active section is expanded by default. Workspace and Complete sections are collapsed by default, displaying their summary badge/status indicator.
    *   **State Persistence:** Section expanded/collapsed states MUST be persisted to `localStorage` (key: `purlin-section-states`). On page load, saved states are restored, overriding the defaults above. This ensures the user's preferred section layout survives page reloads and browser restarts. Each toggle updates the stored state immediately.
*   **Matched Column Widths:** The Active and Complete tables MUST have matching column widths, computed as if they were a single table. This ensures the columns align visually when both sections are expanded.
*   **Active Section Sorting:** Features sorted by urgency: any red state (FAIL, INFEASIBLE) first, then any yellow/orange state (TODO, DISPUTED), then alphabetical.
*   **Feature Click:** Clicking a feature name in the status table opens the shared feature detail modal (Section 2.2.4).
*   **Compact Design:** Minimal padding and margins to ensure the dashboard fits in a small window.
*   **Badge Color Mapping:**

| Badge | Color | Roles |
|-------|-------|-------|
| DONE | Green | Architect, Builder |
| CLEAN | Green | QA |
| TODO | Yellow | Architect, Builder, QA |
| FAIL | Red | Builder, QA |
| INFEASIBLE | Red | Builder |
| BLOCKED | Gray | Builder |
| DISPUTED | Orange | QA |
| N/A | Blank/dim | QA |
| ?? | Dim (`--purlin-dim`) | Any (no critic.json -- not yet generated) |

*   **Scope:** The web dashboard is for human consumption only. Agents must use the `/status.json` API endpoint or the CLI tool.

#### 2.2.3 Search/Filter
*   **Position:** A search text input appears on the right side of the header's second row (Row 2), right-justified.
*   **Behavior:** Filters Active and Complete table rows by feature name (case-insensitive substring match). Sections with no matching rows are hidden.
*   **Placeholder:** Uses `var(--purlin-dim)` color token for readable contrast in both themes.

#### 2.2.4 Feature Detail Modal
*   **Trigger:** Clicking a feature name in the status table opens the modal.
*   **Content:** Renders the feature file's markdown content in a scrollable container.
*   **Tabbed View:** When a companion `.impl.md` file exists for the feature, the modal shows two tabs: "Specification" and "Implementation Notes". Tab content is lazy-loaded and cached for instant switching.
*   **Single Tab:** When no companion file exists, the modal shows content without tabs (same as current behavior).
*   **Close Methods:** The modal MUST close via: (1) X button in the top-right corner, (2) clicking outside the modal, (3) pressing Escape.
*   **API Endpoints:** Feature content is served via `/feature?file=<path>` and companion content via `/impl-notes?file=<path>` (Section 2.4).

### 2.3 Verification Signals
*   **Role Status Source:** The CDD monitor reads role status from pre-computed `tests/<name>/critic.json` files produced by the Critic tool. CDD does NOT compute role status itself.
*   **Test Status (Internal):** The monitor still resolves `tests/<name>/tests.json` for internal lifecycle logic, but test status is no longer displayed as a separate column on the dashboard or exposed as a standalone field in the API. Test pass/fail state is reflected through the Builder role status (DONE vs FAIL).
*   **Section Heading Visual Separation:** The dashboard MUST render section headings ("ACTIVE", "COMPLETE", "WORKSPACE") with an underline separator (e.g., a bottom border or `<hr>`) to clearly distinguish them from the content beneath.

### 2.4 Machine-Readable Output (Agent Interface)
*   **API Endpoint (`/status.json`):** The server MUST expose a `/status.json` route that returns the feature status JSON directly with `Content-Type: application/json`. This is the **primary** agent interface.
*   **API Schema (`/status.json`):**
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
      "delivery_phase": {
        "current": 2,
        "total": 3
      },
      "features": [
        {
          "file": "features/<name>.md",
          "label": "<label>",
          "architect": "DONE | TODO",
          "builder": "DONE | TODO | FAIL | INFEASIBLE | BLOCKED",
          "qa": "CLEAN | TODO | FAIL | DISPUTED | N/A",
          "change_scope": "full | targeted:... | cosmetic | dependency-only"
        }
      ]
    }
    ```
    *   Flat `features` array (no `todo`/`testing`/`complete` sub-arrays).
    *   No top-level `test_status` field.
    *   No per-feature `test_status` or `qa_status` fields (replaced by role columns).
    *   Role fields (`architect`, `builder`, `qa`) are omitted when no `critic.json` exists for that feature (dashboard shows `??`).
    *   `change_scope` is extracted from the most recent status commit message's `[Scope: ...]` trailer. Omitted when no scope is declared (consumers should treat absent as `full`).
    *   `delivery_phase` is present ONLY when `.agentic_devops/cache/delivery_plan.md` exists and has at least one non-COMPLETE phase. `current` = the phase number of the first PENDING or IN_PROGRESS phase. `total` = total number of phases in the plan. When all phases are COMPLETE or no delivery plan exists, the `delivery_phase` field is omitted entirely.
    *   Array sorted by file path (deterministic).
*   **API Endpoint (`/dependency_graph.json`):** Serves the contents of `.agentic_devops/cache/dependency_graph.json` with `Content-Type: application/json`. Returns 404 if the file does not exist.
*   **API Endpoint (`/feature?file=<path>`):** Serves the raw content of the specified feature file. The `file` query parameter is the relative path (e.g., `features/cdd_status_monitor.md`). Returns 200 with `Content-Type: text/plain` on success, 404 if the file does not exist. Path traversal outside the project root MUST be rejected.
*   **API Endpoint (`/impl-notes?file=<path>`):** Resolves the companion file for the specified feature file. If `features/<name>.md` is requested, serves `features/<name>.impl.md`. Returns 200 with `Content-Type: text/plain` on success, 404 if no companion file exists.
*   **Internal Artifact (`feature_status.json`):** The monitor MUST also produce a `feature_status.json` file at `.agentic_devops/cache/feature_status.json`, regenerated on every request (web) or CLI invocation. This file retains the **old** lifecycle-based format with `todo`/`testing`/`complete` arrays and `test_status` fields, plus a `change_scope` field per feature (extracted from the most recent status commit's `[Scope: ...]` trailer, omitted when absent). This is an internal implementation detail consumed by the Critic for lifecycle-state-dependent computations (e.g., QA TODO detection, regression scope). It is NOT part of the public API contract.
*   **Regeneration:** Both outputs MUST be freshly computed on every `/status.json` request. The disk file is also regenerated on dashboard requests.
*   **Deterministic Output:** Arrays MUST be sorted by file path. Keys MUST be sorted.
*   **Agent Contract:** Agents MUST query status via `tools/cdd/status.sh`, which outputs the same JSON schema to stdout without requiring the web server. Agents MUST NOT scrape the web dashboard, use HTTP endpoints, or guess ports.

### 2.5 Role Status Integration
*   **Critic JSON Discovery:** For each feature `features/<name>.md`, the monitor checks for `tests/<name>/critic.json` on disk.
*   **Per-Feature Role Status:** If `critic.json` exists, the monitor reads the `role_status` object and exposes its `architect`, `builder`, and `qa` fields on the per-feature API entry. If no `critic.json` exists, all role fields are omitted (dashboard shows `??` in each column).
*   **No Direct Computation:** CDD does NOT compute role status itself. It reads pre-computed values from the Critic's `role_status` output.
*   **Dashboard Columns:** Each feature entry on the web dashboard displays Architect, Builder, and QA columns with the badge/color mapping defined in Section 2.2.2. Blank cells when no `critic.json` exists.
*   **No Blocking:** The `critic_gate_blocking` config key is deprecated (no-op). CDD does not gate status transitions based on critic or role status results.

### 2.6 CLI Status Tool (Agent Interface)
*   **Script Location:** `tools/cdd/status.sh` (executable, `chmod +x`). Wrapper calls a Python module for status computation.
*   **Purpose:** Provides agents with feature status without requiring the web server to be running. This is the primary agent interface for CDD status queries.
*   **Output:** Writes the same JSON schema as the `/status.json` API endpoint to stdout. The output MUST be valid JSON parseable by `python3 json.load()`.
*   **`--graph` Flag:** When invoked with `--graph`, the tool outputs the `dependency_graph.json` content to stdout instead of the status JSON. If the cached file is stale or missing, it regenerates the dependency graph first.
*   **Side Effect:** Regenerates `.agentic_devops/cache/feature_status.json` (the internal lifecycle-based artifact consumed by the Critic).
*   **Project Root Detection:** Uses `AGENTIC_PROJECT_ROOT` if set, then climbing fallback (per submodule_bootstrap Section 2.11).
*   **No Server Dependency:** The tool MUST NOT depend on the web server being running. It computes status directly from disk (feature files, git history, critic.json files).
*   **Shared Logic:** The status computation logic MUST be consistent with the web server's `/status.json` endpoint. Implementation MAY share code with `serve.py` or extract a common module.
*   **Auto-Critic Integration:** When invoked without `--graph`, `status.sh` MUST run `tools/critic/run.sh` as a prerequisite step before computing status output. This ensures all `critic.json` files and `CRITIC_REPORT.md` are current, so agents always receive fresh role status data from a single invocation. **Recursion guard:** If the `CRITIC_RUNNING` environment variable is already set, the Critic step MUST be skipped. The Critic's `run.sh` wrapper still invokes `tools/cdd/status.sh` internally to refresh `feature_status.json` before analysis; the guard ensures that inner call does not trigger a second Critic run.

### 2.7 Manual Critic Trigger (Dashboard)
*   **Button Location:** Per Section 2.9 Header Layout -- the "Run Critic" button is on the right side of the header's second row (Row 2), immediately to the left of the search input.
*   **Visual Design:** The button should be compact, styled consistently with the dashboard theme (dark/high-contrast). It should not dominate the layout.
*   **Behavior on Click:**
    1.  The button becomes disabled and shows a loading/spinner state to indicate the Critic is running.
    2.  The server executes `tools/critic/run.sh` (or equivalent logic) server-side.
    3.  On completion, the dashboard refreshes to reflect updated role status columns.
    4.  The button returns to its enabled state.
*   **Error Handling:** If the Critic run fails, the button returns to its enabled state and a brief error indicator is shown near the button (e.g., red text "Critic run failed"). The dashboard retains its previous data.
*   **No Agent Use:** This button is for human use only. Agents MUST continue to use `tools/critic/run.sh` via CLI.

### 2.8 Lifecycle Integration Test
An automated end-to-end test MUST verify that `tools/cdd/status.sh` and `tools/critic/run.sh` correctly report feature lifecycle state and role status columns through the complete feature lifecycle (TODO -> TESTING -> COMPLETE -> spec edit -> TODO reset). This test eliminates the need for manual QA verification of lifecycle and role status logic.

*   **Test Script:** `tools/cdd/test_lifecycle.sh` (Bash). Executable (`chmod +x`).
*   **Dependency:** Requires `tools/cdd/status.sh` (Section 2.6) to be implemented first. The test invokes `status.sh` at each lifecycle stage.
*   **Temporary Feature:** The test creates a well-formed temporary feature file (e.g., `features/_test_lifecycle_temp.md`) containing all required sections (Overview, Requirements, Scenarios), both Automated and Manual scenario subsections, a `> Prerequisite:` link to an existing feature, and properly structured Gherkin. The feature MUST pass the Critic Spec Gate (architect=DONE).
*   **Temporary Tests:** The test creates a minimal passing test result at `tests/_test_lifecycle_temp/tests.json` with `{"status": "PASS"}`.
*   **Git Commits:** The test creates real git commits (feature creation, implementation, status tag commits, spec edits) to exercise the lifecycle state machine. Each commit SHA is recorded for rollback.
*   **Verification Method:** At each lifecycle stage, the test runs `tools/cdd/status.sh` and parses the JSON output to assert expected role status values for the temporary feature. (The Critic runs automatically as part of `status.sh`, regenerating `critic.json` files before the status JSON is produced.) Assertions use `python3 -c` or `jq` to extract and compare JSON fields.
*   **Cleanup Guarantee:** The test MUST use `trap` to ensure cleanup runs on exit (success, failure, or signal). Cleanup sequence: (1) `git reset --hard <pre-test-sha>` to revert all temporary commits, (2) remove any untracked temporary files (`features/_test_lifecycle_temp.md`, `tests/_test_lifecycle_temp/`), (3) run `tools/cdd/status.sh` to restore clean critic.json state. After cleanup, `git log` and `git status` MUST show no trace of the test.
*   **Test Results:** On success, output `[Scenario] <title>` lines for each passing stage (Bash test file convention) and write `tests/cdd_status_monitor/tests.json` with `{"status": "PASS"}`. On any assertion failure, report the failing stage and expected vs actual values, then proceed to cleanup.

### 2.9 Branding & Theme

#### Header Layout
The page header is a two-row bar:

**Row 1** (primary header):

*   **Left side** (left-justified, in this order left-to-right):
    1.  Purlin logo mark (`assets/purlin-logo.svg`, inline SVG, ~24px height, CSS classes for theme-responsive fills)
    2.  Title and project name block (stacked vertically):
        *   **Line 1:** Title text: "Purlin CDD Dashboard"
        *   **Line 2:** Active project name (per `design_visual_standards.md` Section 2.6). Resolved from `project_name` in config, falling back to the project root directory name. The project name's left edge MUST align with the left edge of the "P" in the title above. Font: `var(--font-body)` Inter Medium 500, 14px, color `var(--purlin-primary)`.
*   **Right side** (right-justified, in this order from the right edge inward):
    1.  Theme toggle (sun/moon icon) -- rightmost element
    2.  Last-refreshed timestamp (monospace font to prevent layout shift as digits change)

Row 1 uses CSS flexbox (`justify-content: space-between`) to position its left and right sides.

**Row Separator:** A subtle 1px border (`var(--purlin-border)`) separates Row 1 from Row 2, providing visual distinction between the branding/utility row and the navigation/tools row. Implemented as a top border on Row 2 with small top padding.

**Row 2** (sub-header, directly below Row 1):

*   **Left side** (left-justified):
    1.  View mode toggle buttons ("Status" / "SW Map"). These buttons MUST be left-aligned below the logo/title block.
*   **Right side** (right-justified, in this order from the right edge inward):
    1.  Search/filter text input -- rightmost element
    2.  "Run Critic" button (and its error indicator) -- immediately left of the search input

Row 2 uses CSS flexbox (`justify-content: space-between`) to position its left and right sides. The right side uses a flex container with gap for consistent spacing between the Critic button and search input.

#### Title
*   The dashboard title MUST read "Purlin CDD Dashboard".

#### Theme
*   **CSS Tokens:** All colors in the dashboard MUST use `var(--purlin-*)` custom properties defined in `features/design_visual_standards.md`. No hardcoded hex colors.
*   **Default Theme:** Dark (Blueprint).
*   **Persistence:** Theme choice stored in `localStorage` key `purlin-theme`, value `light` or `dark`.
*   **FOUC Prevention:** A synchronous `<script>` in `<head>` reads `localStorage` and sets the `data-theme` attribute on `<html>` before first paint. This prevents theme flash on the 5-second auto-refresh cycle.
*   **Theme Toggle:** Clicking the sun/moon icon switches between Blueprint (dark, default) and Architect (light) themes.

#### Typography
Per `design_visual_standards.md` Section 2.3. Tool title uses `var(--font-display)` (Montserrat ExtraLight 200, wide tracking `0.12em`, `uppercase`). Section headers use `var(--font-body)` (Inter Bold 700, `uppercase`, wide tracking `0.1em`). Body/UI text uses `var(--font-body)` (Inter 400-500). Data/code retains monospace. The last-refreshed timestamp MUST use the monospace font stack (`'Menlo', 'Monaco', 'Consolas', monospace`) so that digit changes do not cause width fluctuation. CDN loads: Montserrat weights 200,800,900; Inter weights 400,500,700.

### 2.10 Visual Stability on Refresh
The dashboard refreshes data every 5 seconds. This refresh MUST NOT cause visible flicker, layout shift, or font re-rendering on any static element. The page loads once; all subsequent updates are incremental DOM mutations via JavaScript.

*   **Refresh Mechanism:** The dashboard MUST use JavaScript `fetch()` to retrieve updated data and apply incremental DOM mutations. It MUST NOT use `<meta http-equiv="refresh">` or `window.location.reload()`.
*   **Dynamic Elements (updated every refresh cycle):**
    *   Feature table rows (Active and Complete sections).
    *   Last-refreshed timestamp (text content only).
    *   Workspace section (git status and last commit).
*   **Static Elements (rendered once on initial page load, never re-created or replaced):**
    *   Page header structure (logo, title, project name).
    *   Theme toggle, search input, and Run Critic button.
    *   Section headings ("ACTIVE", "COMPLETE", "WORKSPACE") and table column headers.
    *   Google Fonts CDN `<link>` tags.
*   **Font Stability:** Because the page never fully reloads, fonts remain cached in the browser and do not trigger re-layout or FOUT (Flash of Unstyled Text) on refresh cycles.
*   **No Scroll Reset:** If the user has scrolled down, a data refresh MUST NOT reset the scroll position.
*   **Minimal Re-Rendering:** Rows that did not change SHOULD NOT be re-rendered.

### 2.11 Delivery Phase Indicator

*   **ACTIVE Header Annotation:** When a delivery plan exists at `.agentic_devops/cache/delivery_plan.md`, the ACTIVE section heading displays the current phase progress: `ACTIVE (<feature_count>) [PHASE (<current>/<total>)]`. Example: `ACTIVE (5) [PHASE (2/3)]`.
*   **Parsing:** The CDD tool reads the delivery plan file, counts phases by `### Phase N:` headings, and determines the current phase (first phase with Status `PENDING`, or the phase with Status `IN_PROGRESS`). If all phases are `COMPLETE` or no delivery plan exists, the phase annotation is omitted.
*   **Styling:** The `[PHASE (X/Y)]` text is styled with the same color as a `TODO` badge (yellow: `--purlin-warn`). It appears inline after the feature count, separated by a space.
*   **Collapsed State:** The phase annotation MUST also appear when the ACTIVE section is collapsed. It renders alongside the collapsed summary badge. Example collapsed state: `> ACTIVE (5) [PHASE (2/3)] TODO`.
*   **Disappears When Complete:** When the delivery plan is deleted (all phases complete) or does not exist, the phase annotation is not rendered. Only the standard `ACTIVE (<count>)` heading appears.
*   **No Per-Feature Changes:** Individual feature status badges (DONE, TODO, FAIL, etc.) are unchanged. The phase indicator is purely a section-level annotation.

## 3. Scenarios

### Automated Scenarios
These scenarios are validated by the Builder's automated test suite.

#### Scenario: Agent Reads Feature Status via API
    Given the CDD server is running
    When an agent needs to check feature queue status
    Then the agent reads cdd_port from .agentic_devops/config.json
    And the agent calls GET /status.json on that port
    And the agent receives a valid JSON response
    And the agent does NOT scrape the web dashboard or guess ports

#### Scenario: Zero-Queue Verification
    Given a release is being prepared
    When the Architect checks the Zero-Queue Mandate
    Then the Architect calls GET /status.json on the configured CDD port
    And verifies that all features have architect DONE, builder DONE, and qa either CLEAN or N/A

#### Scenario: Role Status in API Response
    Given the CDD server is running
    And tests/<feature_name>/critic.json exists with role_status architect DONE, builder DONE, qa CLEAN
    When an agent calls GET /status.json
    Then the feature entry includes architect, builder, and qa fields with the correct values
    And no test_status or qa_status fields are present

#### Scenario: Role Status Omitted When No Critic File
    Given the CDD server is running
    And no critic.json exists for a feature
    When an agent calls GET /status.json
    Then the feature entry does not include architect, builder, or qa fields

#### Scenario: Flat Features Array in API Response
    Given the CDD server is running with features in various lifecycle states
    When an agent calls GET /status.json
    Then the response contains a flat features array sorted by file path
    And no todo, testing, or complete sub-arrays exist
    And no top-level test_status field exists

#### Scenario: Lifecycle Preserved When Only Discoveries Section Changes
    Given a feature is in COMPLETE lifecycle state with a status commit
    And the feature file is modified after the status commit
    And the modification is limited to the User Testing Discoveries section
    When the monitor computes feature status
    Then the feature remains in COMPLETE lifecycle state
    And the feature is NOT reset to TODO

#### Scenario: Lifecycle Reset When Spec Content Changes
    Given a feature is in COMPLETE lifecycle state with a status commit
    And the feature file is modified after the status commit
    And the modification includes changes above the User Testing Discoveries section
    When the monitor computes feature status
    Then the feature is reset to TODO lifecycle state

#### Scenario: Internal Feature Status File Preserved
    Given the CDD server is running
    When any request is made to the server
    Then .agentic_devops/cache/feature_status.json is regenerated with the old lifecycle-based format
    And it contains todo, testing, and complete arrays with test_status fields

#### Scenario: CLI Status Tool Output
    Given feature files exist in features/ with various lifecycle states
    And critic.json files exist for some features
    When an agent runs tools/cdd/status.sh
    Then valid JSON is written to stdout matching the /status.json schema
    And .agentic_devops/cache/feature_status.json is regenerated
    And the tool does not require the CDD web server to be running

#### Scenario: CLI Graph Output
    Given feature files exist in features/ with prerequisite links
    When an agent runs tools/cdd/status.sh --graph
    Then valid JSON is written to stdout matching the dependency_graph.json schema
    And the output includes features, cycles, and orphans arrays

#### Scenario: Run Critic Endpoint
    Given the CDD server is running
    When a POST request is sent to /run-critic
    Then the server executes tools/critic/run.sh (or equivalent logic) server-side
    And returns a JSON response with a success or error status
    And the response includes a Content-Type of application/json

#### Scenario: Change Scope in API Response
    Given a feature has a status commit with [Scope: targeted:Web Dashboard Auto-Refresh]
    When an agent calls GET /status.json
    Then the feature entry includes change_scope with value "targeted:Web Dashboard Auto-Refresh"

#### Scenario: Change Scope Omitted When No Scope Declared
    Given a feature has a status commit with no [Scope: ...] trailer
    When an agent calls GET /status.json
    Then the feature entry does not include a change_scope field

#### Scenario: CLI Status Tool Project Root Detection
    Given AGENTIC_PROJECT_ROOT is set to a valid project root
    When an agent runs tools/cdd/status.sh
    Then the tool uses AGENTIC_PROJECT_ROOT for all path resolution
    And it scans features/ relative to that root

#### Scenario: Lifecycle Integration -- TODO with No Tests
    Given a temporary feature file is created and committed
    And the feature has both Automated and Manual scenario subsections
    And no tests or status commits exist for the feature
    When tools/cdd/status.sh is run
    Then the feature lifecycle is TODO
    And role_status.builder is TODO
    And role_status.qa is N/A

#### Scenario: Lifecycle Integration -- TODO with Passing Tests
    Given the temporary feature exists
    And tests are created and pass (tests.json with status PASS)
    And an implementation commit is made (no status tag)
    When tools/cdd/status.sh is run
    Then the feature lifecycle is TODO
    And role_status.builder is TODO
    And role_status.qa is CLEAN

#### Scenario: Lifecycle Integration -- TESTING
    Given the temporary feature has passing tests
    And a status commit "[Ready for Verification features/<temp>.md]" is made
    When tools/cdd/status.sh is run
    Then the feature lifecycle is TESTING
    And role_status.builder is DONE
    And role_status.qa is TODO

#### Scenario: Lifecycle Integration -- COMPLETE
    Given the temporary feature has passing tests
    And a status commit "[Complete features/<temp>.md]" is made
    When tools/cdd/status.sh is run
    Then the feature lifecycle is COMPLETE
    And role_status.builder is DONE
    And role_status.qa is CLEAN

#### Scenario: Lifecycle Integration -- Spec Edit Resets to TODO
    Given the temporary feature is in COMPLETE lifecycle state
    When the feature file spec content is modified (above User Testing Discoveries)
    And tools/cdd/status.sh is run
    Then the feature lifecycle is reset to TODO
    And role_status.builder is TODO

#### Scenario: Lifecycle Integration -- Cleanup
    Given the lifecycle integration test has run (pass or fail)
    When cleanup executes
    Then no temporary feature files remain in features/
    And no temporary test artifacts remain in tests/
    And all temporary git commits are reverted
    And git log shows no trace of the temporary feature

#### Scenario: Theme Toggle LocalStorage Behavior
    Given the CDD server is running
    When the theme toggle is activated via the /status.json endpoint or client-side
    Then the purlin-theme key in localStorage switches between "light" and "dark"
    And the data-theme attribute on the html element reflects the current theme
    And the theme persists across page refreshes including auto-refresh cycles

#### Scenario: Dependency Graph Endpoint
    Given the CDD server is running
    And .agentic_devops/cache/dependency_graph.json exists
    When a GET request is sent to /dependency_graph.json
    Then the server returns the dependency graph JSON with Content-Type application/json

#### Scenario: Feature Content Endpoint
    Given the CDD server is running
    And features/cdd_status_monitor.md exists
    When a GET request is sent to /feature?file=features/cdd_status_monitor.md
    Then the server returns the feature file content with status 200

#### Scenario: Impl Notes Endpoint
    Given the CDD server is running
    And features/cdd_status_monitor.impl.md exists
    When a GET request is sent to /impl-notes?file=features/cdd_status_monitor.md
    Then the server returns the companion file content with status 200

#### Scenario: Impl Notes Endpoint Returns 404 When No Companion
    Given the CDD server is running
    And features/policy_critic.md has no companion file
    When a GET request is sent to /impl-notes?file=features/policy_critic.md
    Then a 404 status is returned

#### Scenario: Delivery Phase in API Response
    Given a delivery plan exists at .agentic_devops/cache/delivery_plan.md
    And the plan has 3 phases with Phase 1 COMPLETE, Phase 2 IN_PROGRESS, Phase 3 PENDING
    When an agent calls GET /status.json
    Then the response includes delivery_phase with current 2 and total 3

#### Scenario: Delivery Phase Omitted When No Plan
    Given no delivery plan exists at .agentic_devops/cache/delivery_plan.md
    When an agent calls GET /status.json
    Then the response does not include a delivery_phase field

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder must start the server and instruct the User to verify the web dashboard visually.

#### Scenario: Search Filters Status View
    Given the User is viewing the Status view
    And multiple features are displayed in the Active and Complete sections
    When the User types a partial feature name in the search box
    Then only matching features are displayed in both Active and Complete sections
    And sections with no matching features are hidden

#### Scenario: Feature Click Opens Modal
    Given the User is viewing the Status view
    When the User clicks a feature name in the Active or Complete table
    Then the feature detail modal opens showing the rendered markdown content
    And the modal has an X button in the top-right corner
    When the User clicks the X button or clicks outside the modal or presses Escape
    Then the modal closes

#### Scenario: Section Collapse and Expand
    Given the User is viewing the Status view
    When the User clicks the "ACTIVE" section heading
    Then the Active section collapses showing only the heading with a summary badge
    And the chevron changes from down to right
    When the User clicks the "ACTIVE" section heading again
    Then the Active section expands showing all feature rows
    And the chevron changes from right to down

#### Scenario: Section State Persists Across Reloads
    Given the User is viewing the Status view
    And the Active section is expanded and the Complete section is collapsed (defaults)
    When the User collapses the Active section and expands the Complete section
    And the User reloads the page
    Then the Active section is still collapsed
    And the Complete section is still expanded
    And the saved states override the default expand/collapse behavior

#### Scenario: Web Dashboard Auto-Refresh
    Given the User is viewing the web dashboard
    When a feature status changes (e.g., a status commit is made)
    Then the dashboard reflects the updated status within 5 seconds
    And the refresh is incremental (no full page reload)

#### Scenario: Server Start/Stop Lifecycle
    Given the CDD server is not running
    When the User runs tools/cdd/start.sh
    Then the server starts on the configured port on the first invocation
    And a PID file is written to .agentic_devops/runtime/cdd.pid
    When the User runs tools/cdd/stop.sh
    Then the server process is terminated
    And the PID file is removed
    When the User runs tools/cdd/start.sh again
    Then the server starts successfully on the first invocation without requiring a second run

#### Scenario: Run Critic Button
    Given the CDD server is running
    And the User opens the web dashboard
    When the User locates the header's second row (Row 2)
    Then a "Run Critic" button is visible to the left of the search input
    When the User clicks the "Run Critic" button
    Then the button enters a disabled/loading state
    And after the Critic finishes, the dashboard refreshes with updated role status columns
    And the button returns to its enabled state

## 4. Implementation Notes
See [cdd_status_monitor.impl.md](cdd_status_monitor.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.

## Visual Specification

### Screen: CDD Dashboard -- Status View
- **Reference:** N/A
- [ ] Dashboard title reads "PURLIN CDD DASHBOARD" in the header left group
- [ ] Active project name displayed on a second line below the title, left-aligned with the "P" in PURLIN
- [ ] Project name uses Inter Medium 500, body text size (14px), color matches the logo triangle (`--purlin-primary`)
- [ ] Project name color switches correctly between dark and light themes
- [ ] Project name shows config value when `project_name` is set; falls back to project directory name otherwise
- [ ] Header Row 1 left side: Logo + Title + project name; right side: timestamp, theme toggle
- [ ] Header Row 2 left side: "Status" / "SW Map" toggle buttons below the logo; right side: Run Critic button, search input
- [ ] A subtle 1px border separates Row 1 from Row 2
- [ ] View mode toggle buttons are left-justified below the logo/title block (Row 2)
- [ ] Active view button is visually distinguished from inactive
- [ ] Search/filter text input is right-justified in Row 2
- [ ] Search input placeholder text uses `--purlin-dim` color token for readable contrast in both themes
- [ ] Last-refreshed timestamp uses monospace font (no width shift when digits change)
- [ ] Clicking toggle switches between Blueprint (dark) and Architect (light) themes
- [ ] Theme persists across page refreshes (auto-refresh every 5s does not reset theme)
- [ ] All UI colors use the Purlin design tokens (no hardcoded hex)
- [ ] On 5-second auto-refresh, the page header remains completely static with no flicker
- [ ] Fonts do not visibly re-load or cause layout shift on auto-refresh
- [ ] Scroll position is preserved across auto-refresh cycles
- [ ] Only feature status data updates; table headers and section headings remain stable
- [ ] Section headings ("ACTIVE", "COMPLETE", "WORKSPACE") have a visible underline separator
- [ ] Section headings are clearly distinguished from the content beneath them
- [ ] Section headings have chevron indicators (right=collapsed, down=expanded)
- [ ] Collapsed sections show a summary badge (DONE/??/TODO/most-severe)
- [ ] Active section expanded by default; Workspace and Complete sections collapsed by default
- [ ] Section collapse/expand states persist across page reloads via localStorage
- [ ] Workspace section shows "Clean State" or status summary in its collapsed form
- [ ] URL hash reads `#status` when Status view is active and `#map` when SW Map view is active
- [ ] Switching views updates the URL hash immediately
- [ ] Loading the page with `#map` in the URL activates the SW Map view
- [ ] Active and Complete tables have matching column widths
- [ ] Status column headers (Architect, Builder, QA) are centered
- [ ] Feature column header is left-justified
- [ ] Workspace section visible between Active and Complete sections (or at its collapsible position)
- [ ] Workspace shows "Clean State" or "Work in Progress" with file list
- [ ] Workspace shows last commit summary (hash, message, relative timestamp)
- [ ] Workspace updates on each 5-second refresh cycle without full page reload
- [ ] Features grouped into "ACTIVE" and "COMPLETE" sections
- [ ] Table has columns: Feature, Architect, Builder, QA
- [ ] Badges use correct color mapping: DONE/CLEAN=green, TODO=yellow, FAIL/INFEASIBLE=red, BLOCKED=gray, DISPUTED=orange, ??=dim
- [ ] Cells show "??" when no critic.json exists for that feature, using `--purlin-dim` color token for readable contrast in both themes
- [ ] Each feature with a critic.json shows role status badges in the correct columns
- [ ] Active section sorts features by urgency (red states first, then yellow/orange, then alphabetical)
- [ ] When a delivery plan is active, ACTIVE header shows [PHASE (X/Y)] annotation after the feature count
- [ ] Phase annotation uses TODO/yellow color (--purlin-warn)
- [ ] Phase annotation visible in both expanded and collapsed ACTIVE section states
- [ ] Phase annotation disappears when no delivery plan exists

## User Testing Discoveries
