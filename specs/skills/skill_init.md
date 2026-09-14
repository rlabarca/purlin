# Feature: skill_init

> Description: What `skills/init/SKILL.md` must say. The init skill sets a project up for
>   Purlin and changes the gate later, so its text is the only place a reader learns
>   which question they are asked and which script answers it.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/init/SKILL.md` opens with a frontmatter block whose `name` is `init` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:init` [risk: medium] [origin: eng]
- RULE-2: The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}`, passing `--project-root` and `--gate`, and names the `--update`, `--ci`, `--add` and `--dry-run` forms [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/init/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/init/SKILL.md` is at most 240 lines [risk: low] [origin: eng]
- RULE-5: The skill asks one question, what must be true before CI lets a change merge, and names exactly three answers, `tested`, `recorded` and `approved`, with what CI requires under each; the only two further questions are the language of an empty repository and the approver emails under `approved` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/init/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: init` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:init`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/init/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` and each of `--project-root`, `--gate`, `--update`, `--ci`, `--add` and `--dry-run`, one assertion per literal so the failure names the missing one. Dropping the `--dry-run` row fails naming `--dry-run`
- PROOF-3 (RULE-3): Read `skills/init/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/init/SKILL.md` and count its lines; verify the count is at most 240. Appending prose until the file passes 240 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/init/SKILL.md` with its line wrapping collapsed; verify it carries `what must be true before CI lets a change merge` and each of the three gate names `tested`, `recorded` and `approved`, and that the section whose heading names the exceptions carries `empty repository` and `approver emails` and holds exactly two numbered items. Adding a third numbered question to that section fails, reporting three where two were expected
