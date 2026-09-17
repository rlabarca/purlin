# Feature: skill_test

> Description: What `skills/test/SKILL.md` must say. The test skill is the one an engineer runs
>   constantly: it runs the tagged tests, writes the runtime proof files and prints
>   the state of every rule.
> Scope: skills/test/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/test/SKILL.md` opens with a frontmatter block whose `name` is `test` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:test` [risk: medium] [origin: eng]
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--quick`, and states its three exit codes: 0 everything passed, 1 a test failed, 2 the invocation was wrong [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/test/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/test/SKILL.md` is at most 90 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/test/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: test` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:test`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/test/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` followed by `--quick` on the same line, and that one line names all three exit codes `0`, `1` and `2`. Deleting the exit-code line fails naming it
- PROOF-3 (RULE-3): Read `skills/test/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/test/SKILL.md` and count its lines; verify the count is at most 90. Appending prose until the file passes 90 lines fails, and the failure reports the count it found beside the ceiling
