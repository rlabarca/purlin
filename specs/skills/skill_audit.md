# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must say. An audit runs the tests, the deliberate
>   breaks where mutation testing is on and the AI audit, reports how good the tests are and
>   writes the audit into the evidence, so its text decides what a reader expects of it and
>   which file the audit they are waiting for lands in.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/audit/SKILL.md` opens with a frontmatter block whose `name` is `audit` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:audit`
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--audit`, and states that a remote runner runs the same script in an arm of its own that nobody runs by hand
- RULE-3: The last section of `skills/audit/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines [level: passed]
- RULE-5: The skill states which evidence counts under which gate, naming both folders: a `ci` file and a `local` file each count under `passed`, `strong` and `signed`
- RULE-6: The skill states that under `passed` the run reads the rules with the AI audit, measures no strength and blocks nothing, ending `Nothing blocks at the gate passed.`, that under `strong` and `signed` it runs the breaks where mutation testing is on and prints the strength beside the minimum, that with `--commit` it commits the evidence as `purlin: evidence at <sha7>`, that it ends with `gate strong: <n> of <rules>`, and that evidence either source wrote counts at every gate
- RULE-7: The skill states that the run writes the audit into `.purlin/evidence/local/<feature>.json`, that a file keeps the newest section per operating system and the newest audit entry per rule, and that `--remote` belongs to `purlin:test`

## Proof

- PROOF-1 (RULE-1): Read `skills/audit/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: audit` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:audit`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/audit/SKILL.md`; verify it carries the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--audit` on the same line, and one further sentence saying a remote runner runs the same script in an arm of its own and that you never run it by hand. Removing that sentence fails naming it
- PROOF-3 (RULE-3): Read `skills/audit/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/audit/SKILL.md` and count its lines; verify the count is at most 105. Appending prose until the file passes 105 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read the source table in `skills/audit/SKILL.md`; verify it carries one row each for `ci` and `local`, that each row names all three gates, and that the file names both `.purlin/evidence/ci/` and `.purlin/evidence/local/`. Dropping a gate from either row fails, naming the gate it could not find
- PROOF-6 (RULE-6): Read the gate table of `skills/audit/SKILL.md`; verify the `passed` row names `not measured` and `Nothing blocks at the gate passed.`, and that the `strong` row names the breaks and the minimum. Verify the file carries `counts here too`, `gate strong: <n> of <rules>` and `purlin: evidence at <sha7>`; removing any of the three fails naming it
- PROOF-7 (RULE-7): Read `skills/audit/SKILL.md` with its line wrapping collapsed; verify it carries ``into `.purlin/evidence/local/<feature>.json` ``, `the newest section per operating system` and `purlin:test --remote`. Dropping the retention sentence fails naming it
