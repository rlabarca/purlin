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
- RULE-6: The documented feature table carries a Design and an Integrity column alongside Feature, Coverage and Status, so both quality gauges are visible per feature and not only in aggregate. Its sample carries one row whose status token ends in `*` and, under the box, the one legend line `sync_status` prints for that marker, with the prose stating that the marker means proved here and awaiting a declared platform and that the legend is printed verbatim and omitted when no row carries it. A sample with no marked row would leave a reader meeting `PASSING*` for the first time with nowhere to look it up
- RULE-7: The skill prints the summary line that `sync_status` returns rather than composing a replacement. A reconstructed status-count line cannot carry either gauge, which is why both were absent from `purlin:status` output while the server was already computing them
- RULE-8: The skill documents gauge-driven recommendations and their remediation targets: a Design finding routes to `purlin:spec`, an Integrity WEAK or HOLLOW finding routes to `purlin:build`, and an unmeasured gauge routes to `purlin:audit`. It states that Design is addressed before Integrity, because Integrity criteria compare a test against its proof description and a vague description leaves them nothing to catch
- RULE-9: The skill documents a step that prints the `Platforms (host: <id>):` line `sync_status` returns, verbatim and in the position it was returned, directly under the summary line, and prints nothing in its place when the line is absent. It states that the line is not to be expanded into a block and that no figure in it is recomputed, for the reason RULE-7 gives about the summary line: two surfaces computing one figure is how they come to disagree, and a project declaring no platform has no platform standing to report
- RULE-10: The skill's Status Definitions table defines AWAITING RUNNER: a proof declaring a platform that has no result here, which warns and never blocks, does not count against coverage, and holds an otherwise complete feature at `PASSING*` rather than VERIFIED until a runner proves that platform. Its Step 3b table carries a row routing `PASSING*` or an awaiting platform to `purlin:test`. Without both, the marker and the status word appear in output the skill never explains, and a reader has no directive for the one state in the vocabulary that is neither a failure nor a gap in the tests

## Proof

- PROOF-1 (RULE-1): Grep `skills/status/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/status/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `status`
- PROOF-4 (RULE-4): Grep `skills/status/SKILL.md` for `sync_status`; verify the MCP tool is referenced
- PROOF-5 (RULE-5): Grep `skills/status/SKILL.md` for the sort order; verify all five statuses are named in the implementation's order, and compare against the priority map in `_build_summary_table`
- PROOF-6 (RULE-6): Parse the feature-table code block in `skills/status/SKILL.md`; verify its header row names Feature, Coverage, Status, Design and Integrity, that the prose does not still claim the table has three columns, and that at least one sample row carries a percentage in each gauge column
- PROOF-7 (RULE-7): Grep `skills/status/SKILL.md` for a hardcoded `Summary: <N> features |` template; verify zero matches, and verify the skill instead instructs printing the summary line returned by `sync_status` verbatim
- PROOF-8 (RULE-8): Grep `skills/status/SKILL.md` for the three remediation targets; verify a Design finding maps to `purlin:spec`, an Integrity WEAK/HOLLOW finding maps to `purlin:build`, an unmeasured gauge maps to `purlin:audit`, and that Design is stated to come before Integrity with the reason given
- PROOF-9 (RULE-9): Parse `skills/status/SKILL.md` and assert it contains exactly one step whose heading names the Platforms line, that the step's body contains the literal `Platforms (host: ` inside a fenced code block, the word `verbatim`, and a statement that nothing is printed in its place when the line is absent; assert the step forbids expanding the line into a block and forbids recomputing its figures, and that the sample line carries a ` | ` segment separator and a ` (host)` marker so the grammar a reader copies is the one `sync_status` RULE-57 emits
- PROOF-10 (RULE-10): Parse the Status Definitions table of `skills/status/SKILL.md` and assert it carries an `AWAITING RUNNER` row whose text names `PASSING*`, says it warns and never blocks, and names `purlin:test` as what closes it; parse the Step 3b directive table and assert it carries a row whose first cell names `PASSING*` and whose directive cell names `purlin:test`. Assert no row of either table claims an awaiting platform fails or blocks anything
