# Agentic Core Tools

This directory contains the tools that power the **Agentic Workflow**.

## CDD Scanner
**Continuous Design-Driven status scanner.**
- **Purpose:** Scans feature files in `features/` and generates status JSON.
- **Run:** `bash tools/cdd/scan.sh`
- **Output:** `.purlin/cache/scan.json`

## Feature Cleanup
- **Purpose:** Identifies orphaned feature files that are not part of the dependency tree.
- **Run:** `python3 tools/cleanup_orphaned_features.py`
