# Feature: skill_init

> Description: What `skills/init/SKILL.md` must say. The init skill sets a project up for
>   Purlin and changes the gate later, so its text is the only place a reader learns
>   which questions they are asked and which script answers them.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/init/SKILL.md` opens with a frontmatter block whose `name` is `init` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:init`
- RULE-2: The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}` on one line passing `--project-root` and `--gate`, and its lines that run the script and its flag table name the `--project-root`, `--gate`, `--mutation`, `--yes`, `--update` and `--add` forms, and no flag the script does not take
- RULE-3: The last section of `skills/init/SKILL.md`, whose heading names the next step or reads `When you are done`, lists each state the skill may find as an item with its own `→` directive, among them `No specs and no code`, `Code but no specs` and `Specs but no tests`
- RULE-4: The whole of `skills/init/SKILL.md` is at most 250 lines
- RULE-5: The skill names the questions init asks, in order and no others: the gate, what must be true of every rule before a version is proven, with its three answers `passed`, `strong` and `signed`; and, at `strong` and `signed` only, and only where an engine exists for a framework the project carries, whether to measure test strength by breaking the code on purpose, with no as the default
- RULE-6: The skill shows the settings file init writes with exactly its seven keys, `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` and `ci`, says `audit_parallel` is not asked, and says init creates `.purlin/evidence/` with a README
- RULE-7: The skill says init installs nothing in a project's tests, writes the `tests` setting as an empty list, and that the first `purlin:test` suggests the entry, and points at `references/supported_frameworks.md` and `references/formats/marker_format.md`

## Proof

- PROOF-1 (RULE-1): A reader of the init skill finds that it opens with a frontmatter block between two `---` lines, carrying `name: init` and a `description:` whose value sits whole on that same line, not empty and not opening a `>` or `|` block
- PROOF-16 (RULE-1): A reader of the plugin's command reference finds a table row whose first cell is the `purlin:init` command and whose second cell holds its purpose
- PROOF-17 (RULE-1): A copy of the init skill with its `name:` line deleted is reported as having no name where `init` is expected
- PROOF-18 (RULE-1): A copy of the init skill whose `description:` line is left with no text is reported as carrying no one-line description
- PROOF-19 (RULE-1): A copy of the init skill whose `description:` line is left empty, with its text moved to an indented line below it, is reported as carrying no one-line description
- PROOF-20 (RULE-1): A copy of the init skill whose description is written as a `|` block is reported as carrying no one-line description
- PROOF-21 (RULE-1): A copy of the init skill whose description runs onto a second, indented line is reported as carrying no one-line description
- PROOF-22 (RULE-1): A copy of the plugin's command reference with the `purlin:init` row removed is reported as carrying no row for `purlin:init`
- PROOF-2 (RULE-2): A reader of the init skill finds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with both `--project-root` and `--gate`
- PROOF-23 (RULE-2): A reader of the init skill finds each of the six flags `--project-root`, `--gate`, `--mutation`, `--yes`, `--update` and `--add` on a line that runs the setup script or in the first column of its flag table
- PROOF-24 (RULE-2): The setup script is asked for its usage with `--help`; it exits 0, and every flag the init skill hands a reader, on its lines that run the script and in its flag table, is one the usage lists
- PROOF-8 (RULE-2): A copy of the init skill with the `--add` row dropped from its flag table is reported as not handing the reader `--add`
- PROOF-9 (RULE-2): A copy of the init skill with a `--force` row added to its flag table is reported as naming `--force`, which the setup script's usage does not list
- PROOF-10 (RULE-2): A copy of the init skill with `--gate` taken off its line that runs the setup script is reported as having no single line that carries the script with both `--project-root` and `--gate`
- PROOF-3 (RULE-3): A reader of the init skill finds that its last section is headed `When you are done`, lists the outcomes `No specs and no code`, `Code but no specs` and `Specs but no tests` as list items, and that every outcome it lists carries its own `→` directive
- PROOF-25 (RULE-3): A copy of the init skill with its closing section deleted is reported as closing with a section, named in the report, whose heading does not name the next step
- PROOF-26 (RULE-3): A copy of the init skill with every `→` taken out of its closing section is reported as giving no directive there
- PROOF-27 (RULE-3): A copy of the init skill whose closing list is cut after its first item is reported as naming 1 outcome where at least 2 are expected
- PROOF-28 (RULE-3): A copy of the init skill with the `→` taken out of the `Code but no specs` item alone is reported as giving that outcome no directive
- PROOF-4 (RULE-4): A reader counts the lines of the init skill and finds at most 250
- PROOF-29 (RULE-4): A copy of the init skill with prose appended until it is 251 lines long is reported as `251 lines, ceiling 250`
- PROOF-5 (RULE-5): A reader of the init skill finds, in its section `The questions`, exactly two numbered questions: the first carries `What must be true of every rule before a version is proven?`, the second `Measure test strength by breaking the code on purpose?`
- PROOF-30 (RULE-5): A reader of the init skill finds that its second question is asked `only at` `strong` and `signed`, `only where an engine exists` for a framework the project carries, and says `The default is no`
- PROOF-31 (RULE-5): A reader of the init skill finds, after `The first answer is the **gate**, one of three`, a gate table whose rows are `passed`, `strong` and `signed`, in that order
- PROOF-32 (RULE-5): A new git project holding a `conftest.py` is set up, answering `strong` and then pressing Enter; setup asks exactly 2 questions, each worded as the init skill quotes it, the gate question first and then the mutation question naming `mutmut` where the skill writes `<engine>`
- PROOF-33 (RULE-5): A new git project holding a `conftest.py` is set up, answering `passed`; setup asks exactly 1 question, `What must be true of every rule before a version is proven?`
- PROOF-34 (RULE-5): A new git project holding a `conftest.py` is set up, answering `strong`; the gate question offers the answers `passed`, `strong` and `signed`, in that order
- PROOF-35 (RULE-5): A new git project holding a `conftest.py` is set up, answering `strong` and then pressing Enter at the mutation question; the settings file it writes reads `"mutation_engine": "none"` and `"min_strength": null`
- PROOF-11 (RULE-5): A copy of the init skill with a third numbered question added to its section `The questions` is reported as naming 3 questions where 2 are expected
- PROOF-12 (RULE-5): A copy of the init skill with the `strong` row removed from its gate table is reported with the gates it found in place of `passed`, `strong` and `signed`
- PROOF-36 (RULE-5): A copy of the init skill with its two numbered questions swapped is reported as its first question not carrying `What must be true of every rule before a version is proven?`
- PROOF-37 (RULE-5): A copy of the init skill with `The default is no` taken out of its second question is reported as that question not carrying those words
- PROOF-6 (RULE-6): A reader of the init skill finds that the first settings block it shows reads as JSON and its keys are exactly `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` and `ci`
- PROOF-38 (RULE-6): A new git project is set up, answering `passed`; the `.purlin/config.json` it writes carries exactly the keys of the settings block the init skill shows
- PROOF-39 (RULE-6): A reader of the init skill finds one sentence carrying both `audit_parallel` and `is not asked`
- PROOF-40 (RULE-6): A reader of the init skill finds one sentence, starting `It writes`, that names `.purlin/evidence/` with one README
- PROOF-13 (RULE-6): A copy of the init skill with an eighth key `colour` added to its settings block is reported as showing `colour`, by name, as not one of the seven
- PROOF-14 (RULE-6): A copy of the init skill with `is not asked` taken out of its `audit_parallel` sentence, while those words still stand in another sentence, is reported as having no sentence carrying both
- PROOF-41 (RULE-6): A copy of the init skill whose `It writes` sentence names `.purlin/evidence/` without `with one README` is reported as having no sentence that says so
- PROOF-7 (RULE-7): A reader of the init skill finds that it says it installs nothing in the project's tests, that it writes the `tests` setting as an empty list, and that the first `purlin:test` suggests the entry
- PROOF-42 (RULE-7): A reader of the init skill finds it names `references/supported_frameworks.md` and `references/formats/marker_format.md`
- PROOF-15 (RULE-7): A copy of the init skill with the words saying the first `purlin:test` suggests the entry taken out is reported as missing those words
- PROOF-43 (RULE-7): A copy of the init skill with `references/formats/marker_format.md` taken out is reported as not naming that reference
