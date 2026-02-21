# Feature: CDD Status Monitor

> Label: "Tool: CDD Monitor"
> Category: "DevOps Tools"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/design_visual_standards.md


## 1. Overview
The Continuous Design-Driven (CDD) Monitor tracks the status of all feature files in `features/`. Provides both a web dashboard for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Feature Scanning
*   **Path Awareness:** The monitor must scan the project's `features/` directory for all feature files.
*   **Status Detection:** Status is derived from a combination of file modification timestamps (for [TODO] detection) and source control history/tags.
*   **Discovery-Aware Lifecycle Preservation:** When a feature file is modified after a status commit, the monitor MUST check whether the modification is limited to the `## User Testing Discoveries` section. If the spec content above that section is identical to the content at the status commit, the lifecycle state is preserved (COMPLETE or TESTING). This prevents QA housekeeping (pruning resolved discoveries) from triggering a false lifecycle reset to TODO.

### 2.2 UI & Layout
*   **Role-Based Columns:** The dashboard MUST render features in a table with the following columns:
    *   **Feature** -- The feature filename.
    *   **Architect** -- The Architect role status badge.
    *   **Builder** -- The Builder role status badge.
    *   **QA** -- The QA role status badge.
*   **Two Groups:** Features are displayed in two sections:
    *   **Active** -- Any feature where at least one role is not fully satisfied (i.e., not all of: Architect=DONE, Builder=DONE, QA=CLEAN or N/A).
    *   **Complete** -- All roles fully satisfied. Capped at 10 most recent entries.
*   **Active Section Sorting:** Features sorted by urgency: any red state (FAIL, INFEASIBLE) first, then any yellow/orange state (TODO, DISPUTED), then alphabetical.
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
| ?? | Blank/dim | Any (no critic.json -- not yet generated) |

*   **Scope:** The web dashboard is for human consumption only. Agents must use the `/status.json` API endpoint.

### 2.3 Verification Signals
*   **Role Status Source:** The CDD monitor reads role status from pre-computed `tests/<name>/critic.json` files produced by the Critic tool. CDD does NOT compute role status itself.
*   **Test Status (Internal):** The monitor still resolves `tests/<name>/tests.json` for internal lifecycle logic, but test status is no longer displayed as a separate column on the dashboard or exposed as a standalone field in the API. Test pass/fail state is reflected through the Builder role status (DONE vs FAIL).
*   **Section Heading Visual Separation:** The dashboard MUST render section headings ("ACTIVE", "COMPLETE") with an underline separator (e.g., a bottom border or `<hr>`) to clearly distinguish them from the feature rows beneath.

### 2.4 Machine-Readable Output (Agent Interface)
*   **API Endpoint:** The server MUST expose a `/status.json` route that returns the feature status JSON directly with `Content-Type: application/json`. This is the **primary** agent interface.
*   **API Schema (`/status.json`):**
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
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
    *   Array sorted by file path (deterministic).
*   **Internal Artifact (`feature_status.json`):** The monitor MUST also produce a `feature_status.json` file at `.agentic_devops/cache/feature_status.json`, regenerated on every request (web) or CLI invocation. This file retains the **old** lifecycle-based format with `todo`/`testing`/`complete` arrays and `test_status` fields, plus a `change_scope` field per feature (extracted from the most recent status commit's `[Scope: ...]` trailer, omitted when absent). This is an internal implementation detail consumed by the Critic for lifecycle-state-dependent computations (e.g., QA TODO detection, regression scope). It is NOT part of the public API contract.
*   **Regeneration:** Both outputs MUST be freshly computed on every `/status.json` request. The disk file is also regenerated on dashboard requests.
*   **Deterministic Output:** Arrays MUST be sorted by file path. Keys MUST be sorted.
*   **Agent Contract:** Agents MUST query status via `tools/cdd/status.sh`, which outputs the same JSON schema to stdout without requiring the web server. Agents MUST NOT scrape the web dashboard, use HTTP endpoints, or guess ports.

### 2.5 Role Status Integration
*   **Critic JSON Discovery:** For each feature `features/<name>.md`, the monitor checks for `tests/<name>/critic.json` on disk.
*   **Per-Feature Role Status:** If `critic.json` exists, the monitor reads the `role_status` object and exposes its `architect`, `builder`, and `qa` fields on the per-feature API entry. If no `critic.json` exists, all role fields are omitted (dashboard shows `??` in each column).
*   **No Direct Computation:** CDD does NOT compute role status itself. It reads pre-computed values from the Critic's `role_status` output.
*   **Dashboard Columns:** Each feature entry on the web dashboard displays Architect, Builder, and QA columns with the badge/color mapping defined in Section 2.2. Blank cells when no `critic.json` exists.
*   **No Blocking:** The `critic_gate_blocking` config key is deprecated (no-op). CDD does not gate status transitions based on critic or role status results.

### 2.6 CLI Status Tool (Agent Interface)
*   **Script Location:** `tools/cdd/status.sh` (executable, `chmod +x`). Wrapper calls a Python module for status computation.
*   **Purpose:** Provides agents with feature status without requiring the web server to be running. This is the primary agent interface for CDD status queries.
*   **Output:** Writes the same JSON schema as the `/status.json` API endpoint to stdout. The output MUST be valid JSON parseable by `python3 json.load()`.
*   **Side Effect:** Regenerates `.agentic_devops/cache/feature_status.json` (the internal lifecycle-based artifact consumed by the Critic).
*   **Project Root Detection:** Uses `AGENTIC_PROJECT_ROOT` if set, then climbing fallback (per submodule_bootstrap Section 2.11).
*   **No Server Dependency:** The tool MUST NOT depend on the web server being running. It computes status directly from disk (feature files, git history, critic.json files).
*   **Shared Logic:** The status computation logic MUST be consistent with the web server's `/status.json` endpoint. Implementation MAY share code with `serve.py` or extract a common module.

### 2.7 Manual Critic Trigger (Dashboard)
*   **Button Location:** Per Section 2.9 Header Layout -- the "Run Critic" button is in the right group of the page header, between the timestamp and the theme toggle.
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
*   **Verification Method:** At each lifecycle stage, the test runs `tools/critic/run.sh` to regenerate `critic.json` files, then runs `tools/cdd/status.sh` and parses the JSON output to assert expected role status values for the temporary feature. Assertions use `python3 -c` or `jq` to extract and compare JSON fields.
*   **Cleanup Guarantee:** The test MUST use `trap` to ensure cleanup runs on exit (success, failure, or signal). Cleanup sequence: (1) `git reset --hard <pre-test-sha>` to revert all temporary commits, (2) remove any untracked temporary files (`features/_test_lifecycle_temp.md`, `tests/_test_lifecycle_temp/`), (3) run `tools/critic/run.sh` to restore clean critic.json state. After cleanup, `git log` and `git status` MUST show no trace of the test.
*   **Test Results:** On success, output `[Scenario] <title>` lines for each passing stage (Bash test file convention) and write `tests/cdd_status_monitor/tests.json` with `{"status": "PASS"}`. On any assertion failure, report the failing stage and expected vs actual values, then proceed to cleanup.

### 2.9 Branding & Theme

#### Header Layout
The page header is a single horizontal bar with two groups, vertically centered:

**Left group** (left-justified, in this order left-to-right):
1.  Purlin logo mark (`assets/purlin-logo.svg`, inline SVG, ~24px height, CSS classes for theme-responsive fills)
2.  Title and project name block (stacked vertically):
    *   **Line 1:** Title text: "Purlin CDD Monitor"
    *   **Line 2:** Active project name (per `design_visual_standards.md` Section 2.6). Resolved from `project_name` in config, falling back to the project root directory name. The project name's left edge MUST align with the left edge of the "P" in the title above. Font: `var(--font-body)` Inter Medium 500, 14px, color `var(--purlin-primary)`.

**Right group** (right-justified, in this order from the right edge inward):
1.  Theme toggle (sun/moon icon) -- rightmost element
2.  "Run Critic" button
3.  Last-refreshed timestamp (monospace font to prevent layout shift as digits change)

The two groups MUST be laid out with CSS flexbox (`justify-content: space-between`). The right group items are ordered via `flex-direction: row` with the timestamp first, Run Critic button second, and theme toggle last in DOM order -- or equivalently, the right group uses `flex-direction: row-reverse` with theme toggle first, Run Critic second, timestamp third in DOM order. The visual result MUST match: timestamp on the left side of the right group, theme toggle on the far right.

#### Title
*   The dashboard title MUST read "Purlin CDD Monitor".

#### Theme
*   **CSS Tokens:** All colors in the dashboard MUST use `var(--purlin-*)` custom properties defined in `features/design_visual_standards.md`. No hardcoded hex colors.
*   **Default Theme:** Dark (Blueprint).
*   **Persistence:** Theme choice stored in `localStorage` key `purlin-theme`, value `light` or `dark`.
*   **FOUC Prevention:** A synchronous `<script>` in `<head>` reads `localStorage` and sets the `data-theme` attribute on `<html>` before first paint. This prevents theme flash on the 5-second auto-refresh cycle.
*   **Theme Toggle:** Clicking the sun/moon icon switches between Blueprint (dark, default) and Architect (light) themes.

#### Typography
Per `design_visual_standards.md` Section 2.3. Tool title uses `var(--font-display)` (Montserrat ExtraLight 200, wide tracking `0.12em`, `uppercase`). Section headers use `var(--font-body)` (Inter Bold 700, `uppercase`, wide tracking `0.1em`). Body/UI text uses `var(--font-body)` (Inter 400-500). Data/code retains monospace. The last-refreshed timestamp MUST use the monospace font stack (`'Menlo', 'Monaco', 'Consolas', monospace`) so that digit changes do not cause width fluctuation. CDN loads: Montserrat weights 200,800,900; Inter weights 400,500,700.

### 2.10 Visual Stability on Refresh
The dashboard refreshes data every 5 seconds. This refresh MUST NOT cause visible flicker, layout shift, or font re-rendering on any static element.

*   **In-Place Data Refresh:** The dashboard MUST use JavaScript `fetch()` to retrieve updated status data and replace only the changed DOM content. It MUST NOT use `<meta http-equiv="refresh">` or `window.location.reload()`. The page loads once; all subsequent updates are incremental DOM mutations.
*   **Static Elements:** The page header (left group: logo + title; right group: timestamp, Run Critic button, theme toggle) MUST render once on initial page load and never be re-created or replaced during data refresh cycles. Only the timestamp text value updates.
*   **Font Stability:** Google Fonts CDN `<link>` tags load once on initial page load. Because the page never fully reloads, fonts remain cached in the browser and do not trigger re-layout or FOUT (Flash of Unstyled Text) on refresh cycles.
*   **Table Update:** When feature status data changes, only the table body content updates. The table headers (Feature, Architect, Builder, QA) and section headings (ACTIVE, COMPLETE) remain stable. Rows that did not change SHOULD NOT be re-rendered.
*   **No Scroll Reset:** If the user has scrolled down, a data refresh MUST NOT reset the scroll position.

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

#### Scenario: Run Critic Endpoint
    Given the CDD server is running
    When a POST request is sent to /run-critic
    Then the server executes tools/critic/run.sh (or equivalent logic) server-side
    And returns a JSON response with a success or error status
    And the response includes a Content-Type of application/json

#### Scenario: Change Scope in API Response
    Given a feature has a status commit with [Scope: targeted:Web Dashboard Display]
    When an agent calls GET /status.json
    Then the feature entry includes change_scope with value "targeted:Web Dashboard Display"

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
    When tools/critic/run.sh is run
    And tools/cdd/status.sh is run
    Then the feature lifecycle is TODO
    And role_status.builder is TODO
    And role_status.qa is N/A

#### Scenario: Lifecycle Integration -- TODO with Passing Tests
    Given the temporary feature exists
    And tests are created and pass (tests.json with status PASS)
    And an implementation commit is made (no status tag)
    When tools/critic/run.sh is run
    And tools/cdd/status.sh is run
    Then the feature lifecycle is TODO
    And role_status.builder is TODO
    And role_status.qa is CLEAN

#### Scenario: Lifecycle Integration -- TESTING
    Given the temporary feature has passing tests
    And a status commit "[Ready for Verification features/<temp>.md]" is made
    When tools/critic/run.sh is run
    And tools/cdd/status.sh is run
    Then the feature lifecycle is TESTING
    And role_status.builder is DONE
    And role_status.qa is TODO

#### Scenario: Lifecycle Integration -- COMPLETE
    Given the temporary feature has passing tests
    And a status commit "[Complete features/<temp>.md]" is made
    When tools/critic/run.sh is run
    And tools/cdd/status.sh is run
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

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder must start the server and instruct the User to verify the web dashboard visually.

#### Scenario: Web Dashboard Display
    Given the CDD server is running
    When the User opens the web dashboard in a browser
    Then features are grouped into Active and Complete sections
    And the table has columns for Feature, Architect, Builder, and QA
    And badges use the defined color mapping (DONE/CLEAN=green, TODO=yellow, FAIL/INFEASIBLE=red, BLOCKED=gray, DISPUTED=orange)
    And cells show "??" when no critic.json exists for that feature

#### Scenario: Web Dashboard Auto-Refresh
    Given the User is viewing the web dashboard
    When a feature status changes (e.g., a status commit is made)
    Then the dashboard reflects the updated status within 5 seconds
    And the page header (logo, title, toggle, button) does not flicker or re-render
    And fonts do not re-load or cause layout shift
    And the scroll position is preserved

#### Scenario: Role Columns on Dashboard
    Given the CDD server is running
    And critic.json files exist for some features
    When the User opens the web dashboard
    Then each feature with a critic.json shows role status badges in the Architect, Builder, and QA columns
    And features without critic.json show "??" in all role columns
    And the Active section sorts features by urgency (red states first, then yellow/orange, then alphabetical)

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
    When the User locates the top-right area next to the last-updated timestamp
    Then a "Run Critic" button is visible
    When the User clicks the "Run Critic" button
    Then the button enters a disabled/loading state
    And after the Critic finishes, the dashboard refreshes with updated role status columns
    And the button returns to its enabled state

## 4. Implementation Notes
*   **Test Scope:** Automated tests cover the `/status.json` API endpoint, the `status.sh` CLI tool, the underlying status logic, AND the full lifecycle integration test (Section 2.8). The lifecycle integration test eliminates the need for manual QA verification of lifecycle state transitions and role status column values -- these are fully verified by automation. Manual scenarios are reserved exclusively for web dashboard visual/UI verification. The Builder MUST NOT start the CDD server during automated tests.
*   **Visual Polish:** Use a dark, high-contrast theme suitable for 24/7 monitoring.
*   **Test Isolation:** The test aggregator scans `tests/<feature_name>/tests.json` (resolved relative to `PROJECT_ROOT`) and treats malformed JSON as FAIL.
*   **Name Convention:** Feature-to-test mapping uses the feature file's stem: `features/<name>.md` maps to `tests/<name>/tests.json`. The `<name>` must match exactly (case-sensitive).
*   **Server-Side Rendering + Client-Side Refresh:** The initial HTML page is generated server-side on first request (no static `index.html`). After initial load, the page uses a JavaScript `setInterval` (5 seconds) to `fetch('/status.json')` and update only the table body DOM. The page does NOT use `<meta http-equiv="refresh">` -- this avoids full-page reloads that cause font re-rendering, layout shift, and scroll resets.
*   **Status Logic:** `COMPLETE` requires `complete_ts > test_ts` AND either `file_mod_ts <= complete_ts` OR the only changes since the status commit are in the `## User Testing Discoveries` section (discovery-aware lifecycle preservation). To check: retrieve the file content at the status commit hash via `git show <hash>:<path>`, strip the `## User Testing Discoveries` section and everything below from both versions, and compare. If the spec content above discoveries is identical, preserve the lifecycle state. Otherwise reset to `TODO`.
*   **Escape Sequences:** Git grep patterns use `\\[` / `\\]` in f-strings to avoid Python 3.12+ deprecation warnings for invalid escape sequences.
*   **Agent Interface:** `tools/cdd/status.sh` is the primary agent interface. All agent tooling (Status Management, Context Clear Protocol, Release Protocol Zero-Queue checks) MUST use `tools/cdd/status.sh` for status queries. The `/status.json` web endpoint provides the same data for human tooling or when the server is running. Agents MUST NOT use HTTP endpoints, scrape the web dashboard, or guess port numbers.
*   **Path Normalization:** `os.path.relpath` may resolve to `.`, making `features_rel` = `./features`. The `f_path` used for git grep MUST be normalized with `os.path.normpath()` to strip the `./` prefix, otherwise status commit patterns like `[Complete features/file.md]` won't match `./features/file.md`.
*   **Section Heading Underline:** Section headings ("ACTIVE", "COMPLETE") require a visible underline separator to distinguish them from feature rows. Verified 2026-02-19.
*   **Badge "??" for missing critic.json:** SPEC_DISPUTE resolved -- spec updated from "--" to "??" for missing critic data. Verified 2026-02-20.
*   **CLI Mode:** `serve.py --cli-status` outputs API JSON to stdout and regenerates `feature_status.json`. `status.sh` is a shell wrapper that detects project root and calls this mode.
*   **Start/Stop PID Path Consistency:** `start.sh` writes PID files to `.agentic_devops/runtime/`. `stop.sh` MUST read from the same runtime directory using the same project root detection logic. A path mismatch between start and stop causes orphaned server processes and port conflicts on subsequent starts.
*   **Lifecycle Test Timing:** `test_lifecycle.sh` uses `sleep 1` between status tag commits (Ready for Verification -> Complete, Complete -> spec edit) to ensure git commit timestamps differ by at least 1 second, avoiding `int()` truncation equality in the lifecycle comparison logic.
*   **Run Critic Button:** BUG resolved 2026-02-20 — button was missing from dashboard, Builder added it. Verified: displays in top-right, enters loading state on click, refreshes dashboard with updated role columns.
*   **Port TIME_WAIT fix:** Set `allow_reuse_address = True` on `socketserver.TCPServer` in `serve.py` so the server can rebind to a port in TIME_WAIT state after stop/restart. Also added startup verification to `start.sh` — waits 0.5s and checks if the PID is still alive, reporting an error with log path if the process exited (e.g., bind failure).
*   **start.sh multi-invocation issue:** DISCOVERY resolved 2026-02-20 — port TIME_WAIT fix and startup verification resolved the need for multiple start.sh invocations after stop. Server now starts reliably on first invocation.
*   **Change Scope in API (2026-02-21):** Added `get_change_scope()` to `serve.py` — extracts `[Scope: ...]` trailer from the most recent status commit message (Complete or Ready for Verification). Included as `change_scope` field in both `/status.json` API response and internal `feature_status.json`. Omitted when no scope is declared, per spec.
*   **Purlin Branding (2026-02-21):** Implemented Section 2.9 — replaced all hardcoded hex colors with `var(--purlin-*)` CSS custom properties. Added `:root` (Blueprint dark default) and `[data-theme='light']` (Architect light) theme definitions. Inline SVG logo (mark only, no text) in header. Title updated to "Purlin CDD Monitor". Sun/moon theme toggle via CSS visibility + JS `toggleTheme()`. FOUC prevention script in `<head>` reads `purlin-theme` from localStorage before first paint. Google Fonts CDN for Montserrat (headings) and Inter (body). Monospace retained for data table cells and pre blocks.
*   **Visual Stability on Refresh (2026-02-21):** Implemented Section 2.10 — replaced `<meta http-equiv="refresh" content="5">` with JavaScript `setInterval(refreshData, 5000)` that calls `fetch('/status.json')`. The JS rebuilds only the feature table bodies (Active/Complete), using wrapper `<div>` elements with `id="active-content"` and `id="complete-content"`. The page header (logo, title, theme toggle, Run Critic button) renders once on initial server-side load and is never re-created. The timestamp updates client-side via `Date()`. The Run Critic button now calls `refreshData()` on success instead of `location.reload()`. The JS replicates Python's `_is_feature_complete()` and `_feature_urgency()` logic for Active/Complete splitting and urgency sorting.
*   **Typography Alignment (2026-02-21):** Aligned CDD and Software Map with `design_visual_standards.md` Section 2.3. Added `--font-display` and `--font-body` CSS custom properties to both `:root` and `[data-theme='light']` blocks. Updated CDN weights to Montserrat 200,800,900 and Inter 400,500,700. Page title uses `var(--font-display)` at weight 200 (ExtraLight) with `letter-spacing:0.12em;text-transform:uppercase` (wide tracking matching SVG logo treatment — thin strokes with generous spacing). Section headers (h2) use `var(--font-body)` at weight 700, uppercase, `letter-spacing:0.1em`. Sub-labels (h3) and table headers use `var(--font-body)` at weight 700, uppercase, `letter-spacing:0.1em`. All hardcoded `'Montserrat'` and `'Inter'` font-family values replaced with CSS custom property references.
*   **[CLARIFICATION]** Title font-size kept at 14px (CDD) / 14px (Software Map) despite design spec guideline of 32-40px. The compact monitoring dashboard layout requires a smaller title. The weight (200), letter-spacing (0.12em), text-transform (uppercase), and font-family (var(--font-display)) match the spec. (Severity: INFO)
*   **[CLARIFICATION]** h3 sub-labels kept at 11px (CDD) rather than the 14px section header guideline. These "Active"/"Complete" dividers function as captions/sub-labels (design spec: 10px), not full section headers. (Severity: INFO)
*   **Header right-group order fix (2026-02-21):** BUG resolved — DOM order in `.hdr-right` was [toggle][critic][timestamp], rendering visually reversed from spec Section 2.9. Fixed to [timestamp][critic-err][critic][toggle] so left-to-right reads: timestamp, Run Critic button, theme toggle (rightmost). Added inline monospace font-family to timestamp `<span>` for explicit width stability.
*   **Discovery-aware lifecycle false match (2026-02-21):** See `[BUG] strip_discoveries false match` in User Testing Discoveries below. The `strip_discoveries()` function in `serve.py` uses `text.find()` which matches a backtick-quoted reference in Section 2.1 before the actual section header. Builder must fix with a regex line-start match.

## Visual Specification

### Screen: CDD Web Dashboard
- **Reference:** N/A
- [ ] Section headings ("ACTIVE", "COMPLETE") have a visible underline separator (e.g., a bottom border or horizontal rule)
- [ ] Section headings are clearly distinguished from the feature table rows beneath them
- [ ] Header left group: Purlin logo mark then "PURLIN CDD MONITOR" title, left-justified
- [ ] Active project name displayed on a second line below the title, left-aligned with the "P" in PURLIN
- [ ] Project name uses Inter Medium 500, body text size (14px), color matches the logo triangle (`--purlin-primary`)
- [ ] Project name color switches correctly between dark and light themes
- [ ] Project name shows config value when `project_name` is set; falls back to project directory name otherwise
- [ ] Header right group (from right edge inward): sun/moon toggle, Run Critic button, last-refreshed timestamp
- [ ] Last-refreshed timestamp uses monospace font (no width shift when digits change)
- [ ] Clicking toggle switches between Blueprint (dark) and Architect (light) themes
- [ ] Theme persists across page refreshes (auto-refresh every 5s does not reset theme)
- [ ] All UI colors use the Purlin design tokens (no hardcoded hex)
- [ ] On 5-second auto-refresh, the page header remains completely static with no flicker
- [ ] Fonts do not visibly re-load or cause layout shift on auto-refresh
- [ ] Scroll position is preserved across auto-refresh cycles
- [ ] Only feature status data updates; table headers and section headings remain stable

## User Testing Discoveries

### [BUG] strip_discoveries false match on backtick-quoted section header
- **Status:** OPEN
- **Found by:** Architect (during spec editing -- lifecycle did not reset to TODO after spec change)
- **Description:** The `strip_discoveries()` function in `serve.py` uses `text.find('## User Testing Discoveries')` to locate the section boundary for the discovery-aware lifecycle comparison. This matches the first occurrence of the literal string in the file -- which in this feature file appears inside a backtick-quoted reference in Section 2.1 (char 866), not the actual section header (char 34638). The lifecycle comparison truncates at the wrong position, making all spec edits above char 866 invisible and preventing lifecycle reset to TODO.
- **Expected:** Spec edits to Section 2.9 (Header Layout) and Visual Specification should reset the feature lifecycle from COMPLETE to TODO.
- **Actual:** Feature remains in COMPLETE lifecycle, Builder role_status stays DONE, hiding the work.
- **Fix:** Replace `text.find('## User Testing Discoveries')` with a regex line-start match (e.g., `re.search(r'^## User Testing Discoveries', text, re.MULTILINE)`) in `serve.py`.
