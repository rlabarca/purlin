# Feature: skill_status

> Description: What `skills/status/SKILL.md` must say. Status prints where every feature stands, or one named spec's rules, and
>   ends on the summary and `Left to do`; the command line and the dashboard show one answer from one computation.
> Scope: skills/status/SKILL.md, scripts/mcp/purlin/status.py, scripts/mcp/purlin/summary.py, scripts/mcp/purlin/report_data.py
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and the table of commands in `references/purlin_commands.md` carries a row for `purlin:status` whose purpose cell is not empty
- RULE-2: `skills/status/SKILL.md` tells the agent to print the sentence and the `Left to do` lines `sync_status` returned and never to recount them; those lines and the data the dashboard reads come from one computation, so the two cannot disagree
- RULE-3: The last section of `skills/status/SKILL.md` names the next step, the first line of `Left to do`; its table names every kind of `Left to do` line with a `→` directive to the command that line names, and every row gives a `→` directive but `Nothing left to do.`, which names none
- RULE-4: The whole of `skills/status/SKILL.md` is at most 100 lines
- RULE-5: `skills/status/SKILL.md` says that `purlin:status <name>` shows one spec, its rules and their cells, and what it does when several specs or none match the name, and `references/purlin_commands.md` names that form `purlin:status [name]`

## Proof

- PROOF-1 (RULE-1): The status skill opens with a frontmatter block set between two `---` lines; its `name` reads `status`, and its `description` reads `Show every rule's cells and what blocks the gate` on that one line, with no line continuing it
- PROOF-12 (RULE-1): The plugin's command reference has, in its table of commands, a row whose first cell reads `` `purlin:status [name]` `` and whose second cell reads `Show every rule's cells and what blocks the gate`
- PROOF-13 (RULE-1): A copy of the status skill with its `name: status` line deleted fails, naming `status` as the name expected
- PROOF-14 (RULE-1): A copy of the status skill whose `description:` line is left with no text fails as carrying no one-line description
- PROOF-15 (RULE-1): A copy of the status skill whose description is written as `""` fails as carrying no one-line description
- PROOF-16 (RULE-1): A copy of the status skill whose description is opened as a `|` block, its text on the indented line below, fails as carrying no one-line description
- PROOF-17 (RULE-1): A copy of the status skill whose description text sits on the indented line below an empty `description:` fails as carrying no one-line description
- PROOF-18 (RULE-1): A copy of the status skill whose description runs on to an indented second line reading `and a second line` fails as carrying no one-line description
- PROOF-19 (RULE-1): A copy of the plugin's command reference with the `purlin:status [name]` row deleted fails, saying the reference carries no row for `purlin:status`
- PROOF-20 (RULE-1): A copy of the plugin's command reference whose `purlin:status [name]` row has an empty second cell fails, saying the reference carries no row for `purlin:status`
- PROOF-2 (RULE-2): The status skill, its line breaks ignored, carries these two sentences in a row: ``Print the sentence and the `Left to do` lines `sync_status` returned. Never recount them: the command line and the dashboard must show one answer from one computation.``
- PROOF-6 (RULE-2): A copy of the status skill whose first of those two sentences reads `Count the rules in the table yourself.` fails, naming the passage ``Print the sentence and the `Left to do` lines`` it no longer finds
- PROOF-21 (RULE-2): At the gate `strong`, of 2 rules one passes its test and one has no test. `sync_status` ends on `2 rules. 1 passes its tests. 0 are strong.`, `Left to do:`, `1 rule to write a test for: purlin:build`, `1 rule to audit: purlin:audit`; the dashboard data counts 2 rules, 1 passing, 0 strong, and those two lines, 1 each
- PROOF-3 (RULE-3): The last section of the status skill is headed `Step 4: name the next step`
- PROOF-7 (RULE-3): A copy of the status skill with its last section removed fails, naming `With a name`, the heading of the section then last
- PROOF-22 (RULE-3): The last section of the status skill says ``The next step is the first line of `Left to do`.``
- PROOF-11 (RULE-3): A copy of the status skill whose last section says `The next step is yours to choose.` in place of ``The next step is the first line of `Left to do`.`` fails, naming the sentence it lacks
- PROOF-23 (RULE-3): The table in the last section of the status skill has at least 2 rows, and every row gives a `→` directive except the one reading `Nothing left to do.`, whose next step reads `None: every rule reached every step the gate asks.`
- PROOF-8 (RULE-3): A copy of the status skill with every `→` in its last section written as `->` fails as giving no directive
- PROOF-9 (RULE-3): A copy of the status skill whose last section is cut after the table's first row fails with the count 1 beside the 2 expected
- PROOF-10 (RULE-3): A copy of the status skill whose row for `<n> rules to audit` loses its `→` fails, naming that row
- PROOF-24 (RULE-3): Every kind of line `Left to do` can print, from `rules to write a proof for` to `the version to tag`, is named in a row of the status skill's closing table whose directive runs the command the line itself names, such as `to strengthen` with `→ Run: purlin:build`
- PROOF-25 (RULE-3): A copy of the status skill whose row for `<n> rules to audit` gives `→ Run: purlin:test` fails, naming `rules to audit` and `purlin:audit`, the command the line names
- PROOF-26 (RULE-3): A copy of the status skill whose closing table no longer names `to strengthen` fails, naming `rules to strengthen` as a line with no row
- PROOF-4 (RULE-4): The status skill as shipped is at most 100 lines long
- PROOF-27 (RULE-4): A copy of the status skill made exactly 100 lines long passes the ceiling of 100
- PROOF-28 (RULE-4): A copy of the status skill made 101 lines long fails, reporting `101 lines, ceiling 100`
- PROOF-5 (RULE-5): The status skill's usage shows `purlin:status <name>` on one line with `One spec: its rules and their cells`, and the skill says `Naming a spec shows its rules and their standing.`
- PROOF-29 (RULE-5): The plugin's command reference names the command `purlin:status [name]`
- PROOF-30 (RULE-5): A copy of the plugin's command reference whose row reads `` `purlin:status` `` without `[name]` fails, naming `purlin:status [name]`
- PROOF-31 (RULE-5): The status skill's section `With a name` says that when several specs match it will `list them and ask which one`, that when none does it will `print the whole table`, and that otherwise it will `print its path, its header, and one line per rule with the cells the gate creates`
- PROOF-32 (RULE-5): A copy of the status skill whose section `With a name` says `take the first` in place of `list them and ask which one` fails, naming the words it lacks
- PROOF-33 (RULE-5): A copy of the status skill whose section `With a name` says `print nothing` in place of `print the whole table` fails, naming the words it lacks
- PROOF-34 (RULE-5): A copy of the status skill whose section `With a name` prints only `one line per rule`, without its path and header, fails, naming the words it lacks
