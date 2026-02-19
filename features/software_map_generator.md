# Feature: Software Map Generator

> Label: "Tool: Software Map"
> Category: "DevOps Tools"


## 1. Overview
Generates a visual and machine-readable representation of the project's feature dependency graph. Provides both a web UI for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Core Graph Generation
*   **Tree Generation:** Recursively parses `> Prerequisite:` links in all feature files.
*   **Cycle Detection:** Must identify and flag circular dependencies.
*   **Mermaid Export:** Generates Mermaid diagrams for documentation and the interactive web view.

### 2.2 Machine-Readable Output (Agent Interface)
*   **Canonical File:** The generator MUST produce a `dependency_graph.json` file at `tools/software_map/dependency_graph.json`.
*   **Schema:** The JSON file MUST contain the following structure:
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
      "domains": {
        "application": {
          "features": [
            {
              "file": "<relative path to feature file>",
              "label": "<Label from metadata>",
              "category": "<Category from metadata>",
              "prerequisites": ["<relative path>", "..."]
            }
          ]
        },
        "agentic": {
          "features": [...]
        }
      },
      "cycles": ["<description of any detected cycles>"],
      "orphans": ["<files with no prerequisite links>"]
    }
    ```
*   **Deterministic Output:** Given the same set of feature files, the JSON output MUST be identical (sorted keys, sorted arrays by file path).
*   **Agent Contract:** This file is the ONLY interface agents should use to query the dependency graph. Agents MUST NOT scrape the web UI or parse Mermaid files.

### 2.3 Reactive Generation
*   **File Watch Mode:** When the web server is running (`start.sh`), the tool MUST watch `features/` directories for file changes (create, modify, delete).
*   **Auto-Regenerate:** When a change is detected, the tool MUST automatically re-run the graph generation, updating both the Mermaid exports and `dependency_graph.json`.
*   **Manual Trigger:** Running `generate_tree.py` directly MUST always regenerate all outputs regardless of whether changes were detected.

### 2.4 Interactive View
*   **Web UI:** Serves an interface with a filterable, searchable tree of features for human review.
*   **Scope:** The web view is for human consumption only. Agents must use `dependency_graph.json`.

## 3. Scenarios

### Scenario: Update Feature Graph
    Given a new feature file is added with prerequisites
    When the software map generator is run
    Then the dependency graph is updated
    And the new feature appears in the interactive view
    And dependency_graph.json is regenerated with the new feature

### Scenario: Reactive Update on Feature Change
    Given the software map server is running
    When a feature file is created, modified, or deleted
    Then the tool automatically regenerates the Mermaid exports
    And the tool automatically regenerates dependency_graph.json

### Scenario: Agent Reads Dependency Graph
    Given dependency_graph.json exists at tools/software_map/dependency_graph.json
    When an agent needs to query the dependency graph
    Then the agent reads dependency_graph.json directly
    And the agent does NOT use the web UI or parse Mermaid files

## 4. Implementation Notes
*   **Acyclic Mandate:** The tool is the primary enforcer of the acyclic graph rule defined in the workflow.
*   **Agent Interface:** `dependency_graph.json` is the single machine-readable contract. All agent tooling (Context Clear Protocol, Dependency Integrity checks, Release Protocol) MUST read this file.
*   **Cycle Detection:** Uses DFS with 3-color marking (WHITE/GRAY/BLACK). External prerequisites (not in the features directory) are skipped without triggering false positives.
*   **File Watch Mode:** `serve.py` polls `features/` directories every 2 seconds using `os.scandir` mtime snapshots. No external dependencies required (no `watchdog`).
*   **Deterministic JSON:** `dependency_graph.json` uses `sort_keys=True` on `json.dump` and all arrays are pre-sorted by filename/path before serialization.
*   **Meta Mode:** When `is_meta_agentic_dev: true`, both Application and Agentic domains resolve to the same `features/` directory. This is expected - the core framework IS the project.
