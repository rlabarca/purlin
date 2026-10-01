# Feature: purlin_agent

> Description: What `agents/purlin.md` must name. The agent definition is the only text every
>   Purlin session loads before it does anything, so it names the commands of the work, the
>   hand-off and the sign-off, and the files that say what each word means; this spec holds
>   those commands and files, its length and its characters.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition
> Highest-Rule: 17
> Highest-Proof: 48

## Rules

- RULE-2: The agent definition names the commands `sync_status`, `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --all --commit`, `purlin:test --remote`, `purlin:status`, `purlin:audit` and `purlin:sign`
- RULE-3: The agent definition holds no emoji
- RULE-6: The agent definition is at most 135 lines
- RULE-7: The agent definition names the files `references/glossary.md`, `references/evidence_and_signoff.md`, `references/spec_quality_guide.md`, `references/formats/marker_format.md` and `.purlin/evidence/<source>/<name>.json`

## Proof

- PROOF-2 (RULE-2): The text of `agents/purlin.md` holds each of `sync_status`, `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --all --commit`, `purlin:test --remote`, `purlin:status`, `purlin:audit` and `purlin:sign`; nothing is reported
- PROOF-3 (RULE-3): Every character of `agents/purlin.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
- PROOF-6 (RULE-6): The agent definition, counted line by line, is at most 135 lines long; nothing is reported
- PROOF-38 (RULE-6): A copy of the agent definition padded with lines of prose to exactly 135 lines is not refused
- PROOF-7 (RULE-7): The text of `agents/purlin.md` holds each of `references/glossary.md`, `references/evidence_and_signoff.md`, `references/spec_quality_guide.md`, `references/formats/marker_format.md` and `.purlin/evidence/<source>/<name>.json`; nothing is reported
