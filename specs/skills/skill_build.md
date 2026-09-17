# Feature: skill_build

> Description: What `skills/build/SKILL.md` must say. The build skill loads the rules a feature is
>   bound by, writes the code and the tagged tests, and commits the changeset, so its
>   text decides what a commit records about which rule each change serves.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/build/SKILL.md` opens with a frontmatter block whose `name` is `build` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:build` [risk: medium] [origin: eng]
- RULE-2: The skill chooses what to build from `sync_status` and runs the tests through `purlin:test`, never through the test framework directly [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/build/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/build/SKILL.md` is at most 130 lines [risk: low] [origin: eng]
- RULE-5: The commit the skill makes carries the `feat(<name>):` subject prefix and a body whose Changeset section maps every rule the build addressed as `RULE-N → file:line`, with Decisions and Review omitted when they are empty and Changeset never omitted, as `references/commit_conventions.md` renders it [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/build/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: build` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:build`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/build/SKILL.md`; verify it names `sync_status` in the section that chooses what to build, carries the fenced command `purlin:test <name>`, and carries the sentence `Never run the test framework directly.` Deleting that sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/build/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/build/SKILL.md` and count its lines; verify the count is at most 130. Appending prose until the file passes 130 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Run `bash dev/test_e2e_build_changeset.sh` from the repository root; verify it exits 0 and prints a line beginning `ok:`. The suite writes a fixture commit whose body follows the contract, reads the message back out of git and checks it, then rejects three fixtures that each break the contract in one way, and it asserts that `skills/build/SKILL.md` still names Changeset, Decisions, Review, `RULE-N → file:line`, `feat(<name>):` and `references/commit_conventions.md`. Dropping the Changeset section from the skill fails the suite with a non-zero exit @integration
