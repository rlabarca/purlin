# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks the queue and attests that a
>   rule, its proof and its test belong together, and the attestation is a signed commit, so the
>   text has to say who may make it, what the walk asks, and when the signature stops counting.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/sign/SKILL.md` opens with a frontmatter block whose `name` is `sign` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:sign`
- RULE-2: The skill reads the queue from `sync_status` as `payload.queue`, shows what the audit read and found with `scripts/review/ai_audit.py` before it writes anything, and writes the signature with `scripts/review/sign.py`, both scripts inside `${CLAUDE_PLUGIN_ROOT}`
- RULE-3: The last section of `skills/sign/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/sign/SKILL.md` is at most 185 lines [level: passed]
- RULE-5: The skill states the two things that make a signature count under the `signed` gate, a signing commit that is signed and verifies and bound hashes that still match, and that it counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it
- RULE-6: The skill names the walk's three answers, sign, add a case and skip, and says that a skipped rule is in the queue again next time
- RULE-7: The skill says what each of the three gates leaves it able to do: under `passed` it names what `purlin:init --gate strong` would add and stops, under `strong` the walk and `--note` work on the hand checks, and under `signed` every rule whose level is `signed` needs a signature

## Proof

- PROOF-1 (RULE-1): Read `skills/sign/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: sign` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:sign`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/sign/SKILL.md`; verify it carries `payload.queue`, and that the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"` appears at a smaller offset than the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"`. Swapping the two steps fails on the offset comparison
- PROOF-3 (RULE-3): Read `skills/sign/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/sign/SKILL.md` and count its lines; verify the count is at most 185. Appending prose until the file passes 185 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/sign/SKILL.md` with its line wrapping collapsed; verify it carries the clause `The commit that added the file is signed and the signature verifies`, the clause `Its bound hashes still match the rule, the proof, the test and what the audit found` and the clause `whoever wrote it, whoever last committed to the test file, and on whatever branch carries it`. Deleting any one of them fails naming the clause it did not find
- PROOF-6 (RULE-6): Read `skills/sign/SKILL.md`; verify the section whose heading names the answers carries the three bold labels `**Sign.**`, `**Add a case.**` and `**Skip.**`, one assertion per label, and that the section carries the sentence `A skipped rule is in the queue again next time`. Deleting the skip answer fails naming `**Skip.**`
- PROOF-7 (RULE-7): Read the gate table of `skills/sign/SKILL.md`; verify it carries one row each for `passed`, `strong` and `signed`, that the `passed` row names `purlin:init --gate strong` and the word `stops`, that the `strong` row names `--note` and `hand check`, and that the `signed` row names `[level: passed]`. Removing the `passed` row fails naming the gate it did not find
