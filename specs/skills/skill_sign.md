# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign builds the evidence package from the
>   committed evidence, walks it with a person, stopping only at hand checks, and adds their
>   sign-off over the package in a signed commit, in any project and at any time. The skill
>   names the commands and the files the agent runs and reads.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 35
> Highest-Proof: 65

## Rules

- RULE-35: The skill names the commands and files the agent runs, reads or hands on: `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit`, `purlin:test --remote`, `git push origin`, `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`

## Proof

- PROOF-63 (RULE-35): The sign skill's text holds each of `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit`, `purlin:test --remote` and `git push origin`, and the check of the commands it must name lists no problem
- PROOF-64 (RULE-35): The sign skill's text holds each of `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`, and the check of the paths it must name lists no problem
