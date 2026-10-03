# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: the commands and paths they must name.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 19
> Highest-Proof: 46

## Rules

- RULE-16: The skill names the commands `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the paths `references/purlin_commands.md` and `skills/spec/SKILL.md`
- RULE-17: The skill says when the line `<n> features whose results are not committed` shows: only once nothing else stops the tests being met
- RULE-18: The skill's part `With a name` gives the command that prints one spec's view: a line naming `scripts/run/purlin_status.py` and `--spec <name>`
- RULE-19: The example in the skill's part `With a name` is, line for line, what `purlin_status.py --spec login` prints for `login` of 3 rules: `RULE-1`, whose test passed and which the audit found strong; `RULE-2`, which no test carries; and `RULE-3`, whose one proof is `@manual`

## Proof

- PROOF-37 (RULE-16): The status skill as shipped names each of `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the check reports no problem
- PROOF-38 (RULE-16): A copy of the status skill with every `purlin:sign` taken out is reported with `status does not name purlin:sign`
- PROOF-39 (RULE-16): The status skill as shipped names `references/purlin_commands.md` and `skills/spec/SKILL.md`, and the check reports no problem
- PROOF-41 (RULE-17): Exactly one sentence of the status skill as shipped holds both `features whose results are not committed` and `shows only once nothing else stops the tests being met`
- PROOF-42 (RULE-17): A copy of the status skill with every `shows only once nothing else stops the tests being met` taken out holds no sentence with both
- PROOF-43 (RULE-18): The status skill as shipped holds, in its part `With a name`, a line naming both `scripts/run/purlin_status.py` and `--spec <name>`
- PROOF-44 (RULE-18): A copy of the status skill with every `--spec <name>` taken out holds no such line in that part
- PROOF-45 (RULE-19): The code block of the shipped skill's part `With a name` equals, line for line, what `purlin_status.py --spec login` prints for that `login`
- PROOF-46 (RULE-19): A copy of the status skill whose example reads `PROOF-1  passed` as `PROOF-1  passing` does not equal it
