# Feature: skill_rename

> Description: What `skills/rename/SKILL.md` must say. Rename moves a feature name everywhere Purlin
>   wrote it, in one commit, because a name left behind points a live test, a
>   signature or a record at a spec that no longer exists.
> Scope: skills/rename/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/rename/SKILL.md` opens with a frontmatter block whose `name` is `rename` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:rename` [risk: medium] [origin: eng]
- RULE-2: The skill moves the files with `git mv` so history follows them, and calls `sync_status` afterwards, treating any unresolved reference it reports as a miss to fix before the commit [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/rename/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/rename/SKILL.md` is at most 85 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/rename/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: rename` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:rename`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/rename/SKILL.md`; verify the numbered steps carry `git mv` and `sync_status` in that order, comparing their offsets, and that the `sync_status` step names an unresolved reference as a miss. Reordering the two steps fails on the offset comparison
- PROOF-3 (RULE-3): Read `skills/rename/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/rename/SKILL.md` and count its lines; verify the count is at most 85. Appending prose until the file passes 85 lines fails, and the failure reports the count it found beside the ceiling
