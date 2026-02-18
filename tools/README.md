# Agentic Core Tools

This directory contains the tools that power the **Agentic Workflow**.

## CDD Web Monitor
**Continuous Design-Driven Dashboard.**
- **Purpose:** Monitors the status of feature files across both Application and Agentic domains.
- **Run:** `./tools/cdd/start.sh`
- **View:** `http://localhost:8086`

## Software Map & Tree Generation
**Dependency Visualization.**
- **Purpose:** Manages the feature dependency graph and Mermaid visualizations.
- **Generate Tree:** `./tools/software_map/generate_tree.py`
  - Regenerates Mermaid graph files in `tools/`.
  - Injects the graph into the project's root `README.md`.
  - Outputs a text-based dependency tree for CLI agents.
- **Interactive Map:** `./tools/software_map/start.sh`
  - Starts a web server for interactive visualization.
  - **View:** `http://localhost:8087`

## Feature Cleanup
- **Purpose:** Identifies orphaned feature files that are not part of the dependency tree.
- **Run:** `python3 tools/cleanup_orphaned_features.py`
