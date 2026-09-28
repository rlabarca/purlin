# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what changed since your last
>   pull, in one view per role, `pm`, `eng` and `qa`, and it writes nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/drift/SKILL.md` opens with a frontmatter block whose `name` is `drift` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:drift`
- RULE-2: The skill takes its data from the `drift` tool and points at `references/drift_criteria.md` for what each view's lines mean rather than restating it, and it invents no line the tool does not return
- RULE-3: The last section of `skills/drift/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/drift/SKILL.md` is at most 150 lines [level: passed]

## Proof

- PROOF-1 (RULE-1): The `purlin:drift` skill definition opens on its first line with a block set between two `---` lines. The block carries `name: drift` and a `description:` whose one-line value is on that line. The command reference has a table row whose first cell is `` `purlin:drift [role]` `` and whose second cell holds its purpose. A definition whose `name:` line is deleted fails, naming the expected name `drift`. A `description:` left empty, written as `>-` or `|`, moved to the line below or run on to an indented second line fails as carrying no one-line description. A definition whose first line is blank fails as not opening with a frontmatter block. A command reference whose row has an empty purpose cell, or that has no row, fails, saying it carries no row for `purlin:drift`
- PROOF-2 (RULE-2): The `purlin:drift` skill definition, read across its line breaks, carries the call `drift(role="eng")`, the path `references/drift_criteria.md` and the sentence `do not restate them here and do not invent a line the tool does not return`. None of the git facts that the drift criteria give as the source of each `eng` and `qa` line, such as ``Rules whose passed cell reads `no test` ``, appears in it. A definition into which that fact is pasted fails, naming the fact it restates
- PROOF-3 (RULE-3): The last `## ` section of the `purlin:drift` skill definition has a heading containing `next step`. Its table has at least two outcome rows below the header and divider, each giving its own `→` directive. A definition that closes on `Step 3: what drift never does` fails, naming that heading. With every `→` taken out it fails as giving no directive. A table cut to its header and divider fails with the count 0 beside the 2 expected, and cut to one row with the count 1. The row `A rule removed` fails without its `→`, naming that row
- PROOF-4 (RULE-4): Read `skills/drift/SKILL.md` and count its lines; verify the count is at most 150. Appending prose until the file passes 150 lines fails, and the failure reports the count it found beside the ceiling
