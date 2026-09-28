# Feature: skill_build

> Description: What `skills/build/SKILL.md` must say. The build skill loads the rules a feature is
>   bound by, writes the code and the marked tests, and commits the changeset, so its
>   text decides what a commit says about which rule each change serves.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/build/SKILL.md` opens with a frontmatter block whose `name` is `build` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:build`
- RULE-2: The skill chooses what to build from `sync_status` and runs the tests through `purlin:test`, never through the test framework directly
- RULE-3: The last section of `skills/build/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/build/SKILL.md` is at most 130 lines [level: passed]
- RULE-5: The commit the skill makes carries the `feat(<name>):` subject prefix and a body whose Changeset section maps every rule the build addressed as `RULE-N → file:line`, with Decisions and Review omitted when they are empty and Changeset never omitted, as `references/commit_conventions.md` renders it
- RULE-6: The skill compares the files the build created, changed or deleted for the feature with its `> Scope:`, adds each new file no entry covers, removes each entry whose file was deleted, and rewrites the line in the same commit as the code
- RULE-7: For each proof with no marked test the skill looks first for an existing test that already shows what the proof asks and offers to add the marker above it, writing nothing new; otherwise it writes an ordinary test in the project's own framework, folder and style with the marker comment above it, `purlin: <feature> PROOF-<n>`, or the rule's id where the rule has no proof

## Proof

- PROOF-1 (RULE-1): The build skill's file begins with a frontmatter block set between two `---` lines; the block reads `name: build` and carries a `description:` whose value sits on that same line and is neither empty nor a lone `>` that folds it onto the lines below. The command reference names `purlin:build`
- PROOF-2 (RULE-2): The build skill's section on choosing what to build names `sync_status`; the skill gives the command `purlin:test <name>` and carries the sentence `Never run the test framework directly.`
- PROOF-3 (RULE-3): The last section of the build skill is headed with the words `next step` or `when you are done`, in any case; under that heading at least two outcomes stand as list items or table rows, and at least one line gives a `→` directive
- PROOF-4 (RULE-4): Read `skills/build/SKILL.md` and count its lines; verify the count is at most 130. Appending prose until the file passes 130 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): A commit is made with a message written to the contract the build skill describes: the subject `feat(login): implement RULE-1, RULE-2, RULE-3` and a body of Changeset, Decisions and Review sections, the Changeset mapping each rule as in `RULE-1 → src/login.py:12`. Read back from git, the message still has all three sections and maps every rule its subject names. Three messages are each found to break the contract: one with no Changeset section, one whose subject names `RULE-2` while its Changeset maps only `RULE-1`, and one with no `feat(<name>):` prefix. The build skill names Changeset, Decisions, Review, `RULE-N → file:line`, `feat(<name>):` and `commit_conventions.md`, and the commit conventions name all three sections
- PROOF-6 (RULE-6): The build skill's section on committing carries `compare the files you created, changed or deleted for the feature with its` followed directly by `> Scope:`, and the three steps `add each new file no entry covers`, `remove each entry whose file you deleted` and `rewrite the line in the same commit as the code`
- PROOF-7 (RULE-7): The build skill carries the instructions `Look first for a test that already shows it`, `offer to add the marker above it and write nothing new` and `in the folder and the style its other tests use`. Its example shows the comment `# purlin: login PROOF-1` on the line directly above a `def test_` line, and it carries the marker `purlin: login RULE-2`
