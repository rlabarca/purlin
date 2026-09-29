# Feature: skill_export

> Description: What `skills/export/SKILL.md` must say. Export writes the evidence package for a
>   version, says whether the version is finished, commits only when asked, checks a package
>   against its fingerprint, and says that Purlin makes no claim of compliance.
> Scope: skills/export/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and the table of commands in `references/purlin_commands.md` carries a row for `purlin:export` with its purpose
- RULE-2: The skill gives the command line that runs `scripts/export/package.py` and names each form of the command on a line of its own: bare, `--release <name>`, `--commit` and `--check <file>`
- RULE-3: The skill says that Purlin makes no claim that the software is compliant and that the package is evidence for review in a regulated document and sign-off system
- RULE-4: The skill names the two states, `finished` and `not finished`, and says that a package that is not finished lists the lines of `Left to do` in `left`
- RULE-5: The last section of `skills/export/SKILL.md` is headed with the words `next step` and gives a `→` directive for each outcome of an export: evidence not committed, no version, `not finished`, `finished` and a `--check` mismatch
- RULE-6: The whole of `skills/export/SKILL.md` is at most 90 lines

## Proof

- PROOF-1 (RULE-1): The export skill opens with a frontmatter block set between two `---` lines; in it `name:` reads `export`, and `description:` is followed on the same line by text
- PROOF-14 (RULE-1): The plugin's command reference has a row in a table headed `Command` and `Purpose` whose first cell is `` `purlin:export` `` and whose second cell holds its purpose
- PROOF-15 (RULE-1): A copy of the export skill with its `name:` line deleted fails, finding no name where `export` is expected
- PROOF-16 (RULE-1): A copy of the export skill whose `description:` line has nothing after it fails as carrying no one-line description
- PROOF-17 (RULE-1): A copy of the export skill whose description text is moved to an indented line below `description:` fails as carrying no one-line description
- PROOF-18 (RULE-1): A copy of the export skill whose description is written as a `|` block fails as carrying no one-line description
- PROOF-19 (RULE-1): A copy of the export skill whose description runs on to an indented second line fails as carrying no one-line description
- PROOF-20 (RULE-1): A copy of the command reference with its `purlin:export` row deleted fails as carrying no row for `purlin:export`
- PROOF-2 (RULE-2): The export skill gives each form of the command a line that begins with it: `purlin:export`, `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`
- PROOF-21 (RULE-2): A line of the export skill begins with the command `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"`
- PROOF-22 (RULE-2): A copy of the export skill without the line for the bare `purlin:export` fails, naming the bare form
- PROOF-23 (RULE-2): A copy of the export skill without the line for `purlin:export --check <file>` fails, naming that form
- PROOF-24 (RULE-2): A copy of the export skill whose command lines are each replaced by the prose `Run scripts/export/package.py` fails, naming the command line it no longer finds
- PROOF-3 (RULE-3): The export skill, its line breaks read as spaces, carries the sentence `Purlin makes no claim that the software is compliant.` word for word
- PROOF-25 (RULE-3): The export skill, its line breaks read as spaces, carries the words `The package is evidence for review in a regulated document and sign-off system` word for word
- PROOF-26 (RULE-3): A copy of the export skill without the sentence `Purlin makes no claim that the software is compliant.` fails, naming that sentence
- PROOF-4 (RULE-4): The export skill's table headed `State` has two rows, `` `finished` `` and then `` `not finished` ``
- PROOF-27 (RULE-4): In the export skill's table of states, the row for `` `not finished` `` says ``` `left` holds the lines of `Left to do` ```
- PROOF-7 (RULE-4): A copy of the export skill whose `not finished` row reads `holds the work` in place of ``holds the lines of `Left to do` `` fails, naming the words it no longer finds
- PROOF-28 (RULE-4): A copy of the export skill whose table of states has lost its `not finished` row fails, naming `finished` alone where `finished` and `not finished` are expected
- PROOF-5 (RULE-5): The last heading of the export skill contains the words `next step`, in any case
- PROOF-29 (RULE-5): The closing table of the export skill gives `Evidence not committed` the line `→ Run: purlin:test --commit`, `No version` the line `→ Run: purlin:export --release <version>`, and a `--check` mismatch the line `→ Export the package again at its tag: purlin:export`
- PROOF-13 (RULE-5): The closing table of the export skill gives `not finished` the line `→ Run: <the command of the first line of left>`, and `finished` the line `→ Hand .purlin/evidence/package/<version>.json to the system of record.`
- PROOF-30 (RULE-5): The closing table of the export skill has 5 outcome rows, and the line each one gives begins with `→`
- PROOF-8 (RULE-5): A copy of the export skill with its closing section removed, so that its last heading is `Checking a package`, fails as closing on a section that does not name the next step
- PROOF-31 (RULE-5): A copy of the export skill whose last heading reads `When you are done` fails as closing on a section that does not name the next step
- PROOF-9 (RULE-5): A copy of the export skill with every `→` taken out of its closing section fails as giving no directive
- PROOF-10 (RULE-5): A copy of the export skill cut after the first outcome row of its closing table fails, naming 1 outcome where at least 2 are expected
- PROOF-11 (RULE-5): A copy of the export skill whose `finished` row has lost its `→` fails, naming that row as giving no directive
- PROOF-12 (RULE-5): A copy of the export skill whose closing table has no row for a `--check` mismatch fails, naming that missing row
- PROOF-6 (RULE-6): The export skill, counted line by line, is at most 90 lines
- PROOF-32 (RULE-6): A copy of the export skill with lines of prose added until it is 91 lines fails, naming 91 lines beside the ceiling of 90
- PROOF-33 (RULE-6): A copy of the export skill with lines of prose added until it is exactly 90 lines passes
