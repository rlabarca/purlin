# Feature: purlin_agent

> Description: What `agents/purlin.md` must name. The agent definition is the only text every
>   Purlin session loads before it does anything, so it names the commands of the work, the
>   hand-off and the sign-off, and the files that say what each word means; this spec holds
>   the one list of those commands and files. It also holds seven checks on what every skill,
>   the agent definition and the references tell an agent to run.
> Scope: agents/purlin.md, skills/, references/
> Stack: markdown, Claude Code agent definition
> Highest-Rule: 27
> Highest-Proof: 61

## Rules

- RULE-18: The agent definition names the commands `sync_status`, `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:test --all --commit`, `purlin:status`, `purlin:audit` and `purlin:sign`, and the files `references/glossary.md`, `references/evidence_and_signoff.md`, `references/spec_quality_guide.md`, `references/formats/marker_format.md` and `.purlin/evidence/<source>/<name>.json`
- RULE-19: The agent definition says that after merging work from a worktree the agent runs `purlin:status` in the main checkout, so the main checkout's status and dashboard describe the merged work
- RULE-20: Every path under `scripts/`, `references/`, `templates/`, `skills/` or `docs/` that a skill or the agent definition names is a file or folder in the repository
- RULE-21: Every flag a skill writes on a line that runs a script is one that script takes
- RULE-22: The answers file the sign skill shows is one `purlin:sign --answers` walks without a refusal about the file
- RULE-23: No skill, agent definition or reference names a path under `dev/`, `/dev/null` aside
- RULE-24: Every skill that names `sync_status` names the tool as a session lists it, `mcp__plugin_purlin_purlin__sync_status`, and the script that prints the same status, `scripts/run/purlin_status.py`
- RULE-25: `references/purlin_commands.md` and `references/glossary.md` each name the command that settles a weak rule, `purlin:audit <feature> RULE-N --settle`
- RULE-26: The agent definition says a proof about what an AI does is an AI proof, and names the two references that say how one is written and how its test makes the output
- RULE-27: `references/purlin_commands.md` gives the helper's command line, and no skill and no agent definition restates it

## Proof

- PROOF-49 (RULE-18): The text of `agents/purlin.md` holds each command and each file RULE-18 names, from `sync_status` to `purlin:sign` and from `references/glossary.md` to `.purlin/evidence/<source>/<name>.json`; none is missing
- PROOF-60 (RULE-18): A name is held whole, each space as written: the same check on a copy of `agents/purlin.md` in which every `purlin:spec` reads `purlin:specs` lists exactly `purlin:spec`, and on a copy in which every `purlin:test --all --commit` reads `purlin:test  --all --commit`, with two spaces after `purlin:test`, lists exactly `purlin:test --all --commit`
- PROOF-50 (RULE-19): The text of `agents/purlin.md` holds one sentence that names a worktree, merging, `purlin:status` and the main checkout
- PROOF-51 (RULE-20): Each such path read out of the ten `SKILL.md` files and `agents/purlin.md` exists; the same check on a copy of the sign skill naming `scripts/review/signoff.py` lists that path
- PROOF-61 (RULE-20): A path is looked for letter for letter: the same check on a copy of `agents/purlin.md` in which every `references/glossary.md` reads `references/Glossary.md` lists exactly `references/Glossary.md`
- PROOF-52 (RULE-21): Each `--flag` on a line of a `SKILL.md` naming a `scripts/**/*.py` is in that script's `--help`; the same check on a copy of the test skill passing `--nonesuch` to `purlin_run.py` lists `--nonesuch`
- PROOF-53 (RULE-22): The JSON block under `Step 5` of `skills/sign/SKILL.md`, written to `.purlin/runtime/signoff-answers.json` in a project whose hand checks are `accession_screen RULE-1` and `sample_age RULE-6`, is walked with `--answers`; it exits 0 and the sign-off holds the note `the tube is red`
- PROOF-54 (RULE-23): No line of `skills/*/SKILL.md`, `agents/purlin.md` or `references/**/*.md` holds `dev/` once every `/dev/null` is set aside; the same check on a copy of the build skill naming `dev/test_x.py` lists that line
- PROOF-55 (RULE-24): Each `SKILL.md` holding `sync_status` holds `mcp__plugin_purlin_purlin__sync_status` and `scripts/run/purlin_status.py`; the same check on a copy of the build skill with the script's line taken out lists `build does not name scripts/run/purlin_status.py`
- PROOF-56 (RULE-25): The text of `references/purlin_commands.md` holds `purlin:audit <feature> RULE-N --settle`, and so does the text of `references/glossary.md`
- PROOF-57 (RULE-26): The text of `agents/purlin.md` holds one sentence that names `AI proof`, `@ai(<model>)`, `references/spec_quality_guide.md` and `references/purlin_commands.md`
- PROOF-58 (RULE-27): The text of `references/purlin_commands.md` holds the three lines `purlin_ai.py run --skill <folder> | --plugin <folder> | --instructions <file>...`, `purlin_ai.py record --from <folder> [--model <name>]` and `purlin_ai.py grade --feature <name> --proof PROOF-N`
- PROOF-59 (RULE-27): No `SKILL.md` and not `agents/purlin.md` holds `--instructions`, `--from <folder>` or `--proof PROOF-N`; the same check on a copy of the build skill with the line `purlin_ai.py record --from <folder>` added lists `--from <folder>`
