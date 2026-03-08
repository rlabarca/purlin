# Collaboration Protocol

> **Reference file.** Loaded on demand when working on an `isolated/*` branch.
> Stub location: ARCHITECT_BASE Section 10.

This protocol applies when any agent is working in an isolated worktree session.

## Isolation Branch Conventions

*   Isolated sessions run on `isolated/<name>` branches (e.g., `isolated/feat1`, `isolated/ui`).
*   Any agent type (Architect, Builder, QA) may use any isolation name. No role is associated with the name.
*   Worktrees live at `.worktrees/<name>/` (gitignored in the consumer project).
*   `PURLIN_PROJECT_ROOT` is set by the launcher to the worktree directory path.
*   Isolations are created via `tools/collab/create_isolation.sh <name>` and killed via `tools/collab/kill_isolation.sh <name>`.

## Session Completion

Each isolation session is independent. Merges to the collaboration branch happen when the session's work is complete, not in a prescribed order. The merge-before-proceed principle still applies: any agent that needs work from another isolation must wait for that isolation's merge before starting.

1.  Agent completes its work in `.worktrees/<name>/`.
2.  Agent runs `/pl-isolated-push` to verify readiness and merge `isolated/<name>` to the collaboration branch.
3.  User confirms the merge happened before another session that depends on it starts.

## Isolated Teams Dashboard

When the CDD server runs from the project root with active named worktrees under `.worktrees/`, the dashboard enters Isolated Teams Mode (see `features/cdd_isolated_teams.md`). Detection is automatic -- no action required.

## Branch-Scope Limitation Awareness

The Critic's `git log` only sees commits reachable from HEAD. A `[Complete]` commit on an unmerged `isolated/<name>` branch is invisible to other agents on other branches until merged. The merge-before-proceed rule (Session Completion above) is the only mitigation. There is no tool enforcement of this rule -- it is a process discipline requirement.

## ACTIVE_EDITS.md (Multi-Architect Only)

When `config.json` has `"collaboration": { "multi_architect": true }`, Architect sessions MUST declare their in-progress edits in `.purlin/ACTIVE_EDITS.md` (committed, not gitignored). This file prevents simultaneous edits to the same feature spec sections. Single-Architect projects do not use this file.
