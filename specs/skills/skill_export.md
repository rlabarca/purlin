# Feature: skill_export

> Description: What `skills/export/SKILL.md` must say. Export writes the evidence package for a
>   version, says whether the version is finished, commits only when asked, checks a package
>   against its fingerprint, and says that Purlin makes no claim of compliance.
> Scope: skills/export/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 13
> Highest-Proof: 35

## Rules

- RULE-1: `skills/export/SKILL.md` tells the agent the skill's name, `export`, and its purpose in one non-empty line, in a frontmatter block at its top
- RULE-2: The skill tells the agent the command line that runs `scripts/export/package.py` through `scripts/purlin_python.sh`
- RULE-3: The skill tells the agent that Purlin makes no claim that the software is compliant
- RULE-4: The skill tells the agent the package's two states, `finished` and `not finished`
- RULE-5: The last section of the skill tells the agent the next step, under a heading with the words `next step`
- RULE-6: The skill gives the agent its instructions in at most 90 lines, the whole of `skills/export/SKILL.md`
- RULE-7: The table of commands in `references/purlin_commands.md` tells the agent that `purlin:export` exists, in a row carrying its purpose
- RULE-8: The skill tells the agent each form of the command on a line of its own: bare, `--release <name>`, `--commit` and `--check <file>`
- RULE-9: The skill tells the agent that the package is evidence for review in a regulated document and sign-off system
- RULE-10: The skill tells the agent that a package that is not finished lists the lines of `Left to do` in `left`
- RULE-11: The last section of the skill tells the agent a `→` directive for each outcome of an export: evidence not committed, no version, `not finished`, `finished` and a `--check` mismatch
- RULE-12: The skill tells the agent the line the script prints when no version is stated, `No version: nothing in this project states one. Run purlin:export --release <version>, or write it to a VERSION file.`
- RULE-13: The skill tells the agent that the package is read in the system of record, and that the system of record holds the controlled document, the authority to sign it off and the signature that counts under the regulation

## Proof

- PROOF-1 (RULE-1): The export skill opens with a frontmatter block set between two `---` lines; in it `name:` reads `export`, and `description:` is followed on the same line by text
- PROOF-14 (RULE-7): The plugin's command reference has a row in a table headed `Command` and `Purpose` whose first cell is `` `purlin:export` `` and whose second cell holds its purpose
- PROOF-2 (RULE-8): The export skill gives each form of the command a line that begins with it: `purlin:export`, `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`
- PROOF-21 (RULE-2): A line of the export skill begins with `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"` followed by `"${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"`
- PROOF-3 (RULE-3): The export skill, its line breaks read as spaces, carries the sentence `Purlin makes no claim that the software is compliant.` word for word
- PROOF-25 (RULE-9): The export skill, its line breaks read as spaces, carries the words `The package is evidence for review in a regulated document and sign-off system` word for word
- PROOF-4 (RULE-4): The export skill's table headed `State` has two rows, `` `finished` `` and then `` `not finished` ``
- PROOF-27 (RULE-10): In the export skill's table of states, the row for `` `not finished` `` says ``` `left` holds the lines of `Left to do` ```
- PROOF-5 (RULE-5): The last heading of the export skill contains the words `next step`, in any case
- PROOF-29 (RULE-11): The closing table of the export skill gives `Evidence not committed` the line `→ Run: purlin:test --commit`, `No version` the line `→ Run: purlin:export --release <version>`, and a `--check` mismatch the line `→ Run: git show signed/<version>:.purlin/evidence/package/<version>.json`
- PROOF-13 (RULE-11): The closing table of the export skill gives `not finished` the line `→ Run: <the command of the first line of left>`, and `finished` the line `→ Hand .purlin/evidence/package/<version>.json to the system of record.`
- PROOF-30 (RULE-11): The closing table of the export skill has 5 outcome rows, and the line each one gives begins with `→`
- PROOF-34 (RULE-12): The export skill, its line breaks read as spaces, quotes `No version: nothing in this project states one. Run purlin:export --release <version>, or write it to a VERSION file.` word for word
- PROOF-6 (RULE-6): The export skill, counted line by line, is at most 90 lines
- PROOF-35 (RULE-13): The export skill, its line breaks read as spaces, carries the words `reads it in the system of record, which holds the controlled document, the authority to sign it off and the signature that counts under the regulation` word for word
