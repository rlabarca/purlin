# Worktree Guide

How to run multiple Purlin agents in parallel using isolated git worktrees, and how work gets merged back.

---

## Worktree Lifecycle

Worktrees follow the **ephemeral by default, resumable when needed** model:

- A worktree is created for a task and cleaned up when the task merges.
- On session exit, pending work is auto-committed and merged. If the merge succeeds, the worktree is gone.
- If the merge fails (conflict) or the session crashes, the worktree is preserved and a breadcrumb is written.
- A new session can **resume** a preserved worktree to continue the work.
- At most **one live agent** may occupy a worktree at any time.

---

## Launching a Worktree Agent

Add `--worktree` to any `purlin:resume` invocation:

```
# Build in a worktree
purlin:resume --worktree --build

# Verify in a worktree
purlin:resume --worktree --verify
```

Each `--worktree` launch creates an isolated copy of the repository under `.purlin/worktrees/` with a timestamped branch. The agent works entirely inside this copy — it cannot modify the main working directory.

---

## Resuming a Worktree

If a previous session ended without merging (crash, context clear, or merge conflict), the worktree is preserved. Resume it from a new session:

```
# Resume by label
purlin:resume --resume W1

# Or: startup detects stale worktrees and offers resume/merge/discard
purlin:resume
```

Resuming updates the session lock with the new PID — no merge attempt, no cleanup. You pick up where you left off. The next session exit handles the merge as usual.

**Concurrent access protection:** If the worktree is already owned by a live agent (PID alive), resume is rejected. One agent at a time.

---

## Terminal Identity

Worktree agents get a distinct terminal badge so you can tell which terminal is which:

```
purlin(W1)     # first worktree
purlin(W2)     # second worktree
purlin(W3)     # third worktree
```

The main session shows its branch: `purlin(main)`. Worktrees include their label.

---

## Session Locks

Each worktree writes a `.purlin_session.lock` file containing the PID, mode, timestamp, and label. This lock establishes ownership — one agent per worktree. It's used for liveness detection (`kill -0 $PID`) and is deleted after a successful merge.

---

## Merging Work Back

### 1. Normal Exit (Automatic)

When the session ends, the **SessionEnd hook** fires automatically:

1. Auto-commits pending changes (tracked and untracked files).
2. Merges the worktree branch back to the source branch.
3. Removes the worktree and deletes the branch.

You don't need to do anything.

### 2. Manual Merge with `purlin:merge`

Invoke `purlin:merge` while in a worktree to merge back explicitly. Useful when you've finished and want to merge before ending the session.

### 3. Crash or Conflict (Worktree Preserved)

If the merge fails (conflicts), the hook:

1. Aborts the merge attempt.
2. Preserves the worktree — no work lost.
3. Writes a breadcrumb to `.purlin/cache/merge_pending/<branch>.json`.
4. Sets the terminal badge to `MERGE FAILED`.
5. Prints a prominent warning to stderr.

The hook always exits cleanly — it never blocks shutdown.

---

## Recovering from Failed Merges

The next `purlin:resume` picks up failed merges automatically, before scan and mode activation:

1. Displays each pending merge with branch name, age, and worktree path.
2. Attempts to merge each one.
3. If conflicts remain: shows the files and offers LLM-assisted resolution or lets you defer.

Deferred merges show a warning banner for the rest of the session.

---

## Merge Conflict Handling

- **Safe files** (`.purlin/work_plan.md`, `.purlin/cache/*`) are auto-resolved by keeping main's version.
- **Code and spec files** are presented to you for resolution.
- Concurrent merges are serialized via `.purlin/cache/merge.lock` to prevent races. Stale locks (dead PIDs) are cleaned up automatically.

---

## Managing Worktrees

```
purlin:worktree list
```

Shows all worktrees with status:

```
Worktrees:
  W1  Engineer  PID 12345  active    2h ago   purlin-engineer-20260325-1430
  W2  PM        (dead)     stale     5h ago   purlin-pm-20260325-1130
```

- **active** — agent is running (PID alive)
- **stale** — agent exited without merging (PID dead)
- **orphaned** — old worktree with no session lock

To clean up stale worktrees that are no longer needed:

```
purlin:worktree cleanup-stale              # Remove stale worktrees
purlin:worktree cleanup-stale --dry-run    # Preview what would be cleaned
```

Worktrees with uncommitted changes prompt for merge or discard.

---

## Automatic Parallel Builds

You don't need to manually launch worktrees for parallel feature building. When a delivery plan has 2+ independent features in the same phase, `purlin:build` spawns worktree sub-agents automatically. Each sub-agent implements its feature in isolation, and branches merge back sequentially when done.

See the [Parallel Execution Guide](parallel-execution-guide.md) for the full delivery plan workflow.
