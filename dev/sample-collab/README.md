# Sample: Multi-Role Concurrent Collaboration

This sample project demonstrates Purlin's multi-role concurrent collaboration workflow using git worktrees. Three agents — Architect, Builder, and QA — work on the same feature set from isolated worktrees, merging back to `main` at each handoff.

The application itself is a minimal Task Manager API with CRUD and filtering features. The implementation is intentionally simple; the purpose is to show the Purlin workflow, not to build production software.

---

## Prerequisites

- Git (with worktree support; Git 2.5+)
- Claude CLI (`claude`)
- Purlin submodule initialized (see Quick Start)

---

## Quick Start

**1. Clone the sample repo and enter the project directory.**

```bash
git clone <your-repo-url>
cd sample-collab
```

**2. Initialize the Purlin submodule.**

```bash
git submodule update --init
```

**3. Create worktrees for a feature.**

```bash
bash setup_worktrees.sh --feature task-crud
```

This creates three worktrees under `.worktrees/`:

| Worktree path | Role |
|---|---|
| `.worktrees/architect-session/` | Architect |
| `.worktrees/builder-session/` | Builder |
| `.worktrees/qa-session/` | QA |

**4. Open three terminals, one per role.**

Each terminal sets `PURLIN_PROJECT_ROOT` to its worktree and starts a Claude session with the appropriate role instructions.

**5. Monitor progress from the project root.**

```bash
# From the project root (not a worktree)
claude   # then run /pl-dashboard
```

---

## Workflow Overview

The collaboration follows a strict handoff sequence per feature:

```
Architect (spec branch)
  --> merge to main
    --> Builder (impl branch)
          --> merge to main
            --> QA (verify branch)
                  --> merge to main
```

1. **Architect** writes or refines the feature spec, commits it on a spec branch, and opens a PR to `main`. Once merged, Builder can begin.
2. **Builder** pulls `main` into its worktree, implements the feature and automated tests, and commits with a `[Ready for Verification]` tag. After merging to `main`, QA can begin.
3. **QA** pulls `main`, runs `/pl-handoff-check`, confirms tests pass, and merges the verification branch. The feature is complete.

Roles work concurrently when their dependencies allow. For example, Builder can work on `task_crud` while Architect is speccing `task_filtering`, as long as Builder's prerequisite spec is already merged.

---

## Directory Structure

```
sample-collab/
  .purlin/                        # Project-specific Purlin overrides
    HOW_WE_WORK_OVERRIDES.md      # Workflow additions for this sample
    ARCHITECT_OVERRIDES.md        # Architect scope restrictions
    BUILDER_OVERRIDES.md          # Builder tech stack and pre-flight rules
    QA_OVERRIDES.md               # QA verification scope
  features/                       # Feature specs (owned by Architect)
    arch_data_schema.md           # Anchor: canonical Task data model
    task_crud.md                  # Feature: Task CRUD REST API
    task_filtering.md             # Feature: Task filtering via query params
  README.md                       # This file
```

The `src/` and `tests/` directories are created by the Builder session and are not present in the template.

---

## Notes

- This is a template and demonstration project. The `src/` implementation and `tests/` directories are intentionally absent — they are left for the Builder session to create.
- In-memory storage is used throughout. Do not add database persistence; it is out of scope for this sample.
- Keep the feature set to the three specs provided. The Architect Overrides (`ARCHITECT_OVERRIDES.md`) enforce this constraint explicitly.
