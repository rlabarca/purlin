# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must name. The skill reads a codebase that
>   has no specs and writes the rules it already implies; it is optional, and its instructions
>   load only when it is used. This spec holds the one list of the commands and files it names.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 54
> Highest-Proof: 168

## Rules

- RULE-53: The spec-from-code skill names the commands `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build` and `purlin:test`, and the files `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`
- RULE-54: The spec-from-code skill says what it drafts for a prompt, a skill, an agent definition or a Claude project's instructions: rules, proofs and their tags, the model asked of the person, no test, and what it says of such a rule as it hands over

## Proof

- PROOF-167 (RULE-53): The text of `skills/spec-from-code/SKILL.md` holds each of `sync_status`, `purlin:init`, `purlin:anchor create`, `purlin:build`, `purlin:test`, `.purlin/runtime/spec-from-code.json`, `references/spec_quality_guide.md`, `references/formats/spec_format.md` and `references/commit_conventions.md`; none is missing
- PROOF-168 (RULE-54): The text of `skills/spec-from-code/SKILL.md` under the heading `Prompts, skills and agent definitions` holds `**Stop and ask** which model or models each is shown on`, ``Write no test for one: `purlin:build` does.`` and `A rule read from instructions says what they ask for, not what the AI does.`
