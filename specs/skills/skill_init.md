# Feature: skill_init

> Description: What `skills/init/SKILL.md` must name. The init skill sets a project up for
>   Purlin, so its text is the only place a reader learns which script runs, with which
>   flags, and which files it writes.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 86
> Highest-Proof: 98

## Rules

- RULE-2: The skill names the commands it hands the agent: the line that runs `scripts/init/scaffold.py` through the interpreter lookup, `scripts/purlin_python.sh`, passing `--project-root`; the flags `--project-root`, `--yes` and `--update`, each one the script takes; and `purlin:test`, `purlin:status`, `purlin:spec` and `purlin:build`
- RULE-11: The skill names the files setup writes, `.purlin/config.json`, `.purlin/evidence/` and `specs/`, and the references `references/supported_frameworks.md` and `references/formats/marker_format.md`
- RULE-4: The whole of `skills/init/SKILL.md` is at most 250 lines
- RULE-86: `skills/init/SKILL.md` holds no emoji

## Proof

- PROOF-2 (RULE-2): A reader of the init skill finds one line that runs `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with `--project-root`
- PROOF-23 (RULE-2): A reader of the init skill finds each of the three flags `--project-root`, `--yes` and `--update` on a line that runs the setup script or in the first column of its flag table
- PROOF-24 (RULE-2): The setup script is asked for its usage with `--help`; it exits 0, and every flag the init skill hands a reader, on its lines that run the script and in its flag table, is one the usage lists
- PROOF-97 (RULE-2): A reader of the init skill finds each of the commands `purlin:test`, `purlin:status`, `purlin:spec` and `purlin:build`
- PROOF-42 (RULE-11): A reader of the init skill finds it names `.purlin/config.json`, `.purlin/evidence/`, `specs/`, `references/supported_frameworks.md` and `references/formats/marker_format.md`
- PROOF-4 (RULE-4): A reader counts the lines of the init skill and finds at most 250
- PROOF-98 (RULE-86): A reader checks every character of the init skill against the Unicode emoji ranges and finds `0` emoji
