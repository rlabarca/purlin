# Feature: skill_build

> Description: What `skills/build/SKILL.md` must say. The build skill loads the rules a feature is
>   bound by, writes the code and the marked tests, and commits the changeset, so its
>   text decides what a commit says about which rule each change serves.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/build/SKILL.md` opens with a frontmatter block whose `name` is `build` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:build`
- RULE-2: The skill tells the agent to choose what to build from `sync_status` and to run the tests through `purlin:test`, never through the test framework directly
- RULE-3: The last section of `skills/build/SKILL.md` tells the agent to name the next step from the summary and `Left to do` that `purlin:test` ended on, and lists the outcomes, each with its own `→` directive except `Nothing left to do.`
- RULE-4: The whole of `skills/build/SKILL.md` is at most 130 lines
- RULE-5: The skill tells the agent to make one commit per build with the `feat(<name>):` subject prefix and a body whose sections open with `Changeset:`, `Decisions:` and `Review:`, the changeset mapping every rule the build addressed as `RULE-N → file:line`, as `references/commit_conventions.md` renders it
- RULE-6: Before it commits, the skill tells the agent to compare the files it created, changed or deleted for the feature with the spec's `> Scope:`, add each new file no entry covers, remove each entry whose file was deleted, and rewrite the line in the same commit as the code
- RULE-7: For each proof with no marked test the skill tells the agent to look first for an existing test that already shows what the proof asks and offer to add the marker above it, writing nothing new; otherwise to write an ordinary test in the project's own framework, folder and style
- RULE-8: In a section before the one on running the tests, the skill gives the command that starts `scripts/mcp/purlin/markers.py --near-misses` through `scripts/purlin_python.sh` and tells the agent to show each comment it returns with its fix and the reason, ask, and make the edits the person accepts
- RULE-9: The skill tells the agent that `purlin:test` suggests a test command for each test tool it recognises and writes them where none is set, and that the agent writes no test command itself
- RULE-10: The skill tells the agent never to leave the Changeset section out of a build commit, as `references/commit_conventions.md` says
- RULE-11: The skill tells the agent to leave Decisions out when every rule had one obvious implementation and Review out when nothing needs a second pass, as `references/commit_conventions.md` says
- RULE-12: The skill tells the agent that a test's marker is one comment on the line above it, `purlin: <feature> PROOF-<n>`
- RULE-13: The skill tells the agent that where a rule has no proof the marker names the rule's own id

## Proof

- PROOF-1 (RULE-1): The build skill's file opens with a frontmatter block between two `---` lines that reads `name: build` and carries a `description:` whose text sits whole on that line; the command reference carries a table row whose first cell is `purlin:build` and whose second cell gives its purpose
- PROOF-2 (RULE-2): The build skill's section on choosing what to build names `sync_status`; its section on running the tests gives `purlin:test <name>` alone on a line in a fenced block and says `Never run the test framework directly.`; and no fenced block in the skill runs a test framework itself, such as `pytest`, `jest`, `go test` or `dotnet test`
- PROOF-3 (RULE-3): The last section of the build skill is headed `When you are done` and says to name the next step from the summary and `Left to do` that `purlin:test` ended on; every outcome it lists gives its own `→` directive, except a finished project at the gate `passed` or `strong`, which reads `Nothing left to do.` and names no command
- PROOF-4 (RULE-4): The build skill's file is at most 130 lines long
- PROOF-5 (RULE-5): The build skill's section on committing says `One commit per build`, names the `feat(<name>):` prefix, says the body's three sections open with `Changeset:`, `Decisions:` and `Review:`, gives the line form `RULE-N → file:line`, and names `references/commit_conventions.md` as the rendering to follow
- PROOF-35 (RULE-10): The build skill says `Changeset is never omitted.`, and the commit conventions' table of the build commit's sections gives `Never` as when Changeset is left out
- PROOF-36 (RULE-11): The build skill says in one sentence to omit Decisions when every rule had one obvious implementation and Review when nothing needs a second pair of eyes; the commit conventions' table leaves Decisions out `When every rule had one obvious implementation` and Review `When nothing needs a second pass`
- PROOF-37 (RULE-5): The commit conventions' example of a build commit opens with `feat(auth_login): `; a line reading `Changeset:` stands before the mapped lines; every rule the subject names is mapped on a line of its own as `RULE-N → <file>:<line>`; and a `Decisions:` and a `Review:` section follow the changeset
- PROOF-6 (RULE-6): The build skill's section on committing says to compare the files created, changed or deleted for the feature with its `> Scope:`, then to add each new file no entry covers, remove each entry whose file was deleted, and rewrite the line in the same commit as the code
- PROOF-7 (RULE-7): For each proof with no test marked for it, the build skill gives first the step `Look first for a test that already shows it.`, saying to offer to add the marker above such a test and write nothing new, and then the step `Otherwise write an ordinary test` in the project's own framework, folder and style
- PROOF-40 (RULE-12): The build skill's example shows the comment `# purlin: login PROOF-1` on the line directly above a `def test_` line
- PROOF-41 (RULE-13): One sentence of the build skill says that where a rule has no proof the marker names the rule, as in `purlin: login RULE-2`
- PROOF-9 (RULE-8): The build skill gives, in a fenced block, the line `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root .`, in a section before the one on running the tests, and one sentence says to show each `fix` beside its `why`, ask, and make the edits accepted
- PROOF-11 (RULE-9): The build skill's section on running the tests says that where no test command is set `purlin:test` suggests one for each test tool it recognises and writes them once the person confirms, and says `write no entry yourself`; nowhere does the skill name the `purlin_config` tool
