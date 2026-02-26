# Implementation Notes: Workflow Handoff Checklist

These notes cover the handoff checklist infrastructure and the four skills that use it (`/pl-local-push`, `/pl-local-pull`, `/pl-collab-push`, `/pl-collab-pull`). Notes were originally colocated in a single combined feature file and preserved here during the split into separate skill specs.

## Handoff Infrastructure

*   **resolve.py changes:** Added `checklist_type` parameter. `checklist_type="handoff"` routes to `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`. The `roles` field is removed from the step schema — all handoff steps apply universally.
*   **run.py import strategy:** `resolve.py` is imported from the framework's `tools/release/` directory (sibling path relative to `tools/handoff/`), not from the project root. Explicit `global_path`, `local_path`, `config_path` are computed from the `--project-root` argument and passed to `resolve_checklist()`.
*   **Step evaluation:** Steps with a `code` field are auto-evaluated via `subprocess.run()` with 30s timeout. Steps without `code` are reported as PENDING.
*   **No role inference:** The previous `infer_role_from_branch()` function and `--role` CLI flag are removed. `run.sh` has no role argument.

## /pl-local-push

*   **`--ff-only` rationale:** Fast-forward only merge prevents accidental merge commits on `main`. If the branch cannot be fast-forwarded, the agent must rebase first.
*   **DIVERGED early block:** When both N (behind) and M (ahead) are nonzero, push is blocked before the checklist runs. The agent must run `/pl-local-pull` to rebase and resolve conflicts, then retry `/pl-local-push`.
*   **PROJECT_ROOT detection:** `/pl-local-push` uses `PURLIN_PROJECT_ROOT` if set, falls back to `git worktree list --porcelain` to locate the main checkout path.

## /pl-local-pull

*   **Rebase-not-merge:** Both `/pl-local-pull` and the BEHIND auto-rebase in `/pl-local-push` use `git rebase main` instead of `git merge main`. A merge commit on the worktree branch makes `--ff-only` fail; a rebase produces linear history.
*   **Per-file conflict context:** When `/pl-local-pull` hits a rebase conflict, it shows commits from each side that touched the conflicting file (using `git log HEAD..main -- <file>` and `git log main..ORIG_HEAD -- <file>`).
*   **Post-rebase command re-sync:** After a successful rebase, extra command files restored by git are deleted and marked with `git update-index --skip-worktree` to keep the working tree clean. This addresses the prior bug where deleting all `.claude/commands/` left 21 unstaged deletion entries in `git status`. The `--skip-worktree` flag survives across sessions and does not affect what is committed to the branch.
*   **Physical command placement:** `pl-local-push.md` and `pl-local-pull.md` are placed in the worktree's `.claude/commands/` by `create_isolation.sh`. They are NOT present in the project root's `.claude/commands/`. This ensures the commands are only discoverable inside a worktree session. No runtime guard is needed.
*   **[RESOLVED BUG 2026-02-24]** `purlin.handoff.critic_report` step had `"code": null`, causing permanent PENDING/FAIL on every `/pl-local-push`. Fixed: step now evaluates `CRITIC_REPORT.md` freshness against last git commit timestamp.

## Shared History

*   **Command rename (pl-work-* -> pl-local-*):** When `agent_launchers_multiuser` was retired, `/pl-work-push` and `/pl-work-pull` were renamed to `/pl-local-push` and `/pl-local-pull`. Both `BUILDER_BASE.md` and `QA_BASE.md` were updated (commit `ba68a76`) to reflect the new names in the startup command table, shutdown protocol, and authorized slash commands sections.
