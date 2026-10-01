# Feature: purlin_agent

> Description: What `agents/purlin.md` must name. The agent definition is the only text every
>   Purlin session loads before it does anything, so it names the commands of the work, the
>   hand-off and the sign-off, and the files that say what each word means; this spec holds
>   the one list of those commands and files.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition
> Highest-Rule: 18
> Highest-Proof: 49

## Rules

- RULE-18: The agent definition names the commands `sync_status`, `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --all --commit`, `purlin:test --remote`, `purlin:status`, `purlin:audit` and `purlin:sign`, and the files `references/glossary.md`, `references/evidence_and_signoff.md`, `references/spec_quality_guide.md`, `references/formats/marker_format.md` and `.purlin/evidence/<source>/<name>.json`

## Proof

- PROOF-49 (RULE-18): The text of `agents/purlin.md` holds each command and each file RULE-18 names, from `sync_status` to `purlin:sign` and from `references/glossary.md` to `.purlin/evidence/<source>/<name>.json`; none is missing
