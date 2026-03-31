# Terminal Identity Protocol

## Unified Format

`(<context>) <label>` — e.g., `(main) purlin`, `(dev/0.8.6) building webhook_delivery`, `(W1) verifying auth`.

**Context:** Worktree label (from `.purlin_worktree_label`) if present, otherwise branch via `git rev-parse --abbrev-ref HEAD`. Context MUST always be present.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<label>"
```

## When Identity Is Set

Terminal identity is a **session-level concern**, not a per-skill concern. It is set in two places:

1. **Session start** — via `purlin:resume` (Step 3) or the SessionStart hook. Label defaults to the project name.
2. **Manual override** — via `purlin:session-name <label>` when the user wants a different label.

Individual skills (build, spec, verify, etc.) do NOT update terminal identity. This avoids wasting context tokens on cosmetic updates during every skill invocation.

The `purlin:merge` skill resets identity after a worktree merge (the context changes from worktree to source branch).
