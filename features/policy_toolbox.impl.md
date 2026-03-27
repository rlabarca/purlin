## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Tool ID namespacing: reserved prefix check (purlin., community.) in manage.py and resolve.py. Purlin tool immutability: no write functions for purlin_tools.json. Shadowing behavior: project tool shadows purlin tool (documented in resolve.py). Forward compatibility: unrecognized fields preserved with warning. Old-format backward compatibility via schema version detection.

**[GAP]** PM ownership not enforced (no mode guards prevent Engineer from modifying .purlin/toolbox/ directly). Community tool integrity tracking (source_repo, version, author) not implemented — depends on toolbox_community. Destructive operation safety (dry-run + confirm for delete/push/pull) not implemented — depends on missing pl_toolbox subcommands. Estimated: ~50% complete.
