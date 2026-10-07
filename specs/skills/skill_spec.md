# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must name. The spec skill turns a requirement in any
>   form into rules and proofs; this spec holds the one list of the commands and files it names.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 34
> Highest-Proof: 65

## Rules

- RULE-32: The spec skill names the commands `sync_status`, `purlin:build` and `purlin:drift`, and the files `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`
- RULE-33: The spec skill says where `> Highest-Rule:` and `> Highest-Proof:` go in a spec that has neither: after the last `>` line of the header, `> Highest-Rule:` first
- RULE-34: The spec skill shows the two tags of an AI proof with the model in each, tells the agent to ask the person which kind of check a sentence about an AI gets and which models, and never to pick a model itself

## Proof

- PROOF-62 (RULE-32): The text of `skills/spec/SKILL.md` holds each of `sync_status`, `purlin:build`, `purlin:drift`, `scripts/purlin_python.sh`, `scripts/spec/renumber.py`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; none is missing
- PROOF-63 (RULE-33): A reader of the spec skill's part headed `Ids` finds the sentence ``In a spec that has neither line, both go after the last `>` line of the header: `> Highest-Rule:` first, then `> Highest-Proof:`.``
- PROOF-64 (RULE-34): A reader of the spec skill's part headed `Proofs` finds the two lines `- PROOF-9 (RULE-9): With the sample report, the reply names the three findings by their ids @ai(claude-opus-5-5)` and `- PROOF-10 (RULE-10): Asked for a refund over the limit, the reply refuses and blames nobody @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)`
- PROOF-65 (RULE-34): That part holds the sentences `Where a sentence about what an AI does could be checked exactly, graded or by hand, **Stop and ask** which.` and `Never pick a model yourself: the model is what is being validated.`
