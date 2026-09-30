# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must say. The skill reads a codebase that has
>   no specs and writes the rules it already implies, which is the one place a rule
>   enters the project without a person asking for it.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 51

## Rules

- RULE-1: `skills/spec-from-code/SKILL.md` opens with a frontmatter block whose `name` is `spec-from-code` and whose `description` is one non-empty line
- RULE-2: Before its procedure, the skill tells the agent to call `sync_status` with `project_root` set to the project root, the top folder of the git checkout, and to run `purlin:init` first when the project carries no `.purlin/config.json`
- RULE-3: The last section of `skills/spec-from-code/SKILL.md` tells the agent to name the first of three next steps that applies, in this order: `→ Run: purlin:test` for rules whose existing tests now carry their comments, `→ Run: purlin:build <name>` for rules with no test, and `→ Run: purlin:init --gate strong` at the gate `passed`
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines
- RULE-6: In its paragraph on an existing test that already shows what a proof asks, the skill tells the agent to offer to add the marker comment `purlin: <feature> PROOF-<n>` above that test and to write no new test
- RULE-7: The skill tells the agent to end the report on the source files that got no rule, for a person or an agent to decide
- RULE-8: The skill tells the agent that an existing test is left untied for one of five reasons, and that the report lists each such test with its reason: it shows only part of what a rule needs, it repeats a test already tied, it tests code the project does not own, it cannot carry a comment, or it tests code no caller can reach
- RULE-9: The skill tells the agent that every rule is written from what its test expects, whether that test passes or not, and that no test is run before the rules are written
- RULE-10: The skill tells the agent to write no rule for code no caller outside the project can reach, and to list its files among the files with no rule
- RULE-11: `references/purlin_commands.md` carries a table row for `purlin:spec-from-code` with its purpose beside it
- RULE-33: The skill tells the agent to write `.purlin/runtime/spec-from-code.json` after each commit, holding `features`, the agreed list in order, and `written`, each feature committed so far, and to go on with the first feature not in `written` when a session finds the file
- RULE-34: The skill tells the agent to commit each spec on its own, with the `spec(<name>):` prefix and the comments it adds above existing tests
- RULE-35: The skill tells the agent to run `git branch --show-current` before the first commit and, when it prints nothing, to make a branch with `git switch -c <name>`
- RULE-36: The skill tells the agent to report one line per feature, giving its rules, its proofs, how many proofs an existing test already shows and how many have no test
- RULE-37: The skill tells the agent to write rules that features share once, in an anchor made first with `purlin:anchor create <name>`, which each feature names with `> Requires: <name>`, and that `> Requires:` names anchors only
- RULE-38: The skill tells the agent that a commented-out test, or a benchmark the project's test command does not run, is not a test, and is left alone and counted nowhere
- RULE-39: The spec the skill shows as the shape of what it writes carries `> Highest-Rule:` after its other `>` lines, holding its highest rule number
- RULE-40: The skill's first step walks the tree once, noting the entry points, the modules with real branching, the configuration surface and the test files, and ignoring generated code, vendored dependencies and build output
- RULE-41: The skill tells the agent to group the behaviour into features and print the list with a one-line description and the files each would carry in `> Scope:`
- RULE-42: The skill tells the agent to show the list of features and stop until the person says it is right
- RULE-43: The skill tells the agent to write one spec at a time, in the order its dependency step sets
- RULE-44: The skill tells the agent that every rule it writes is a draft until a person reads it, and to say so when handing the result over
- RULE-45: The skill tells the agent not to copy an implementation into a rule
- RULE-46: The skill tells the agent not to write evidence or signatures
- RULE-47: The skill tells the agent to drop a rule it could not state as an observable and note the behaviour in `> Description:`
- RULE-48: The skill tells the agent what a caller reaches: in Python the names `__all__` lists, or with none the names with no leading underscore; in JavaScript what `package.json`'s `main` or `exports` reaches; in C# the `public` types of a project that is not a test project
- RULE-49: The skill tells the agent that twenty to forty features is normal for a mid-sized service and that two hundred means the grouping is too fine
- RULE-50: The skill tells the agent that a proof an existing test already shows says what that test shows and never names the test
- RULE-51: The skill tells the agent that a test of the test suite's own helpers tests code no caller can reach

## Proof

- PROOF-1 (RULE-1): The spec-from-code skill's file begins with a frontmatter block between two `---` lines; the block reads `name: spec-from-code` and carries a `description:` whose text sits whole on that same line
- PROOF-125 (RULE-11): Purlin's command reference carries a table row whose first cell is the command `purlin:spec-from-code` with its arguments and whose second cell is not empty
- PROOF-2 (RULE-2): The skill's section `Before you start`, placed before `Procedure`, says ``Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout.`` and ``When the project has no `.purlin/config.json`, run `purlin:init` first.``
- PROOF-3 (RULE-3): The skill's last section says `name the first of these that applies:` and lists, numbered 1 to 3 in this order, `→ Run: purlin:test`, `→ Run: purlin:build <name>` and `→ Run: purlin:init --gate strong`, the third beside ``At the gate `passed` ``
- PROOF-4 (RULE-4): The spec-from-code skill's file, counted line by line, is at most 130 lines long
- PROOF-141 (RULE-4): A copy of the skill padded with lines of prose to exactly 130 lines is accepted
- PROOF-6 (RULE-6): The skill's paragraph on a test that `already shows what a proof asks` says `offer to add the marker comment above that test`, gives the marker `purlin: <feature> PROOF-<n>` and says `write no new test`
- PROOF-7 (RULE-7): The skill's report step ends on the sentence part `and last the source files that got no rule, for a person or an agent to decide.`
- PROOF-8 (RULE-8): One sentence of the skill says `A test is left untied for one of five reasons`, that the report lists each with its reason, and the five: it shows only part of what a rule needs, repeats a test already tied, tests code the project does not own, cannot carry a comment, or tests code no caller can reach
- PROOF-9 (RULE-9): One sentence of the skill says `Every rule is written from what its test expects, passing or not` and `no test is run first`
- PROOF-145 (RULE-10): The skill's section `What not to do` says, read across its line breaks, `Do not write a rule for code no caller outside the project can reach: list its files among the files with no rule.`
- PROOF-146 (RULE-48): The skill's section `What not to do` names what a caller reaches in each of Python (`__all__`, no leading underscore), JavaScript (`package.json`'s `main` or `exports`) and C# (the `public` types of a project that is not a test project)
- PROOF-147 (RULE-33): The skill's fifth step says to write `.purlin/runtime/spec-from-code.json` after each commit as `{"features": [<the agreed list, in order>], "written": [<each feature committed so far>]}`, and that a session finding it goes on with the first feature not in `written`
- PROOF-148 (RULE-34): The skill's fifth step says, read across its line breaks, ``committing each spec with the comments it adds above existing tests, on its own, with the `spec(<name>):` prefix``
- PROOF-149 (RULE-34): The commit conventions' `spec(<name>):` row reads, in its second cell, ``from `purlin:spec-from-code`, with the comments it adds above the project's existing tests``
- PROOF-150 (RULE-35): The skill's section `Before you start` gives `git branch --show-current` and says that when it prints nothing, make a branch with `git switch -c <name>` before the first commit
- PROOF-151 (RULE-36): The skill's report step says `Print one line per feature: its rules, its proofs, how many proofs an existing test already shows, and how many have no test.`
- PROOF-152 (RULE-37): The skill's fourth step says to write shared rules once in an anchor with `purlin:anchor create <name>`, first, to have each feature name it with `> Requires: <name>`, and says `> Requires:` names anchors only.
- PROOF-153 (RULE-38): One sentence of the skill says a test that is commented out, or a benchmark the project's test command does not run, `is not a test: leave it and count it nowhere`
- PROOF-154 (RULE-39): The skill's example spec carries the line `> Highest-Rule: 2` after its other `>` lines, and 2 is the highest rule number the example holds
- PROOF-155 (RULE-40): The skill's first step, `Survey`, says `Walk the tree once`, names the entry points, the modules with real branching, the configuration surface and the test files, and says to ignore generated code, vendored dependencies and build output
- PROOF-156 (RULE-41): The skill's second step says to group the behaviour into features and to print the list with a one-line description and the files each would carry in `> Scope:`
- PROOF-157 (RULE-42): The skill's third step says `Show the list and stop.` and to merge, split and rename until the person says it is right
- PROOF-158 (RULE-43): The skill's fifth step opens `Write one spec at a time`, `in that order`, and comes directly after the step headed `Order by dependency`
- PROOF-159 (RULE-44): The skill says every rule it writes `is a draft until a person reads it`, followed by `Say so when you hand the result over.`
- PROOF-160 (RULE-45): The skill's section `What not to do` says `Do not copy an implementation into a rule.`
- PROOF-161 (RULE-46): The skill's section `What not to do` says `Do not write evidence or signatures.`
- PROOF-162 (RULE-47): The skill says ``Drop the rule instead and note the behaviour in `> Description:` `` for a rule it could not state as an observable
- PROOF-163 (RULE-49): The skill's step `Propose a taxonomy`, read across its line breaks, says `Twenty to forty features is normal for a mid-sized service; two hundred means the grouping is too fine.`
- PROOF-164 (RULE-50): The skill's section `Where the proofs come from`, read across its line breaks, says that when a test already shows what a proof asks, the proof says what that test shows and `never names the test`
- PROOF-165 (RULE-51): The skill's section `Where the proofs come from`, read across its line breaks, carries the sentence `A test of the test suite's own helpers tests code no caller can reach.`
