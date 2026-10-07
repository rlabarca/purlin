# Feature: skill_build

> Description: What `skills/build/SKILL.md` must name. The build skill loads the rules a feature
>   is bound by, writes the code and the marked tests, and commits the changeset; this spec holds
>   the one list of the commands and files it names.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 23
> Highest-Proof: 54

## Rules

- RULE-21: The build skill names the commands `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec` and `purlin:audit <feature> RULE-N --settle`, and the files `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`
- RULE-22: The build skill says how it settles a proof whose test it left alone because the test already asserts what the proof names: with `purlin:audit <feature> RULE-N --settle --sound PROOF-N`, and only for a test it read against its proof
- RULE-23: The build skill says how the test of an AI proof is written: with the helper the run names in `PURLIN_AI`, one output per test, `grade` for a graded proof, passing or skipping with `PURLIN_AI` not set, and `purlin:test --all` run once it is written, said first

## Proof

- PROOF-51 (RULE-21): The text of `skills/build/SKILL.md` holds each of `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec`, `purlin:audit <feature> RULE-N --settle`, `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`; none is missing
- PROOF-52 (RULE-22): The text of `skills/build/SKILL.md` under the heading `Strengthening a weak rule` holds `purlin:audit <feature> RULE-N --settle --sound PROOF-N` and `Never pass it for a test you did not read against its proof`
- PROOF-53 (RULE-23): The text of `skills/build/SKILL.md` under the heading `The test of an AI proof` holds `references/purlin_commands.md`, `references/rule_examples.md`, `One test makes one output.`, ``A graded proof's test then starts `grade` and asserts it exits 0.`` and ``The test passes or skips when `PURLIN_AI` is not set``
- PROOF-54 (RULE-23): That part holds the sentence ``Run `purlin:test --all` once the test is written, and say first that it reaches a real model and takes minutes.``
