**Purlin command: Purlin agent only**
**Purlin mode: shared**

Legacy agents: This command is for the Purlin unified agent. It is not available in role-specific agent sessions.
Purlin agent: Worktree management. Available in any mode without switching.

---

## Usage

```
/pl-worktree list
/pl-worktree cleanup-stale
```

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Subcommands

### `list`

Show all worktrees with their status.

1. Run `git worktree list --porcelain` and filter entries under `.purlin/worktrees/`.
2. For each worktree, read:
   - `.purlin_worktree_label` for the label (e.g., `W1`)
   - `.purlin_session.lock` for PID, mode, and start time
3. Classify each worktree:
   - **active** — `.purlin_session.lock` exists AND `kill -0 $PID` succeeds (process is alive)
   - **stale** — `.purlin_session.lock` exists AND `kill -0 $PID` fails (process is dead)
   - **orphaned** — no `.purlin_session.lock` file
4. Display:
   ```
   Active worktrees:
     W1  Engineer  PID 12345  active    2h ago   purlin-engineer-20260325-1430
     W2  PM        PID 67890  stale     5h ago   purlin-pm-20260325-1130
     W3  QA        (no lock)  orphaned  1d ago   purlin-qa-20260324-0900
   ```
5. If no worktrees exist: "No active worktrees."

### `cleanup-stale`

Remove stale and orphaned worktrees.

1. Scan for stale and orphaned worktrees (same classification as `list`).
2. Skip active worktrees entirely.
3. For each stale/orphaned worktree:
   - Check for uncommitted work: `git -C <path> status --porcelain`
   - If uncommitted work exists: prompt — "Worktree <label> has uncommitted changes. Merge back to main, or discard?"
     - **Merge:** commit changes, merge to main (using merge lock from `/pl-merge`), clean up
     - **Discard:** remove worktree and delete branch without merging
   - If no uncommitted work: auto-remove worktree directory and delete branch
4. Report: "Cleaned up N worktrees."
