# Feature: skill_approve

> Description: What `skills/approve/SKILL.md` must say. Approve attests that a rule, its proof and
>   its test belong together, and the attestation is a signed commit, so the text has
>   to say who may make it and when it stops counting.
> Scope: skills/approve/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/approve/SKILL.md` opens with a frontmatter block whose `name` is `approve` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:approve` [risk: medium] [origin: eng]
- RULE-2: The skill shows the brief with `scripts/review/brief.py` before it writes anything and writes the approval with `scripts/review/approve.py`, both inside `${CLAUDE_PLUGIN_ROOT}` [risk: high] [origin: eng]
- RULE-3: The last section of `skills/approve/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/approve/SKILL.md` is at most 95 lines [risk: low] [origin: eng]
- RULE-5: The skill states that an approval does not count when its author is the author of the commit that last touched the test, and that under the `approved` gate the approval commit is signed and reaches the default branch by pull request [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/approve/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: approve` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:approve`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/approve/SKILL.md`; verify the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"` appears in a step before the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py"`, comparing their offsets in the file. Swapping the two steps fails on the offset comparison
- PROOF-3 (RULE-3): Read `skills/approve/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/approve/SKILL.md` and count its lines; verify the count is at most 95. Appending prose until the file passes 95 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/approve/SKILL.md` with its line wrapping collapsed; verify it carries the sentence `An approval also does not count when you are the author of the commit that last touched the test.` and the clause `it reaches the default branch by pull request`. Dropping the negation, so that the sentence reads `An approval counts when you are the author of the commit that last touched the test`, fails naming the sentence it did not find
