# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must name. The skill reads a codebase that
>   has no specs and writes the rules it already implies; it is optional, and its instructions
>   load only when it is used. This spec holds the one list of the commands and files it names.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 53
> Highest-Proof: 167

## Rules

- RULE-53: The spec-from-code skill names the commands `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build` and `purlin:test`, and the files `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`

## Proof

- PROOF-167 (RULE-53): The text of `skills/spec-from-code/SKILL.md` holds each of `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build`, `purlin:test`, `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; none is missing
