# Agentic Core Tools

This directory contains the tools that power the **Agentic Workflow**.

## CDD Web Monitor
**Continuous Design-Driven Dashboard.**
- **Purpose:** Monitors the status of feature files in `features/`.
- **Run:** `./tools/cdd/start.sh`
- **View:** `http://localhost:8086`

## Feature Cleanup
- **Purpose:** Identifies orphaned feature files that are not part of the dependency tree.
- **Run:** `python3 tools/cleanup_orphaned_features.py`
