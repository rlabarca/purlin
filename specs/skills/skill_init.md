# Feature: skill_init

> Description: What `skills/init/SKILL.md` must say. The init skill sets a project up for
>   Purlin and changes the gate later, so its text is the only place a reader learns
>   which questions they are asked and which script answers them.
> Scope: skills/init/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 85
> Highest-Proof: 96

## Rules

- RULE-1: `skills/init/SKILL.md` opens with a frontmatter block whose `name` is `init` and whose `description` is one non-empty line
- RULE-8: `references/purlin_commands.md` carries a row for `purlin:init`
- RULE-2: The skill gives the agent the line that runs `scripts/init/scaffold.py` through the interpreter lookup, `scripts/purlin_python.sh`, passing `--project-root` and `--gate`, and hands it the flags `--project-root`, `--gate`, `--mutation`, `--yes` and `--update`, each one the script takes
- RULE-3: The skill's last section, whose heading names the next step or reads `When you are done`, tells the agent each state it may find as an item with its own `→` directive, among them `No specs and no code`, `Code but no specs` and `Specs but no tests`
- RULE-4: The whole of `skills/init/SKILL.md` is at most 250 lines
- RULE-5: The skill tells the agent the questions init asks, in order and no others: the gate, what must be true of every rule before a version is finished, with its two answers `passed` and `signed`; at `signed` only, and only where an engine exists for a framework the project carries, whether to measure test strength by breaking the code on purpose, with no as the default; and whether to commit the files setup wrote, with no as the default
- RULE-6: The skill shows the agent the settings file init writes with exactly its six keys, `version`, `gate`, `mutation_engine`, `audit_parallel`, `tests` and `ci`
- RULE-9: The skill tells the agent that `audit_parallel` is not asked
- RULE-10: The skill tells the agent that init creates `.purlin/evidence/` with a README
- RULE-7: The skill tells the agent that init installs nothing in a project's tests and writes the `tests` setting as an empty list, and that the first `purlin:test` suggests a command for each test tool it recognises, confirmed together
- RULE-11: The skill points the agent at `references/supported_frameworks.md` and `references/formats/marker_format.md`
- RULE-85: The skill tells the agent to ask the person each question itself, to pass `--mutation` on a yes to breaking the code on purpose and `--yes` on a yes to the commit, and otherwise to run the script with its input empty

## Proof

- PROOF-1 (RULE-1): A reader of the init skill finds that it opens with a frontmatter block between two `---` lines, carrying `name: init` and a `description:` whose value sits whole on that same line, not empty and not opening a `>` or `|` block
- PROOF-16 (RULE-8): A reader of the plugin's command reference finds a table row whose first cell is the `purlin:init` command and whose second cell holds its purpose
- PROOF-2 (RULE-2): A reader of the init skill finds one line that runs `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"` with both `--project-root` and `--gate`
- PROOF-23 (RULE-2): A reader of the init skill finds each of the five flags `--project-root`, `--gate`, `--mutation`, `--yes` and `--update` on a line that runs the setup script or in the first column of its flag table
- PROOF-96 (RULE-2): A reader of the init skill finds its flag table's `--yes` row reads `Takes the default answer to every question and commits the files setup wrote`
- PROOF-24 (RULE-2): The setup script is asked for its usage with `--help`; it exits 0, and every flag the init skill hands a reader, on its lines that run the script and in its flag table, is one the usage lists
- PROOF-3 (RULE-3): A reader of the init skill finds that its last section is headed `When you are done`, lists the outcomes `No specs and no code`, `Code but no specs` and `Specs but no tests` as list items, and that every outcome it lists carries its own `→` directive
- PROOF-4 (RULE-4): A reader counts the lines of the init skill and finds at most 250
- PROOF-5 (RULE-5): A reader of the init skill finds, in its section `The questions`, exactly three numbered questions: the first carries `What must be true of every rule before a version is finished?`, the second `Measure test strength by breaking the code on purpose?`, the third `Commit the files setup wrote? [y/N]`
- PROOF-30 (RULE-5): A reader of the init skill finds that its second question is asked `only at` `signed`, `only where an engine exists` for a framework the project carries, and says `The default is no`
- PROOF-31 (RULE-5): A reader of the init skill finds, after `The first answer is the **gate**, one of two`, a gate table whose rows are `passed` and `signed`, in that order
- PROOF-32 (RULE-5): A new git project holding a `conftest.py` is set up, answering `signed`, then pressing Enter; setup asks exactly 3 questions, each worded as the init skill quotes it: the gate question, the mutation question naming `mutmut` where the skill writes `<engine>`, then the commit question
- PROOF-33 (RULE-5): A new git project holding a `conftest.py` is set up, answering `passed`; setup asks exactly 2 questions, `What must be true of every rule before a version is finished?`, then `Commit the files setup wrote? [y/N]`
- PROOF-94 (RULE-5): A reader of the init skill finds its third question carries `Commit the files setup wrote? [y/N]`, says `The default is no`, and names the commit `chore(init): set up Purlin at the gate <gate>`
- PROOF-34 (RULE-5): A new git project holding a `conftest.py` is set up, answering `signed`; the gate question offers the answers `passed` and `signed`, in that order
- PROOF-35 (RULE-5): A new git project holding a `conftest.py` is set up, answering `signed` and then pressing Enter at the mutation question; the settings file it writes reads `"mutation_engine": "none"` and carries no `min_strength`
- PROOF-6 (RULE-6): A reader of the init skill finds that the first settings block it shows reads as JSON and its keys are exactly `version`, `gate`, `mutation_engine`, `audit_parallel`, `tests` and `ci`
- PROOF-38 (RULE-6): A new git project is set up, answering `passed`; the `.purlin/config.json` it writes carries exactly the keys of the settings block the init skill shows
- PROOF-39 (RULE-9): A reader of the init skill finds one sentence carrying both `audit_parallel` and `is not asked`
- PROOF-40 (RULE-10): A reader of the init skill finds one sentence, starting `It writes`, that names `.purlin/evidence/` with one README
- PROOF-7 (RULE-7): A reader of the init skill finds that it says it installs nothing in the project's tests, that it writes the `tests` setting as an empty list, and that the first `purlin:test` suggests a command for each test tool it recognises
- PROOF-42 (RULE-11): A reader of the init skill finds it names `references/supported_frameworks.md` and `references/formats/marker_format.md`
- PROOF-95 (RULE-85): A reader of the init skill finds, under `Run it`, the words telling the agent to ask the person each question itself, to pass `--mutation` when they say yes to breaking the code on purpose and `--yes` when they say yes to the commit, and otherwise to run the script with its input empty, `< /dev/null`
