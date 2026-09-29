# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must say. The skill reads a codebase that has
>   no specs and writes the rules it already implies, which is the one place a rule
>   enters the project without a person asking for it.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec-from-code/SKILL.md` opens with a frontmatter block whose `name` is `spec-from-code` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a table row for `purlin:spec-from-code` with its purpose beside it
- RULE-2: Before its procedure, the skill tells the reader to call `sync_status`, and to run `purlin:init` first when the project carries no `.purlin/config.json`
- RULE-3: The last section of `skills/spec-from-code/SKILL.md` tells the reader to name the next step from the state the skill found, and lists at least two such states, each carrying its own `→` directive
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines
- RULE-6: In its paragraph on an existing test that already shows what a proof asks, the skill tells the reader to offer to add the marker comment `purlin: <feature> PROOF-<n>` above that test and to write no new test
- RULE-7: The skill tells the reader to give every source file a rule where it can, and to end the report by listing the source files that got none, for a person or an agent to decide
- RULE-8: The skill says an existing test is left untied for one of three reasons, and that the report lists each such test with its reason: it shows only part of what a rule needs, it repeats a test already tied, or it tests code the project does not own
- RULE-9: The skill says every rule is written from what its test expects, whether that test passes or not, and that no test is run before the rules are written

## Proof

- PROOF-1 (RULE-1): The spec-from-code skill's file begins with a frontmatter block between two `---` lines; the block reads `name: spec-from-code` and carries a `description:` whose text sits whole on that same line
- PROOF-125 (RULE-1): Purlin's command reference carries a table row whose first cell is the command `purlin:spec-from-code` with its arguments and whose second cell is not empty
- PROOF-126 (RULE-1): A copy of the skill with its `name:` line deleted is refused, and the refusal names the skill's file and the expected name `spec-from-code`
- PROOF-127 (RULE-1): A copy of the skill whose `description:` line has nothing after it is refused as carrying no one-line description
- PROOF-128 (RULE-1): A copy of the skill whose description text is moved to the line below an empty `description:` is refused as carrying no one-line description
- PROOF-129 (RULE-1): A copy of the skill whose `description:` opens a `|` block, its text on the indented line below, is refused as carrying no one-line description
- PROOF-130 (RULE-1): A copy of the skill whose description runs on to a second, indented line is refused as carrying no one-line description
- PROOF-131 (RULE-1): A copy of the command reference without the `purlin:spec-from-code` table row, though the name still appears elsewhere in it, is refused, and the refusal says the reference carries no row for `purlin:spec-from-code`
- PROOF-2 (RULE-2): The skill has a section headed `Before you start`, placed before its `Procedure` section, that names `sync_status` and says ``When the project has no `.purlin/config.json`, run `purlin:init` first``
- PROOF-132 (RULE-2): A copy of the skill without its `Before you start` section is refused, saying the skill has no section that runs before the survey
- PROOF-133 (RULE-2): A copy of the skill with its `Before you start` section moved below `Procedure` is refused, saying the start section comes after the Procedure section
- PROOF-134 (RULE-2): A copy of the skill whose start section reads ``Read `.purlin/config.json`, then run`` in place of the condition is refused, saying it does not send the reader to `purlin:init` when `.purlin/config.json` is missing
- PROOF-135 (RULE-2): A copy of the skill whose start section no longer says ``Call `sync_status`.`` is refused, saying the start section does not name `sync_status`
- PROOF-3 (RULE-3): The skill's last section says `name the next step from the state` and lists its outcomes as list items, at least two of them, each carrying its own `→` directive
- PROOF-136 (RULE-3): A copy of the skill with its last section deleted is refused, and the refusal names `What not to do`, the section that is then last, as not naming the next step
- PROOF-137 (RULE-3): A copy of the skill whose last section has every `→` replaced by `->` is refused as giving no directive
- PROOF-138 (RULE-3): A copy of the skill whose last section is cut after its first outcome is refused, with the count 1 beside the 2 expected
- PROOF-139 (RULE-3): A copy of the skill whose outcome `Rules with no test at all` loses its `→` is refused, and the refusal names that outcome as giving no directive
- PROOF-140 (RULE-3): A copy of the skill whose last section says `name the next step:` with `from the state` taken out is refused, saying the section does not name the next step from the state
- PROOF-4 (RULE-4): The spec-from-code skill's file, counted line by line, is at most 130 lines long
- PROOF-141 (RULE-4): A copy of the skill padded with lines of prose to exactly 130 lines is accepted
- PROOF-142 (RULE-4): A copy of the skill padded with lines of prose to 131 lines is refused, and the refusal gives the count 131 beside the ceiling 130
- PROOF-6 (RULE-6): The skill's paragraph on a test that `already shows what a proof asks` says `offer to add the marker comment above that test`, gives the marker `purlin: <feature> PROOF-<n>` and says `write no new test`
- PROOF-10 (RULE-6): A copy of the skill with the offer of the marker moved to a paragraph of its own is refused, saying the marker is not offered in the paragraph on a test that already shows the proof
- PROOF-143 (RULE-6): A copy of the skill with `, and write no new test` taken out is refused, saying the skill does not carry `write no new test`
- PROOF-7 (RULE-7): One sentence of the skill says `Give every source file a rule where you can`, `end the report by listing the source files that got none` and `for a person or an agent to decide`
- PROOF-11 (RULE-7): A copy of the skill whose sentence says only `end the report`, without `by listing the source files that got none`, is refused, saying no sentence carries `Give every source file a rule where you can` with the rest
- PROOF-8 (RULE-8): One sentence of the skill says `A test is left untied for one of three reasons` and `the report lists each such test with its reason`, and names the three: `it shows only part of what a rule needs`, `it repeats a test already tied` and `it tests code the project does not own`
- PROOF-12 (RULE-8): A copy of the skill without its third reason, `it tests code the project does not own`, is refused, saying no sentence carries `A test is left untied for one of three reasons` with the rest
- PROOF-9 (RULE-9): One sentence of the skill says `Every rule is written from what its test expects, passing or not` and `no test is run first`
- PROOF-13 (RULE-9): A copy of the skill with `, and no test is run first` taken out is refused, saying no sentence carries `Every rule is written from what its test expects, passing or not` with the rest
- PROOF-144 (RULE-9): A copy of the skill with `, passing or not` taken out is refused, saying no sentence carries `Every rule is written from what its test expects, passing or not` with the rest
