# Feature: skill_status

> Description: What `skills/status/SKILL.md` must say. Status prints where every feature stands, or one named spec's rules, and
>   the command line and the dashboard have to show one answer from one computation.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:status`
- RULE-2: The skill prints the numbers `sync_status` returned and never recounts them, so the command line and the dashboard cannot disagree
- RULE-3: The last section of `skills/status/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/status/SKILL.md` is at most 100 lines [level: passed]
- RULE-5: `purlin:status <name>` shows one spec, its rules and their cells, and both `skills/status/SKILL.md` and `references/purlin_commands.md` name that form

## Proof

- PROOF-1 (RULE-1): Read `skills/status/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: status` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:status`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/status/SKILL.md`; verify it names `sync_status`, carries the sentence `Never recount them` and the phrase `one answer from one computation`. Deleting the never-recount sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/status/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/status/SKILL.md` and count its lines; verify the count is at most 100. Appending prose until the file passes 100 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/status/SKILL.md` with its line wrapping collapsed; verify it carries `purlin:status <name>` and the sentence `Naming a spec shows its rules and their standing.`, and that `references/purlin_commands.md` carries `purlin:status [name]`, one assertion per literal. Deleting the sentence fails naming it
