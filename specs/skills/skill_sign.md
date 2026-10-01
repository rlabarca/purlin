# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign builds the evidence package from the
>   committed evidence, walks it with a person, stopping only at hand checks, and adds their
>   sign-off over the package in a signed commit, in any project and at any time. The skill
>   names the commands and the files the agent runs and reads, keeps within its line ceiling and
>   holds no emoji.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 34
> Highest-Proof: 65

## Rules

- RULE-4: The skill gives the agent its instructions in at most 185 lines, the whole of `skills/sign/SKILL.md`
- RULE-32: The skill names the commands the agent runs or hands on: `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit`, `purlin:test --remote` and `git push origin`
- RULE-33: The skill names the files and paths the agent runs or reads: `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`
- RULE-34: The skill holds no emoji

## Proof

- PROOF-4 (RULE-4): The sign skill, counted line by line, is at most 185 lines long
- PROOF-63 (RULE-32): The sign skill's text holds each of `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit`, `purlin:test --remote` and `git push origin`, and the check of the commands it must name lists no problem
- PROOF-64 (RULE-33): The sign skill's text holds each of `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`, and the check of the paths it must name lists no problem
- PROOF-65 (RULE-34): The sign skill's text holds no character from the emoji ranges
