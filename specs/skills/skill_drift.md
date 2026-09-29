# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what changed since your last
>   pull, in one view per role, `pm`, `eng` and `qa`, and it writes nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/drift/SKILL.md` opens with a frontmatter block whose `name` is `drift` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:drift` in its command table, with its purpose
- RULE-2: The skill takes its data from the `drift` tool, tells the agent to print the lines the tool returns as they come and to invent none, and points at `references/drift_criteria.md` for what each line means and where it comes from rather than restating it
- RULE-3: The last section of `skills/drift/SKILL.md` names the next step in a table that gives, for each kind of line the three views print and for a view that shows no change, the `→` directive to print when the view shows it
- RULE-4: The whole of `skills/drift/SKILL.md` is at most 150 lines

## Proof

- PROOF-1 (RULE-1): The drift skill opens with a frontmatter block between two `---` lines that carries `name: drift` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-9 (RULE-1): The command reference carries a row in its command table whose first cell is `purlin:drift [role]` and whose second cell gives its purpose
- PROOF-10 (RULE-1): A copy of the drift skill with its `name: drift` line deleted is reported as having no name where `drift` is expected
- PROOF-11 (RULE-1): A copy of the drift skill whose `description:` line is left empty is reported as carrying no one-line description
- PROOF-12 (RULE-1): A copy of the drift skill whose description is written as a `>-` block, its text on the indented line below, is reported as carrying no one-line description
- PROOF-13 (RULE-1): A copy of the drift skill whose description is written as a `|` block, its text on the indented line below, is reported as carrying no one-line description
- PROOF-14 (RULE-1): A copy of the drift skill whose `description:` line is left empty, its text moved to the indented line below, is reported as carrying no one-line description
- PROOF-15 (RULE-1): A copy of the drift skill whose description runs onto an indented second line is reported as carrying no one-line description
- PROOF-16 (RULE-1): A copy of the drift skill whose first line is blank, the frontmatter block starting on the second, is reported as not opening with a frontmatter block
- PROOF-17 (RULE-1): A copy of the command reference whose `purlin:drift [role]` row has an empty purpose cell is reported as carrying no row for `purlin:drift`
- PROOF-18 (RULE-1): A copy of the command reference with the `purlin:drift [role]` row removed from its command table, the name still written elsewhere in it, is reported as carrying no row for `purlin:drift`
- PROOF-2 (RULE-2): The drift skill's step that gets the data shows the call `drift(role="eng")` alone in a fenced block
- PROOF-19 (RULE-2): The drift skill, read across its line breaks, says ``What each line means and which git facts it comes from live in `references/drift_criteria.md` ``
- PROOF-20 (RULE-2): The drift skill, read across its line breaks, says `do not restate them here and do not invent a line the tool does not return`
- PROOF-21 (RULE-2): The drift skill's step that prints the view says ``Print `lines` as they come, one per line`` and `Do not reword a line, do not drop one`
- PROOF-22 (RULE-2): The drift skill, read across its line breaks, repeats no definition from the drift criteria: no `From` cell of the `eng` or `qa` table, no cell saying where the range starts, no anchor condition and no git command the criteria name
- PROOF-23 (RULE-2): A copy of the drift skill into which ``Rules whose passed cell reads `no test` `` is pasted is reported as restating what the drift criteria say a line is built from, naming that fact
- PROOF-24 (RULE-2): A copy of the drift skill into which ``Where HEAD stood before the rebase's first step, `rebase (start)` `` is pasted is reported as restating where the drift criteria say the range starts, naming it
- PROOF-25 (RULE-2): A copy of the drift skill into which ``A `> Source:` with no `> Pinned:` `` is pasted is reported as restating an anchor condition from the drift criteria, naming it
- PROOF-26 (RULE-2): A copy of the drift skill into which `git reflog show HEAD` is pasted is reported as naming a git command the drift criteria give as a source, naming it
- PROOF-3 (RULE-3): The drift skill's last section has a heading naming the `next step` and a table of at least 2 outcomes below its header and divider, each carrying its own `→` directive
- PROOF-27 (RULE-3): The drift skill's closing table, headed `What the view shows` and `The line to print`, has a row for each kind of line the drift criteria give the three views, one for spec files not committed and one for a view that shows no change
- PROOF-28 (RULE-3): A copy of the drift skill with its closing section deleted is reported as closing with the section `Step 3: what drift never does`, which does not name the next step
- PROOF-29 (RULE-3): A copy of the drift skill with every `→` in its closing section written as `->` is reported as giving no directive there
- PROOF-30 (RULE-3): A copy of the drift skill whose closing table is cut to its header and divider is reported as naming 0 outcomes where at least 2 are expected
- PROOF-31 (RULE-3): A copy of the drift skill whose closing table is cut to its header, its divider and its first row is reported as naming 1 outcome where at least 2 are expected
- PROOF-32 (RULE-3): A copy of the drift skill with the `→` taken out of the row `A rule removed` alone is reported as that outcome giving no `→` directive, naming the row
- PROOF-33 (RULE-3): A copy of the drift skill with the row `An anchor behind its source` deleted from its closing table is reported as giving no next step for the line `anchors_behind`
- PROOF-4 (RULE-4): The drift skill, counted line by line, is at most 150 lines long
- PROOF-34 (RULE-4): A copy of the drift skill lengthened with lines of prose to exactly 150 lines is reported as having no problem
- PROOF-35 (RULE-4): A copy of the drift skill lengthened with lines of prose to 151 lines is reported as being 151 lines against its ceiling of 150
