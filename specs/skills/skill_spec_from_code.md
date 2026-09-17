# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must say. The skill reads a codebase that has
>   no specs and writes the rules it already implies, which is the one place a rule
>   enters the project without a person asking for it.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec-from-code/SKILL.md` opens with a frontmatter block whose `name` is `spec-from-code` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec-from-code` [risk: medium] [origin: eng]
- RULE-2: The skill calls `sync_status` before it surveys anything and sends the reader to `purlin:init` when the project carries no `.purlin/config.json` [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/spec-from-code/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines [risk: low] [origin: eng]
- RULE-5: Every rule the skill writes carries `[origin: eng]` and `[risk: low]`, and the skill forbids `[origin: pm]` and any risk above `low` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/spec-from-code/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: spec-from-code` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:spec-from-code`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/spec-from-code/SKILL.md`; verify the section that precedes the procedure names `sync_status`, `.purlin/config.json` and `purlin:init`, one assertion per literal. Deleting that section fails naming `sync_status`
- PROOF-3 (RULE-3): Read `skills/spec-from-code/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/spec-from-code/SKILL.md` and count its lines; verify the count is at most 130. Appending prose until the file passes 130 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/spec-from-code/SKILL.md`; verify every line that opens `- RULE-` carries both `[origin: eng]` and `[risk: low]`, and that the file carries the two prohibitions "Do not tag anything `[origin: pm]`" and "Do not add risk tags above `low`". Changing one example rule to `[risk: medium]` fails, printing that line
