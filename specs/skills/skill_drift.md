# Feature: skill_drift

> Scope: skills/drift/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:drift` skill detects spec drift by calling the `drift` MCP tool and summarizing changes since last verification, cross-referenced with specs. It produces PM/QA/eng-readable reports.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `drift`, matching the directory name
- RULE-4: Skill references the `drift` MCP tool by name
- RULE-5: Skill requires reading git diffs for behavioral changes, not just interpreting MCP categories
- RULE-6: The classification step states that CHANGED_SPECS does not imply the code is out of sync, and requires checking whether the spec's `> Scope:` files exist before describing spec edits as drift — a project authored spec-first produces that category on every run
- RULE-7: Every field of the `drift` response that the analysis steps read is declared in Step 1's response-shape list. Step 2a reads `since`, Step 2d reads `rule_details`, `drift_flags` and `broken_scopes`, and the anchor step reads `external_anchor_drift`, so a field named only where it is consumed leaves the agent parsing a shape the skill never described

## Proof

- PROOF-1 (RULE-1): Grep `skills/drift/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/drift/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `drift`
- PROOF-4 (RULE-4): Grep `skills/drift/SKILL.md` for `drift`; verify the MCP tool is referenced
- PROOF-5 (RULE-5): Grep `skills/drift/SKILL.md` for `git diff`; verify the diff-reading requirement is present
- PROOF-6 (RULE-6): Grep `skills/drift/SKILL.md` for the CHANGED_SPECS caveat; verify it requires checking whether the scope files exist and routes to `purlin:build` rather than reporting a mismatch when they do not
- PROOF-7 (RULE-7): Collect the backticked field tokens of the response-shape list in Step 1 of `skills/drift/SKILL.md` (at least seven bullet heads, plus the nested field names declared inside a bullet), and the backticked tokens the analysis steps (Step 2 through Step 2e, the anchor-drift step included) name as a `field` or an `array` of the tool output; verify the second set is non-empty, contains `rule_details` and `external_anchor_drift`, and is a subset of the first. Deleting `rule_details` from the Step 1 list fails the proof and names it
