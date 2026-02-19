# Feature: Software Map Generator

> Label: "Tool: Software Map"
> Category: "DevOps Tools"


## 1. Overview
Generates a visual and machine-readable representation of the project's feature dependency graph. Provides both a web UI for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Core Graph Generation
*   **Tree Generation:** Recursively parses `> Prerequisite:` links in all feature files in `features/`.
*   **Cycle Detection:** Must identify and flag circular dependencies.
*   **Mermaid Export:** Generates Mermaid diagrams for documentation and the interactive web view.

### 2.2 Machine-Readable Output (Agent Interface)
*   **Canonical File:** The generator MUST produce a `dependency_graph.json` file at `tools/software_map/dependency_graph.json`.
*   **Schema:** The JSON file MUST contain the following structure:
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
      "features": [
        {
          "file": "<relative path to feature file>",
          "label": "<Label from metadata>",
          "category": "<Category from metadata>",
          "prerequisites": ["<relative path>", "..."]
        }
      ],
      "cycles": ["<description of any detected cycles>"],
      "orphans": ["<files with no prerequisite links>"]
    }
    ```
*   **Deterministic Output:** Given the same set of feature files, the JSON output MUST be identical (sorted keys, sorted arrays by file path).
*   **Agent Contract:** This file is the ONLY interface agents should use to query the dependency graph. Agents MUST NOT scrape the web UI or parse Mermaid files.

### 2.3 Reactive Generation
*   **File Watch Mode:** When the web server is running (`start.sh`), the tool MUST watch `features/` for file changes (create, modify, delete).
*   **Auto-Regenerate:** When a change is detected, the tool MUST automatically re-run the graph generation, updating both the Mermaid exports and `dependency_graph.json`.
*   **Manual Trigger:** Running `generate_tree.py` directly MUST always regenerate all outputs regardless of whether changes were detected.

### 2.4 Interactive View
*   **Scope:** The web view is for human consumption only. Agents must use `dependency_graph.json`.
*   **Graph Display:** The dependency graph MUST be rendered as an interactive diagram with feature nodes and directed edges representing prerequisite links.
*   **Zoom-to-Fit on Load:** On initial page load, the graph MUST be automatically zoomed and centered to fit the viewable page area. On auto-refresh cycles, the current zoom level and pan position MUST be preserved.
*   **Search/Filter:** A text input MUST be provided that filters visible graph nodes by label or filename. Nodes that do not match the filter should be visually de-emphasized or hidden.
*   **Feature Detail Modal:** Clicking a feature node MUST open a scrollable modal window that renders the feature file's markdown content. The modal MUST have a close button (X) in the top-right corner. Clicking outside the modal MUST also close it.
*   **Hover Highlighting:** When the User hovers over a feature node, the node's immediate neighbors (direct prerequisites and direct dependents, one edge away) MUST be visually highlighted. Non-adjacent nodes should be de-emphasized.

## 3. Scenarios

### Automated Scenarios
These scenarios are validated by the Builder's automated test suite.

#### Scenario: Update Feature Graph
    Given a new feature file is added with prerequisites
    When the software map generator is run
    Then dependency_graph.json is regenerated with the new feature
    And the Mermaid export files are regenerated

#### Scenario: Reactive Update on Feature Change
    Given the software map server is running
    When a feature file is created, modified, or deleted
    Then the tool automatically regenerates the Mermaid exports
    And the tool automatically regenerates dependency_graph.json

#### Scenario: Agent Reads Dependency Graph
    Given dependency_graph.json exists at tools/software_map/dependency_graph.json
    When an agent needs to query the dependency graph
    Then the agent reads dependency_graph.json directly
    And the agent does NOT use the web UI or parse Mermaid files

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder MUST NOT start the server. The Builder must instruct the User to start the server (`tools/software_map/start.sh`) and verify the web UI visually.

#### Scenario: Interactive Web View
    Given the software map server is running
    When the User opens the web UI in a browser
    Then the dependency graph is rendered with nodes and edges
    And the graph is zoomed to fit the viewable page area
    And a search input is visible for filtering nodes

#### Scenario: Feature Detail Modal
    Given the User is viewing the web UI
    When the User clicks a feature node
    Then a scrollable modal opens showing the rendered markdown content
    And the modal has an X button in the top-right corner
    When the User clicks the X button or clicks outside the modal
    Then the modal closes

#### Scenario: Hover Highlighting
    Given the User is viewing the web UI
    When the User hovers over a feature node
    Then the node's direct prerequisites and direct dependents are highlighted
    And non-adjacent nodes are visually de-emphasized

#### Scenario: Zoom Persistence on Refresh
    Given the User has zoomed or panned the graph
    When the dashboard auto-refreshes
    Then the current zoom level and pan position are preserved

## 4. Implementation Notes
*   **Test Scope:** Automated tests MUST only cover graph generation, cycle detection, and `dependency_graph.json` output. The web UI MUST NOT be tested through automated tests. The Builder MUST NOT start the server. After passing automated tests, the Builder should use the `[Ready for Verification]` status tag and instruct the User to start the server (`tools/software_map/start.sh`) and visually verify the web view.
*   **Acyclic Mandate:** The tool is the primary enforcer of the acyclic graph rule defined in the workflow.
*   **Agent Interface:** `dependency_graph.json` is the single machine-readable contract. All agent tooling (Context Clear Protocol, Dependency Integrity checks, Release Protocol) MUST read this file.
*   **Cycle Detection:** Uses DFS with 3-color marking (WHITE/GRAY/BLACK). External prerequisites (not in the features directory) are skipped without triggering false positives.
*   **File Watch Mode:** `serve.py` polls `features/` directory every 2 seconds using `os.scandir` mtime snapshots. No external dependencies required (no `watchdog`).
*   **Deterministic JSON:** `dependency_graph.json` uses `sort_keys=True` on `json.dump` and all arrays are pre-sorted by filename/path before serialization.
