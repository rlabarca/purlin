# Feature: skill_status

> Description: What `skills/status/SKILL.md` must say. Status prints where every feature stands, and
>   the command line and the dashboard have to show one answer from one computation.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:status` [risk: medium] [origin: eng]
- RULE-2: The skill prints the numbers `sync_status` returned and never recounts them, so the command line and the dashboard cannot disagree [risk: high] [origin: eng]
- RULE-3: The last section of `skills/status/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/status/SKILL.md` is at most 80 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/status/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: status` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:status`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/status/SKILL.md`; verify it names `sync_status`, carries the sentence `Never recount them` and the phrase `one answer from one computation`. Deleting the never-recount sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/status/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/status/SKILL.md` and count its lines; verify the count is at most 80. Appending prose until the file passes 80 lines fails, and the failure reports the count it found beside the ceiling
