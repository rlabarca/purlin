# Feature: skill_build

> Description: What `skills/build/SKILL.md` must name. The build skill loads the rules a feature
>   is bound by, writes the code and the marked tests, and commits the changeset; this spec holds
>   the commands and files it names, its length and its characters.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 20
> Highest-Proof: 50

## Rules

- RULE-2: The build skill names the commands `sync_status`, `purlin:test`, `purlin:test --all --commit` and `purlin:spec`
- RULE-4: The whole of `skills/build/SKILL.md` is at most 130 lines
- RULE-8: The build skill names the files `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py` and `references/commit_conventions.md`
- RULE-20: The build skill holds no emoji

## Proof

- PROOF-2 (RULE-2): The text of `skills/build/SKILL.md` holds each of `sync_status`, `purlin:test`, `purlin:test --all --commit` and `purlin:spec`; nothing is reported
- PROOF-4 (RULE-4): The build skill's file is at most 130 lines long
- PROOF-9 (RULE-8): The text of `skills/build/SKILL.md` holds each of `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py` and `references/commit_conventions.md`; nothing is reported
- PROOF-49 (RULE-8): The text of `skills/build/SKILL.md` holds `scripts/mcp/purlin/wording.py`, the check that lists each test comment whose proof was reworded after its test last changed, run before the skill adds a marker comment; nothing is reported
- PROOF-50 (RULE-20): Every character of `skills/build/SKILL.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
