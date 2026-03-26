# Agentic Core Tools

This directory contains the tools that power the **Agentic Workflow**.

## CDD Scanner
**Continuous Design-Driven status scanner.**
- **Purpose:** Scans feature files in `features/` and generates status JSON.
- **Run:** `bash tools/cdd/scan.sh`
- **Output:** `.purlin/cache/scan.json`

## Feature Cleanup
- **Purpose:** Orphan detection is handled by the scan engine (`tools/cdd/graph.py`), which reports orphaned features in `dependency_graph.json`. Run `tools/cdd/scan.sh` and check the `orphans` key.
