# Feature: skill_init

> Description: What `skills/init/SKILL.md` must name. The init skill sets a project up for
>   Purlin, so its text is the only place a reader learns which script runs, with which
>   flags, and which files it writes.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 87
> Highest-Proof: 98

## Rules

- RULE-87: The skill names what a reader needs to run setup: the line that runs `scripts/init/scaffold.py` through the interpreter lookup, `scripts/purlin_python.sh`, passing `--project-root`; only flags the script takes; the files setup writes, `.purlin/config.json`, `.purlin/evidence/` and `specs/`; and the references `references/supported_frameworks.md` and `references/formats/marker_format.md`

## Proof

- PROOF-2 (RULE-87): A reader of the init skill finds one line that runs `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with `--project-root`
- PROOF-24 (RULE-87): The setup script is asked for its usage with `--help`; it exits 0, and every flag the init skill hands a reader, on its lines that run the script and in its flag table, is one the usage lists
- PROOF-42 (RULE-87): A reader of the init skill finds it names `.purlin/config.json`, `.purlin/evidence/`, `specs/`, `references/supported_frameworks.md` and `references/formats/marker_format.md`
