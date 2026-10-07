# Feature: skill_test

> Description: What `skills/test/SKILL.md` must name. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked. Its
>   hand-off is `purlin:test --all --commit`; for a proof tagged for another system it points at
>   the one reference that says what a project sets up.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 25
> Highest-Proof: 59

## Rules

- RULE-23: `skills/test/SKILL.md` names the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md`
- RULE-24: `skills/test/SKILL.md` gives the hand-off as the run script takes it: one line that names `scripts/run/purlin_run.py` with `--test`, `--all` and `--commit`
- RULE-25: `skills/test/SKILL.md` shows the three lines a run prints about an AI proof, and says what to do about a model that was not reached

## Proof

- PROOF-55 (RULE-23): Checking the `purlin:test` skill file as shipped for the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md` reports nothing
- PROOF-52 (RULE-23): A copy of the skill file with every `references/evidence_and_signoff.md` taken out is reported as `test does not name references/evidence_and_signoff.md`
- PROOF-56 (RULE-24): Checking the skill file as shipped for one line that holds `scripts/run/purlin_run.py`, `--test`, `--all` and `--commit` reports nothing
- PROOF-57 (RULE-24): A copy of the skill file with every `--test --all --commit` taken out is reported as `skills/test/SKILL.md has no single line carrying all of 'scripts/run/purlin_run.py', '--test', '--all', '--commit'`
- PROOF-58 (RULE-25): The text of `skills/test/SKILL.md` holds each of the lines `Running <feature> <PROOF-N> on <model>, <i> of <n>`, `<model>: model not reached. <why>. Run purlin:test --all.` and `<n> rules to test on <model>: purlin:test --all`
- PROOF-59 (RULE-25): The text of `skills/test/SKILL.md` holds the sentences ``Check that `claude` is logged in and that the proof's tag spells the model's name as the model is named, then run `purlin:test --all` again.`` and `It is never a failure: never change the code or the test for it, and never reword the proof.`
