# Feature: skill_spec_from_code

> Description: What `skills/spec-from-code/SKILL.md` must say. The skill reads a codebase that has
>   no specs and writes the rules it already implies, which is the one place a rule
>   enters the project without a person asking for it.
> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec-from-code/SKILL.md` opens with a frontmatter block whose `name` is `spec-from-code` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec-from-code`
- RULE-2: The skill calls `sync_status` before it surveys anything and sends the reader to `purlin:init` when the project carries no `.purlin/config.json`
- RULE-3: The last section of `skills/spec-from-code/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/spec-from-code/SKILL.md` is at most 130 lines [level: passed]
- RULE-5: Every rule the skill writes carries `[level: passed]`, and the skill forbids `[level: strong]` and `[level: signed]`
- RULE-6: Where an existing test already shows what a proof the skill writes asks, the skill offers to add the marker comment `purlin: <feature> PROOF-<n>` above that test and writes no new test, and a test that shows only part of it is left unmarked

## Proof

- PROOF-1 (RULE-1): The `purlin:spec-from-code` skill opens with a frontmatter block reading `name: spec-from-code` and a `description:` of one line of text. Purlin's command reference has a table row whose first cell is `` `purlin:spec-from-code [dir]` `` and whose second cell holds its purpose. A skill whose `name:` line is deleted fails, naming the skill file and the expected name `spec-from-code`. A `description:` left empty, moved to the line below, opened as a `|` block or run on to an indented second line fails as carrying no one-line description. A command reference without that row fails, saying it carries no row for `purlin:spec-from-code`
- PROOF-2 (RULE-2): The skill has a section headed `Before you start`, placed before its `Procedure` section, that names `sync_status` and says ``When the project has no `.purlin/config.json`, run `purlin:init` first``. With that section removed the skill fails, saying it has no section that runs before the survey. With the section moved after `Procedure` it fails, saying the start section comes after the Procedure section. With the condition reworded to ``Read `.purlin/config.json`, then run `purlin:init` first`` it fails, saying it does not send the reader to `purlin:init` when `.purlin/config.json` is missing
- PROOF-3 (RULE-3): The skill's last section is headed `When you are done` and lists at least two outcomes as list items, each carrying its own `→` directive. With that section removed the skill fails, naming `What not to do`, the heading of the section that is then last. With every `→` taken out it fails as giving no directive. Cut to one outcome it fails with the count 1 beside the 2 expected. The outcome for rules with no test fails without its `→`, naming that outcome
- PROOF-4 (RULE-4): Read `skills/spec-from-code/SKILL.md` and count its lines; verify the count is at most 130. Appending prose until the file passes 130 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The skill says ``Every rule this skill writes carries `[level: passed]` ``. Every example rule it shows, each line opening `- RULE-`, carries `[level: passed]`, and the skill says "Do not write `[level: strong]` or `[level: signed]`". With one example rule changed to `[level: strong]` the skill fails, printing that rule's line. With the example rules removed it fails as showing no example rule. With the stating sentence replaced by `For example:` it fails, naming the sentence it lacks
- PROOF-6 (RULE-6): In the paragraph on a test that already shows what a proof asks, the skill says to `offer to add the marker comment above that test`, gives the marker `purlin: <feature> PROOF-<n>` and says to `write no new test`. One sentence says `A test that shows part of what the proof asks is not that test` and to `leave it unmarked`. Each is found even where the skill breaks it across two lines. With `leave it unmarked` deleted the skill fails, naming the sentence it no longer finds. With the offer moved to a paragraph of its own it fails, saying the marker is not offered in the paragraph on a test that already shows the proof
