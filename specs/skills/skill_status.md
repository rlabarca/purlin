# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: the commands and paths they must name.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 17
> Highest-Proof: 42

## Rules

- RULE-16: The skill names the commands `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the paths `references/purlin_commands.md` and `skills/spec/SKILL.md`
- RULE-17: The skill says when the line `<n> features whose results are not committed` shows: only once nothing else stops the tests being met

## Proof

- PROOF-37 (RULE-16): The status skill as shipped names each of `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the check reports no problem
- PROOF-38 (RULE-16): A copy of the status skill with every `purlin:sign` taken out is reported with `status does not name purlin:sign`
- PROOF-39 (RULE-16): The status skill as shipped names `references/purlin_commands.md` and `skills/spec/SKILL.md`, and the check reports no problem
- PROOF-41 (RULE-17): Exactly one sentence of the status skill as shipped holds both `features whose results are not committed` and `shows only once nothing else stops the tests being met`
- PROOF-42 (RULE-17): A copy of the status skill with every `shows only once nothing else stops the tests being met` taken out holds no sentence with both
