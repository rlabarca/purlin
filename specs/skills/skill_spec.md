# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must name. The spec skill turns a requirement in any
>   form into rules and proofs; this spec holds the commands and files it names, its length and
>   its characters.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 31
> Highest-Proof: 61

## Rules

- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines
- RULE-14: The spec skill names the commands `sync_status`, `purlin:build` and `purlin:drift`
- RULE-29: The spec skill names the files `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`
- RULE-31: The spec skill holds no emoji

## Proof

- PROOF-4 (RULE-4): The spec skill, counted line by line, is at most 210 lines
- PROOF-28 (RULE-4): A copy of the spec skill lengthened with prose to exactly 210 lines is accepted, with nothing reported
- PROOF-43 (RULE-14): The text of `skills/spec/SKILL.md` holds each of `sync_status`, `purlin:build` and `purlin:drift`; nothing is reported
- PROOF-59 (RULE-29): The text of `skills/spec/SKILL.md` holds each of `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; nothing is reported
- PROOF-61 (RULE-31): Every character of `skills/spec/SKILL.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
