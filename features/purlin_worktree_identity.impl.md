# Implementation Notes: Purlin Worktree Identity

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (none) | | | |

## Notes

**[CLARIFICATION]** Most of this feature was originally implemented in the retired shell launcher during the Phase 2 worktree concurrency work: label assignment with gap-filling, label file persistence, badge format without "Purlin:" prefix, and `--name` CLI argument. Worktree identity is now handled by `purlin:start --worktree`. The implementation gap was the terminal title format — `set_agent_identity` set both title and badge to the same text, but the spec requires title = `<project> - <badge>`. (Severity: INFO)

**[CLARIFICATION]** The `set_agent_identity` function was updated to accept an optional second `project` parameter. When provided, the title is formatted as `<project> - <text>`. When omitted, the title equals the text (backward compatible with all legacy launchers). (Severity: INFO)

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 13 total, 13 passed
- AP scan: clean
- Date: 2026-03-25
