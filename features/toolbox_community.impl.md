## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Community tool index reading implemented in tools/toolbox/resolve.py (load_community_tools). Per-tool directory reading works.

**[IMPL]** Community tool lifecycle module at tools/toolbox/community.py implements all four operations: `cmd_add()` (clone, validate tool.json, normalize ID with community. prefix, check collisions, register), `cmd_pull()` (ls-remote HEAD check, local edit detection via SHA comparison, auto-update or conflict reporting), `cmd_push()` (community tool update to existing repo or project tool promotion to community with ID rename). All operations support `--dry-run`. CLI entry point with argparse. 17 unit tests in tools/toolbox/test_community.py covering add (valid, auto-prefix, missing tool.json, missing fields, collision, dry-run, invalid URL), pull (empty, not found, up-to-date, updates), push (purlin blocked, project without URL, dry-run, not found).

**[IMPL]** Edit flow handled by agent via pl-toolbox skill file (reads community tool.json, presents fields, writes back). Local edit divergence warning documented in skill file §2.6.
