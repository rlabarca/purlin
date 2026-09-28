# Feature: skill_init

> Description: What `skills/init/SKILL.md` must say. The init skill sets a project up for
>   Purlin and changes the gate later, so its text is the only place a reader learns
>   which questions they are asked and which script answers them.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/init/SKILL.md` opens with a frontmatter block whose `name` is `init` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:init`
- RULE-2: The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}`, passing `--project-root` and `--gate`, and names the `--mutation`, `--yes`, `--update`, `--add` and `--dry-run` forms, and no flag the script does not take
- RULE-3: The last section of `skills/init/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/init/SKILL.md` is at most 250 lines [level: passed]
- RULE-5: The skill names the questions init asks, in order and no others: the gate, what must be true of every rule before a version is proven, with its three answers `passed`, `strong` and `signed`; the test command and where its report lands, where no framework is detected, as in an empty repository; whether to measure test strength by breaking the code on purpose, with no as the default; and whether this machine is trusted
- RULE-6: The skill shows the settings file init writes with exactly its eight keys, `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci` and `trust`, says `audit_parallel` is not asked, and says init creates `.purlin/evidence/` with a README
- RULE-7: The skill says init installs nothing in a project's tests and writes one entry of the `tests` setting per framework it detects, with the flag that writes the report already in the command, that Jest needs the package `jest-junit`, and points at `references/supported_frameworks.md` and `references/formats/marker_format.md`

## Proof

- PROOF-1 (RULE-1): The init skill opens with a frontmatter block set between two `---` lines, whose `name` reads `init` and whose `description` holds text, neither empty nor a folded `>` block spread over the lines below; the plugin's command reference names `purlin:init`
- PROOF-2 (RULE-2): The init skill shows the command `"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` and names each of the seven flags `--project-root`, `--gate`, `--mutation`, `--yes`, `--update`, `--add` and `--dry-run`; every flag on a line that runs the script, and every flag in the first column of its flag table, is one of those seven, so a flag the script does not take, such as `--force`, appears in neither place
- PROOF-3 (RULE-3): The last section of the init skill has a heading that reads `When you are done` or names the `next step`, in any case; under it at least two outcomes are listed as list items or table rows, and at least one line gives a `→` directive
- PROOF-4 (RULE-4): Read `skills/init/SKILL.md` and count its lines; verify the count is at most 250. Appending prose until the file passes 250 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The init skill's section headed `The questions` lists exactly four numbered questions and no fifth, in this order: the first carries `What must be true of every rule before a version is proven?`, the second `empty repository`, the third `Measure test strength by breaking the code on purpose?` and `The default is no`, and the fourth `trusted`; the skill also names the three gates `passed`, `strong` and `signed`
- PROOF-6 (RULE-6): The settings file the init skill shows in its first `json` block parses, and its keys are exactly the keys of the settings template a new project is given, no more and no fewer; the skill also carries the words `is not asked`, `.purlin/evidence/` and `one README`
- PROOF-7 (RULE-7): The init skill says it installs nothing in the project's tests and writes one entry of the `tests` setting, names the package `jest-junit`, and points the reader at `references/supported_frameworks.md` and `references/formats/marker_format.md`
