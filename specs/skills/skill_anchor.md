# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must say. An anchor is a set of rules for the whole
>   project, and the skill is what creates one, pulls one from another
>   repository and keeps its pin current.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 16
> Highest-Proof: 38

## Rules

- RULE-1: `skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent to start `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` through `scripts/purlin_python.sh` for `add` and for `sync`
- RULE-3: The last section of `skills/anchor/SKILL.md` tells the agent to name the next step for each state the skill can end in, at least two, and gives each its own `→` directive
- RULE-4: The whole of `skills/anchor/SKILL.md` is at most 160 lines
- RULE-5: The skill tells the agent that a pin is always a commit, never a branch
- RULE-6: The skill tells the agent that the folder `specs/_anchors/` is created with the first anchor, whether written by `create` or brought in by `add`
- RULE-7: The skill tells the agent that an anchor's source is a spec in Purlin's format with at least one rule, kept in a git repository, and that any other source is refused and written with `purlin:anchor create`
- RULE-8: The `Command`, `Purpose` table of `references/purlin_commands.md` carries a row for `purlin:anchor` with its purpose
- RULE-9: The skill tells the agent that `sync --check` reports without writing and that `purlin:drift` runs the same check
- RULE-10: The skill tells the agent never to edit a pinned rule in place in the consuming project
- RULE-11: The skill tells the agent that a change to a pinned rule is a pull request against the source repository
- RULE-12: The skill tells the agent that a rule belonging only to this project goes in a local anchor of its own when it holds across the whole project, and in the spec of each feature it holds for when it does not
- RULE-13: The skill tells the agent that an anchor repository is for rules two or more projects must share, and that one project keeps its anchors in `specs/_anchors/`
- RULE-14: The skill tells the agent to commit a new anchor with the `anchor(<name>): create` prefix
- RULE-15: The skill tells the agent that an anchor carries no `> Scope:`, since its rules cover the whole project, and that a rule not checkable across the whole project goes in the spec of each feature that needs it
- RULE-16: The skill tells the agent that a rule of a pinned anchor that does not apply to this project is signed as not applying, with the reason, and that a rule of the project's own anchor that does not apply is deleted

## Proof

- PROOF-1 (RULE-1): The anchor skill opens with a frontmatter block set between two `---` lines; the block reads `name: anchor` and carries a `description:` whose text sits on that same line
- PROOF-9 (RULE-8): Purlin's command reference has a row in its `Command`, `Purpose` table whose first cell is `` `purlin:anchor <cmd>` `` and whose second cell holds the command's purpose
- PROOF-2 (RULE-2): The anchor skill gives `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"`, quoted exactly so, on one line followed by the word `add` and on another followed by the word `sync`
- PROOF-16 (RULE-9): The anchor skill's `sync` section, read across its line breaks, says `` `--check` reports without writing `` and `` `purlin:drift` runs the same check ``
- PROOF-3 (RULE-3): The anchor skill's last section is headed with the words `next step` or `when you are done`, in any case; under that heading at least two outcomes stand as list items or table rows, and every one of them gives its own `→` directive
- PROOF-4 (RULE-4): The anchor skill, as shipped, holds at most 160 lines
- PROOF-24 (RULE-4): A copy of the anchor skill with lines of prose added until it holds exactly 160 lines passes
- PROOF-5 (RULE-5): The anchor skill, read across its line breaks, carries the sentence `A pin is always a commit, never a branch.`
- PROOF-27 (RULE-10): The anchor skill's section `Changing a pinned rule`, read across its line breaks, carries the sentence `Never edit a pinned rule in place.`
- PROOF-29 (RULE-11): The anchor skill's section `Changing a pinned rule`, read across its line breaks, says a change to the rule is `a pull request against the source repository`
- PROOF-31 (RULE-12): The anchor skill's section `Changing a pinned rule`, read across its line breaks, carries the sentence `A rule that belongs only to this project goes in a local anchor of its own when it holds across the whole project, and in the spec of each feature it holds for when it does not.`
- PROOF-7 (RULE-6): The anchor skill's section on `create`, read across its line breaks, carries the sentence ``The folder `specs/_anchors/` is created with the first anchor, written here or brought in by `add`.``
- PROOF-33 (RULE-7): The anchor skill's section on `add`, read across its line breaks, says `The file is a spec in Purlin's format that holds at least one rule, kept in a git repository.`, that any other source is refused and nothing is written, and that the refusal names `purlin:anchor create <name>`
- PROOF-34 (RULE-13): The anchor skill's section `One repository is the default` says `Reach for an anchor repository only when two or more projects must share the same rules`, and that most projects need nothing but `specs/_anchors/`
- PROOF-35 (RULE-14): The anchor skill's section on `create`, read across its line breaks, says to commit the new anchor with the `anchor(<name>): create` prefix
- PROOF-36 (RULE-15): The anchor skill's section on `create`, read across its line breaks, says ``An anchor carries no `> Scope:`: its rules cover the whole project``, and the only other metadata lines it names are `> Description:` and `> Type:`
- PROOF-37 (RULE-15): The anchor skill's section on `create`, read across its line breaks, says a rule that cannot be checked across the whole project is not an anchor's and is written in the spec of each feature that needs it, with `purlin:spec <feature>`
- PROOF-38 (RULE-16): The anchor skill's section `Changing a pinned rule`, read across its line breaks, says a rule of a pinned anchor that does not apply here is signed as not applying with `--does-not-apply "<why>"`, and a rule of the project's own anchor that does not apply is deleted
