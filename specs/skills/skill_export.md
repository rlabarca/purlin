# Feature: skill_export

> Description: What `skills/export/SKILL.md` must say. Export writes the evidence package for a
>   version, says where the version stands, commits only when asked, checks a package against
>   its fingerprint, and says that Purlin makes no claim of compliance.
> Scope: skills/export/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:export`
- RULE-2: The skill runs `scripts/export/package.py` and names each form of the command: bare, `--release <name>`, `--commit` and `--check <file>`
- RULE-3: The skill says that Purlin makes no claim that the software is compliant and that the package is evidence for review in a regulated document and sign-off system
- RULE-4: The skill names the three states, `work in progress`, `gate <gate> met` and `signed`, and says that only `purlin:sign` writes a package whose state is `signed`
- RULE-5: The last section of `skills/export/SKILL.md` names the next step, giving a `→` directive for each outcome
- RULE-6: The whole of `skills/export/SKILL.md` is at most 90 lines [level: passed]

## Proof

- PROOF-1 (RULE-1): The export skill opens with a frontmatter block between two `---` lines that reads `name: export` and `description:` followed, on the same line, by text that is neither empty nor a folded `>`, and the command reference carries `purlin:export`; a copy of the skill with the `name:` line removed, or naming any skill but `export`, does not meet the rule
- PROOF-2 (RULE-2): The export skill, read with each line break as a space, carries the script path `scripts/export/package.py` and the commands `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`, each word for word; a copy of the skill without the `purlin:export --check <file>` line does not meet the rule
- PROOF-3 (RULE-3): The export skill, read with each line break as a space, carries the sentence `Purlin makes no claim that the software is compliant.` and the words `evidence for review in a regulated document and sign-off system`, each word for word; a copy of the skill without that first sentence does not meet the rule
- PROOF-4 (RULE-4): The export skill, read with each line break as a space, names the states `` `work in progress` ``, `` `gate <gate> met` `` and `` `signed` ``, each in backticks, and carries ``Only `purlin:sign` writes a package whose state is``; a copy of the skill without that sentence does not meet the rule
- PROOF-5 (RULE-5): The last heading of the export skill contains the words `next step`, in any case, and the section under it holds at least two lines that open a table row or a list item and at least one `→`; with that section removed the last heading is `Checking a package`, and the skill does not meet the rule
- PROOF-6 (RULE-6): Read `skills/export/SKILL.md` and count its lines; verify the count is at most 90. Appending prose until the file passes 90 lines fails, and the failure reports the count it found beside the ceiling
