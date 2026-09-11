# Feature: skill_status

> Scope: skills/status/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:status` skill calls the `sync_status` MCP tool and displays per-feature rule coverage and both quality gauges, with actionable directives. It reports what `sync_status` computed rather than reconstructing its own summary.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `status`, matching the directory name
- RULE-4: Skill references the `sync_status` MCP tool by name
- RULE-5: The documented feature-table sort order matches the implementation: FAILING, PARTIAL, PASSING, VERIFIED, then UNTESTED
- RULE-6: The documented feature table carries a Design and an Integrity column alongside Feature, Coverage and Status, so both quality gauges are visible per feature and not only in aggregate
- RULE-7: The skill prints the summary line that `sync_status` returns rather than composing a replacement. A reconstructed status-count line cannot carry either gauge, which is why both were absent from `purlin:status` output while the server was already computing them
- RULE-8: The skill documents gauge-driven recommendations and their remediation targets: a Design finding routes to `purlin:spec`, an Integrity WEAK or HOLLOW finding routes to `purlin:build`, and an unmeasured gauge routes to `purlin:audit`. It states that Design is addressed before Integrity, because Integrity criteria compare a test against its proof description and a vague description leaves them nothing to catch

## Proof

- PROOF-1 (RULE-1): Grep `skills/status/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/status/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `status`
- PROOF-4 (RULE-4): Grep `skills/status/SKILL.md` for `sync_status`; verify the MCP tool is referenced
- PROOF-5 (RULE-5): Grep `skills/status/SKILL.md` for the sort order; verify all five statuses are named in the implementation's order, and compare against the priority map in `_build_summary_table`
- PROOF-6 (RULE-6): Parse the feature-table code block in `skills/status/SKILL.md`; verify its header row names Feature, Coverage, Status, Design and Integrity, that the prose does not still claim the table has three columns, and that at least one sample row carries a percentage in each gauge column
- PROOF-7 (RULE-7): Grep `skills/status/SKILL.md` for a hardcoded `Summary: <N> features |` template; verify zero matches, and verify the skill instead instructs printing the summary line returned by `sync_status` verbatim
- PROOF-8 (RULE-8): Grep `skills/status/SKILL.md` for the three remediation targets; verify a Design finding maps to `purlin:spec`, an Integrity WEAK/HOLLOW finding maps to `purlin:build`, an unmeasured gauge maps to `purlin:audit`, and that Design is stated to come before Integrity with the reason given
