# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must say. An anchor is a spec for something shared
>   across features, and the skill is what creates one, pulls one from another
>   repository and keeps its pin current.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line, and the `Command`, `Purpose` table of `references/purlin_commands.md` carries a row for `purlin:anchor` with its purpose
- RULE-2: The skill runs `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` for `add` and `sync`, and its `sync` section says that `--check` reports without writing and that `purlin:drift` runs the same check
- RULE-3: The last section of `skills/anchor/SKILL.md` names the next step for each state the skill can end in, at least two, and gives each its own `→` directive
- RULE-4: The whole of `skills/anchor/SKILL.md` is at most 160 lines
- RULE-5: A pin is a commit and never a branch, and a pinned rule is never edited in the consuming project: the skill sends a change to a pull request against the source repository or to a separate local anchor that requires the pinned one
- RULE-6: The skill states that the folder `specs/_anchors/` is created with the first anchor, whether written by `create` or brought in by `add`

## Proof

- PROOF-1 (RULE-1): The anchor skill opens with a frontmatter block set between two `---` lines; the block reads `name: anchor` and carries a `description:` whose text sits on that same line
- PROOF-9 (RULE-1): Purlin's command reference has a row in its `Command`, `Purpose` table whose first cell is `` `purlin:anchor <cmd>` `` and whose second cell holds the command's purpose
- PROOF-10 (RULE-1): A copy of the anchor skill with its `name:` line deleted fails, saying the frontmatter name is missing where `anchor` is expected
- PROOF-11 (RULE-1): A copy of the anchor skill whose `description:` is left empty fails, saying the frontmatter carries no one-line description
- PROOF-12 (RULE-1): A copy of the anchor skill whose description text is moved to the line below `description:` fails, saying the frontmatter carries no one-line description
- PROOF-13 (RULE-1): A copy of the anchor skill whose description opens as a `|` block, its text indented on the next line, fails, saying the frontmatter carries no one-line description
- PROOF-14 (RULE-1): A copy of the anchor skill whose description runs on to an indented second line fails, saying the frontmatter carries no one-line description
- PROOF-15 (RULE-1): A copy of the command reference with the `purlin:anchor` row deleted from its `Command`, `Purpose` table fails, saying it carries no row for `purlin:anchor`
- PROOF-2 (RULE-2): The anchor skill gives the script `"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"`, quoted exactly so, on one line followed by the word `add` and on another followed by the word `sync`
- PROOF-16 (RULE-2): The anchor skill's `sync` section, read across its line breaks, says `` `--check` reports without writing `` and `` `purlin:drift` runs the same check ``
- PROOF-17 (RULE-2): A copy of the anchor skill that writes `address` where the script is followed by `add` fails, saying no line gives the script with the subcommand `add`
- PROOF-18 (RULE-2): A copy of the anchor skill that writes `syncall` where the script is followed by `sync` fails, saying no line gives the script with the subcommand `sync`
- PROOF-19 (RULE-2): A copy of the anchor skill whose `sync` section says `--check` `reports and rewrites` fails, saying that section does not carry `` `--check` reports without writing ``
- PROOF-20 (RULE-2): A copy of the anchor skill whose `sync` section says `purlin:drift` `runs its own check` fails, saying that section does not carry `` `purlin:drift` runs the same check ``
- PROOF-3 (RULE-3): The anchor skill's last section is headed with the words `next step` or `when you are done`, in any case; under that heading at least two outcomes stand as list items or table rows, and every one of them gives its own `→` directive
- PROOF-6 (RULE-3): A copy of the anchor skill whose outcome `Pin current and nothing moved` loses its `→` fails, naming that outcome as giving no directive
- PROOF-21 (RULE-3): A copy of the anchor skill with its closing section deleted, so that it ends on `Changing a pinned rule`, fails, saying it closes with that section, which does not name the next step
- PROOF-22 (RULE-3): A copy of the anchor skill whose closing section writes `->` in place of every `→` fails, saying the closing section gives no directive
- PROOF-23 (RULE-3): A copy of the anchor skill whose closing section is cut after its first outcome fails, saying it names 1 outcome where at least 2 are expected
- PROOF-4 (RULE-4): The anchor skill, as shipped, holds at most 160 lines
- PROOF-24 (RULE-4): A copy of the anchor skill with lines of prose added until it holds exactly 160 lines passes
- PROOF-25 (RULE-4): A copy of the anchor skill with lines of prose added until it holds 161 lines fails, saying it is 161 lines against a ceiling of 160
- PROOF-5 (RULE-5): The anchor skill, read across its line breaks, carries the sentence `A pin is always a commit, never a branch.`
- PROOF-26 (RULE-5): A copy of the anchor skill in which that sentence reads `A pin is a commit or a branch.` fails, saying the skill does not carry `A pin is always a commit, never a branch.`
- PROOF-27 (RULE-5): The anchor skill's section `Changing a pinned rule`, read across its line breaks, carries the sentence `Never edit a pinned rule in place.`
- PROOF-28 (RULE-5): A copy of the anchor skill in which `Never edit a pinned rule in place.` reads `Edit a pinned rule in place when the change is small.` fails, saying the section `Changing a pinned rule` does not carry the first
- PROOF-29 (RULE-5): The anchor skill's section `Changing a pinned rule`, read across its line breaks, says a change to the rule is `a pull request against the source repository`
- PROOF-30 (RULE-5): A copy of the anchor skill in which a change to a pinned rule is `a commit to the local copy` instead fails, saying the section `Changing a pinned rule` does not carry `a pull request against the source repository`
- PROOF-31 (RULE-5): In the anchor skill's section `Changing a pinned rule`, one sentence names a `separate local anchor` and the line `> Requires: <the pinned one>`
- PROOF-32 (RULE-5): A copy of the anchor skill in which a rule that belongs only to this project goes `in the pinned copy` instead fails, saying no sentence of the section `Changing a pinned rule` carries both
- PROOF-7 (RULE-6): The anchor skill's section on `create`, read across its line breaks, carries the sentence ``The folder `specs/_anchors/` is created with the first anchor, written here or brought in by `add`.``
- PROOF-8 (RULE-6): A copy of the anchor skill whose section on `create` says the folder `is created at setup` fails, saying that section does not say the folder is created with the first anchor
