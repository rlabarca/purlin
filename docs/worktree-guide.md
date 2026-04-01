# Worktree Guide

How to run multiple Purlin agents in parallel using isolated git worktrees.

## Overview

The `purlin:worktree` skill manages git worktrees for parallel agent work. Each worktree is an isolated copy of the repository where an agent can work without affecting the main working directory.

## Creating a Worktree

```
purlin:worktree create
```

This creates a new worktree under `.purlin/worktrees/` with a timestamped branch. The agent works entirely inside this copy.

## Listing Worktrees

```
purlin:worktree list
```

Shows all worktrees with their status (active, stale, or orphaned).

## Cleanup

```
purlin:worktree cleanup-stale
```

Removes worktrees whose owning agent has exited.

## Merging Back

When work in a worktree is complete, merge the branch back to the source branch using standard git commands. The worktree can then be removed.

## Key Points

- One agent per worktree — concurrent access is prevented via session locks.
- Worktrees are ephemeral — create for a task, merge and clean up when done.
- The main session and worktree agents each have their own `sync_status` state (separate spec/proof files).
- Session start clears stale runtime locks, so a crashed worktree won't block future sessions.
