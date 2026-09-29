# Feature: skill_export

> Description: What `skills/export/SKILL.md` must say. Export writes the evidence package for a
>   version, says whether the version is finished, commits only when asked, checks a package
>   against its fingerprint, and says that Purlin makes no claim of compliance.
> Scope: skills/export/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:export`
- RULE-2: The skill runs `scripts/export/package.py` and names each form of the command: bare, `--release <name>`, `--commit` and `--check <file>`
- RULE-3: The skill says that Purlin makes no claim that the software is compliant and that the package is evidence for review in a regulated document and sign-off system
- RULE-4: The skill names the two states, `finished` and `not finished`, and says that a package that is not finished lists the lines of `Left to do` in `left`
- RULE-5: The last section of `skills/export/SKILL.md` names the next step, giving a `→` directive for each outcome
- RULE-6: The whole of `skills/export/SKILL.md` is at most 90 lines

## Proof

- PROOF-1 (RULE-1): The export skill opens with a frontmatter block between two `---` lines that reads `name: export` and `description:` followed, on the same line, by text that is not empty, not a `>` or `|` block and not continued on an indented line, and the command reference has a row in its command tables whose first cell is `purlin:export`; a copy of the skill with the `name:` line removed is reported as naming no skill where `export` is expected, a copy whose description is emptied, moved to the next line, written as a `|` block or continued onto a second line is reported as carrying no one-line description, and a copy of the command reference without the `purlin:export` row is reported as carrying no row for `purlin:export`
- PROOF-2 (RULE-2): The export skill's usage block gives each form of the command a line of its own: bare `purlin:export`, `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`. A line of the skill opens with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"`. A copy of the skill without the bare usage line fails, naming the bare form; a copy without the `--check <file>` usage line fails, naming that form; a copy where the command line is turned into prose that names only the script fails, naming the missing command line
- PROOF-3 (RULE-3): The export skill, read with each line break as a space, carries the sentence `Purlin makes no claim that the software is compliant.` and the words `evidence for review in a regulated document and sign-off system`, each word for word; a copy of the skill without that first sentence does not meet the rule
- PROOF-4 (RULE-4): The export skill, read with each line break as a space, names the states `` `finished` `` and `` `not finished` ``, each in backticks, and carries ``holds the lines of `Left to do` ``
- PROOF-7 (RULE-4): A copy of the export skill whose `not finished` row no longer says it ``holds the lines of `Left to do` `` is reported as not carrying those words
- PROOF-5 (RULE-5): The last heading of the export skill contains `next step`, in any case, and its table gives `Evidence not committed` the line `→ Run: purlin:test --commit`, `No version` the line `→ Run: purlin:export --release <version>`, and a `--check` mismatch the line `→ Export the package again at its tag: purlin:export`
- PROOF-13 (RULE-5): The closing table of the export skill gives `not finished` the line `→ Run: <the command of the first line of left>`, and `finished` the line `→ Hand .purlin/evidence/package/<version>.json to the system of record.`
- PROOF-8 (RULE-5): A copy of the export skill with its closing section removed, so that its last heading is `Checking a package`, is reported as closing on a section that does not name the next step
- PROOF-9 (RULE-5): A copy of the export skill with every `→` taken out of its closing section is reported as giving no directive
- PROOF-10 (RULE-5): A copy of the export skill cut after the first outcome row of its closing table is reported as naming 1 outcome where at least 2 are expected
- PROOF-11 (RULE-5): A copy of the export skill whose `finished` row has lost its `→` is reported as an outcome that gives no directive
- PROOF-12 (RULE-5): A copy of the export skill whose closing table has no row for a `--check` mismatch is reported as having no row for that outcome
- PROOF-6 (RULE-6): Read `skills/export/SKILL.md` and count its lines; verify the count is at most 90. Appending prose until the file passes 90 lines fails, and the failure reports the count it found beside the ceiling
