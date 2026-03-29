## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Tool ID namespacing: reserved prefix check (purlin., community.) in manage.py and resolve.py. Purlin tool immutability: no write functions for purlin_tools.json. Shadowing behavior: project tool shadows purlin tool (documented in scripts/toolbox/resolve.py). Forward compatibility: unrecognized fields preserved with warning. Old-format backward compatibility via schema version detection.

**[IMPL]** Community tool integrity tracking now implemented in scripts/toolbox/community.py: `cmd_add()` records source_repo, version, author, last_pull_sha at registration time. `cmd_pull()` checks upstream SHA, detects local edits, preserves divergence info. `cmd_push()` updates version and last_pull_sha in registry.

**[IMPL]** Destructive operation safety: manage.py delete supports `--dry-run`. community.py add/pull/push all support `--dry-run`. The skill file (pl-toolbox.md) instructs the agent to show a preview and confirm before executing destructive operations.

**[DEVIATION]** [ACKNOWLEDGED] PM ownership (§2.6): file_classification.md lists `.purlin/toolbox/*.json` as CODE (Engineer-owned), but the policy spec said PM-owned. The pl-toolbox skill file says write subcommands activate Engineer mode. Current behavior follows file_classification (Engineer writes via purlin:toolbox).
- **Severity:** LOW
- **Resolution:** Policy spec §2.6 updated to align with file_classification.md and operational reality. Section renamed from "PM Ownership" to "Toolbox Governance". Engineer writes registries via skill; PM governs schema and policy. Source: purlin:spec-code-audit 2026-03-29.
