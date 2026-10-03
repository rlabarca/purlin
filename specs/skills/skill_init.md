# Feature: skill_init

> Description: What `skills/init/SKILL.md` must name. The init skill sets a project up for
>   Purlin, so its text is the only place a reader learns which script runs, with which
>   flags, and which files it writes.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 89
> Highest-Proof: 102

## Rules

- RULE-87: The skill names what a reader needs to run setup: the line that runs `scripts/init/scaffold.py` through the interpreter lookup, `scripts/purlin_python.sh`, passing `--project-root`; only flags the script takes; the files setup writes, `.purlin/config.json`, `.purlin/evidence/` and `specs/`; and the references `references/supported_frameworks.md` and `references/formats/marker_format.md`
- RULE-88: For an upgrade the skill tells the agent to list the pending migrations with the script's input empty, to stop and ask the person about each migration and each proposed test command, and to pass each answer as a flag: `--apply` for the migrations and `--test-command` for a command
- RULE-89: For a project 0.9.5 did not set up the skill names the four files the update restores, and tells the agent to list them with the script's input empty, to stop and ask the person whether to restore them, and to run the script with `--update` and `--yes`; each line it quotes as printed is one the script prints there

## Proof

- PROOF-2 (RULE-87): A reader of the init skill finds one line that runs `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with `--project-root`
- PROOF-24 (RULE-87): The setup script is asked for its usage with `--help`; it exits 0, and every flag the init skill hands a reader, on its lines that run the script and in its flag table, is one the usage lists
- PROOF-42 (RULE-87): A reader of the init skill finds it names `.purlin/config.json`, `.purlin/evidence/`, `specs/`, `references/supported_frameworks.md` and `references/formats/marker_format.md`
- PROOF-99 (RULE-88): A reader of the init skill's part on bringing a 0.9.5 project forward finds a line that runs the setup script with `--update` and `< /dev/null`, then a `Stop and ask` step naming each migration and each proposed test command, then a line that runs it with `--update`, `--apply` and `--test-command`
- PROOF-100 (RULE-88): The setup script run with `--update --apply` and `--test-command`, as that line of the init skill gives them, on a project 0.9.5 set up asks no question and applies the migration named alone
- PROOF-101 (RULE-89): A reader of the init skill's part on restoring a file setup writes finds `.gitignore`, `.purlin/evidence/README.md`, `.purlin/config.json` and the dashboard page named, then a `List` step, then a `Stop and ask` step naming the restoring, then a line naming `--update` and `--yes`
- PROOF-102 (RULE-89): That part quotes `<n> files to restore in <folder>:`, `Nothing was restored. Add --yes to restore each file.`, `Restoring <n> files: <files>.`, `restored <file>: <what the file is for>` and `chore(update): restore <files>`; the setup script run with `--update` and its input empty on a sample project this release set up, which lacks two of the files, prints `2 files to restore in <folder>:` first and `Nothing was restored. Add --yes to restore each file.` last, and run with `--update --yes` prints `Restoring 2 files: .gitignore, .purlin/evidence/README.md.` first, `  restored .purlin/evidence/README.md: says what the evidence folder holds` third, and a fourth line ending `as chore(update): restore .gitignore, .purlin/evidence/README.md`
