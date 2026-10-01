# Feature: skill_test

> Description: What `skills/test/SKILL.md` must name. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked. Its
>   hand-off is `purlin:test --all --commit`; for a proof tagged for another system it points at
>   the one reference that says what a project sets up.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 23
> Highest-Proof: 55

## Rules

- RULE-23: `skills/test/SKILL.md` names the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md`

## Proof

- PROOF-55 (RULE-23): Checking the `purlin:test` skill file as shipped for the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md` reports nothing
- PROOF-52 (RULE-23): A copy of the skill file with every `references/evidence_and_signoff.md` taken out is reported as `test does not name references/evidence_and_signoff.md`
