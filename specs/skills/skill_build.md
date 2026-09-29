# Feature: skill_build

> Description: What `skills/build/SKILL.md` must say. The build skill loads the rules a feature is
>   bound by, writes the code and the marked tests, and commits the changeset, so its
>   text decides what a commit says about which rule each change serves.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/build/SKILL.md` opens with a frontmatter block whose `name` is `build` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:build`
- RULE-2: The skill tells the agent to choose what to build from `sync_status` and to run the tests through `purlin:test`, never through the test framework directly
- RULE-3: The last section of `skills/build/SKILL.md` tells the agent to name the next step from the summary and `Left to do` that `purlin:test` ended on, and lists the outcomes, each with its own `→` directive
- RULE-4: The whole of `skills/build/SKILL.md` is at most 130 lines
- RULE-5: The skill tells the agent to make one commit per build with the `feat(<name>):` subject prefix and a body whose Changeset section maps every rule the build addressed as `RULE-N → file:line`, with Decisions and Review omitted when they are empty and Changeset never omitted, as `references/commit_conventions.md` renders it
- RULE-6: Before it commits, the skill tells the agent to compare the files it created, changed or deleted for the feature with the spec's `> Scope:`, add each new file no entry covers, remove each entry whose file was deleted, and rewrite the line in the same commit as the code
- RULE-7: For each proof with no marked test the skill tells the agent to look first for an existing test that already shows what the proof asks and offer to add the marker above it, writing nothing new; otherwise to write an ordinary test in the project's own framework, folder and style with the marker comment above it, `purlin: <feature> PROOF-<n>`, or the rule's id where the rule has no proof
- RULE-8: In a section before the one on running the tests, the skill gives the command `scripts/mcp/purlin/markers.py --near-misses` and tells the agent to show each comment it returns with its fix and the reason, ask, and make the edits the person accepts
- RULE-9: The skill tells the agent that `purlin:test` suggests and writes the test command where none is set, and that the agent writes no test command itself

## Proof

- PROOF-1 (RULE-1): The build skill's file opens with a frontmatter block between two `---` lines that reads `name: build` and carries a `description:` whose text sits whole on that line; the command reference carries a table row whose first cell is `purlin:build` and whose second cell gives its purpose
- PROOF-24 (RULE-1): A copy of the build skill with its `name:` line deleted fails, reporting that it found no name where `build` is expected
- PROOF-25 (RULE-1): A copy of the build skill whose `description:` is left empty fails, reporting that the frontmatter carries no one-line description
- PROOF-26 (RULE-1): A copy of the build skill whose `description:` is left empty, with the `name: build` line moved below it, fails, reporting that the frontmatter carries no one-line description; the line below is not read as the description
- PROOF-27 (RULE-1): A copy of the build skill whose description is written as a `|` block fails, reporting that the frontmatter carries no one-line description
- PROOF-28 (RULE-1): A copy of the build skill whose description runs onto a second, indented line fails, reporting that the frontmatter carries no one-line description
- PROOF-29 (RULE-1): A copy of the command reference with the `purlin:build` row removed fails, reporting that the reference carries no row for `purlin:build`
- PROOF-2 (RULE-2): The build skill's section on choosing what to build names `sync_status`; its section on running the tests gives `purlin:test <name>` alone on a line in a fenced block and says `Never run the test framework directly.`; and no fenced block in the skill runs a test framework itself, such as `pytest`, `jest`, `go test` or `dotnet test`
- PROOF-30 (RULE-2): A copy of the build skill whose fenced `purlin:test <name>` is replaced by `python3 -m pytest tests/` fails twice: it reports the framework's own command, and that the section on running the tests gives no `purlin:test <name>` line
- PROOF-31 (RULE-2): A copy of the build skill whose fenced `purlin:build [<name>]` is replaced by `npx jest` fails, reporting the framework's own command
- PROOF-32 (RULE-2): A copy of the build skill whose section on choosing what to build no longer calls `sync_status` fails, reporting that the skill does not read the state with `sync_status` before it chooses
- PROOF-3 (RULE-3): The last section of the build skill is headed `When you are done` and says to name the next step from the summary and `Left to do` that `purlin:test` ended on; it lists at least two outcomes, and each gives its own `→` directive
- PROOF-8 (RULE-3): A copy of the build skill whose outcome `Some rules still have no test` loses its `→` fails, naming that outcome as giving no directive
- PROOF-33 (RULE-3): A copy of the build skill whose last section no longer says where the next step is named from fails, reporting that it does not say to name the next step from `purlin:test`'s summary and `Left to do`
- PROOF-4 (RULE-4): The build skill's file is at most 130 lines long
- PROOF-34 (RULE-4): A copy of the build skill with prose lines added until it is 131 lines long fails, reporting `skills/build/SKILL.md is 131 lines, ceiling 130`
- PROOF-5 (RULE-5): The build skill's section on committing says `One commit per build`, names the `feat(<name>):` prefix, the body's three sections Changeset, Decisions and Review, the line form `RULE-N → file:line`, and `references/commit_conventions.md` as the rendering to follow
- PROOF-35 (RULE-5): The build skill says `Changeset is never omitted.`, and the commit conventions' table of the build commit's sections gives `Never` as when Changeset is left out
- PROOF-36 (RULE-5): The build skill says in one sentence to omit Decisions when every rule had one obvious implementation and Review when nothing needs a second pair of eyes; the commit conventions' table leaves Decisions out `When every rule had one obvious implementation` and Review `When nothing needs a second pass`
- PROOF-37 (RULE-5): The commit conventions' example of a build commit opens with `feat(auth_login): `, every line of its changeset that names a rule maps it as `RULE-N → <file>:<line>`, and a `Decisions:` and a `Review:` section follow the changeset
- PROOF-38 (RULE-5): A copy of the commit conventions whose table leaves Changeset out `When empty` fails, reporting that value where `Never` is expected
- PROOF-6 (RULE-6): The build skill's section on committing says to compare the files created, changed or deleted for the feature with its `> Scope:`, then to add each new file no entry covers, remove each entry whose file was deleted, and rewrite the line in the same commit as the code
- PROOF-39 (RULE-6): A copy of the build skill with the step `remove each entry whose file you deleted` taken out fails, naming that step as missing
- PROOF-7 (RULE-7): For each proof with no test marked for it, the build skill gives first the step `Look first for a test that already shows it.`, saying to offer to add the marker above such a test and write nothing new, and then the step `Otherwise write an ordinary test` in the project's own framework, folder and style
- PROOF-40 (RULE-7): The build skill's example shows the comment `# purlin: login PROOF-1` on the line directly above a `def test_` line
- PROOF-41 (RULE-7): One sentence of the build skill says that where a rule has no proof the marker names the rule, as in `purlin: login RULE-2`
- PROOF-42 (RULE-7): A copy of the build skill with the look-first step moved below the write step fails, reporting the two steps out of order
- PROOF-43 (RULE-7): A copy of the build skill with `in the project's own framework` deleted from the write step fails, reporting the write step missing
- PROOF-44 (RULE-7): A copy of the build skill with `it names the rule` deleted fails, reporting that no sentence ties `purlin: login RULE-2` to a rule with no proof
- PROOF-9 (RULE-8): The build skill gives, in a fenced block, the line `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root .`, in a section before the one on running the tests, and one sentence says to show each `fix` beside its `why`, ask, and make the edits accepted
- PROOF-10 (RULE-8): A copy of the build skill whose fenced line lacks `--near-misses` fails, saying the skill gives no line that finds the comments that are nearly markers
- PROOF-45 (RULE-8): A copy of the build skill with the section that repairs nearly right markers moved below the section on running the tests fails, reporting that it does not come before that section
- PROOF-11 (RULE-9): The build skill's section on running the tests says that where no test command is set `purlin:test` suggests one and writes it once the person confirms, and says `write no entry yourself`; nowhere does the skill name the `purlin_config` tool
- PROOF-12 (RULE-9): A copy of the build skill told to write the test command with the `purlin_config` tool fails, naming `purlin_config`
