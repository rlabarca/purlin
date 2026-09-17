# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must say. An audit runs the tests and the deliberate
>   breaks and writes the record a gate reads, so its text decides which record a reader
>   believes and what the run does under each gate.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/audit/SKILL.md` opens with a frontmatter block whose `name` is `audit` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:audit` [risk: medium] [origin: eng]
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--record` and `--commit`, and states that `--ci` is CI's flag and is never passed by hand [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/audit/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines [risk: low] [origin: eng]
- RULE-5: The skill states which record counts under which gate: a `ci` record counts under `passed`, `strong` and `signed`, and a `developer` or a `local` record under `passed` alone [risk: high] [origin: eng]
- RULE-6: The skill states that under `passed` the run does the tests only and the record carries test strength `n/a`, and that under `strong` and `signed` a local run is a preview whose record does not count [risk: high] [origin: eng]
- RULE-7: The skill states that `--ci` also writes the briefs under `.purlin/briefs/`, and that `--tag <name>` writes the tag `record/<name>` [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/audit/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: audit` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:audit`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/audit/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--record` and `--commit` on the same line, and one further sentence naming `--ci` and saying it is never passed by hand. Removing that sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/audit/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/audit/SKILL.md` and count its lines; verify the count is at most 105. Appending prose until the file passes 105 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read the record-source table in `skills/audit/SKILL.md`; verify it carries one row each for `ci`, `developer` and `local`, that the `ci` row names all three gates, and that the `developer` and `local` rows each name `passed` and neither `strong` nor `signed`. Changing the `developer` row to name `strong` fails, naming the gate it found there
- PROOF-6 (RULE-6): Read the gate table of `skills/audit/SKILL.md`; verify the `passed` row names `n/a` and says the run does the tests only, and that the `strong` row carries the word `preview` and says the local record does not count. Removing the word `preview` fails naming the row it read
- PROOF-7 (RULE-7): Read `skills/audit/SKILL.md` with its line wrapping collapsed; verify it carries `.purlin/briefs/` in the sentence that names `--ci`, and the literal `record/<name>` beside `--tag`. Renaming the tag prefix fails naming `record/<name>`
