# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked,
>   prints the passed cell of every rule and ends on the summary and `Left to do`.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:test`
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--test`, and states its three exit codes on one line: `0` everything asked happened, `1` a tied test failed or did not run, evidence is missing, a marker names nothing a spec has, there is no settings file, an older Purlin set the project up, or no test command is set, `2` the invocation was wrong; and it says that a test run cannot make an audit or a signature appear
- RULE-3: The last section of `skills/test/SKILL.md` names the next step: it lists at least two outcomes the run can end on, and every outcome gives a `→` directive except `Nothing left to do.`, which names no command
- RULE-4: The whole of `skills/test/SKILL.md` is at most 120 lines
- RULE-5: The skill names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`, the flag `--commit` and its two commits, `purlin: specs, tests and settings for <feature>` and then `purlin: evidence at <sha7>`, the lines `Evidence committed.` and `Evidence unchanged.`, that the run never pushes, and that it ends on the summary sentence and `Left to do`, whose first line is the next step
- RULE-6: The skill says that with no feature named the run selects the features whose spec, code or tests changed since their evidence, that have no run on this operating system, that have an untracked file under their `> Scope:` or beside their tests, or whose spec names no files, and runs only their test files; it names `purlin:test --all` as the way to run every feature, and the line printed when nothing is selected
- RULE-7: When the run stops for want of a test command, the skill shows the person the suggested command, asks, and on yes writes the suggested entry with the `purlin_config` tool under the key `tests` and runs again; where the run found no test tool, the skill reads the project and proposes an entry first

## Proof

- PROOF-1 (RULE-1): The `purlin:test` skill file as shipped opens with a block between two `---` lines holding `name: test` and a `description:` line whose value is on that line and is not empty; checking the skill file reports nothing
- PROOF-19 (RULE-1): The command reference as shipped has a row, in a table headed `Command` and `Purpose`, whose first cell is `purlin:test` with its arguments and whose second cell is a purpose sentence; checking it reports nothing
- PROOF-20 (RULE-1): A copy of the skill file with its `name: test` line deleted is reported, naming the skill file, as having no name where `test` is expected
- PROOF-21 (RULE-1): A copy of the skill file whose `description:` line is left with no value is reported as carrying no one-line description
- PROOF-22 (RULE-1): A copy of the skill file whose description value is moved, indented, onto the line below `description:` is reported as carrying no one-line description
- PROOF-23 (RULE-1): A copy of the skill file whose description is written as a `|` block, the value indented on the next line, is reported as carrying no one-line description
- PROOF-24 (RULE-1): A copy of the skill file whose description is written as a `>` block, the value indented on the next line, is reported as carrying no one-line description
- PROOF-25 (RULE-1): A copy of the skill file whose one-line description is continued onto an indented second line is reported as carrying no one-line description
- PROOF-26 (RULE-1): A copy of the command reference with the `purlin:test` row deleted is reported as carrying no row for `purlin:test`
- PROOF-2 (RULE-2): The `purlin:test` skill file as shipped has one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--test`
- PROOF-27 (RULE-2): The `purlin:test` skill file as shipped has one line carrying `Exit codes:` and the three codes, `0`, `1` and `2`, each followed by its meaning word for word as the rule gives it
- PROOF-28 (RULE-2): The `purlin:test` skill file as shipped carries the words `cannot make an audit or a signature appear`
- PROOF-8 (RULE-2): A copy of the skill file with `2` and its meaning moved to the next line is reported as having no single line carrying all of the exit codes
- PROOF-17 (RULE-2): A copy of the skill file with the meaning of `1` reworded to `something failed` is reported as having no single line carrying all of the exit codes
- PROOF-9 (RULE-2): A copy of the skill file with `--test` taken off the command's line is reported as having no single line that runs the script with `--test`
- PROOF-29 (RULE-2): A copy of the skill file with `cannot make an audit or a signature appear` reworded to `does not audit or sign` is reported as not carrying it
- PROOF-3 (RULE-3): In the `purlin:test` skill file as shipped, the last section's heading carries `next step`, in any case, its table lists at least 2 outcomes below the header and divider, and every outcome but the one reading `Nothing left to do.` gives its own `→`
- PROOF-10 (RULE-3): A copy of the skill file with its closing section deleted is reported as closing with the section `Step 5: operating systems`
- PROOF-14 (RULE-3): A copy of the skill file with every `→` in its closing section replaced by `->` is reported as its closing section giving no directive
- PROOF-15 (RULE-3): A copy of the skill file cut off after the first row of its closing table is reported as naming 1 outcome where at least 2 are expected
- PROOF-16 (RULE-3): A copy of the skill file with the `→` taken out of the row for a rule that fails is reported as that row giving no `→` directive
- PROOF-4 (RULE-4): The `purlin:test` skill file as shipped is at most 120 lines long; checking its length reports nothing
- PROOF-30 (RULE-4): A copy of the skill file padded with lines of prose to exactly 120 lines is not reported
- PROOF-31 (RULE-4): A copy of the skill file padded with lines of prose to 121 lines is reported as 121 lines against a ceiling of 120
- PROOF-5 (RULE-5): The `purlin:test` skill file as shipped names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`
- PROOF-32 (RULE-5): The `purlin:test` skill file as shipped carries `--commit` and names its two commits in this order: `purlin: specs, tests and settings for <feature>`, then `purlin: evidence at <sha7>`
- PROOF-33 (RULE-5): The `purlin:test` skill file as shipped carries the two lines a committing run prints, `Evidence committed.` and `Evidence unchanged.`
- PROOF-34 (RULE-5): The `purlin:test` skill file as shipped carries the sentence `It never pushes.`
- PROOF-35 (RULE-5): The `purlin:test` skill file as shipped has a sentence carrying ``The run ends on the summary sentence and `Left to do` ``
- PROOF-36 (RULE-5): The `purlin:test` skill file as shipped has a sentence carrying ``The first line of `Left to do` is the next step``
- PROOF-11 (RULE-5): A copy of the skill file with `purlin: specs, tests and settings for <feature>` reworded to `a commit` is reported as not carrying it
- PROOF-37 (RULE-5): A copy of the skill file with the two commit subjects swapped is reported as carrying them out of order
- PROOF-18 (RULE-5): A copy of the skill file with ``The first line of `Left to do` is the next step`` reworded to `The lines follow` is reported as having no sentence saying it
- PROOF-6 (RULE-6): The usage block of the `purlin:test` skill file as shipped lists `purlin:test --all`
- PROOF-38 (RULE-6): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` gives four reasons: `with no run on this operating system`, `whose spec, code or tests changed since its evidence`, ``with an untracked file under its `> Scope:` or beside its tests`` and `whose spec names no files`
- PROOF-39 (RULE-6): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` carries `runs only the test files` and `purlin:test --all runs them too.`
- PROOF-40 (RULE-6): In the `purlin:test` skill file as shipped, the paragraph that says `With neither, the run selects` carries, whole, the line printed when nothing is selected: `Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --all runs them anyway.`
- PROOF-41 (RULE-6): A copy of the skill file with the `purlin:test --all` line taken out of its usage block is reported as its usage not naming `purlin:test --all`
- PROOF-42 (RULE-6): A copy of the skill file with the `Nothing to run` line moved out of the selection paragraph to the end of the file is reported as that paragraph not carrying it
- PROOF-43 (RULE-6): A copy of the skill file whose untracked-file reason reads `in the project` in place of ``under its `> Scope:` or beside its tests`` is reported as that paragraph not carrying the reason
- PROOF-12 (RULE-7): In the `purlin:test` skill file as shipped, the row for a run that prints `Suggested entry: <JSON>` says to show the person the command and ask, write the entry with the `purlin_config` tool, key `tests`, and run Step 1 again
- PROOF-44 (RULE-7): In the `purlin:test` skill file as shipped, the row for a run that prints `no test tool Purlin knows was found` says to read the project, propose one entry, ask, write it the same way and run Step 1 again
- PROOF-13 (RULE-7): A copy of the skill file whose row for `Suggested entry: <JSON>` reads `a tool` in place of the `purlin_config` tool is reported as that row not carrying it
