# Feature: skill_test

> Description: What `skills/test/SKILL.md` must name. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked. Its
>   hand-off is `purlin:test --all --commit`, and `purlin:test --remote` for the proofs tagged
>   for another system, whose first run writes the git host's runner.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 22
> Highest-Proof: 54

## Rules

- RULE-4: The whole of `skills/test/SKILL.md` is at most 120 lines
- RULE-5: `skills/test/SKILL.md` names the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json` and `.purlin/config.json`
- RULE-13: `skills/test/SKILL.md` names the commands `purlin:test --all --commit`, `purlin:test --remote` and `purlin:test --remote --commit-runner`
- RULE-22: `skills/test/SKILL.md` holds no emoji

## Proof

- PROOF-4 (RULE-4): The `purlin:test` skill file as shipped is at most 120 lines long; checking its length reports nothing
- PROOF-30 (RULE-4): A copy of the skill file padded with lines of prose to exactly 120 lines is not reported
- PROOF-31 (RULE-4): A copy of the skill file padded with lines of prose to 121 lines is reported as 121 lines against a ceiling of 120
- PROOF-51 (RULE-13): Checking the `purlin:test` skill file as shipped for the commands `purlin:test --all --commit`, `purlin:test --remote` and `purlin:test --remote --commit-runner` reports nothing
- PROOF-52 (RULE-13): A copy of the skill file with every `purlin:test --remote --commit-runner` taken out is reported as `test does not name purlin:test --remote --commit-runner`
- PROOF-53 (RULE-5): Checking the `purlin:test` skill file as shipped for the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json` and `.purlin/config.json` reports nothing
- PROOF-54 (RULE-22): The `purlin:test` skill file as shipped holds no emoji
