# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what the specs, the tests and
>   the approvals have not caught up with, in one view per role, and it writes
>   nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/drift/SKILL.md` opens with a frontmatter block whose `name` is `drift` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:drift` [risk: medium] [origin: eng]
- RULE-2: The skill takes its data from the `drift` tool and points at `references/drift_criteria.md` for the file classification rather than restating it, and it invents no category the tool does not return [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/drift/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/drift/SKILL.md` is at most 150 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/drift/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: drift` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:drift`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/drift/SKILL.md` with its line wrapping collapsed; verify it carries the fenced call `drift(role="eng")`, the path `references/drift_criteria.md` and the instruction `do not restate them here and do not invent a category the tool does not return`, one assertion per literal so a failure names the missing one. Deleting the do-not-restate sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/drift/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/drift/SKILL.md` and count its lines; verify the count is at most 150. Appending prose until the file passes 150 lines fails, and the failure reports the count it found beside the ceiling
