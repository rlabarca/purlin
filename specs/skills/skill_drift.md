# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what changed since your last
>   pull, in one view per role, `pm`, `eng` and `qa`, and it writes nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/drift/SKILL.md` opens with a frontmatter block whose `name` is `drift` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent to take its data from the `drift` tool and to show the lines it returns, and points at `references/drift_criteria.md` for what each line means and where it comes from rather than restating it
- RULE-3: The last section of `skills/drift/SKILL.md` names the next step in a table that gives, for each kind of line the three views print and for a view that shows no change, the `→` directive to print when the view shows it
- RULE-4: The whole of `skills/drift/SKILL.md` is at most 150 lines
- RULE-5: `references/purlin_commands.md` carries a row for `purlin:drift` in its command table, with its purpose

## Proof

- PROOF-1 (RULE-1): The drift skill opens with a frontmatter block between two `---` lines that carries `name: drift` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-9 (RULE-5): The command reference carries a row in its command table whose first cell is `purlin:drift [role]` and whose second cell gives its purpose
- PROOF-2 (RULE-2): The drift skill's step that gets the data shows the call `drift(role="eng")` alone in a fenced block
- PROOF-19 (RULE-2): The drift skill, read across its line breaks, says ``What each line means and which git facts it comes from live in `references/drift_criteria.md` ``
- PROOF-20 (RULE-2): The drift skill, read across its line breaks, says `do not restate them here and do not invent a line the tool does not return`
- PROOF-21 (RULE-2): The drift skill's step that prints the view says ``Print `lines` as they come, one per line`` and `Do not reword a line, do not drop one`
- PROOF-22 (RULE-2): The drift skill, read across its line breaks, repeats no definition from the drift criteria: no `From` cell of the `eng` or `qa` table, no cell saying where the range starts, no anchor condition and no git command the criteria name
- PROOF-3 (RULE-3): The drift skill's last section has a heading naming the `next step` and a table of at least 2 outcomes below its header and divider, each carrying its own `→` directive
- PROOF-27 (RULE-3): The drift skill's closing table, headed `What the view shows` and `The line to print`, has a row for each kind of line the drift criteria give the three views, one for spec files not committed and one for a view that shows no change
- PROOF-4 (RULE-4): The drift skill, counted line by line, is at most 150 lines long
- PROOF-34 (RULE-4): A copy of the drift skill lengthened with lines of prose to exactly 150 lines is reported as having no problem
- PROOF-35 (RULE-4): A copy of the drift skill lengthened with lines of prose to 151 lines is reported as being 151 lines against its ceiling of 150
