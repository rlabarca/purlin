# Feature: skill_find

> Description: What `skills/find/SKILL.md` must say. Find locates a spec by name and shows the state
>   of each of its rules. It writes nothing.
> Scope: skills/find/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/find/SKILL.md` opens with a frontmatter block whose `name` is `find` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:find` [risk: medium] [origin: eng]
- RULE-2: The skill reads the state from `sync_status` rather than counting rules itself, and it shows the risk and the origin columns only when the spec carries them [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/find/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/find/SKILL.md` is at most 85 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/find/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: find` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:find`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/find/SKILL.md`; verify it names `sync_status`, and that the sentence about the risk and origin columns names both `risk` and `origin` and the `passed` gate under which they are optional. Deleting that sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/find/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/find/SKILL.md` and count its lines; verify the count is at most 85. Appending prose until the file passes 85 lines fails, and the failure reports the count it found beside the ceiling
