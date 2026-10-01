# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: the commands and paths they must name.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 16
> Highest-Proof: 40

## Rules

- RULE-16: The skill names the commands `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the paths `references/purlin_commands.md` and `skills/spec/SKILL.md`

## Proof

- PROOF-37 (RULE-16): The status skill as shipped names each of `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the check reports no problem
- PROOF-38 (RULE-16): A copy of the status skill with every `purlin:sign` taken out is reported with `status does not name purlin:sign`
- PROOF-39 (RULE-16): The status skill as shipped names `references/purlin_commands.md` and `skills/spec/SKILL.md`, and the check reports no problem
