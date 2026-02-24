# Feature: Isolated Teams

> Label: "Tool: Isolated Teams"
> Category: "Install, Update & Scripts"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

Isolated Teams provides a flexible, named worktree system where any agent or combination of agents can run in any number of user-named isolated workspaces. A single call to `create_isolation.sh <name>` creates one isolated team: a git worktree at `.worktrees/<name>/` on branch `isolated/<name>`. Each isolated team is independent — it has its own branch, its own `.purlin/` state, and its own view of `features/`. Multiple simultaneous isolated teams are fully supported.

This replaces the rigid three-role setup of the retired `agent_launchers_multiuser.md`. No role assignment is assumed or enforced — the name is the identifier.

---

## 2. Requirements

### 2.1 Name Validation

- Names MUST be 1–12 characters.
- Names MUST match the pattern `[a-zA-Z0-9_-]+` (alphanumeric, hyphen, underscore; no spaces, no dots, no slashes).
- Names are case-sensitive. `Feat1` and `feat1` are distinct isolations.
- Validation is enforced by both `create_isolation.sh` and `kill_isolation.sh`.

### 2.2 create_isolation.sh

- **Location:** `tools/collab/create_isolation.sh`
- **Invocation:** `tools/collab/create_isolation.sh <name>`
- **Purpose:** Creates a single named git worktree isolated team.

**Behavior:**

1. Validate `<name>` against the name validation rules (Section 2.1). Exit with code 1 and a clear error message if invalid.
2. Accept an optional `--project-root <path>` argument; defaults to CWD.
3. Check that `.worktrees/` is gitignored; if not, warn and exit with code 1.
4. Create branch `isolated/<name>` and worktree at `.worktrees/<name>/` from the current HEAD of `main`.
5. **Idempotency:** If `.worktrees/<name>/` already exists, print a status message and exit cleanly (code 0). Do not create duplicate worktrees or branches.
6. **Command file setup:**
   a. Ensure `.worktrees/<name>/.claude/commands/` exists (create if absent).
   b. Copy `pl-local-push.md` and `pl-local-pull.md` from the project root's `.claude/commands/` into the worktree's `.claude/commands/`.
   c. Delete all OTHER files from the worktree's `.claude/commands/` (any file that is NOT `pl-local-push.md` or `pl-local-pull.md`).
   d. Net result: the worktree's `.claude/commands/` contains ONLY `pl-local-push.md` and `pl-local-pull.md`. All other `/pl-*` commands are discovered via directory tree climbing from the parent repo.
7. **Config propagation:** After `git worktree add` completes, copy the live project root `.purlin/config.json` into the new worktree's `.purlin/config.json`, overwriting the git-committed copy. If the live config does not exist, the git-committed copy is used as-is. After copying, run `git update-index --skip-worktree .purlin/config.json` inside the worktree so that any session-local modifications to the config are never reported as dirty by `git status` and cannot be accidentally committed. Print a note: `"Note: .purlin/config.json is marked skip-worktree. Use /pl-agent-config to make persistent changes."`.
8. **Config is ephemeral by design:** The worktree config is a snapshot of the MAIN config at creation time. It diverges from MAIN over the session's lifetime (e.g., agents may change settings locally). It is destroyed when `kill_isolation.sh` removes the worktree. To make a persistent config change from a worktree, use `/pl-agent-config`, which always routes changes to the MAIN config.
9. Print a summary of what was created and next-steps instructions.

### 2.3 kill_isolation.sh

- **Location:** `tools/collab/kill_isolation.sh`
- **Invocation:** `tools/collab/kill_isolation.sh <name> [--dry-run] [--force]`
- **Purpose:** Safely remove a named isolation worktree.

**Safety conditions (two distinct levels):**

**HARD BLOCK — uncommitted/staged changes (dirty state):**

- Detected via: `git -C .worktrees/<name> status --porcelain`, excluding `.purlin/` files.
- These changes would be permanently lost if the worktree is removed.
- Script exits with code 1, lists the dirty files, and instructs the user to commit or stash first.
- Only bypassed with `--force`.

**WARN + ALLOW — commits not yet merged to `main` (unsynced):**

- Detected via: `git -C .worktrees/<name> log main..HEAD --oneline` returns commits.
- The commits are NOT at risk — removing a worktree does not delete its branch. The branch `isolated/<name>` survives and can be re-added with `git worktree add`.
- Script prints a warning listing the unmerged branch and its commit count, then proceeds without user input.
- The dashboard Kill modal surfaces this warning with an "I understand, the branch still exists" checkbox before enabling Confirm.

**Behavior sequence:**

1. Validate `<name>` and verify `.worktrees/<name>/` exists; exit with code 1 if not found.
2. Check dirty (hard block), then unsynced (soft warn).
3. If dirty and `--force` is not set: exit code 1, list files, instruct user to commit/stash first.
4. If unsynced (but not dirty, or `--force` is set): list branch + commit count with a warning, then proceed.
5. Delete the three generated launcher scripts from `$PROJECT_ROOT/` if they exist: `run_<name>_architect.sh`, `run_<name>_builder.sh`, `run_<name>_qa.sh`.
6. Remove the worktree: `git worktree remove .worktrees/<name>`.
7. Remove the `isolated/<name>` branch: `git branch -d isolated/<name>` (skip if unsynced commits exist — branch has unmerged work).
8. Remove `.worktrees/` directory if now empty.

**Flags:**

- `--force`: Bypasses the HARD BLOCK dirty check. The unsynced branch warning is still shown, and the branch is NOT deleted (it still has unmerged commits).
- `--dry-run`: Reports safety status as JSON without removing anything. Used by the dashboard Kill modal.
- `--project-root <path>`: Defaults to CWD.

**Dry-run JSON output schema:**

```json
{
  "name": "<name>",
  "dirty": false,
  "dirty_files": [],
  "unsynced": true,
  "unsynced_branch": "isolated/<name>",
  "unsynced_commits": 3
}
```

### 2.6 Per-Team Launcher Scripts

When `create_isolation.sh <name>` succeeds, it MUST generate three scripts in `$PROJECT_ROOT/`:
- `run_<name>_architect.sh`
- `run_<name>_builder.sh`
- `run_<name>_qa.sh`

**Script contract:**
- Each script MUST `cd` into the worktree directory and then `exec` the corresponding launcher: `cd "$WORKTREE_PATH" && exec "$WORKTREE_PATH/run_<role>.sh" "$@"`.
- **Why `cd` is required:** The agent startup protocol runs `git rev-parse --abbrev-ref HEAD` to detect whether it is in an isolated session. Git resolves the branch from the process's working directory. Without `cd`, the process inherits the caller's CWD (project root, on `main` branch), causing `git rev-parse` to return `main` instead of `isolated/<name>` — suppressing `/pl-local-push` and `/pl-local-pull` from the startup command print.
- Each script sets `PURLIN_PROJECT_ROOT` indirectly: `exec` replaces the wrapper subshell with the worktree's launcher, which sets `PURLIN_PROJECT_ROOT="$SCRIPT_DIR"` (resolved to the worktree path via `dirname "${BASH_SOURCE[0]}"`). No explicit `PURLIN_PROJECT_ROOT` override is needed.
- **CWD preservation (user's shell):** The `cd` inside the generated script does NOT change the user's interactive shell working directory. Because `exec` replaces only the child subshell (not the user's interactive shell), the user's working directory at the project root is preserved after the agent exits. A comment in each generated script MUST document this guarantee.
- If the worktree does not exist at execution time, the script exits with code 1 and a descriptive error message.
- Generated scripts MUST NOT be tracked by git. `.gitignore` MUST contain patterns `run_*_architect.sh`, `run_*_builder.sh`, `run_*_qa.sh`.

**On kill:** `kill_isolation.sh <name>` MUST delete these three scripts (if they exist) from `$PROJECT_ROOT/` as part of its cleanup sequence, before removing the worktree.

**Idempotency:** If the scripts already exist (e.g., from a prior interrupted run), overwrite them silently.

### 2.4 Worktree Isolation Invariants

- Each worktree has its own `.purlin/cache/` and `.purlin/runtime/` (generated, gitignored).
- Each worktree has its own `CRITIC_REPORT.md` (generated, gitignored).
- `features/` content differs per worktree (different branch checkouts).
- `tests/` content differs per worktree.
- The only shared state between worktrees is the git object database (commits, branches).
- Multiple simultaneous named isolations are fully supported. Creating "ui" while "feat1" exists does not affect "feat1".

### 2.5 PURLIN_PROJECT_ROOT in Worktrees

The standard launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) already export `PURLIN_PROJECT_ROOT="$SCRIPT_DIR"`. When run from within a worktree, `$SCRIPT_DIR` resolves to the worktree directory — which is the correct value. No modification to the launcher scripts is required.

**Verification:** A worktree launched with `PURLIN_PROJECT_ROOT` set to the worktree path will:

- Scan `features/` relative to the worktree (sees the worktree's branch checkout of features/).
- Write `.purlin/cache/` and `.purlin/runtime/` relative to the worktree (isolated from other sessions).
- Write `CRITIC_REPORT.md` to the worktree root (isolated).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: create_isolation Creates Named Worktree

    Given the project root has no worktree at .worktrees/feat1/
    And .worktrees/ is gitignored
    When create_isolation.sh feat1 is run
    Then .worktrees/feat1/ is created on branch isolated/feat1
    And the branch starts from the same HEAD as main

#### Scenario: create_isolation Is Idempotent

    Given .worktrees/feat1/ already exists on branch isolated/feat1
    When create_isolation.sh feat1 is run again
    Then the script prints a status message and exits with code 0
    And no duplicate worktree or branch is created

#### Scenario: create_isolation Rejects Name Longer Than 12 Characters

    Given the name "toolongname123" (14 characters)
    When create_isolation.sh toolongname123 is run
    Then the script exits with code 1
    And the output describes the name validation rule (max 12 chars)

#### Scenario: create_isolation Rejects Name With Invalid Characters

    Given the name "bad.name" (contains a dot)
    When create_isolation.sh "bad.name" is run
    Then the script exits with code 1
    And the output describes the name validation rule (alphanumeric, hyphen, underscore only)

#### Scenario: create_isolation Places Only pl-local Commands in Worktree

    Given the project root .claude/commands/ contains pl-local-push.md, pl-local-pull.md, and pl-status.md
    When create_isolation.sh ui is run
    Then .worktrees/ui/.claude/commands/pl-local-push.md exists
    And .worktrees/ui/.claude/commands/pl-local-pull.md exists
    And .worktrees/ui/.claude/commands/pl-status.md does not exist
    And .claude/commands/ at the project root still contains all command files

#### Scenario: create_isolation Propagates Live Config

    Given the project root .purlin/config.json has startup_sequence true for the builder role
    And the git-committed .purlin/config.json has startup_sequence false for the builder role
    When create_isolation.sh worker is run
    Then .worktrees/worker/.purlin/config.json has startup_sequence true for the builder role
    And the value matches the live project root config, not the git-committed version

#### Scenario: Multiple Simultaneous Isolations Are Supported

    Given .worktrees/feat1/ exists on branch isolated/feat1
    When create_isolation.sh ui is run
    Then .worktrees/ui/ is created on branch isolated/ui
    And .worktrees/feat1/ is unaffected

#### Scenario: kill_isolation Blocks When Worktree Has Uncommitted Changes

    Given .worktrees/feat1/ exists and has uncommitted file changes (excluding .purlin/)
    When kill_isolation.sh feat1 is run without --force
    Then the script exits with code 1
    And the output lists the dirty files
    And the worktree is not removed

#### Scenario: kill_isolation Force Removes Dirty Worktree

    Given .worktrees/feat1/ exists and has uncommitted file changes
    When kill_isolation.sh feat1 is run with --force
    Then the worktree at .worktrees/feat1/ is removed

#### Scenario: kill_isolation Proceeds with Warning When Branch Has Unmerged Commits

    Given .worktrees/feat1/ exists with 3 commits not yet merged to main
    And the worktree has no uncommitted changes
    When kill_isolation.sh feat1 is run
    Then the script prints a warning listing the unmerged branch and commit count
    And the worktree is removed
    And the isolated/feat1 branch still exists in the git repository

#### Scenario: kill_isolation Dry Run Returns JSON Safety Report

    Given .worktrees/feat1/ exists with uncommitted changes and 2 unmerged commits
    When kill_isolation.sh feat1 --dry-run is run
    Then the script exits without removing anything
    And the output is valid JSON matching the dry-run schema
    And dirty is true and dirty_files lists the uncommitted files
    And unsynced is true and unsynced_commits is 2

#### Scenario: kill_isolation Exits When Worktree Not Found

    Given no worktree exists at .worktrees/missing/
    When kill_isolation.sh missing is run
    Then the script exits with code 1
    And the output reports that the isolation was not found

#### Scenario: PURLIN_PROJECT_ROOT Resolves to Worktree Path

    Given the user runs run_architect.sh from .worktrees/feat1/
    When the launcher script executes
    Then PURLIN_PROJECT_ROOT is exported as the absolute path of .worktrees/feat1/
    And features/ scanning targets the worktree's features/ directory
    And .purlin/cache/ writes target the worktree's .purlin/cache/

#### Scenario: create_isolation Generates All Three Launcher Scripts

    Given create_isolation.sh feat1 is run successfully
    Then run_feat1_architect.sh exists at $PROJECT_ROOT/ and is executable
    And run_feat1_builder.sh exists at $PROJECT_ROOT/ and is executable
    And run_feat1_qa.sh exists at $PROJECT_ROOT/ and is executable

#### Scenario: Generated Launcher Scripts cd Into Worktree Before Exec

    Given create_isolation.sh feat1 is run successfully
    When run_feat1_architect.sh is inspected
    Then it contains: cd "$WORKTREE_PATH"
    And it contains: exec "$WORKTREE_PATH/run_architect.sh" "$@"

#### Scenario: Generated Launcher Scripts Delegate to Correct Worktree Launcher Per Role

    Given create_isolation.sh feat1 is run successfully
    Then run_feat1_architect.sh delegates to .worktrees/feat1/run_architect.sh
    And run_feat1_builder.sh delegates to .worktrees/feat1/run_builder.sh
    And run_feat1_qa.sh delegates to .worktrees/feat1/run_qa.sh

#### Scenario: kill_isolation Removes All Three Launcher Scripts

    Given .worktrees/feat1/ exists and run_feat1_architect.sh, run_feat1_builder.sh, run_feat1_qa.sh exist at $PROJECT_ROOT/
    When kill_isolation.sh feat1 is run
    Then run_feat1_architect.sh no longer exists at $PROJECT_ROOT/
    And run_feat1_builder.sh no longer exists at $PROJECT_ROOT/
    And run_feat1_qa.sh no longer exists at $PROJECT_ROOT/

#### Scenario: Launcher Scripts Are Not Modified on Idempotent Create

    Given .worktrees/feat1/ already exists
    And run_feat1_architect.sh already exists at $PROJECT_ROOT/ with known content
    When create_isolation.sh feat1 is run again
    Then the script exits with code 0
    And run_feat1_architect.sh still has the same content as before

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Implementation Notes

The `create_isolation.sh` approach avoids modifying the main checkout during setup. The branch is created from `HEAD` of `main`. The key insight: when a launcher script does `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)`, running from within a worktree makes `$SCRIPT_DIR` the worktree root — which is exactly what `PURLIN_PROJECT_ROOT` should be.

**Command file placement (inverted from legacy):** The old `setup_worktrees.sh` deleted `.claude/commands/` entirely from each worktree, relying on tree climbing to find all commands in the parent repo. The new design places ONLY `pl-local-push.md` and `pl-local-pull.md` in the worktree's `.claude/commands/`. This ensures:

1. The worktree-exclusive commands (pl-local-push and pl-local-pull) are present and take precedence over any parent-repo versions.
2. All other commands (pl-status, pl-spec, etc.) are still discoverable via tree climbing.
3. No duplicate command completions appear in the Claude Code UI.

**`.purlin/` exclusion from dirty detection:** The kill script excludes `.purlin/` files from dirty detection — the same pattern as the retired `teardown_worktrees.sh`. Auto-propagated `config.json` changes must not trigger false dirty blocks.

**Dry-run JSON:** The `--dry-run` flag outputs structured JSON consumed by the dashboard Kill modal. The schema is scoped to a single named worktree (unlike the old teardown, which covered all three worktrees simultaneously).

**`.worktrees/` detection:** The `.worktrees/` directory convention is required for the CDD Isolated Teams dashboard to detect active isolated teams. The dashboard uses `git worktree list --porcelain` and filters to paths under `.worktrees/` relative to the project root.

**Per-team launcher scripts:** `create_isolation.sh` generates `run_<name>_architect.sh`, `run_<name>_builder.sh`, and `run_<name>_qa.sh` in `$PROJECT_ROOT/` using `cd "$WORKTREE_PATH" && exec` to delegate to the corresponding launchers inside the worktree. The `cd` before `exec` is required so the agent process inherits the worktree as its working directory — without it, `git rev-parse --abbrev-ref HEAD` returns `main` (the caller's CWD) instead of `isolated/<name>`, suppressing the `/pl-local-push`/`/pl-local-pull` commands in the startup print. `PURLIN_PROJECT_ROOT` is still resolved correctly by the worktree's own launcher (`SCRIPT_DIR` → worktree path via `dirname "${BASH_SOURCE[0]}"`). The user's interactive shell working directory is preserved because `exec` replaces only the child subshell, not the interactive shell. These scripts are gitignored and removed by `kill_isolation.sh` before worktree removal.

---

## User Testing Discoveries

**[BUG] OPEN — Generated launcher scripts do not cd into worktree before exec** (Severity: HIGH)
- **Observed:** Running `./run_<team>_architect.sh` from the project root does not print `/pl-local-push` and `/pl-local-pull` in the Architect startup command table. Running the same session by cd-ing into the worktree and running `./run_architect.sh` directly does show them.
- **Root cause:** The generated scripts delegate via `exec` without first `cd`-ing into the worktree. Claude inherits the caller's CWD (project root, branch `main`), so `git rev-parse --abbrev-ref HEAD` returns `main` instead of `isolated/<name>`, causing the startup protocol to skip the isolation command table variant.
- **Fix required (Builder):** In `tools/collab/create_isolation.sh`, change the generated script's delegation line from `exec "$WORKTREE_PATH/run_${ROLE}.sh" "$@"` to `cd "$WORKTREE_PATH" && exec "$WORKTREE_PATH/run_${ROLE}.sh" "$@"`. The `cd` occurs in the child subshell; `exec` replaces it — the user's interactive shell CWD is unaffected.
- **Spec updated:** Section 2.6 now mandates `cd` before `exec` and explains why.
