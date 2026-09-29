# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks the rules that wait for a person
>   and attests that a rule, its proof, its test, its code and what the audit found belong
>   together, and the attestation is a signed commit, so the text has to say what the walk asks,
>   when the signature counts, and where the version for the tag comes from.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/sign/SKILL.md` opens with a frontmatter block whose `name` is `sign` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:sign`
- RULE-2: The skill reads what waits for a person from `sync_status` as each rule's `left`, `to_test_by_hand` or `to_sign`, shows what the audit read and found with `scripts/review/ai_audit.py` before it writes anything, and writes the signature with `scripts/review/sign.py`, both scripts inside `${CLAUDE_PLUGIN_ROOT}`
- RULE-3: The last section of `skills/sign/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/sign/SKILL.md` is at most 185 lines
- RULE-5: The skill states the two things that make a signature count, a last commit signed with any key and a signature still made over the rule, the proof, the test, the code, what the audit found and the machine each system's tests ran on, and that it counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it
- RULE-6: The skill names the walk's three answers, sign, add a case and skip, and says that a skipped rule waits again next time
- RULE-7: The skill says what each of the three gates leaves it able to do: under `passed` and `strong` the walk and `--note` work on the hand checks, and under `signed` every rule waits for a signature once its tests pass and its audit is strong
- RULE-8: The skill says that at the gate `signed`, when nothing is left but the tag, the script writes the evidence package `.purlin/evidence/package/<version>.json`, commits it as a signed commit and writes the signed tag `signed/<version>` on that commit; that below `signed` it writes no tag and no package; and that it never pushes
- RULE-9: The skill says the version is read from the `VERSION` file, then `package.json`, then `pyproject.toml`, then the first `*.csproj` at the root, and that with none stated it asks the person for the version and offers to write it to a `VERSION` file
- RULE-10: The skill shows the commands the script prints when there is no key to sign with, and says to offer to run them and carry on

## Proof

- PROOF-1 (RULE-1): A reader of the sign skill finds that it opens with a frontmatter block between two `---` lines, carrying `name: sign` and a `description:` whose value sits whole on that same line, not empty and not opening a `>` or `|` block; the command reference, `references/purlin_commands.md`, carries a table row whose first cell is the `purlin:sign` command. With the `name:` line deleted, the check reports that it found no name where `sign` is expected; with the description left empty, left empty with text on the next line, written as a `|` block, or run onto a second line, it reports that the frontmatter carries no one-line description; with the `purlin:sign` row removed from the command reference, though the name still appears elsewhere in it, it reports that the reference carries no row for `purlin:sign`
- PROOF-2 (RULE-2): A reader of the sign skill finds, in its section on what waits, the `sync_status()` call and then `to_test_by_hand` and `to_sign`, and finds the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"` earlier in the file than the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"`
- PROOF-9 (RULE-2): A copy of the sign skill whose first mentions of the audit script and the signing script are swapped is reported, with the two paths named out of order and their offsets
- PROOF-10 (RULE-2): A copy of the sign skill with the `sync_status()` call deleted from its section on what waits is reported as not reading `to_test_by_hand` and `to_sign` from `sync_status`
- PROOF-11 (RULE-2): A copy of the sign skill whose audit script path is written without `${CLAUDE_PLUGIN_ROOT}` is reported as not carrying that path
- PROOF-3 (RULE-3): A reader of the sign skill finds that its last section's heading names the `next step`, or reads `when you are done`, in any case; that the section lists at least 2 outcomes, counting list items and the table rows below a table's header and divider; and that every outcome carries its own `→` directive. With the closing section deleted, the check reports the heading of the section that now closes the file; with every `→` removed from it, it reports that the closing section gives no directive; with its table cut to the header, the divider and the first row, it reports 1 outcome where at least 2 are expected; with the `→` removed from the row `A case was added` alone, it reports that outcome as giving no directive
- PROOF-4 (RULE-4): Read `skills/sign/SKILL.md` and count its lines; verify the count is at most 185. Appending prose until the file passes 185 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): A reader of the sign skill finds a table headed `A signature counts when` whose rows are exactly `The last commit that touched the file is signed, with any key` and `It is still made over the rule, the proof, the test, the code its feature lists, what the audit found and the machine each system's tests ran on`, and, in its section on when a signature counts, the clause `the signature counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it`
- PROOF-12 (RULE-5): A copy of the sign skill with the row `The last commit that touched the file is signed, with any key` deleted is reported as lacking that condition
- PROOF-13 (RULE-5): A copy of the sign skill whose clause reads `whoever committed last` in place of `whoever last committed to the test file` is reported as not saying whose signature counts
- PROOF-6 (RULE-6): A reader of the sign skill finds a section whose heading names the `three answers`, and in it `**Sign.**`, `**Add a case.**`, `**Skip.**` and the sentence `A skipped rule waits again next time`
- PROOF-7 (RULE-7): A reader of the sign skill finds a table headed `Gate` with a row for each of `passed`, `strong` and `signed`; the `passed` and `strong` rows each say `The walk and --note work on the hand checks`, and the `signed` row says `Every rule waits for a signature once its tests pass and its audit is strong`
- PROOF-15 (RULE-7): A copy of the sign skill with the `passed` row of its gate table removed is reported as having no `passed` row
- PROOF-16 (RULE-7): A copy of the sign skill whose `signed` row lacks `Every rule waits for a signature` is reported as lacking those words in that row
- PROOF-8 (RULE-8): A reader of the sign skill finds, in its section on the tag, "At the gate `signed`, when nothing is left but the tag", the path `.purlin/evidence/package/<version>.json`, `commits it as a signed commit`, `writes a signed tag`, `on that commit`, "Below `signed` it writes no tag and no package" and `this skill never pushes`, and the printed line `Evidence package committed: .purlin/evidence/package/1.4.0.json.` above `Tagged signed/1.4.0 at a1b2c3d.`
- PROOF-17 (RULE-8): A copy of the sign skill with its package line and its tag line swapped is reported as printing the tag line before the package line
- PROOF-18 (RULE-8): A copy of the sign skill with "Below `signed` it writes no tag and no package" deleted is reported as lacking those words
- PROOF-19 (RULE-9): A reader of the sign skill finds, in its section on the tag, `VERSION`, `package.json`, `pyproject.toml` and `*.csproj` in that order, and the words `ask the person for the version, offer to write it to a VERSION file`, with the file name in code
- PROOF-20 (RULE-9): A copy of the sign skill with `offer to write it to a` deleted from its section on the tag is reported as lacking the offer
- PROOF-21 (RULE-10): A reader of the sign skill finds, in its section on the key, the lines `No key to sign with. These commands set one up:`, `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""`, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`, and the words `offer to run them` and `carry on`
- PROOF-22 (RULE-10): A copy of the sign skill with `offer to run them` deleted from its section on the key is reported as lacking those words
