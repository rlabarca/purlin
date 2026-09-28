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

- PROOF-1 (RULE-1): The status skill opens with a frontmatter block set between two `---` lines, whose `name` reads `status` and whose `description` holds text on its own line, neither empty nor a folded `>` block spread over the lines below; the plugin's command reference names `purlin:status`
- PROOF-2 (RULE-2): The status skill names the tool `sync_status` and carries, with its line wrapping ignored, the sentence `Never recount them` and the words `one answer from one computation`; a skill missing any one of the three does not meet the rule
- PROOF-3 (RULE-3): The last section of the status skill has a heading that reads `When you are done` or names the `next step`, in any case; under it at least two outcomes are listed as list items or table rows, and at least one line gives a `→` directive. A closing section that lists one outcome, or gives no `→`, does not meet the rule
- PROOF-4 (RULE-4): Read `skills/status/SKILL.md` and count its lines; verify the count is at most 100. Appending prose until the file passes 100 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The status skill shows the form `purlin:status <name>` and says `Naming a spec shows its rules and their standing.`, with its line wrapping ignored, and the plugin's command reference lists the command as `purlin:status [name]`; the rule is not met while any one of the three is missing
