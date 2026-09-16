# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks the review list and attests that a
>   rule, its proof and its test belong together, and the attestation is a signed commit, so the
>   text has to say who may make it, what the walk asks, and when the signature stops counting.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/sign/SKILL.md` opens with a frontmatter block whose `name` is `sign` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:sign` [risk: medium] [origin: eng]
- RULE-2: The skill reads the review list from `sync_status` as `payload.review_list`, shows the brief with `scripts/review/brief.py` before it writes anything, and writes the signature with `scripts/review/sign.py`, both scripts inside `${CLAUDE_PLUGIN_ROOT}` [risk: high] [origin: eng]
- RULE-3: The last section of `skills/sign/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome [risk: medium] [origin: eng]
- RULE-4: The whole of `skills/sign/SKILL.md` is at most 150 lines [risk: low] [origin: eng]
- RULE-5: The skill states that a signature does not count when its author is the author of the commit that last touched the test, and that under the `signed` gate the signing commit is signed and reaches the protected branch [risk: high] [origin: eng]
- RULE-6: The skill names the walk's four answers, sign, add a case, hold and skip, and says that a skipped rule is on the list again next time [risk: high] [origin: eng]
- RULE-7: The skill says what each of the three gates leaves it able to do: under `passed` it names what `purlin:init --gate strong` would add and stops, under `strong` the walk, `--note` and `--hold` work, and under `signed` every rule at or above `sign_at` needs a signature [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `skills/sign/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: sign` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:sign`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/sign/SKILL.md`; verify it carries `payload.review_list`, and that the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"` appears at a smaller offset than the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"`. Swapping the two steps fails on the offset comparison
- PROOF-3 (RULE-3): Read `skills/sign/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/sign/SKILL.md` and count its lines; verify the count is at most 150. Appending prose until the file passes 150 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/sign/SKILL.md` with its line wrapping collapsed; verify it carries the clause `That author did not author the last commit to the test file` and the clause `the commit is on the protected branch`. Dropping the negation, so that the first clause reads `That author authored the last commit to the test file`, fails naming the clause it did not find
- PROOF-6 (RULE-6): Read `skills/sign/SKILL.md`; verify the section whose heading names the answers carries the four bold labels `**Sign.**`, `**Add a case.**`, `**Hold.**` and `**Skip.**`, one assertion per label, and that the section carries the sentence `A skipped rule is on the list again next time`. Deleting the hold answer fails naming `**Hold.**`
- PROOF-7 (RULE-7): Read the gate table of `skills/sign/SKILL.md`; verify it carries one row each for `passed`, `strong` and `signed`, that the `passed` row names `purlin:init --gate strong` and the word `stops`, that the `strong` row names `--note` and `--hold`, and that the `signed` row names `sign_at`. Removing the `passed` row fails naming the gate it did not find
