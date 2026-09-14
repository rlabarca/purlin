# Feature: skill_verify

> Description: What `skills/verify/SKILL.md` must say. Verify runs the tests and the deliberate
>   breaks and writes the record a gate reads, so its text decides which record a
>   reader believes.
> Scope: skills/verify/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/verify/SKILL.md` opens with a frontmatter block whose `name` is `verify` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:verify` [risk: medium] [origin: eng]
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--record` and `--commit`, and states that `--ci` is CI's flag and is never passed by hand [risk: medium] [origin: eng]
- RULE-3: The last section of `skills/verify/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/verify/SKILL.md` is at most 105 lines [risk: low] [origin: eng]
- RULE-5: The skill states which record counts under which gate: a `ci` record counts under `tested`, `recorded` and `approved`, a `developer` record under `tested` alone, and an uncommitted `local` record under none [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/verify/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: verify` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:verify`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/verify/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--record` and `--commit` on the same line, and one further sentence naming `--ci` and saying it is never passed by hand. Removing that sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/verify/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/verify/SKILL.md` and count its lines; verify the count is at most 105. Appending prose until the file passes 105 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read the record-label table in `skills/verify/SKILL.md`; verify it carries one row each for `ci`, `developer` and `local`, that the `ci` row names all three gates, that the `developer` row names `tested` and neither `recorded` nor `approved`, and that the `local` row reads `nothing`. Changing the `developer` row to name `recorded` fails, naming the gate it found there
