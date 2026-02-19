# Feature: CDD Status Monitor

> Label: "Tool: CDD Monitor"
> Category: "DevOps Tools"
> Prerequisite: HOW_WE_WORK.md

## 1. Overview
The Continuous Design-Driven (CDD) Monitor tracks the status of all feature files across both the Application and Agentic (Workflow) domains.

## 2. Requirements

### 2.1 Domain Separation
*   **Split View:** The UI must display two distinct columns/sections: "Application" and "Agentic Core".
*   **Path Awareness:** The monitor must scan the host project's `features/` for Application status and the core framework's `features/` for Agentic status.
*   **Status Detection:** Status is derived from a combination of file modification timestamps (for [TODO] detection) and source control history/tags.

### 2.2 UI & Layout
*   **Compact Design:** Minimal padding and margins to ensure the dashboard fits in a small window.
*   **COMPLETE List Capping:** The "COMPLETE" section for each domain should be limited to the most recent items.
*   **Status Indicators:** Use distinct color coding for TODO, TESTING, and COMPLETE states.

### 2.3 Verification Signals
*   **Application Tests:** Monitor the primary project's test summary.
*   **Agentic Tests (Standardized Protocol):** 
    *   The monitor must scan all subdirectories in `tools/` for a file named `test_status.json`.
    *   **Aggregation:** If ANY `test_status.json` reports a failure, the "Agentic Test Status" must show **FAIL**. 
    *   **Success:** Only shows **PASS** if all existing status files report success.

## 3. Scenarios

### Scenario: Domain Isolation
    Given a feature completion in the Agentic domain
    When the CDD monitor refreshes
    Then the feature appears in the COMPLETE section of the Agentic column
    And it does NOT appear in the Application column

## 4. Implementation Notes
*   **Visual Polish:** Use a dark, high-contrast theme suitable for 24/7 monitoring.
*   **Test Isolation:** The Agentic aggregator scans `tools/*/test_status.json` and treats malformed JSON as FAIL.
*   **Server-Side Rendering:** The HTML is generated dynamically per request (no static `index.html`). Auto-refreshes every 5 seconds via `<meta http-equiv="refresh">`.
*   **Status Logic:** `COMPLETE` requires `complete_ts > test_ts` AND `file_mod_ts <= complete_ts`. Any file edit after the completion commit resets status to `TODO` (the "Status Reset" protocol).
*   **Escape Sequences:** Git grep patterns use `\\[` / `\\]` in f-strings to avoid Python 3.12+ deprecation warnings for invalid escape sequences.
