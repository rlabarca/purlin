## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Community tool index reading implemented in tools/toolbox/resolve.py (load_community_tools). Per-tool directory reading works.

**[GAP]** All four lifecycle operations unimplemented: `add` (clone, validate, register), `pull` (upstream check, conflict resolution), `push` (dry-run preview, version prompting, promotion), `edit` (local edit detection). No git integration for clone/push. Estimated: ~5% complete.
