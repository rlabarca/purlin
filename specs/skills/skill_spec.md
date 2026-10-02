# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must name. The spec skill turns a requirement in any
>   form into rules and proofs; this spec holds the one list of the commands and files it names.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 33
> Highest-Proof: 63

## Rules

- RULE-32: The spec skill names the commands `sync_status`, `purlin:build` and `purlin:drift`, and the files `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`
- RULE-33: The spec skill says where `> Highest-Rule:` and `> Highest-Proof:` go in a spec that has neither: after the last `>` line of the header, `> Highest-Rule:` first

## Proof

- PROOF-62 (RULE-32): The text of `skills/spec/SKILL.md` holds each of `sync_status`, `purlin:build`, `purlin:drift`, `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; none is missing
- PROOF-63 (RULE-33): A reader of the spec skill's part headed `Ids` finds the sentence ``In a spec that has neither line, both go after the last `>` line of the header: `> Highest-Rule:` first, then `> Highest-Proof:`.``
