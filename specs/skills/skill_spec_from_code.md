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

- PROOF-1 (RULE-1): The `purlin:spec-from-code` skill opens with a frontmatter block reading `name: spec-from-code` and a `description:` of one line of text, and Purlin's command reference names `purlin:spec-from-code`. A skill whose `name:` line is deleted, or reads anything but `spec-from-code`, fails, and the failure names the skill file, the name it found and `spec-from-code`; a `description:` left empty, or opened as a folded block with `>`, fails as carrying no one-line description
- PROOF-2 (RULE-2): The skill has a section headed `Before you start` that names `sync_status`, `.purlin/config.json` and `purlin:init`. With that section removed the skill fails, and the failure says it has no section that runs before the survey; with any one of the three names dropped from the section, it fails naming the one that is missing
- PROOF-3 (RULE-3): The skill's last section is headed `When you are done`, or by a heading naming the next step; it lists at least two outcomes, each as a list item or a table row, and carries at least one `→` directive. With that section removed the skill fails, naming the heading of the section that is now last; a closing section that lists one outcome fails with the count 1 beside the 2 expected
- PROOF-4 (RULE-4): Read `skills/spec-from-code/SKILL.md` and count its lines; verify the count is at most 130. Appending prose until the file passes 130 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Every example rule the skill shows, each line opening `- RULE-`, carries `[level: passed]`, and the skill says "Do not write `[level: strong]` or `[level: signed]`". With one example rule changed to `[level: strong]` the skill fails, printing that rule's line; a skill that shows no example rule fails too
- PROOF-6 (RULE-6): The skill carries the instruction to `offer to add the marker comment above that test`, the marker `purlin: <feature> PROOF-<n>`, the instruction to `write no new test` and the words `is not that test`, each found even where the skill breaks it across two lines. With the sentence that offers the marker deleted the skill fails, naming each of the three phrases it no longer carries
