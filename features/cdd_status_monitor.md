# Feature: CDD Status Monitor

> Label: "Tool: CDD Monitor"
> Category: "DevOps Tools"


## 1. Overview
The Continuous Design-Driven (CDD) Monitor tracks the status of all feature files across both the Application and Agentic (Workflow) domains. Provides both a web dashboard for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Domain Separation
*   **Split View:** The UI must display two distinct columns/sections: "Application" and "Agentic Core".
*   **Path Awareness:** The monitor must scan the host project's `features/` for Application status and the core framework's `features/` for Agentic status.
*   **Status Detection:** Status is derived from a combination of file modification timestamps (for [TODO] detection) and source control history/tags.

### 2.2 UI & Layout
*   **Compact Design:** Minimal padding and margins to ensure the dashboard fits in a small window.
*   **COMPLETE List Capping:** The "COMPLETE" section for each domain should be limited to the most recent items.
*   **Status Indicators:** Use distinct color coding for TODO, TESTING, and COMPLETE states.
*   **Scope:** The web dashboard is for human consumption only. Agents must use the `/status.json` API endpoint.

### 2.3 Verification Signals
*   **Application Tests:** Monitor the primary project's test summary.
*   **Agentic Tests (Standardized Protocol):**
    *   The monitor must scan all subdirectories in `tools/` for a file named `test_status.json`.
    *   **Aggregation:** If ANY `test_status.json` reports a failure, the "Agentic Test Status" must show **FAIL**.
    *   **Success:** Only shows **PASS** if all existing status files report success.

### 2.4 Machine-Readable Output (Agent Interface)
*   **API Endpoint:** The server MUST expose a `/status.json` route that returns the feature status JSON directly with `Content-Type: application/json`. This is the **primary** agent interface.
*   **Canonical File:** The monitor MUST also produce a `feature_status.json` file at `tools/cdd/feature_status.json` as a secondary artifact, regenerated on every request.
*   **Schema:** Both the API response and the file MUST contain the following structure:
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
      "domains": {
        "application": {
          "test_status": "PASS | FAIL | UNKNOWN",
          "features": {
            "todo": [{"file": "<relative path>", "label": "<label>"}],
            "testing": [{"file": "<relative path>", "label": "<label>"}],
            "complete": [{"file": "<relative path>", "label": "<label>"}]
          }
        },
        "agentic": {
          "test_status": "PASS | FAIL | UNKNOWN",
          "features": {
            "todo": [...],
            "testing": [...],
            "complete": [...]
          }
        }
      }
    }
    ```
*   **Regeneration:** The JSON MUST be freshly computed on every `/status.json` request. The file on disk is also regenerated on dashboard and API requests.
*   **Deterministic Output:** Arrays MUST be sorted by file path. Keys MUST be sorted.
*   **Agent Contract:** Agents MUST query status via `curl http://localhost:<port>/status.json` where `<port>` is read from `.agentic_devops/config.json` (`cdd_port`, default `8086`). Agents MUST NOT scrape the web dashboard or guess ports.

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

#### Scenario: Domain Isolation in JSON Output
    Given a feature completion in the Agentic domain
    When GET /status.json is called
    Then the feature appears in the "agentic" domain of the JSON response
    And it does NOT appear in the "application" domain

#### Scenario: Zero-Queue Verification
    Given a release is being prepared
    When the Architect checks the Zero-Queue Mandate
    Then the Architect calls GET /status.json on the configured CDD port
    And verifies that the "todo" and "testing" arrays are empty in both domains

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder must start the server and instruct the User to verify the web dashboard visually.

#### Scenario: Web Dashboard Domain Display
    Given the CDD server is running
    When the User opens the web dashboard in a browser
    Then two distinct columns are visible: "Application" and "Agentic Core"
    And each column displays TODO, TESTING, and COMPLETE sections
    And status indicators use distinct color coding per state

#### Scenario: Web Dashboard Auto-Refresh
    Given the User is viewing the web dashboard
    When a feature status changes (e.g., a status commit is made)
    Then the dashboard reflects the updated status within 5 seconds

## 4. Implementation Notes
*   **Test Scope:** Automated tests MUST only cover the `/status.json` API endpoint and the underlying status logic. The web dashboard HTML rendering and visual layout MUST NOT be tested through automated tests. The Builder MUST NOT start the CDD server. After passing automated tests, the Builder should use the `[Ready for Verification]` status tag and instruct the User to start the server (`tools/cdd/start.sh`) and visually verify the dashboard.
*   **Visual Polish:** Use a dark, high-contrast theme suitable for 24/7 monitoring.
*   **Test Isolation:** The Agentic aggregator scans `tools/*/test_status.json` and treats malformed JSON as FAIL.
*   **Server-Side Rendering:** The HTML is generated dynamically per request (no static `index.html`). Auto-refreshes every 5 seconds via `<meta http-equiv="refresh">`.
*   **Status Logic:** `COMPLETE` requires `complete_ts > test_ts` AND `file_mod_ts <= complete_ts`. Any file edit after the completion commit resets status to `TODO` (the "Status Reset" protocol).
*   **Escape Sequences:** Git grep patterns use `\\[` / `\\]` in f-strings to avoid Python 3.12+ deprecation warnings for invalid escape sequences.
*   **Agent Interface:** The `/status.json` API endpoint is the primary machine-readable contract. All agent tooling (Status Management, Context Clear Protocol, Release Protocol Zero-Queue checks) MUST use `curl http://localhost:<cdd_port>/status.json`. The disk file `feature_status.json` is a secondary artifact. Agents MUST read the port from `.agentic_devops/config.json` (`cdd_port` key, default `8086`) and MUST NOT hardcode or guess port numbers.
