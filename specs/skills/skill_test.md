# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked,
>   prints the passed cell of every rule and ends on the summary and `Left to do`.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:test`
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--test`, and states its three exit codes on one line: `0` everything asked happened, `1` a tied test failed or did not run, evidence is missing, a marker names nothing a spec has, there is no settings file, an older Purlin set the project up, or no test command is set, `2` the invocation was wrong; and it says that a test run cannot make an audit or a signature appear
- RULE-3: The last section of `skills/test/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/test/SKILL.md` is at most 120 lines
- RULE-5: The skill names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`, the flag `--commit` and its two commits, `purlin: specs, tests and settings for <feature>` and then `purlin: evidence at <sha7>`, the lines `Evidence committed.` and `Evidence unchanged.`, that the run never pushes, and that it ends on the summary sentence and `Left to do`, whose first line is the next step
- RULE-6: The skill says that with no feature named the run selects the features whose spec, code or tests changed since their evidence, that have no run on this operating system, that have an untracked file under their `> Scope:` or beside their tests, or whose spec names no files, and runs only their test files; it names `purlin:test --all` as the way to run every feature, and the line printed when nothing is selected
- RULE-7: When the run stops for want of a test command, the skill shows the person the suggested entry, asks, writes it with the `purlin_config` tool under the key `tests`, and runs again; where the run found no test tool, the skill reads the project and proposes an entry first

## Proof

- PROOF-1 (RULE-1): The `purlin:test` skill file opens with a block between two `---` lines that reads `name: test` and a `description:` whose value is on that line, is not empty, is not a `>` or `|` block and is not continued on an indented line; the command reference has a row in its command tables whose first cell is `purlin:test` with its arguments. A copy with the `name:` line deleted is reported, naming the skill file and expecting `test`; a copy whose description is emptied, moved to the next line, written as a `|` block or continued onto a second line is reported as carrying no one-line description; a copy of the command reference without the `purlin:test` row is reported as carrying no row for `purlin:test`
- PROOF-2 (RULE-2): The `purlin:test` skill file holds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--test`, one line that carries `Exit codes:` and the three codes, each with its meaning as the rule gives it, and the sentence `cannot make an audit or a signature appear`
- PROOF-8 (RULE-2): A copy of the skill file with `2` moved to the next line is reported as having no single line carrying all of the exit codes
- PROOF-17 (RULE-2): A copy of the skill file with the meaning of `1` reworded to `something failed` is reported as having no single line carrying all of the exit codes
- PROOF-9 (RULE-2): A copy of the skill file with `--test` taken off the command's line is reported as having no single line that runs the script with `--test`
- PROOF-3 (RULE-3): The last section heading of the `purlin:test` skill file carries `next step`, in any case, and the section holds at least 2 table rows below the header and divider, each giving its own `→` but the one that reads `Nothing left to do.`
- PROOF-10 (RULE-3): A copy of the skill file with its closing section deleted is reported as closing with the section `Step 5: operating systems`
- PROOF-14 (RULE-3): A copy of the skill file with every `→` taken out of its closing section is reported as giving no directive
- PROOF-15 (RULE-3): A copy of the skill file cut after the first row of its closing table is reported as naming 1 outcome where at least 2 are expected
- PROOF-16 (RULE-3): A copy of the skill file with the `→` taken out of the row for a rule that fails is reported as that row giving no directive
- PROOF-4 (RULE-4): Read `skills/test/SKILL.md` and count its lines; verify the count is at most 120. Appending prose until the file passes 120 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The `purlin:test` skill file carries `.purlin/evidence/local/<feature>.json`, `.purlin/tests.md`, `--commit`, `purlin: specs, tests and settings for <feature>`, `purlin: evidence at <sha7>`, `Evidence committed.`, `Evidence unchanged.` and `It never pushes.`, and one sentence saying the run ends on the summary sentence and `Left to do`
- PROOF-11 (RULE-5): A copy of the skill file without `purlin: specs, tests and settings for <feature>` is reported as not carrying it
- PROOF-18 (RULE-5): A copy of the skill file whose closing section no longer says that the first line of `Left to do` is the next step is reported as not saying so
- PROOF-6 (RULE-6): The usage block of the `purlin:test` skill file lists `purlin:test --all`, and the paragraph on a run with no feature named, the one that says `With neither, the run selects`, gives the reasons a feature is selected, `with no run on this operating system`, `whose spec, code or tests changed since its evidence`, ``with an untracked file under its `> Scope:` or beside its tests`` and `whose spec names no files`, the words `runs only the test files`, the sentence `purlin:test --all runs them too.` and the line `Nothing to run: every feature's spec, code and tests match its evidence.` A copy without `purlin:test --all` in its usage block is reported; a copy with the `Nothing to run` sentence moved out of that paragraph to the end of the file is reported as the paragraph not carrying it; a copy whose untracked-file reason no longer names `> Scope:` is reported the same way
- PROOF-12 (RULE-7): The `purlin:test` skill file's section on a run that stops before any test carries `Suggested entry:`, `purlin_config`, the key `tests`, the word `ask`, `run Step 1 again`, and, for `no test tool Purlin knows was found`, `Read the project` and `propose one entry`
- PROOF-13 (RULE-7): A copy of the skill file whose stop section no longer names `purlin_config` is reported as not carrying it
