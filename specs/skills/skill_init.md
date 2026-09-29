# Feature: skill_init

> Description: What `skills/init/SKILL.md` must say. The init skill sets a project up for
>   Purlin and changes the gate later, so its text is the only place a reader learns
>   which questions they are asked and which script answers them.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/init/SKILL.md` opens with a frontmatter block whose `name` is `init` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:init`
- RULE-2: The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}`, passing `--project-root` and `--gate`, and names the `--mutation`, `--yes`, `--update` and `--add` forms, and no flag the script does not take
- RULE-3: The last section of `skills/init/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/init/SKILL.md` is at most 250 lines
- RULE-5: The skill names the questions init asks, in order and no others: the gate, what must be true of every rule before a version is proven, with its three answers `passed`, `strong` and `signed`; and, at `strong` and `signed` only, whether to measure test strength by breaking the code on purpose, with no as the default
- RULE-6: The skill shows the settings file init writes with exactly its seven keys, `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` and `ci`, says `audit_parallel` is not asked, and says init creates `.purlin/evidence/` with a README
- RULE-7: The skill says init installs nothing in a project's tests, writes the `tests` setting as an empty list, and that the first `purlin:test` suggests the entry, and points at `references/supported_frameworks.md` and `references/formats/marker_format.md`

## Proof

- PROOF-1 (RULE-1): The init skill opens with a frontmatter block set between two `---` lines, whose `name` reads `init` and whose `description` holds text whole on its own line, not empty and not opening a `>` or `|` block; the plugin's command reference carries a table row whose first cell is the `purlin:init` command. With the `name:` line deleted, the check reports, naming `skills/init/SKILL.md`, that it found no name where `init` is expected; with the description left empty, left empty with text on the next line, written as a `|` block, or run onto a second line, it reports that the frontmatter carries no one-line description; with the `purlin:init` row removed from the command reference, it reports that the reference carries no row for `purlin:init`
- PROOF-2 (RULE-2): The init skill shows one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with both `--project-root` and `--gate`, and each of the six flags `--project-root`, `--gate`, `--mutation`, `--yes`, `--update` and `--add` stands on a line that runs the script or in the first column of its flag table, and every flag in those two places is one of the six
- PROOF-8 (RULE-2): With the `--add` row dropped from the init skill's flag table, the check reports `--add` as a flag the reader is not handed
- PROOF-9 (RULE-2): With a `--force` row added to the init skill's flag table, the check reports `--force` as a flag the script does not take
- PROOF-10 (RULE-2): With `--gate` taken off the init skill's line that runs the script, the check reports that no single line carries the script with both flags
- PROOF-3 (RULE-3): The last section of the init skill has a heading that reads `When you are done` or names the `next step`, in any case; it lists at least two outcomes as list items, among them one for each state `No specs and no code`, `Code but no specs` and `Specs but no tests`, and every outcome carries its own `→` directive. With the closing section deleted, the check reports the heading of the section that now closes the file; with every `→` removed from it, it reports that the closing section gives no directive; with the list cut after its first item, it reports 1 outcome where at least 2 are expected; with the `→` removed from the `Code but no specs` item alone, it reports that outcome as giving no directive
- PROOF-4 (RULE-4): Read `skills/init/SKILL.md` and count its lines; verify the count is at most 250. Appending prose until the file passes 250 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The init skill's section `The questions` lists exactly two numbered questions: the first carries `What must be true of every rule before a version is proven?`, the second `only at`, `strong`, `signed`, `Measure test strength by breaking the code on purpose?` and `The default is no`; its gate table's rows are `passed`, `strong` and `signed`, in that order
- PROOF-11 (RULE-5): With a third numbered question added to the init skill's section `The questions`, the check reports 3 questions where 2 are expected
- PROOF-12 (RULE-5): With the `strong` row removed from the init skill's gate table, the check reports the gates it found instead of `passed`, `strong` and `signed`
- PROOF-6 (RULE-6): The settings block the init skill shows first parses, and its keys are exactly `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` and `ci`, the settings template's keys; one sentence of the skill says `audit_parallel` `is not asked`, and one says it writes `.purlin/evidence/` with one README
- PROOF-13 (RULE-6): With an eighth key `colour` added to the settings block the init skill shows, the check reports `colour` by name as not one of the seven
- PROOF-14 (RULE-6): With `is not asked` taken out of the init skill's `audit_parallel` sentence, while the words still stand elsewhere in the skill, the check reports that no sentence carries both
- PROOF-7 (RULE-7): The init skill says it installs nothing in the project's tests, says it writes the `tests` setting as an empty list and that the first `purlin:test` suggests the entry, and points the reader at `references/supported_frameworks.md` and `references/formats/marker_format.md`
- PROOF-15 (RULE-7): With the words saying the first `purlin:test` suggests the entry taken out of the init skill, the check reports those words missing
