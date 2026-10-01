# Feature: skill_test

> Description: What `skills/test/SKILL.md` must name. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked. Its
>   hand-off is `purlin:test --all --commit`, and `purlin:test --remote` for the proofs tagged
>   for another system, whose first run writes the git host's runner.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 23
> Highest-Proof: 55

## Rules

- RULE-23: `skills/test/SKILL.md` names the commands `purlin:test --all --commit`, `purlin:test --remote` and `purlin:test --remote --commit-runner`, and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json` and `.purlin/config.json`

## Proof

- PROOF-55 (RULE-23): Checking the `purlin:test` skill file as shipped for the commands `purlin:test --all --commit`, `purlin:test --remote` and `purlin:test --remote --commit-runner` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json` and `.purlin/config.json` reports nothing
- PROOF-52 (RULE-23): A copy of the skill file with every `purlin:test --remote --commit-runner` taken out is reported as `test does not name purlin:test --remote --commit-runner`
