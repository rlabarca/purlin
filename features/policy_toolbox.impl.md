## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Tool ID namespacing: reserved prefix check (purlin., community.) in manage.py and resolve.py. Purlin tool immutability: no write functions for purlin_tools.json. Shadowing behavior: project tool shadows purlin tool (documented in resolve.py). Forward compatibility: unrecognized fields preserved with warning. Old-format backward compatibility via schema version detection.

**[IMPL]** Community tool integrity tracking now implemented in tools/toolbox/community.py: `cmd_add()` records source_repo, version, author, last_pull_sha at registration time. `cmd_pull()` checks upstream SHA, detects local edits, preserves divergence info. `cmd_push()` updates version and last_pull_sha in registry.

**[IMPL]** Destructive operation safety: manage.py delete supports `--dry-run`. community.py add/pull/push all support `--dry-run`. The skill file (pl-toolbox.md) instructs the agent to show a preview and confirm before executing destructive operations.

**[DEVIATION]** PM ownership (§2.6): file_classification.md lists `.purlin/toolbox/*.json` as CODE (Engineer-owned), but the policy spec says PM-owned. The pl-toolbox skill file says write subcommands activate Engineer mode. Current behavior follows file_classification (Engineer writes via /pl-toolbox). PM review needed to resolve the classification conflict.
- **Severity:** LOW
- **Why:** The operational model works — Engineer writes tool registries via /pl-toolbox skill, which is the intended workflow. The policy text and file classification disagree on the formal owner label.
