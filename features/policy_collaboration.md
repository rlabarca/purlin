# Policy: Isolated Agent Collaboration

> Label: "Policy: Isolated Agent Collaboration"
> Category: "Coordination & Lifecycle"

## Purpose

Purlin uses named git worktrees (local isolations) to allow any number of agent sessions to work concurrently without interfering with each other. Each isolation is a user-named, independent workspace on a dedicated branch. This policy defines the invariants that keep concurrent work safe and coordinated.

## 2. Collaboration Invariants

### 2.1 Isolation Naming Convention

*   Isolation names MUST be 1–12 characters.
*   Names MUST match `[a-zA-Z0-9_-]+` (alphanumeric, hyphen, underscore; no spaces).
*   Branch naming: `isolated/<name>` — e.g., `isolated/feat1`, `isolated/ui`.
*   Worktree path: `.worktrees/<name>/` relative to the project root.
*   No role assignment is associated with the name. Any agent type may use any isolation name.

### 2.2 Merge-Before-Proceed Rule

*   Each isolation MUST merge to `main` before another session that depends on its changes can start or continue.
*   The Critic uses `git log` without a branch specifier; it only sees commits reachable from HEAD.
*   A COMPLETE status commit on an unmerged isolation branch is invisible to agents on other branches until merged.
*   This is enforced by the handoff protocol, not by tooling (no code enforcement needed).
*   Process rule: merge to `main` → confirm status is visible → hand off to next agent.

### 2.3 PURLIN_PROJECT_ROOT in Worktrees

*   In a git worktree, the `.git` entry is a file (gitdir: pointer), not a directory.
*   Path-climbing fallback may skip the worktree root and land on the parent repo root.
*   Each agent session in a worktree MUST set `PURLIN_PROJECT_ROOT` to the worktree directory path.
*   The launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) are responsible for this export.
*   Without this, `features/` scanning and cache writes target the wrong root.

### 2.4 Integration Moment Protocol

*   The "integration moment" is when an isolation branch merges to `main`.
*   Who merges: the agent that completed the session's work (before shutting down).
*   What it triggers: the next agent that needs the merged work can now see the commits.
*   For remote collaboration, the merge is followed by `git push origin main`.
*   `/pl-local-push` verifies readiness and performs the merge in one step.

### 2.5 Worktree Location Convention

*   Worktrees MUST live at `.worktrees/<name>/` relative to the project root.
*   This path MUST be gitignored in the consumer project.
*   The Purlin CDD tools detect worktrees at `.worktrees/` to activate Isolated Agents Mode.
*   Worktrees are created by `create_isolation.sh` and are never committed to git.

### 2.6 ff-only Merge Invariant

*   All merges from isolation branches to `main` use `git merge --ff-only`.
*   If the branch cannot be fast-forwarded (DIVERGED state), the agent must rebase first via `/pl-local-pull`.
*   This prevents merge commits on `main` and keeps history linear.

### 2.7 .purlin/ Exclusion from Dirty Detection

*   `.purlin/` files are excluded from dirty detection in all isolation scripts and commands.
*   Auto-propagated `config.json` changes must not trigger false dirty blocks.
*   This applies in `kill_isolation.sh`, `/pl-local-push`, and any other dirty check in the collab toolchain.

### 2.8 Critic Branch-Scope Limitation (Known Constraint)

*   The Critic uses `git log -1 --grep='[status tag]'` with no branch specifier.
*   `git log` only searches commits reachable from HEAD.
*   A status commit (TESTING or COMPLETE) on an unmerged isolation branch is invisible to other branches.
*   This is a known, documented limitation — not a bug.
*   Workaround: CDD Isolated Agents Mode queries each worktree's HEAD directly using `git -C <path> log`.

### 2.10 Canonical Isolation Detection

The authoritative method for detecting an isolated session is the current branch name:

```
git rev-parse --abbrev-ref HEAD
```

If the result starts with `isolated/`, the session is isolated. The isolation name is the substring after `isolated/`.

This check is preferred over environment variable checks (`PURLIN_PROJECT_ROOT`) and `.git` file pointer tests because:
*   It works regardless of whether `PURLIN_PROJECT_ROOT` is set.
*   It does not depend on launcher script behavior.
*   It is semantically unambiguous: the branch name directly encodes isolation state.

**Application:** Use this check in:
*   Startup print sequences — to determine which table variant to display.
*   Command guards — to abort commands that are only valid inside isolated sessions.
*   Worktree detection steps — as the primary check; the `.git` file pointer test (`test -f "$PURLIN_PROJECT_ROOT/.git"`) is a valid secondary confirmation when `PURLIN_PROJECT_ROOT` is set.

### 2.9 ACTIVE_EDITS.md Protocol (Multi-Architect Only)

*   Only applies when `config.json` has `"collaboration": { "multi_architect": true }`.
*   When active, each Architect session MUST create `.purlin/ACTIVE_EDITS.md` on start (committed).
*   The file declares which feature files are currently being edited (one per line, with author and timestamp).
*   Other Architect sessions MUST read this file before editing and check for conflicts.
*   On session end, the Architect removes their entries and commits the update.
*   This file MUST NOT be gitignored — it is the coordination signal.
*   For single-Architect workflows (the default), this file does not exist and is not needed.

## 3. Section-Level Ownership Reference

| Section | Owner | Conflict Risk |
|---------|-------|---------------|
| `## Scenarios`, `## Visual Specification` | Architect | Low |
| `## Implementation Notes` | Builder only | Near-zero |
| `## User Testing Discoveries` | QA only | Near-zero |

Git auto-merges non-overlapping hunks. True conflicts only arise when two Architects edit the same scenario section simultaneously.

## 4. Local vs. Remote Collaboration

**Local Isolation:** Single machine, multiple named git worktrees, CDD dashboard runs at project root.

**Remote Collaboration:** Multiple machines, lifecycle branches pushed to origin, CDD Isolated Agents Mode shows remote branch status via `git branch -r`.

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are process invariants enforced by the handoff protocol and instruction files.

## Implementation Notes

This anchor node defines process invariants. There is no buildable implementation. Compliance is enforced through instruction files, handoff checklists, and git branching discipline.
