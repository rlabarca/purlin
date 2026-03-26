# TOMBSTONE: release_system_core

**Retired:** 2026-03-26
**Reason:** Replaced by the Agentic Toolbox system (features/toolbox_core.md, features/pl_toolbox.md).

## Retired Features

- release_checklist_core.md
- release_checklist_core.impl.md
- release_checklist_ui.md
- release_checklist_ui.impl.md
- release_step_management.discoveries.md

## Files to Delete

- `tools/release/resolve.py` -- old release resolver (replaced by tools/toolbox/resolve.py)
- `tools/release/manage_step.py` -- old step management script (replaced by toolbox step management)
- `tools/release/global_steps.json` -- old global step definitions (replaced by toolbox action registry)
- `tools/release/test_release.py` -- old release test suite
- `tools/release/test_manage_step.py` -- old step management test suite

## Dependencies to Check

- References to `/pl-release` in instruction files have been updated to `/pl-toolbox`
- `.purlin/release/*.json` references updated to `.purlin/toolbox/*.json`
- Step schema references (`purlin.` prefixed step IDs) replaced by toolbox action IDs

## Context

This group defined the core data model, file formats, step schema, global step definitions, and auto-discovery protocol for the Purlin release checklist system. It also included the CDD Dashboard UI for viewing and interacting with release checklists, and the step management tooling for adding, removing, reordering, enabling, and disabling release steps. These capabilities have been superseded by the Agentic Toolbox system, which provides a more general-purpose action registry and execution framework.
