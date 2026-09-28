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

- PROOF-1 (RULE-1): The `purlin:drift` skill definition opens on its first line with a block set between two `---` lines, and the block carries `name: drift` and a `description:` line whose value is not empty; the command reference `references/purlin_commands.md` carries `purlin:drift`. A definition whose `name` reads anything but `drift`, whose `description:` line is empty or holds only `>`, the mark of a value folded onto the lines below, or whose first line is anything but `---`, fails
- PROOF-2 (RULE-2): The `purlin:drift` skill definition, read across its line breaks, carries the call `drift(role="eng")`, the path `references/drift_criteria.md` and the sentence `do not restate them here and do not invent a line the tool does not return`. A definition that lacks any one of the three, or words the sentence any other way, fails, and the failure names the one it lacks
- PROOF-3 (RULE-3): The last `## ` section of the `purlin:drift` skill definition has a heading containing `next step` or `when you are done`, in any case, at least two lines that are list items or table lines, and at least one line carrying `→`. A definition that closes on any other section, such as `Step 3: what drift never does`, fails, and the failure names that heading
- PROOF-4 (RULE-4): Read `skills/drift/SKILL.md` and count its lines; verify the count is at most 150. Appending prose until the file passes 150 lines fails, and the failure reports the count it found beside the ceiling
