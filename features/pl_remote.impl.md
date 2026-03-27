## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Unified skill (.claude/commands/pl-remote.md) replaces three separate skills. All subcommands (push/pull/add/branch create/join/leave/list), config reading with priority chain, sync state detection, first-push/pull safety, SSH auth flow. Old skill files deleted. Structural tests: 106/106 PASS.
