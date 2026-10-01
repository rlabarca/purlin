# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must name. An anchor is a set of rules for the whole
>   project, and the skill is what creates one, pulls one from another repository and keeps its
>   pin current; this spec holds the commands and files it names, its length and its characters.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 17
> Highest-Proof: 39

## Rules

- RULE-2: The anchor skill names the files `scripts/purlin_python.sh`, `scripts/anchor/upstream.py`, `specs/_anchors/`, `references/formats/anchor_format.md`, `references/spec_quality_guide.md` and `references/commit_conventions.md`
- RULE-4: The whole of `skills/anchor/SKILL.md` is at most 160 lines
- RULE-9: The anchor skill names the commands `purlin:anchor create`, `purlin:anchor sync`, `purlin:drift`, `purlin:spec` and `purlin:status`
- RULE-17: The anchor skill holds no emoji

## Proof

- PROOF-2 (RULE-2): The text of `skills/anchor/SKILL.md` holds each of `scripts/purlin_python.sh`, `scripts/anchor/upstream.py`, `specs/_anchors/`, `references/formats/anchor_format.md`, `references/spec_quality_guide.md` and `references/commit_conventions.md`; nothing is reported
- PROOF-4 (RULE-4): The anchor skill, as shipped, holds at most 160 lines
- PROOF-24 (RULE-4): A copy of the anchor skill with lines of prose added until it holds exactly 160 lines passes
- PROOF-16 (RULE-9): The text of `skills/anchor/SKILL.md` holds each of `purlin:anchor create`, `purlin:anchor sync`, `purlin:drift`, `purlin:spec` and `purlin:status`; nothing is reported
- PROOF-39 (RULE-17): Every character of `skills/anchor/SKILL.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
