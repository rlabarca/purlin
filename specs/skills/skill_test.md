# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked,
>   prints the passed cell of every rule and ends on the summary and `Left to do`.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent to run `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--test`
- RULE-3: The last section of `skills/test/SKILL.md` tells the agent to name the next step: it lists at least two outcomes the run can end on, and every outcome gives a `→` directive except `Nothing left to do.`, which names no command
- RULE-4: The whole of `skills/test/SKILL.md` is at most 120 lines
- RULE-5: The skill tells the agent the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`
- RULE-6: The skill tells the agent that with no feature named the run selects the features whose spec, code or tests changed since their evidence, that have no run on this operating system, that have an untracked file under their `> Scope:` or beside their tests, or whose spec names no files, and runs only their test files
- RULE-7: When the run stops with a suggested `tests` setting, the skill tells the agent to show the person each suggested command, ask once, and on yes write that array as the `tests` setting with the `purlin_config` tool, then run Step 1 again
- RULE-8: The skill tells the agent the run's three exit codes on one line: `0` everything asked happened, `1` a tied test failed or did not run, evidence is missing, a marker names nothing a spec has, there is no settings file, the settings file cannot be read, an older Purlin set the project up, or no test command is set, `2` the invocation was wrong
- RULE-9: The skill tells the agent that a test run cannot make an audit or a signature appear
- RULE-10: The skill tells the agent that `--commit` makes two commits, `purlin: specs, tests and settings for <feature>` and then `purlin: evidence at <sha7>`, and that the run then prints `Evidence committed.` or `Evidence unchanged.`
- RULE-11: The skill tells the agent that the run never pushes
- RULE-12: The skill tells the agent that the run ends on the summary sentence and `Left to do`, whose first line is the next step
- RULE-13: The skill tells the agent that `purlin:test --all` runs every feature
- RULE-14: The skill tells the agent the line the run prints when it selects nothing
- RULE-15: Where the run found no test tool, the skill tells the agent to read the project, propose one entry, ask, write it the same way and run Step 1 again
- RULE-16: `references/purlin_commands.md` carries a row for `purlin:test`

## Proof

- PROOF-1 (RULE-1): The `purlin:test` skill file as shipped opens with a block between two `---` lines holding `name: test` and a `description:` line whose value is on that line and is not empty; checking the skill file reports nothing
- PROOF-19 (RULE-16): The command reference as shipped has a row, in a table headed `Command` and `Purpose`, whose first cell is `purlin:test` with its arguments and whose second cell is a purpose sentence; checking it reports nothing
- PROOF-2 (RULE-2): The `purlin:test` skill file as shipped has one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--test`
- PROOF-27 (RULE-8): The `purlin:test` skill file as shipped has one line carrying `Exit codes:` and the three codes, `0`, `1` and `2`, each followed by its meaning word for word as the rule gives it
- PROOF-28 (RULE-9): The `purlin:test` skill file as shipped carries the words `cannot make an audit or a signature appear`
- PROOF-3 (RULE-3): In the `purlin:test` skill file as shipped, the last section's heading carries `next step`, in any case, its table lists at least 2 outcomes below the header and divider, and every outcome but the one reading `Nothing left to do.` gives its own `→`
- PROOF-4 (RULE-4): The `purlin:test` skill file as shipped is at most 120 lines long; checking its length reports nothing
- PROOF-30 (RULE-4): A copy of the skill file padded with lines of prose to exactly 120 lines is not reported
- PROOF-31 (RULE-4): A copy of the skill file padded with lines of prose to 121 lines is reported as 121 lines against a ceiling of 120
- PROOF-5 (RULE-5): The `purlin:test` skill file as shipped names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`
- PROOF-32 (RULE-10): The `purlin:test` skill file as shipped carries `--commit` and names its two commits in this order: `purlin: specs, tests and settings for <feature>`, then `purlin: evidence at <sha7>`
- PROOF-33 (RULE-10): The `purlin:test` skill file as shipped carries the two lines a committing run prints, `Evidence committed.` and `Evidence unchanged.`
- PROOF-34 (RULE-11): The `purlin:test` skill file as shipped carries the sentence `It never pushes.`
- PROOF-35 (RULE-12): The `purlin:test` skill file as shipped has a sentence carrying ``The run ends on the summary sentence and `Left to do` ``
- PROOF-36 (RULE-12): The `purlin:test` skill file as shipped has a sentence carrying ``The first line of `Left to do` is the next step``
- PROOF-6 (RULE-13): The usage block of the `purlin:test` skill file as shipped lists `purlin:test --all`
- PROOF-38 (RULE-6): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` gives four reasons: `with no run on this operating system`, `whose spec, code or tests changed since its evidence`, ``with an untracked file under its `> Scope:` or beside its tests`` and `whose spec names no files`
- PROOF-39 (RULE-6): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` carries `runs only the test files` and `purlin:test --all runs them too.`
- PROOF-40 (RULE-14): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` carries, whole, the line printed when nothing is selected: `Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --all runs them anyway.`
- PROOF-12 (RULE-7): In the `purlin:test` skill file as shipped, the row for a run that prints `Suggested tests setting: <the entries as one JSON array on one line>` says to show the person each suggested command, ask once, write that array as the `tests` setting with the `purlin_config` tool, and run Step 1 again
- PROOF-44 (RULE-15): In the `purlin:test` skill file as shipped, the row for a run that prints `no test tool Purlin knows was found` says to read the project, propose one entry, ask, write it the same way and run Step 1 again
