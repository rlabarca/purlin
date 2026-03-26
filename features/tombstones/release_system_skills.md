# TOMBSTONE: release_system_skills

**Retired:** 2026-03-26
**Reason:** Replaced by the Agentic Toolbox system (features/toolbox_core.md, features/pl_toolbox.md).

## Retired Features

- pl_release.md
- policy_release.md
- policy_release.impl.md

## Files to Delete

- `.claude/commands/pl-release.md` -- old /pl-release skill file (replaced by /pl-toolbox)

## Dependencies to Check

- References to `/pl-release` in instruction files have been updated to `/pl-toolbox`
- References to `/pl-release-check`, `/pl-release-run`, `/pl-release-step` updated
- Policy invariants from `policy_release.md` migrated to toolbox policy anchors where applicable

## Context

This group defined the `/pl-release` agent skill and its governing policy. The `/pl-release` skill consolidated release operations (check, run, step) into a single command with subcommands, replacing the older `/pl-release-check`, `/pl-release-run`, and `/pl-release-step` skills. The `policy_release.md` anchor established governance rules and invariants for the release checklist system, including step ID namespacing, immutability of global steps, and the zero-queue mandate. These capabilities have been superseded by the `/pl-toolbox` skill and the toolbox policy framework.
