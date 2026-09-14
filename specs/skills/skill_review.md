# Feature: skill_review

> Description: What `skills/review/SKILL.md` must say. Review finds every rule that needs a human
>   look, orders it by risk and walks it one brief at a time, so its text decides
>   what QA is asked to read.
> Scope: skills/review/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/review/SKILL.md` opens with a frontmatter block whose `name` is `review` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:review` [risk: medium] [origin: eng]
- RULE-2: The skill reads the review list from `sync_status` as `payload.review_list`, shows each rule with `scripts/review/brief.py` and writes the approval with `scripts/review/approve.py`, both inside `${CLAUDE_PLUGIN_ROOT}` [risk: high] [origin: eng]
- RULE-3: The last section of `skills/review/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/review/SKILL.md` is at most 145 lines [risk: low] [origin: eng]
- RULE-5: A rule whose only standing is `re-verify pending` is never put on the review list: the code changed, the approval stands, and CI clears it on the next run [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/review/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: review` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:review`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/review/SKILL.md`; verify it carries `payload.review_list`, the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"` and the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py"`, one assertion per literal. Replacing the brief fence with a bare `brief.py` fails naming the missing literal
- PROOF-3 (RULE-3): Read `skills/review/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/review/SKILL.md` and count its lines; verify the count is at most 145. Appending prose until the file passes 145 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/review/SKILL.md` with its line wrapping collapsed; verify it carries the sentence that opens "Rules with only `re-verify pending` are **not** on the list" and the clause `the approval stands`, and that no row of the table of reasons a rule is on the list names `re-verify`. Adding a `re-verify pending` row to that table fails, printing the row it found
