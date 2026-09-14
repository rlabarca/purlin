# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated and how the
>   skill hands over to the build.
> Scope: skills/spec/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec` [risk: medium] [origin: eng]
- RULE-2: The skill allocates rule and proof ids against `origin/main` with the `ids.next_ids` helper under `${CLAUDE_PLUGIN_ROOT}/scripts/mcp`, never against the working tree [risk: high] [origin: eng]
- RULE-3: The skill closes by offering the build in one fixed sentence, `Spec created: <name>. Build it now?`, with nothing printed after it [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/spec/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: spec` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:spec`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/spec/SKILL.md`; verify it carries `origin/main`, `ids.next_ids` and `${CLAUDE_PLUGIN_ROOT}/scripts/mcp`, and that the sentence naming `origin/main` also names the working tree as what ids are not allocated against. Removing the `ids.next_ids` fence fails naming `ids.next_ids`
- PROOF-3 (RULE-3): Read `skills/spec/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively and that the text under it carries the line `Spec created: <name>. Build it now?` on its own, inside a fenced block. Rewording the offer to `Spec written. Shall I build it?` fails, printing the closing section it read
- PROOF-4 (RULE-4): Read `skills/spec/SKILL.md` and count its lines; verify the count is at most 210. Appending prose until the file passes 210 lines fails, and the failure reports the count it found beside the ceiling
