# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one a developer runs
>   constantly: it runs the marked tests, writes the evidence and commits it when asked,
>   prints the passed cell of every rule and ends with the gate line.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:test`
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--test`, and states its three exit codes: 0 no test failed and no marker is wrong, whatever the gate line says, 1 a test failed, evidence is missing or a marker names nothing a spec has, 2 the invocation was wrong; and it says that a test run cannot make an audit or a signature appear
- RULE-3: The last section of `skills/test/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/test/SKILL.md` is at most 120 lines [level: passed]
- RULE-5: The skill names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`, the flag `--commit`, the commit subject `purlin: evidence at <sha7>` and that the run never pushes, and it names the run's last two lines, `Tests: <p> of <rules> rules pass.` and the gate line `gate <gate> met: <n> of <rules> rules` or `gate <gate> not met: <n> of <rules> rules meet it`, which counts the rules that meet the gate, with `gate passed met: <n> of <rules> rules` as the check at `passed`
- RULE-6: The skill says that with no feature named the run selects the features whose spec, code or tests changed since their evidence, that have no run on this operating system, that have an untracked file under their `> Scope:` or beside their tests, or whose spec names no files, and runs only their test files; it names `purlin:test --all` as the way to run every feature, and the line printed when nothing is selected

## Proof

- PROOF-1 (RULE-1): The `purlin:test` skill file opens with a block between two `---` lines that reads `name: test` and a `description:` that is not empty; a name other than `test`, an empty description or one written as a folded `>` block does not count. The command reference names `purlin:test`
- PROOF-2 (RULE-2): The `purlin:test` skill file holds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--test`, one line that carries `Exit codes:`, the three codes `0`, `1` and `2` and the words `whatever the gate line says`, and the sentence `cannot make an audit or a signature appear`. The three codes spread over more than one line, or the command without `--test` on its line, do not count
- PROOF-3 (RULE-3): The last section heading of the `purlin:test` skill file carries `next step` or `when you are done`, in any case, and the section holds at least 2 list items or table rows, a table's header row counting as one, and at least one `→`. A file that closes on any other heading, such as `Step 6: the last two lines`, does not count, and neither does a closing section of a single list item
- PROOF-4 (RULE-4): Read `skills/test/SKILL.md` and count its lines; verify the count is at most 120. Appending prose until the file passes 120 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The `purlin:test` skill file names the two files the run writes, `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`; the flag `--commit`, the commit subject `purlin: evidence at <sha7>` and the lines `Evidence committed.` and `Evidence unchanged.`; the sentence `It never pushes.`; and the lines `Tests: <p> of <rules> rules pass.`, `gate <gate> met: <n> of <rules> rules`, `gate <gate> not met: <n> of <rules> rules meet it` and `gate passed met: <n> of <rules> rules`. A file missing any one of these, such as the `not met` form of the gate line, does not count
- PROOF-6 (RULE-6): The usage block of the `purlin:test` skill file lists `purlin:test --all`, and the file names the reasons a feature is selected when none is named, `no run on this operating system`, `changed since its evidence`, `untracked file` and `names no files`, the words `runs only the test files`, the sentence `purlin:test --all runs them too.` and the line `Nothing to run: every feature's spec, code and tests match its evidence.` A file that names `purlin:test --all` only outside its usage block does not count
