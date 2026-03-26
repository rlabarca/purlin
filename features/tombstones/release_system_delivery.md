# TOMBSTONE: release_system_delivery

**Retired:** 2026-03-26
**Reason:** Replaced by the Agentic Toolbox system (features/toolbox_core.md, features/pl_toolbox.md).

## Retired Features

- release_push_to_remote.md
- release_push_to_remote.impl.md

## Files to Delete

None. The push-to-remote script has been preserved as a toolbox tool.

## Dependencies to Check

- References to `purlin.push_to_remote` release step updated to toolbox action references
- Remote push configuration in release checklist configs updated to toolbox action format

## Context

This group defined the `purlin.push_to_remote` release step: the delivery step that pushes release commits and tags to the remote repository. It included pre-push verification (remote discovery, branch identification), safety checks (dirty-tree detection, behind-remote detection), and interactive confirmation before push. This capability has been preserved as a reusable toolbox action; only the release-system-specific feature spec is retired.
