# Policy: Multi-Person Collaboration

> Label: "Policy: Multi-Person Collaboration"
> Category: "Coordination & Lifecycle"

## Purpose

Multi-person collaboration in Purlin uses git worktrees (local) and lifecycle branches (remote) to allow Architect, Builder, and QA agents to work concurrently without interfering with each other. This policy defines the invariants that keep concurrent work safe and coordinated.

## 2. Collaboration Invariants

### 2.1 Branch Naming Convention

*   `spec/<feature-name>` — Architect-owned; contains spec commits
*   `impl/<feature-name>` — Builder-owned; contains implementation commits
*   `qa/<feature-name>` — QA-owned; contains verification commits
*   Branch prefix determines role assignment in CDD Collab Mode
*   Branches not matching this pattern are shown in the dashboard but are role-unlabeled

### 2.2 Merge-Before-Proceed Rule

*   Each role's phase MUST merge to `main` before the next agent role starts
*   The Critic uses `git log` without a branch specifier; it only sees commits reachable from HEAD
*   A COMPLETE status commit on a role branch is invisible to agents on other branches until merged
*   This is enforced by the handoff protocol, not by tooling (no code enforcement needed)
*   Process rule: merge to `main` → confirm status is visible → hand off to next role

### 2.3 PURLIN_PROJECT_ROOT in Worktrees

*   In a git worktree, the `.git` entry is a file (gitdir: pointer), not a directory
*   Path-climbing fallback may skip the worktree root and land on the parent repo root
*   Each agent session in a worktree MUST set `PURLIN_PROJECT_ROOT` to the worktree directory path
*   The launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) are responsible for this export
*   Without this, `features/` scanning and cache writes target the wrong root

### 2.4 Integration Moment Protocol

*   The "integration moment" is when a role branch merges to `main`
*   Who merges: the agent that completed the role's phase (before shutting down)
*   What it triggers: the next agent role's pre-flight check can now see the merged commits
*   For remote collaboration, the merge is followed by `git push origin main`
*   The handoff checklist (`/pl-handoff-check`) verifies readiness before the merge

### 2.5 Worktree Location Convention

*   Worktrees MUST live at `.worktrees/<role>-session/` relative to the project root
*   This path MUST be gitignored in the consumer project
*   The Purlin CDD tools detect worktrees at this location to activate Collab Mode
*   Worktrees are created by `setup_worktrees.sh` and are never committed to git

### 2.6 Critic Branch-Scope Limitation (Known Constraint)

*   The Critic uses `git log -1 --grep='[status tag]'` with no branch specifier
*   `git log` only searches commits reachable from HEAD
*   A status commit (TESTING or COMPLETE) on an unmerged branch is invisible to other branches
*   This is a known, documented limitation — not a bug
*   Workaround: CDD Collab Mode queries each worktree's HEAD directly using `git -C <path> log`

### 2.7 ACTIVE_EDITS.md Protocol (Multi-Architect Only)

*   Only applies when `config.json` has `"collaboration": { "multi_architect": true }`
*   When active, each Architect session MUST create `.purlin/ACTIVE_EDITS.md` on start (committed)
*   The file declares which feature files are currently being edited (one per line, with author and timestamp)
*   Other Architect sessions MUST read this file before editing and check for conflicts
*   On session end, the Architect removes their entries and commits the update
*   This file MUST NOT be gitignored — it is the coordination signal
*   For single-Architect workflows (the default), this file does not exist and is not needed

## 3. Section-Level Ownership Reference

| Section | Owner | Conflict Risk |
|---------|-------|---------------|
| `## Scenarios`, `## Visual Specification` | Architect | Low |
| `## Implementation Notes` | Builder only | Near-zero |
| `## User Testing Discoveries` | QA only | Near-zero |

Git auto-merges non-overlapping hunks. True conflicts only arise when two Architects edit the same scenario section simultaneously.

## 4. Local vs. Remote Collaboration

**Local Collaboration:** Single machine, multiple git worktrees (one per role), CDD dashboard runs at project root.

**Remote Collaboration:** Multiple machines, lifecycle branches pushed to origin, CDD Collab Mode shows remote branch status via `git branch -r`.

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are process invariants enforced by the handoff protocol and instruction files.

## Implementation Notes

This anchor node defines process invariants. There is no buildable implementation. Compliance is enforced through instruction files, handoff checklists, and git branching discipline.
