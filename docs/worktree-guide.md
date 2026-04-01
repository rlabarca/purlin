# Worktree Guide

Run multiple Purlin agents in parallel using isolated git worktrees.

## When to Use

You have two features with no dependencies and want to build them at the same time. Each agent gets its own worktree — an isolated copy of the repo.

## Commands

| Command | What it does |
|---------|-------------|
| `purlin:worktree create` | Create a new worktree with a timestamped branch |
| `purlin:worktree list` | Show all worktrees and their status |
| `purlin:worktree cleanup-stale` | Remove worktrees whose agent has exited |

## How It Works

1. `purlin:worktree create` — creates a worktree under `.purlin/worktrees/` with its own branch
2. An agent works inside the worktree — separate spec/proof files, separate `sync_status`
3. When done, merge the branch back with standard git (`git merge`)
4. `purlin:worktree cleanup-stale` — removes the worktree directory

## Key Points

- **One agent per worktree.** Session locks prevent concurrent access.
- **Ephemeral.** Create for a task, merge and clean up when done.
- **Independent state.** Each worktree has its own proof files and `sync_status` view.
- **Stale locks auto-clear.** Session start cleans up locks from crashed sessions.
