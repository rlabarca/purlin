# Feature: skill_build

> Description: What `skills/build/SKILL.md` must name. The build skill loads the rules a feature
>   is bound by, writes the code and the marked tests, and commits the changeset; this spec holds
>   the one list of the commands and files it names.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 21
> Highest-Proof: 51

## Rules

- RULE-21: The build skill names the commands `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec` and `purlin:audit <feature> RULE-N --settle`, and the files `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`

## Proof

- PROOF-51 (RULE-21): The text of `skills/build/SKILL.md` holds each of `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec`, `purlin:audit <feature> RULE-N --settle`, `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`; none is missing
