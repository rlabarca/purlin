# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must name. An anchor is a set of rules for the whole
>   project, and the skill is what creates one, pulls one from another repository and keeps its
>   pin current; this spec holds the commands and files it names and its characters.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 18
> Highest-Proof: 39

## Rules

- RULE-18: The anchor skill names the commands `purlin:anchor create`, `purlin:anchor sync`, `purlin:drift`, `purlin:spec` and `purlin:status`, and the files `scripts/purlin_python.sh`, `scripts/anchor/upstream.py`, `specs/_anchors/`, `references/formats/anchor_format.md`, `references/spec_quality_guide.md` and `references/commit_conventions.md`

## Proof

- PROOF-2 (RULE-18): The text of `skills/anchor/SKILL.md` holds each of `scripts/purlin_python.sh`, `scripts/anchor/upstream.py`, `specs/_anchors/`, `references/formats/anchor_format.md`, `references/spec_quality_guide.md` and `references/commit_conventions.md`; nothing is reported
- PROOF-16 (RULE-18): The text of `skills/anchor/SKILL.md` holds each of `purlin:anchor create`, `purlin:anchor sync`, `purlin:drift`, `purlin:spec` and `purlin:status`; nothing is reported
