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

- PROOF-1 (RULE-1): Read `skills/test/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: test` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:test`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/test/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` followed by `--test` on the same line, that one line names all three exit codes `0`, `1` and `2` and carries `whatever the gate line says`, and that the text carries `cannot make an audit or a signature appear`. Deleting the exit-code line fails naming it
- PROOF-3 (RULE-3): Read `skills/test/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/test/SKILL.md` and count its lines; verify the count is at most 120. Appending prose until the file passes 120 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/test/SKILL.md`; verify it names `.purlin/evidence/local/<feature>.json`, `.purlin/tests.md`, `--commit`, `purlin: evidence at <sha7>`, `Evidence committed.`, `Evidence unchanged.`, `Tests: <p> of <rules> rules pass.`, `gate <gate> met: <n> of <rules> rules`, `gate <gate> not met: <n> of <rules> rules meet it` and `gate passed met: <n> of <rules> rules`, and that one line says the run never pushes
- PROOF-6 (RULE-6): Read `skills/test/SKILL.md`; verify the usage block carries `purlin:test --all`, and that the text names `no run on this operating system`, `changed since its evidence`, `untracked file`, `names no files`, `runs only the test files`, `purlin:test --all runs them too.` and `Nothing to run: every feature's spec, code and tests match its evidence.` Removing the `Nothing to run` sentence fails naming it
