# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: the commands and paths they must name.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 21
> Highest-Proof: 49

## Rules

- RULE-16: The skill names the commands `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the paths `references/purlin_commands.md` and `skills/spec/SKILL.md`
- RULE-17: The skill says when the line `<n> features whose results are not committed` shows: only once nothing else stops the tests being met
- RULE-18: The skill's part `With a name` gives the command that prints one spec's view: a line naming `scripts/run/purlin_status.py` and `--spec <name>`
- RULE-19: The example in the skill's part `With a name` is, line for line, what `purlin_status.py --spec login` prints for `login` of 3 rules: `RULE-1`, whose test passed and which the audit found strong; `RULE-2`, which no test carries; and `RULE-3`, whose one proof is `@manual`
- RULE-20: The second example in the skill's part `With a name` is, line for line, what `purlin_status.py --spec login` prints for `login` of 2 rules whose `PROOF-2` is an AI proof naming `claude-opus-5-5` and `claude-sonnet-5-5`, passed 3 of 3 on the first and not run on the second
- RULE-21: The skill shows the summary with its count of graded rules, and gives the next step for the line `<n> rules to test on <model>`

## Proof

- PROOF-37 (RULE-16): The status skill as shipped names each of `purlin:status`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --commit` and `purlin:sign`, and the check reports no problem
- PROOF-38 (RULE-16): A copy of the status skill with every `purlin:sign` taken out is reported with `status does not name purlin:sign`
- PROOF-39 (RULE-16): The status skill as shipped names `references/purlin_commands.md` and `skills/spec/SKILL.md`, and the check reports no problem
- PROOF-41 (RULE-17): Exactly one sentence of the status skill as shipped holds both `features whose results are not committed` and `shows only once nothing else stops the tests being met`
- PROOF-42 (RULE-17): A copy of the status skill with every `shows only once nothing else stops the tests being met` taken out holds no sentence with both
- PROOF-43 (RULE-18): The status skill as shipped holds, in its part `With a name`, a line naming both `scripts/run/purlin_status.py` and `--spec <name>`
- PROOF-44 (RULE-18): A copy of the status skill with every `--spec <name>` taken out holds no such line in that part
- PROOF-45 (RULE-19): The first code block that names no language in the shipped skill's part `With a name` equals, line for line, what `purlin_status.py --spec login` prints for that `login`
- PROOF-46 (RULE-19): A copy of the status skill whose example reads `PROOF-1  passed` as `PROOF-1  passing` does not equal it
- PROOF-47 (RULE-20): The second code block that names no language in the shipped skill's part `With a name` equals, line for line, what `purlin_status.py --spec login` prints for that `login`
- PROOF-48 (RULE-20): A copy of the status skill whose second example reads `0 of 3 on claude-sonnet-5-5` as `1 of 3 on claude-sonnet-5-5` does not equal it
- PROOF-49 (RULE-21): The status skill as shipped holds the line `40 rules. 40 pass their tests, 6 of them graded by an AI.` and one table row that holds both `<n> rules to test on <model>` and `→ Run: purlin:test --all`
