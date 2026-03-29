# Terminal Identity Protocol

## Unified Format

`<short_mode>(<context>) | <label>` — e.g., `Eng(main) | add auth flow`, `QA(dev/0.8.6) | verify login`.

**Mode shortening:** `Engineer`/`engineer` -> `Eng`; `PM`/`pm`, `QA`/`qa` unchanged; `none`/empty -> `Purlin`.

**Context:** Worktree label (from `.purlin_worktree_label`) if present, otherwise branch via `git rev-parse --abbrev-ref HEAD`. Context MUST always be present.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<label>"
```

## When to Update the Label

| Event | Label |
|-------|-------|
| Mode activation (no specific task yet) | Project name |
| **Starting work on a feature** (implementing, spec authoring, verifying, auditing, testing) | Short task description (3-4 words) derived from the feature name or topic |
| Switching to a different feature | New task description |
| Phase transition in delivery plan | `Phase N/M: <task>` |
| Completing a feature / returning to idle | Project name |

**The task label rule is mandatory.** Whenever you begin focused work on a feature — whether via `purlin:build`, via the resume work plan, via user instruction, or via auto-start — update the terminal identity with a short description of what you're doing. Do NOT leave the label as the project name while actively working on a feature. The user has multiple terminals and needs to see at a glance what each one is doing.
