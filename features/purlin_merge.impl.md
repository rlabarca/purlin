## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Skill file (skills/merge/SKILL.md) and hook (scripts/hooks/merge-worktrees.sh) implement full merge protocol: merge lock, safe-file auto-resolution, breadcrumb on failure, cleanup chain. Structural tests: 47/47 PASS.
