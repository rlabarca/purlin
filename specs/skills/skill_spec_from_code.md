# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must name. The skill reads a codebase that
>   has no specs and writes the rules it already implies; it is optional, and its instructions
>   load only when it is used. This spec holds the commands and files it names, its length and
>   its characters.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 52
> Highest-Proof: 166

## Rules

- RULE-2: The spec-from-code skill names the commands `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build` and `purlin:test`
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines
- RULE-33: The spec-from-code skill names the files `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`
- RULE-52: The spec-from-code skill holds no emoji

## Proof

- PROOF-2 (RULE-2): The text of `skills/spec-from-code/SKILL.md` holds each of `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build` and `purlin:test`; nothing is reported
- PROOF-4 (RULE-4): The spec-from-code skill's file, counted line by line, is at most 130 lines long
- PROOF-141 (RULE-4): A copy of the skill padded with lines of prose to exactly 130 lines is accepted
- PROOF-147 (RULE-33): The text of `skills/spec-from-code/SKILL.md` holds each of `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; nothing is reported
- PROOF-166 (RULE-52): Every character of `skills/spec-from-code/SKILL.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
