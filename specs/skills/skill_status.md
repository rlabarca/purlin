# Feature: skill_status

> Description: What `skills/status/SKILL.md` must say. Status prints where every feature stands, or one named spec's rules, and
>   ends on the summary and `Left to do`; the command line and the dashboard show one answer from one computation.
> Scope: skills/status/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:status`
- RULE-2: The skill prints the sentence and the `Left to do` lines `sync_status` returned and never recounts them, so the command line and the dashboard cannot disagree
- RULE-3: The last section of `skills/status/SKILL.md` names the next step, the first line of `Left to do`, and gives a `→` directive for each kind of line but `Nothing left to do.`, which names none
- RULE-4: The whole of `skills/status/SKILL.md` is at most 100 lines
- RULE-5: `purlin:status <name>` shows one spec, its rules and their cells, and both `skills/status/SKILL.md` and `references/purlin_commands.md` name that form

## Proof

- PROOF-1 (RULE-1): The status skill opens with a frontmatter block set between two `---` lines, whose `name` reads `status` and whose `description` holds text on its own line. The plugin's command reference has a table row whose first cell is `` `purlin:status [name]` `` and whose second cell holds its purpose. A skill whose `name:` line is deleted fails, naming the expected name `status`. A `description:` left empty, written as `""`, opened as a `|` block, moved to the line below or run on to an indented second line fails as carrying no one-line description. A command reference without that row fails, saying it carries no row for `purlin:status`
- PROOF-2 (RULE-2): The status skill, its line wrapping ignored, carries two sentences in a row: ``Print the sentence and the `Left to do` lines `sync_status` returned. Never recount them: the command line and the dashboard must show one answer from one computation.``
- PROOF-6 (RULE-2): A copy of the status skill whose first sentence there reads `Count the rules in the table yourself.` fails, naming the passage it no longer finds
- PROOF-3 (RULE-3): The last section of the status skill has a heading naming the `next step` and says ``The next step is the first line of `Left to do`.``; its table has at least two outcome rows, and every row gives a `→` directive except the one reading `Nothing left to do.`
- PROOF-7 (RULE-3): A copy of the status skill with its last section removed fails, naming `With a name`, the heading of the section then last
- PROOF-8 (RULE-3): A copy of the status skill with every `→` taken out of its last section fails as giving no directive
- PROOF-9 (RULE-3): A copy of the status skill whose last section is cut after its first row fails with the count 1 beside the 2 expected
- PROOF-10 (RULE-3): A copy of the status skill whose row for `<n> rules to audit` loses its `→` fails, naming that row
- PROOF-11 (RULE-3): A copy of the status skill whose last section no longer says ``The next step is the first line of `Left to do`.`` fails, naming that sentence
- PROOF-4 (RULE-4): Read `skills/status/SKILL.md` and count its lines; verify the count is at most 100. Appending prose until the file passes 100 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The status skill shows the form `purlin:status <name>` and says `Naming a spec shows its rules and their standing.`, and the plugin's command reference lists the command as `purlin:status [name]`. The skill's section on a name says that when several specs match it will `list them and ask which one`, that when none does it will `print the whole table`, and that it will `print its path, its header, and one line per rule with the cells the gate creates`. A copy that takes the first of several matches, one that prints nothing when none matches, and one that prints only a line per rule each fail, naming the words they lack
