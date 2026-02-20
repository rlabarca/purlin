# Feature: CDD Status Monitor

> Label: "Tool: CDD Monitor"
> Category: "DevOps Tools"


## 1. Overview
The Continuous Design-Driven (CDD) Monitor tracks the status of all feature files in `features/`. Provides both a web dashboard for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Feature Scanning
*   **Path Awareness:** The monitor must scan the project's `features/` directory for all feature files.
*   **Status Detection:** Status is derived from a combination of file modification timestamps (for [TODO] detection) and source control history/tags.

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
| -- | Blank | Any (no critic.json) |

*   **Scope:** The web dashboard is for human consumption only. Agents must use the `/status.json` API endpoint.

### 2.3 Verification Signals
*   **Role Status Source:** The CDD monitor reads role status from pre-computed `tests/<name>/critic.json` files produced by the Critic tool. CDD does NOT compute role status itself.
*   **Test Status (Internal):** The monitor still resolves `tests/<name>/tests.json` for internal lifecycle logic, but test status is no longer displayed as a separate column on the dashboard or exposed as a standalone field in the API. Test pass/fail state is reflected through the Builder role status (DONE vs FAIL).

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
          "qa": "CLEAN | TODO | FAIL | DISPUTED | N/A"
        }
      ]
    }
    ```
    *   Flat `features` array (no `todo`/`testing`/`complete` sub-arrays).
    *   No top-level `test_status` field.
    *   No per-feature `test_status` or `qa_status` fields (replaced by role columns).
    *   Role fields (`architect`, `builder`, `qa`) are omitted when no `critic.json` exists for that feature (dashboard shows `--`).
    *   Array sorted by file path (deterministic).
*   **Internal Artifact (`feature_status.json`):** The monitor MUST also produce a `feature_status.json` file at `tools/cdd/feature_status.json`, regenerated on every request. This file retains the **old** lifecycle-based format with `todo`/`testing`/`complete` arrays and `test_status` fields. This is an internal implementation detail consumed by the Critic for lifecycle-state-dependent computations (e.g., QA TODO detection). It is NOT part of the public API contract.
*   **Regeneration:** Both outputs MUST be freshly computed on every `/status.json` request. The disk file is also regenerated on dashboard requests.
*   **Deterministic Output:** Arrays MUST be sorted by file path. Keys MUST be sorted.
*   **Agent Contract:** Agents MUST query status via `curl http://localhost:<port>/status.json` where `<port>` is read from `.agentic_devops/config.json` (`cdd_port`, default `8086`). Agents MUST NOT scrape the web dashboard or guess ports.

### 2.5 Role Status Integration
*   **Critic JSON Discovery:** For each feature `features/<name>.md`, the monitor checks for `tests/<name>/critic.json` on disk.
*   **Per-Feature Role Status:** If `critic.json` exists, the monitor reads the `role_status` object and exposes its `architect`, `builder`, and `qa` fields on the per-feature API entry. If no `critic.json` exists, all role fields are omitted (dashboard shows `--` in each column).
*   **No Direct Computation:** CDD does NOT compute role status itself. It reads pre-computed values from the Critic's `role_status` output.
*   **Dashboard Columns:** Each feature entry on the web dashboard displays Architect, Builder, and QA columns with the badge/color mapping defined in Section 2.2. Blank cells when no `critic.json` exists.
*   **No Blocking:** The `critic_gate_blocking` config key is deprecated (no-op). CDD does not gate status transitions based on critic or role status results.

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

#### Scenario: Internal Feature Status File Preserved
    Given the CDD server is running
    When any request is made to the server
    Then tools/cdd/feature_status.json is regenerated with the old lifecycle-based format
    And it contains todo, testing, and complete arrays with test_status fields

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder must start the server and instruct the User to verify the web dashboard visually.

#### Scenario: Web Dashboard Display
    Given the CDD server is running
    When the User opens the web dashboard in a browser
    Then features are grouped into Active and Complete sections
    And the table has columns for Feature, Architect, Builder, and QA
    And badges use the defined color mapping (DONE/CLEAN=green, TODO=yellow, FAIL/INFEASIBLE=red, BLOCKED=gray, DISPUTED=orange)
    And cells show "--" when no critic.json exists for that feature

#### Scenario: Web Dashboard Auto-Refresh
    Given the User is viewing the web dashboard
    When a feature status changes (e.g., a status commit is made)
    Then the dashboard reflects the updated status within 5 seconds

#### Scenario: Role Columns on Dashboard
    Given the CDD server is running
    And critic.json files exist for some features
    When the User opens the web dashboard
    Then each feature with a critic.json shows role status badges in the Architect, Builder, and QA columns
    And features without critic.json show "--" in all role columns
    And the Active section sorts features by urgency (red states first, then yellow/orange, then alphabetical)

## 4. Implementation Notes
*   **Test Scope:** Automated tests MUST only cover the `/status.json` API endpoint and the underlying status logic. The web dashboard HTML rendering and visual layout MUST NOT be tested through automated tests. The Builder MUST NOT start the CDD server. After passing automated tests, the Builder should use the `[Ready for Verification]` status tag and instruct the User to start the server (`tools/cdd/start.sh`) and visually verify the dashboard.
*   **Visual Polish:** Use a dark, high-contrast theme suitable for 24/7 monitoring.
*   **Test Isolation:** The test aggregator scans `tests/<feature_name>/tests.json` (resolved relative to `PROJECT_ROOT`) and treats malformed JSON as FAIL.
*   **Name Convention:** Feature-to-test mapping uses the feature file's stem: `features/<name>.md` maps to `tests/<name>/tests.json`. The `<name>` must match exactly (case-sensitive).
*   **Server-Side Rendering:** The HTML is generated dynamically per request (no static `index.html`). Auto-refreshes every 5 seconds via `<meta http-equiv="refresh">`.
*   **Status Logic:** `COMPLETE` requires `complete_ts > test_ts` AND `file_mod_ts <= complete_ts`. Any file edit after the completion commit resets status to `TODO` (the "Status Reset" protocol).
*   **Escape Sequences:** Git grep patterns use `\\[` / `\\]` in f-strings to avoid Python 3.12+ deprecation warnings for invalid escape sequences.
*   **Agent Interface:** The `/status.json` API endpoint is the primary machine-readable contract. All agent tooling (Status Management, Context Clear Protocol, Release Protocol Zero-Queue checks) MUST use `curl http://localhost:<cdd_port>/status.json`. The disk file `feature_status.json` is a secondary artifact. Agents MUST read the port from `.agentic_devops/config.json` (`cdd_port` key, default `8086`) and MUST NOT hardcode or guess port numbers.
*   **Path Normalization:** `os.path.relpath` may resolve to `.`, making `features_rel` = `./features`. The `f_path` used for git grep MUST be normalized with `os.path.normpath()` to strip the `./` prefix, otherwise status commit patterns like `[Complete features/file.md]` won't match `./features/file.md`.
