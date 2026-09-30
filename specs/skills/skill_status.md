# Feature: skill_status

> Description: The instructions in `skills/status/SKILL.md`: what they tell the agent to print for
>   `purlin:status` and `purlin:status <name>`, ending on the summary and `Left to do` the tool
>   returned, and how they name the next step.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 11

## Rules

- RULE-1: `skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line
- RULE-6: The table of commands in `references/purlin_commands.md` carries a row for `purlin:status` whose purpose cell is not empty
- RULE-2: The skill tells the agent to print the sentence and the `Left to do` lines `sync_status` returned and never to recount them
- RULE-3: The skill tells the agent, in its last section, to name the next step, the first line of `Left to do`
- RULE-7: The skill's closing table names every kind of `Left to do` line with a `→` directive to the command that line names
- RULE-8: Every row of the skill's closing table gives a `→` directive but `Nothing left to do.`, which names none
- RULE-4: The whole of `skills/status/SKILL.md` is at most 100 lines
- RULE-5: The skill tells the agent what to print for `purlin:status <name>` and what to do when several specs or none match
- RULE-9: `references/purlin_commands.md` names the form `purlin:status [name]`
- RULE-11: The skill tells the agent to call `sync_status` with the project root, the top folder of the git checkout, as `project_root`

## Proof

- PROOF-1 (RULE-1): The status skill opens with a frontmatter block set between two `---` lines; its `name` reads `status`, and its `description` reads `Show every rule's cells and what blocks the gate` on that one line, with no line continuing it
- PROOF-12 (RULE-6): The plugin's command reference has, in its table of commands, a row whose first cell reads `` `purlin:status [name]` `` and whose second cell reads `Show every rule's cells and what blocks the gate`
- PROOF-2 (RULE-2): The status skill, its line breaks ignored, carries these two sentences in a row: ``Print the sentence and the `Left to do` lines `sync_status` returned. Never recount them: the command line and the dashboard must show one answer from one computation.``
- PROOF-3 (RULE-3): The last section of the status skill is headed `Step 4: name the next step`
- PROOF-22 (RULE-3): The last section of the status skill says ``The next step is the first line of `Left to do`.``
- PROOF-24 (RULE-7): Every kind of line `Left to do` can print, from `rules to write a proof for` to `the version to tag`, is named in a row of the status skill's closing table whose directive runs the command the line itself names, such as `to strengthen` with `→ Run: purlin:build`
- PROOF-23 (RULE-8): The table in the last section of the status skill has at least 2 rows, and every row gives a `→` directive except the one reading `Nothing left to do.`, whose next step reads `None: every rule reached every step the gate asks.`
- PROOF-4 (RULE-4): The status skill as shipped is at most 100 lines long
- PROOF-27 (RULE-4): A copy of the status skill made exactly 100 lines long passes the ceiling of 100
- PROOF-28 (RULE-4): A copy of the status skill made 101 lines long fails, reporting `101 lines, ceiling 100`
- PROOF-5 (RULE-5): The status skill's usage shows `purlin:status <name>` on one line with `One spec: its rules and their cells`, and the skill says `Naming a spec shows its rules and their standing.`
- PROOF-31 (RULE-5): The status skill's section `With a name` says that when several specs match it will `list them and ask which one`, that when none does it will `print the whole table`, and that otherwise it will `print its path, its header, and one line per rule with the cells the gate creates`
- PROOF-29 (RULE-9): The plugin's command reference names the command `purlin:status [name]`
- PROOF-35 (RULE-11): The status skill's first call of `sync_status`, in Step 1, reads ``Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout.``
