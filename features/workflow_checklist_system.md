# Feature: Workflow Handoff Checklist

> Label: "Tool: Workflow Handoff Checklist"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/release_checklist_core.md

[TODO]

## 1. Overview

The Workflow Handoff Checklist system provides a generic pre-merge checklist that agents run before completing their isolation session and merging their branch to `main`. It is architecturally parallel to the Release Checklist system, reusing the same step schema and resolver infrastructure. Agents invoke `/pl-local-push` to run the checklist and merge in one step.

The commands `/pl-local-push` and `/pl-local-pull` are physically placed ONLY in the worktree's `.claude/commands/` directory (by `create_isolation.sh`). They are not present in the project root's `.claude/commands/` directory. This physical placement enforces that the commands are only available inside an isolated worktree session — there is no need for a runtime "are we in a worktree" guard.

No role is assumed. The checklist steps are generic and apply equally to any agent (Architect, Builder, QA) running in any named isolation.

## 2. Requirements

### 2.1 Step Schema

The handoff step schema is identical to the release checklist step schema. The `roles` field is removed — all steps apply to all agents:

```json
{
  "id": "purlin.handoff.git_clean",
  "friendly_name": "Git Working Directory Clean",
  "description": "No uncommitted changes in the worktree",
  "code": "git diff --exit-code && git diff --cached --exit-code",
  "agent_instructions": "Run git status. If any files are staged or modified, commit or stash them before proceeding."
}
```

### 2.2 File Structure

```
tools/handoff/
  global_steps.json          ← framework handoff steps (generic, no role filtering)
  run.sh                     ← CLI entry point
.purlin/handoff/
  local_steps.json           ← project-specific handoff steps (optional)
  config.json                ← ordering + enable/disable
```

### 2.3 Resolver Reuse

`tools/release/resolve.py` is used to resolve steps. A `checklist_type` parameter routes to the correct file paths:

*   `checklist_type="handoff"` → reads `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`
*   `checklist_type="release"` → current behavior (unchanged)

No logic changes to `resolve.py` are required — only path routing based on the new parameter.

### 2.4 CLI Interface

`tools/handoff/run.sh`

Behavior:

1. Reads `PURLIN_PROJECT_ROOT` to find `.purlin/handoff/config.json`
2. Resolves the ordered, enabled step list via `resolve.py`
3. For each step: displays the step name + `agent_instructions`; auto-evaluates the `code` field if present; reports PASS/FAIL; presents items requiring human judgment as prompts
4. On completion, prints a summary: N passed, M pending
5. If any item is FAIL or PENDING, exits with code 1; if all pass, exits with code 0

### 2.5 Handoff Steps (global_steps.json)

*   `purlin.handoff.git_clean` — working directory has no uncommitted changes (excludes `.purlin/`)
*   `purlin.handoff.critic_report` — Critic report is current (run `tools/cdd/status.sh`)

### 2.6 Slash Commands

**`/pl-local-push`** (available only inside an isolated worktree; file placed by `create_isolation.sh`):

1. Pre-flight sync check: computes N (behind) and M (ahead):
   - **BEHIND (N>0, M=0):** Auto-rebases onto main (fast-forward, no conflict risk) before running checklist
   - **DIVERGED (N>0, M>0):** Blocks immediately — prints the incoming main commits and instructs the agent to run `/pl-local-pull` first; does NOT proceed to the handoff checklist
2. Runs `tools/handoff/run.sh`
3. If ALL steps PASS: merges the current branch into `main` using `git merge --ff-only <current-branch>` from the project root
4. If any steps FAIL or PENDING: prints the list of issues and does NOT merge
5. Safety check: verifies the main checkout (`PROJECT_ROOT`) is on `main` before merging; aborts with a clear error if not
6. Does NOT push to remote — that remains a separate explicit user action

**`/pl-local-pull`** (available only inside an isolated worktree; file placed by `create_isolation.sh`):

1. Checks that the working tree is clean; aborts with message "Commit or stash changes before pulling" if dirty
2. Computes N (commits behind main) and M (commits ahead of main); prints both counts and a state label: SAME / AHEAD / BEHIND / DIVERGED
3. Dispatches on state:
   - **SAME:** Already up to date. Stop.
   - **AHEAD:** Nothing to pull. Prints "N commits ahead, nothing to pull. Run /pl-local-push when ready." Stop.
   - **BEHIND:** Runs `git rebase main` (fast-forward — no conflict risk). Reports commits incorporated.
   - **DIVERGED:** Prints a pre-rebase context report (`git log HEAD..main --stat --oneline`) showing all commits coming in from main with per-file stats. Runs `git rebase main`. On success reports the branch is now AHEAD by M commits.
4. On rebase conflict: for each conflicting file prints the commits from main that touched it, the commits from the worktree branch that touched it, and a resolution hint (`features/` → Architect priority; `tests/` → preserve passing tests; other → review carefully). Ends with instructions to `git add` and `git rebase --continue`, or `git rebase --abort` to abandon.
5. **Post-Rebase Command Re-Sync:** After a successful rebase (BEHIND or DIVERGED states), re-apply the isolation command file setup:
   a. For each file in `.claude/commands/` that is NOT `pl-local-push.md` or `pl-local-pull.md`: delete the file from disk, then run `git update-index --skip-worktree .claude/commands/<file>`. This marks the deletion as intentional so git does not report it as a dirty working tree.
   b. Ensure `pl-local-push.md` and `pl-local-pull.md` are present in `.claude/commands/` (copy from project root if missing).
   c. This step is skipped for SAME and AHEAD states (no rebase occurs).
6. Use case: agent wants updated specs or code from main without pushing own work first

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Handoff CLI Passes When All Auto-Steps Pass

    Given the current worktree is on branch isolated/feat1
    And the working directory is clean
    And the critic report is current
    When run.sh is invoked
    Then the CLI exits with code 0
    And prints a summary with all steps PASS

#### Scenario: Handoff CLI Exits 1 When Any Step Fails

    Given the working directory has uncommitted changes
    When run.sh is invoked
    Then the CLI exits with code 1
    And reports the failing step (purlin.handoff.git_clean) as FAIL

#### Scenario: pl-local-push Merges Branch When All Checks Pass

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch main
    When /pl-local-push is invoked
    Then git merge --ff-only isolated/feat1 is executed from PROJECT_ROOT
    And the command succeeds

#### Scenario: pl-local-push Blocks Merge When Handoff Checks Fail

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 1
    When /pl-local-push is invoked
    Then the failing items are printed
    And no merge is executed

#### Scenario: pl-local-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-local-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git rebase is executed

#### Scenario: pl-local-pull Rebases Main Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And main has 3 new commits not in the worktree branch
    And the worktree branch has no commits not in main
    When /pl-local-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase main is executed
    And the output reports 3 new commits incorporated

#### Scenario: pl-local-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in main
    And main has 3 commits not in the worktree branch
    When /pl-local-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits from main with file stats
    And git rebase main is executed
    And on success the branch is AHEAD of main by 2 commits

#### Scenario: pl-local-pull Reports Per-File Commit Context On Conflict

    Given /pl-local-pull is invoked and git rebase main halts with a conflict on features/foo.md
    When the conflict is reported
    Then the output includes commits from main that touched features/foo.md
    And the output includes commits from the worktree branch that touched features/foo.md
    And a resolution hint is shown for features/ files
    And the output includes instructions to git add and git rebase --continue or git rebase --abort

#### Scenario: pl-local-push Blocks When Branch Is DIVERGED

    Given the current worktree branch has commits not in main
    And main has commits not in the worktree branch
    When /pl-local-push is invoked
    Then the command prints the DIVERGED state and lists incoming main commits
    And the handoff checklist is NOT run
    And no merge is executed
    And the agent is instructed to run /pl-local-pull first

#### Scenario: pl-local-pull Re-Syncs Command Files After Rebase

    Given the current worktree is clean
    And main has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains pl-local-push.md, pl-local-pull.md, and pl-status.md (restored by rebase)
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And .claude/commands/pl-status.md is deleted from the worktree
    And .claude/commands/pl-local-push.md and pl-local-pull.md still exist
    And .claude/commands/ at the project root is unaffected

#### Scenario: Post-Rebase Sync Leaves Working Tree Clean

    Given the current worktree is clean
    And main has 1 new commit not in the worktree branch
    And rebase restores extra command files to .claude/commands/ in the worktree
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And git status --porcelain reports no file changes in the worktree
    And .claude/commands/ in the worktree contains only pl-local-push.md and pl-local-pull.md

#### Scenario: pl-local-pull Does Not Fail When Extra Command Files Are Already Absent

    Given the current worktree is clean
    And main has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains only pl-local-push.md and pl-local-pull.md (no extra files)
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And no error is raised

### Manual Scenarios

None. All scenarios for this feature are fully automated.

## 4. Implementation Notes

The handoff checklist system reuses the resolver infrastructure from the release checklist. The key design principle is that handoff checklists are generic (the same steps for all agents and session types), while the release checklist is comprehensive (all steps, including QA and release-specific). Consumer projects MAY add project-specific steps via `.purlin/handoff/local_steps.json` using the same schema.

*   **resolve.py changes:** Added `checklist_type` parameter. `checklist_type="handoff"` routes to `tools/handoff/global_steps.json` and `.purlin/handoff/local_steps.json`. The `roles` field is removed from the step schema — all handoff steps apply universally.
*   **run.py import strategy:** `resolve.py` is imported from the framework's `tools/release/` directory (sibling path relative to `tools/handoff/`), not from the project root. Explicit `global_path`, `local_path`, `config_path` are computed from the `--project-root` argument and passed to `resolve_checklist()`.
*   **Step evaluation:** Steps with a `code` field are auto-evaluated via `subprocess.run()` with 30s timeout. Steps without `code` are reported as PENDING.
*   **No role inference:** The previous `infer_role_from_branch()` function and `--role` CLI flag are removed. `run.sh` has no role argument.
*   **`--ff-only` rationale:** Fast-forward only merge prevents accidental merge commits on `main`. If the branch cannot be fast-forwarded, the agent must rebase first.
*   **Rebase-not-merge:** Both `/pl-local-pull` and the BEHIND auto-rebase in `/pl-local-push` use `git rebase main` instead of `git merge main`. A merge commit on the worktree branch makes `--ff-only` fail; a rebase produces linear history.
*   **DIVERGED early block in `/pl-local-push`:** When both N (behind) and M (ahead) are nonzero, push is blocked before the checklist runs. The agent must run `/pl-local-pull` to rebase and resolve conflicts, then retry `/pl-local-push`.
*   **Per-file conflict context:** When `/pl-local-pull` hits a rebase conflict, it shows commits from each side that touched the conflicting file (using `git log HEAD..main -- <file>` and `git log main..ORIG_HEAD -- <file>`).
*   **Post-rebase command re-sync:** After a successful rebase, extra command files restored by git are deleted and marked with `git update-index --skip-worktree` to keep the working tree clean. This addresses the prior bug where deleting all `.claude/commands/` left 21 unstaged deletion entries in `git status`. The `--skip-worktree` flag survives across sessions and does not affect what is committed to the branch.
*   **Physical command placement:** `pl-local-push.md` and `pl-local-pull.md` are placed in the worktree's `.claude/commands/` by `create_isolation.sh`. They are NOT present in the project root's `.claude/commands/`. This ensures the commands are only discoverable inside a worktree session. No runtime guard is needed.
*   **PROJECT_ROOT detection:** `/pl-local-push` uses `PURLIN_PROJECT_ROOT` if set, falls back to `git worktree list --porcelain` to locate the main checkout path.
