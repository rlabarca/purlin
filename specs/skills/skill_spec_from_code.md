# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must say. The skill reads a codebase that has
>   no specs and writes the rules it already implies, which is the one place a rule
>   enters the project without a person asking for it.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec-from-code/SKILL.md` opens with a frontmatter block whose `name` is `spec-from-code` and whose `description` is one non-empty line
- RULE-2: Before its procedure, the skill tells the agent to call `sync_status`, and to run `purlin:init` first when the project carries no `.purlin/config.json`
- RULE-3: The last section of `skills/spec-from-code/SKILL.md` tells the agent to name the next step from the state the skill found, and lists at least two such states, each carrying its own `→` directive
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines
- RULE-6: In its paragraph on an existing test that already shows what a proof asks, the skill tells the agent to offer to add the marker comment `purlin: <feature> PROOF-<n>` above that test and to write no new test
- RULE-7: The skill tells the agent to give every source file a rule where it can, and to end the report by listing the source files that got none, for a person or an agent to decide
- RULE-8: The skill tells the agent that an existing test is left untied for one of three reasons, and that the report lists each such test with its reason: it shows only part of what a rule needs, it repeats a test already tied, or it tests code the project does not own
- RULE-9: The skill tells the agent that every rule is written from what its test expects, whether that test passes or not, and that no test is run before the rules are written
- RULE-10: The skill tells the agent to write no rule for a private helper, since rules describe behaviour someone outside the module can see
- RULE-11: `references/purlin_commands.md` carries a table row for `purlin:spec-from-code` with its purpose beside it

## Proof

- PROOF-1 (RULE-1): The spec-from-code skill's file begins with a frontmatter block between two `---` lines; the block reads `name: spec-from-code` and carries a `description:` whose text sits whole on that same line
- PROOF-125 (RULE-11): Purlin's command reference carries a table row whose first cell is the command `purlin:spec-from-code` with its arguments and whose second cell is not empty
- PROOF-2 (RULE-2): The skill has a section headed `Before you start`, placed before its `Procedure` section, that names `sync_status` and says ``When the project has no `.purlin/config.json`, run `purlin:init` first``
- PROOF-3 (RULE-3): The skill's last section says `name the next step from the state` and lists its outcomes as list items, at least two of them, each carrying its own `→` directive
- PROOF-4 (RULE-4): The spec-from-code skill's file, counted line by line, is at most 130 lines long
- PROOF-141 (RULE-4): A copy of the skill padded with lines of prose to exactly 130 lines is accepted
- PROOF-6 (RULE-6): The skill's paragraph on a test that `already shows what a proof asks` says `offer to add the marker comment above that test`, gives the marker `purlin: <feature> PROOF-<n>` and says `write no new test`
- PROOF-7 (RULE-7): One sentence of the skill says `Give every source file a rule where you can`, `end the report by listing the source files that got none` and `for a person or an agent to decide`
- PROOF-8 (RULE-8): One sentence of the skill says `A test is left untied for one of three reasons` and `the report lists each such test with its reason`, and names the three: `it shows only part of what a rule needs`, `it repeats a test already tied` and `it tests code the project does not own`
- PROOF-9 (RULE-9): One sentence of the skill says `Every rule is written from what its test expects, passing or not` and `no test is run first`
- PROOF-145 (RULE-10): The spec-from-code skill carries, read across its line breaks, `Do not write a rule for a private helper.` and `Rules describe behaviour someone outside the module can see`
