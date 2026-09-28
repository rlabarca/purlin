# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated and how the
>   skill hands over to the build.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec`
- RULE-2: The skill allocates rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, never against the working tree
- RULE-3: The skill closes by offering the build in one fixed sentence, `Spec created: <name>. Build it now?`, with nothing printed after it
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines [level: passed]
- RULE-5: The skill writes `> Scope:` on every spec it creates, naming the files the requirement touches or the paths `purlin:build` will create, and says that a spec naming no files has its tests run on every `purlin:test` and cannot be signed at the gate `signed`

## Proof

- PROOF-1 (RULE-1): Read `skills/spec/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: spec` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:spec`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/spec/SKILL.md`; verify it carries `origin/main`, `git show origin/main:`, and that the sentence naming `origin/main` also names the working tree as what ids are not allocated against. Removing the `git show` fence fails naming `git show origin/main:`
- PROOF-3 (RULE-3): Read `skills/spec/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively and that the text under it carries the line `Spec created: <name>. Build it now?` on its own, inside a fenced block. Rewording the offer to `Spec written. Shall I build it?` fails, printing the closing section it read
- PROOF-4 (RULE-4): Read `skills/spec/SKILL.md` and count its lines; verify the count is at most 210. Appending prose until the file passes 210 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/spec/SKILL.md`; verify it carries the sentence that opens `Write` and names `> Scope:` on every spec you create, the phrase naming the paths `purlin:build` will create, the phrase `every run includes it` and the phrase `its rules cannot be signed`, and that its procedure step for the metadata names `> Scope:`. Deleting the sentence that says to write the line fails naming it
