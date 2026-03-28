# Worktree Guide

How to run multiple Purlin agents in parallel using isolated git worktrees, and how work gets merged back.

---

## Launching a Worktree Agent

Add `--worktree` to any `purlin:start` invocation:

```
# Engineer in a worktree
purlin:start --worktree --mode engineer

# QA in a worktree
purlin:start --worktree --mode qa

# Auto-build in a worktree
purlin:start --worktree --build
```

Each `--worktree` launch creates an isolated copy of the repository under `.purlin/worktrees/` with a branch named `purlin-<mode>-<YYYYMMDD>-<HHMMSS>`. The agent works entirely inside this copy — it cannot modify the main working directory.

---

## Terminal Identity

Worktree agents get a distinct terminal badge so you can tell which terminal is which. Instead of the branch name, the badge shows a worktree label:

```
Engineer (W1)      # first worktree
QA (W2)            # second worktree
PM (W3)            # third worktree
```

The main session keeps its normal badge (e.g., `Engineer (main)`). If you have multiple terminals open, the badge tells you at a glance which is the main session and which are worktrees.

Mode switches within a worktree update the mode part of the badge but keep the worktree label: `Engineer (W1)` becomes `PM (W1)`.

---

## Session Locks

Each worktree writes a `.purlin_session.lock` file on creation containing the PID, mode, timestamp, and label. This lock establishes ownership — one agent per worktree. It's used for liveness detection (is the agent still running?) and is deleted automatically after a successful merge.

---

## Merging Work Back

Worktree branches need to merge back to the source branch (usually `main`). There are three ways this happens:

### 1. Normal Exit

When the agent session ends normally, the **SessionEnd hook** (`tools/hooks/merge-worktrees.sh`) fires automatically. It:

1. Auto-commits any pending changes (tracked and untracked files).
2. Merges the worktree branch back to the source branch.
3. Removes the worktree directory and deletes the branch.
4. Deletes the session lock.

You don't need to do anything — the hook handles it.

### 2. Manual Merge with `/pl-merge`

While a worktree agent is still running, invoke `/pl-merge` to merge back explicitly. This is useful when you've finished your work and want to merge before ending the session. It commits pending work, merges, and cleans up the worktree.

### 3. Forced Exit or Crash (Ctrl+C)

The SessionEnd hook also fires on Ctrl+C exits. It follows the same auto-commit and merge flow. If the merge succeeds, everything is cleaned up normally.

If the merge **fails** (conflicts with changes on the source branch), the hook:

1. Aborts the merge attempt.
2. Preserves the worktree so no work is lost.
3. Writes a breadcrumb file to `.purlin/cache/merge_pending/<branch>.json`.
4. Sets the terminal badge to `MERGE FAILED` so the dead terminal tab visually signals the problem.
5. Prints a prominent warning to stderr.

The hook always exits cleanly — it never blocks the agent from shutting down.

---

## Recovering from Failed Merges

If a merge fails (from a crash or conflict), the next Purlin session picks it up automatically. On startup, `/pl-resume` checks for merge breadcrumbs before doing anything else:

1. Displays each pending merge with branch name, age, and worktree path.
2. Attempts to merge each one.
3. If the merge succeeds: cleans up the worktree, branch, and breadcrumb.
4. If conflicts remain: shows the conflicting files and offers LLM-assisted resolution or lets you defer.

Deferred merges show a warning banner for the rest of the session. The breadcrumb persists until the merge is resolved.

You can also trigger recovery manually at any time:

```
/pl-resume merge-recovery
```

---

## Merge Conflict Handling

When conflicts occur during merge:

- **Safe files** (`.purlin/delivery_plan.md`, `.purlin/cache/*`) are auto-resolved by keeping the main branch's version.
- **Code and spec files** are presented to you for resolution.

If two worktrees try to merge at the same time, merges are serialized via `.purlin/cache/merge.lock` to prevent race conditions.

---

## Managing Worktrees

Use `/pl-worktree` to see what's running:

```
/pl-worktree list
```

This shows all worktrees with their status:

```
Active worktrees:
  W1  Engineer  PID 12345  active    2h ago   purlin-engineer-20260325-1430
  W2  PM        PID 67890  stale     5h ago   purlin-pm-20260325-1130
  W3  QA        (no lock)  orphaned  1d ago   purlin-qa-20260324-0900
```

- **active** — agent is still running (PID alive)
- **stale** — agent exited without merging (PID dead, lock file remains)
- **orphaned** — old worktree with no session lock

To clean up stale and orphaned worktrees:

```
/pl-worktree cleanup-stale
```

This removes worktrees whose agent has exited. If a stale worktree has uncommitted changes, you're prompted to merge or discard.

---

## Automatic Parallel Builds

You don't need to manually launch worktrees for parallel feature building. When a delivery plan has 2+ independent features in the same phase, `/pl-build` spawns worktree sub-agents automatically. Each sub-agent implements its feature in isolation, and branches merge back sequentially when done.

See the [Parallel Execution Guide](parallel-execution-guide.md) for the full delivery plan workflow.
