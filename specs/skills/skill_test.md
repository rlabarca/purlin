# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one an engineer runs
>   constantly: it runs the tagged tests, writes and commits the test results, prints the
>   passed cell of every rule and ends with the gate line.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:test` [bar: strong] [origin: eng]
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--quick`, and states its three exit codes: 0 everything passed, 1 a test failed or the passed level is not met, 2 the invocation was wrong [bar: strong] [origin: eng]
- RULE-3: The last section of `skills/test/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [bar: strong] [origin: eng]
- RULE-4: The whole of `skills/test/SKILL.md` is at most 110 lines [bar: passed] [origin: eng]
- RULE-5: The skill names the two files the run writes, `.purlin/tests/<feature>.json` and `.purlin/tests.md`, the commit subject `purlin: tests at <sha7>` and that the run never pushes, and it names the gate line `gate passed: <n> of <rules>` as the last line of the run [bar: strong] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/test/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: test` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:test`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/test/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` followed by `--quick` on the same line, and that one line names all three exit codes `0`, `1` and `2`. Deleting the exit-code line fails naming it
- PROOF-3 (RULE-3): Read `skills/test/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/test/SKILL.md` and count its lines; verify the count is at most 110. Appending prose until the file passes 110 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/test/SKILL.md`; verify it names `.purlin/tests/<feature>.json`, `.purlin/tests.md`, `purlin: tests at <sha7>`, `Test results committed.`, `Test results unchanged.` and `gate passed: <n> of <rules>`, and that one line says the run never pushes
