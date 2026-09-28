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

- PROOF-1 (RULE-1): Read `skills/init/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: init` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:init`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): A reader of the init skill finds the command that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` and each of the flags `--project-root`, `--gate`, `--mutation`, `--yes`, `--update`, `--add` and `--dry-run`, and every flag named on a line that runs the script or in the first column of the flag table is one of those seven. With the `--dry-run` row dropped the check names `--dry-run` as missing, and with a row for `--force` added it names `--force` as a flag the script does not take
- PROOF-3 (RULE-3): Read `skills/init/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/init/SKILL.md` and count its lines; verify the count is at most 250. Appending prose until the file passes 250 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/init/SKILL.md` with its line wrapping collapsed; verify it carries each of the three gate names `passed`, `strong` and `signed`, and that the section headed `The questions` holds exactly four numbered items, carrying in order `What must be true of every rule before a version is proven?`, `empty repository`, `Measure test strength by breaking the code on purpose?` with `The default is no`, and `trusted`. Adding a fifth numbered question to that section fails, reporting five where four were expected
- PROOF-6 (RULE-6): Read the fenced `json` block of `skills/init/SKILL.md`; verify it parses and its sorted keys equal the sorted keys of `templates/config.json`, and that the skill carries `is not asked` and `.purlin/evidence/` with one README. Adding a ninth key to the block fails naming it
- PROOF-7 (RULE-7): Read `skills/init/SKILL.md` with its line wrapping collapsed; verify it says init installs nothing in the project's tests and writes one entry of the tests setting per framework, and that it carries `jest-junit`, `references/supported_frameworks.md` and `references/formats/marker_format.md`. Deleting the Jest sentence fails naming `jest-junit`
