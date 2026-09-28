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

- PROOF-1 (RULE-1): The export skill opens with a frontmatter block between two `---` lines that reads `name: export` and `description:` followed, on the same line, by text that is not empty, not a `>` or `|` block and not continued on an indented line, and the command reference has a row in its command tables whose first cell is `purlin:export`; a copy of the skill with the `name:` line removed is reported as naming no skill where `export` is expected, a copy whose description is emptied, moved to the next line, written as a `|` block or continued onto a second line is reported as carrying no one-line description, and a copy of the command reference without the `purlin:export` row is reported as carrying no row for `purlin:export`
- PROOF-2 (RULE-2): The export skill's usage block gives each form of the command a line of its own: bare `purlin:export`, `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`. A line of the skill opens with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"`. A copy of the skill without the bare usage line fails, naming the bare form; a copy without the `--check <file>` usage line fails, naming that form; a copy where the command line is turned into prose that names only the script fails, naming the missing command line
- PROOF-3 (RULE-3): The export skill, read with each line break as a space, carries the sentence `Purlin makes no claim that the software is compliant.` and the words `evidence for review in a regulated document and sign-off system`, each word for word; a copy of the skill without that first sentence does not meet the rule
- PROOF-4 (RULE-4): The export skill, read with each line break as a space, names the states `` `work in progress` ``, `` `gate <gate> met` `` and `` `signed` ``, each in backticks, and carries ``Only `purlin:sign` writes a package whose state is `signed` ``. A copy in which that sentence ends in `` `gate <gate> met` `` does not meet the rule, and the failure names the sentence it lacks
- PROOF-5 (RULE-5): The last heading of the export skill contains the words `next step`, in any case, and the table under it has five outcome rows below its header, each with its own `→` directive: `Evidence not committed` gives `→ Run: purlin:test --commit`, `` `work in progress` `` gives `→ Run: purlin:status`, `` `gate <gate> met` at the gate `signed` `` gives `→ Run: purlin:sign`, `` `signed` `` gives `→ Hand .purlin/evidence/package/<version>.json to the system of record.` and `` `--check` named a mismatch `` gives `→ Export the package again at its tag: purlin:export`. With that section removed the last heading is `Checking a package`, and the skill fails; with every `→` taken out it fails as giving no directive; cut to one row it fails with the count 1 beside the 2 expected; the `signed` row without its `→` fails, naming that row; and a table without the mismatch row fails, naming that outcome
- PROOF-6 (RULE-6): Read `skills/export/SKILL.md` and count its lines; verify the count is at most 90. Appending prose until the file passes 90 lines fails, and the failure reports the count it found beside the ceiling
