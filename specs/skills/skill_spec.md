# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated and how the
>   skill hands over to the build.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec`
- RULE-2: The skill allocates rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, never against the working tree
- RULE-3: The skill closes by naming `purlin:build` in one fixed line, `Spec saved: <name>. Next: purlin:build <name>`, with nothing printed after it, and never starts building itself
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines [level: passed]
- RULE-5: The skill writes `> Scope:` on every spec it creates, naming the files the requirement touches or the paths `purlin:build` will create, and says that a spec naming no files has its tests run on every `purlin:test` and cannot be signed at the gate `signed`
- RULE-6: Before it saves, the skill prints each rule with its proofs under it and asks whether to change any, saves the spec only once the person is satisfied, and drafts every proof against the guideline for a good proof

## Proof

- PROOF-1 (RULE-1): The spec skill opens with a frontmatter block between two `---` lines, whose `name` reads `spec` and whose `description` carries its value on the same line, neither empty nor the `>` that opens a folded block, and the command reference carries `purlin:spec`. A copy of the skill with its `name:` line deleted fails the check, which names `skills/spec/SKILL.md` and expects `spec`
- PROOF-2 (RULE-2): The spec skill shows the command `git show origin/main:` and says in one sentence that ids are allocated against `origin/main`, not against the working tree. A copy of the skill with that command's block deleted fails the check, which names `git show origin/main:` as missing
- PROOF-3 (RULE-3): The last `## ` section of the spec skill is headed `When you are done`, or otherwise names the next step, in any case; under it the line `Spec saved: <name>. Next: purlin:build <name>` stands on a line of its own, and the section carries the sentence `Never start the build yourself`. A copy of the skill whose line reads `Spec written. Shall I build it?` instead fails the check, which names the missing line `Spec saved: <name>. Next: purlin:build <name>`
- PROOF-4 (RULE-4): Read `skills/spec/SKILL.md` and count its lines; verify the count is at most 210. Appending prose until the file passes 210 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The spec skill says "Write `> Scope:` on every spec you create" and names "the paths `purlin:build` will create", "every run includes it" and "its rules cannot be signed"; and its numbered step that writes the metadata names `> Scope:`. A copy of the skill with the sentence that says to write `> Scope:` deleted fails the check, which names that sentence as missing
- PROOF-6 (RULE-6): The spec skill, read with its line wrapping ignored, carries "Print each rule with its proofs under it and ask whether to change any", "Save the spec when the person is satisfied", "Draft every proof against" and "at least one failure case". A copy of the skill with the step that prints the rules deleted fails the check, which names that step as missing
