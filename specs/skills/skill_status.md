# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: the commands and paths they must
>   name, their length, and no emoji.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 15
> Highest-Proof: 40

## Rules

- RULE-4: The whole of `skills/status/SKILL.md` is at most 100 lines
- RULE-13: The skill names the commands `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --remote`, `purlin:test --commit` and `purlin:sign`
- RULE-14: The skill names the paths `references/purlin_commands.md` and `skills/spec/SKILL.md`
- RULE-15: The skill holds no emoji

## Proof

- PROOF-4 (RULE-4): The status skill as shipped is at most 100 lines long
- PROOF-27 (RULE-4): A copy of the status skill made exactly 100 lines long passes the ceiling of 100
- PROOF-28 (RULE-4): A copy of the status skill made 101 lines long fails, reporting `101 lines, ceiling 100`
- PROOF-37 (RULE-13): The status skill as shipped names each of `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --remote`, `purlin:test --commit` and `purlin:sign`, and the check reports no problem
- PROOF-38 (RULE-13): A copy of the status skill with every `purlin:sign` taken out is reported with `status does not name purlin:sign`
- PROOF-39 (RULE-14): The status skill as shipped names `references/purlin_commands.md` and `skills/spec/SKILL.md`, and the check reports no problem
- PROOF-40 (RULE-15): The status skill as shipped holds no character from the emoji ranges
