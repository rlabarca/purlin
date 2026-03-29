# Gitignore Guide for Purlin Projects

> This reference documents what should be committed vs. gitignored in a Purlin consumer project.
> The source of truth for recommended patterns is `templates/gitignore.purlin` in the Purlin plugin.

## Committed (tracked in git)

| Path | Purpose |
|------|---------|
| `.purlin/config.json` | Shared project configuration |
| `.purlin/PURLIN_OVERRIDES.md` | Project-specific instruction overrides (all modes) |
| `.purlin/delivery_plan.md` | Phased delivery coordination (read by all agents across sessions) |
| `features/*.md` | Feature specs, companion files, discovery sidecars |
| `tests/*/tests.json` | AFT test definitions |
| `.claude/settings.json` | Claude Code hooks/settings (includes plugin enablement) |

## Gitignored (not tracked)

| Pattern | Purpose |
|---------|---------|
| `.purlin/cache/` | Generated artifacts: dependency graph, feature status, status cache |
| `.purlin/runtime/` | Per-machine state: mode, logs, PIDs, session metadata |
| `.purlin/config.local.json` | Per-developer config overrides |
| `.purlin_session.lock` | Session lock file |
| `.purlin_worktree_label` | Worktree label (e.g., W1) |
| `features/digests/` | Per-machine generated digests |
| `.playwright-mcp/` | Web verification screenshots |
| `*.log` | Server and tool logs |
| `*.pid` | Process ID files |

## Why `delivery_plan.md` is committed

The delivery plan is a coordination artifact read by all agents (Engineer, QA, PM) across
sessions. It lives at `.purlin/delivery_plan.md` -- outside the gitignored `.purlin/cache/`
directory -- because it must survive `git clone` and be visible to collaborators.

Generated cache artifacts (dependency graph, feature status) are regenerated on
every scan and are truly ephemeral. The delivery plan is authored by Engineer mode,
reviewed by the user, and consumed by QA -- it is not regenerable.

## Template-Driven Gitignore Management

`templates/gitignore.purlin` in the Purlin plugin is the source of truth for recommended patterns.

- **`purlin:init`:** Reads the template and merges patterns into the consumer's `.gitignore`.
- **Refresh:** Performs an additive-only merge -- appends missing patterns without removing or modifying existing entries.

## Safe to Delete

`.purlin/cache/` and `.purlin/runtime/` are always safe to delete. All contents are regenerated
on next scan or session start.
