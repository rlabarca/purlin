# Gitignore Guide for Purlin Projects

> This reference documents what should be committed vs. gitignored in a Purlin consumer project.
> The single source of truth for recommended gitignore patterns is `purlin-config-sample/gitignore.purlin`.

## Committed (tracked in git)

| Path | Purpose |
|------|---------|
| `.purlin/config.json` | Shared project configuration |
| `.purlin/*_OVERRIDES.md` | Role-specific instruction overrides |
| `.purlin/HOW_WE_WORK_OVERRIDES.md` | Shared workflow overrides |
| `.purlin/release/` | Release configuration |
| `.purlin/.upstream_sha` | Pinned submodule version |
| `.purlin/delivery_plan.md` | Phased delivery coordination (read by all agents across sessions) |
| `features/*.md` | Feature specs, companion files, discovery sidecars |
| `tests/*/tests.json` | AFT test definitions |
| `pl-init.sh` | Submodule bootstrap shim |
| `pl-run-*.sh` | Agent launcher scripts (regenerated on refresh) |
| `.claude/commands/pl-*.md` | Purlin slash commands |
| `.claude/settings.json` | Claude Code hooks/settings |

## Gitignored (not tracked)

| Pattern | Purpose |
|---------|---------|
| `.purlin/cache/` | Generated artifacts: dependency graph, feature status, status cache, mermaid diagrams |
| `.purlin/runtime/` | Per-machine state: agent role, logs, PIDs, active branch, session metadata |
| `.purlin/config.local.json` | Per-developer config overrides |
| `features/digests/` | Per-machine generated digests |
| `.playwright-mcp/` | Web verification screenshots |
| `*.log` | Server and tool logs |
| `*.pid` | Process ID files |

## Why `delivery_plan.md` is committed

The delivery plan is a coordination artifact read by all agents (Engineer, QA, PM) across
sessions. It lives at `.purlin/delivery_plan.md` -- outside the gitignored `.purlin/cache/`
directory -- because it must survive `git clone` and be visible to collaborators.

Generated cache artifacts (dependency graph, feature status) are regenerated on
every `scan.sh` run and are truly ephemeral. The delivery plan is authored by Engineer mode,
reviewed by the user, and consumed by QA -- it is not regenerable.

## Template-Driven Gitignore Management

`purlin-config-sample/gitignore.purlin` is the single source of truth for recommended patterns.

- **Full init:** `init.sh` reads the template and merges patterns into the consumer's `.gitignore`.
- **Refresh mode:** `init.sh` performs an additive-only merge -- appends missing patterns without
  removing or modifying existing entries.
- **Update flow:** When a Purlin developer adds a new generated artifact, they add the pattern to
  `gitignore.purlin`. Consumers get it automatically on next `pl-init.sh` (refresh) after updating
  the Purlin submodule.

## Migration for Existing Consumer Projects

If your project has `.purlin/cache/delivery_plan.md` tracked in git (from before this change),
untrack it and move the file:

```bash
git rm --cached .purlin/cache/delivery_plan.md
mv .purlin/cache/delivery_plan.md .purlin/delivery_plan.md
git add .purlin/delivery_plan.md
git commit -m "fix: move delivery_plan.md out of gitignored cache directory"
```

## Safe to Delete

`.purlin/cache/` and `.purlin/runtime/` are always safe to delete. All contents are regenerated
on next `scan.sh` run or agent session start.
