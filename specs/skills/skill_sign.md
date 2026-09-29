# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks the rules that wait for a person
>   and attests that a rule, its proof, its test, its code and what the audit found belong
>   together, and the attestation is a signed commit, so the text has to say what the walk asks,
>   when the signature counts, and where the version for the tag comes from.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/sign/SKILL.md` opens with a frontmatter block whose `name` is `sign` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:sign`
- RULE-2: The skill reads what waits for a person from `sync_status` as each rule's `left`, `to_test_by_hand` or `to_sign`, says to read what the audit read and found before anything is written, and names `scripts/review/ai_audit.py`, which shows it, ahead of `scripts/review/sign.py`, which writes the signature, both inside `${CLAUDE_PLUGIN_ROOT}`
- RULE-3: The last section of `skills/sign/SKILL.md` names the next step for each way the walk can end, pairing what it ended on with a `→` directive, except `Nothing left to do.`, which at the gates `passed` and `strong` names no command
- RULE-4: The whole of `skills/sign/SKILL.md` is at most 185 lines
- RULE-5: The skill states the two things that make a signature count, a last commit signed with any key and a signature still made over the rule, the proof, the test, the code, what the audit found and the machine each system's tests ran on, and that it counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it
- RULE-6: The skill names the walk's three answers, sign, add a case and skip, and says that a skipped rule waits again next time
- RULE-7: The skill says what each of the three gates leaves it able to do: under `passed` and `strong` the walk and `--note` work on the hand checks, and under `signed` every rule waits for a signature once its tests pass and its audit is strong
- RULE-8: The skill says that at the gate `signed`, when nothing is left but the tag, the script writes the evidence package `.purlin/evidence/package/<version>.json`, commits it as a signed commit and writes the signed tag `signed/<version>` on that commit; that below `signed` it writes no tag and no package; and that it never pushes
- RULE-9: The skill says the version is read from the `VERSION` file, then `package.json`, then `pyproject.toml`, then the first `*.csproj` at the root, and that with none stated it asks the person for the version and offers to write it to a `VERSION` file
- RULE-10: The skill shows the commands the script prints when there is no key to sign with, and says to offer to run them and carry on

## Proof

- PROOF-1 (RULE-1): The sign skill opens with a frontmatter block between two `---` lines that carries `name: sign` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-23 (RULE-1): The command reference carries a row in its command table whose first cell is the `purlin:sign` command and whose second cell gives its purpose
- PROOF-24 (RULE-1): A copy of the sign skill with its `name: sign` line deleted is reported as having no name where `sign` is expected
- PROOF-25 (RULE-1): A copy of the sign skill whose `description:` line is left empty is reported as carrying no one-line description
- PROOF-26 (RULE-1): A copy of the sign skill whose `description:` line is left empty, with the `name: sign` line moved below it, is reported as carrying no one-line description
- PROOF-27 (RULE-1): A copy of the sign skill whose description is written as a `|` block, its text on the indented line below, is reported as carrying no one-line description
- PROOF-28 (RULE-1): A copy of the sign skill whose description runs onto an indented second line is reported as carrying no one-line description
- PROOF-29 (RULE-1): A copy of the command reference with the `purlin:sign` row removed from its command table, the name still written elsewhere in it, is reported as carrying no row for `purlin:sign`
- PROOF-2 (RULE-2): In the sign skill's section on what waits, the `sync_status()` call comes first, then each rule's `left`, then `to_test_by_hand` and `to_sign`, in that order
- PROOF-9 (RULE-2): A copy of the sign skill whose first mentions of the audit script and the signing script are swapped is reported as naming the two paths out of order, with their offsets
- PROOF-10 (RULE-2): A copy of the sign skill with the `sync_status()` call deleted from its section on what waits is reported as not reading `left`, `to_test_by_hand` and `to_sign` from `sync_status`
- PROOF-11 (RULE-2): A copy of the sign skill whose audit script path is written as `"scripts/review/ai_audit.py"`, without `${CLAUDE_PLUGIN_ROOT}`, is reported as not carrying the full path
- PROOF-30 (RULE-2): The sign skill's section on what waits says `Read what the audit read and found for a rule before anything is written`
- PROOF-31 (RULE-2): In the sign skill, the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"` comes before the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"`
- PROOF-3 (RULE-3): The sign skill's last section has a heading naming the `next step` and a table of at least 2 outcomes below its header and divider, and every outcome but `Nothing left to do.` carries its own `→` directive
- PROOF-32 (RULE-3): A copy of the sign skill with its closing section deleted is reported as closing with the section `Step 6: the version and the tag`, which does not name the next step
- PROOF-33 (RULE-3): A copy of the sign skill with every `→` in its closing section written as `->` is reported as giving no directive there
- PROOF-34 (RULE-3): A copy of the sign skill whose closing table is cut to its header, its divider and its first row is reported as naming 1 outcome where at least 2 are expected
- PROOF-35 (RULE-3): A copy of the sign skill with the `→` taken out of the row `A case was added` alone is reported as that outcome giving no `→` directive
- PROOF-4 (RULE-4): The sign skill, counted line by line, is at most 185 lines long
- PROOF-36 (RULE-4): A copy of the sign skill lengthened with lines of prose to exactly 185 lines is reported as having no problem
- PROOF-37 (RULE-4): A copy of the sign skill lengthened with lines of prose to 186 lines is reported as being 186 lines against its ceiling of 185
- PROOF-5 (RULE-5): The sign skill's table headed `A signature counts when` has exactly two rows: `The last commit that touched the file is signed, with any key` and `It is still made over the rule, the proof, the test, the code its feature lists, what the audit found and the machine each system's tests ran on`
- PROOF-12 (RULE-5): A copy of the sign skill with the row `The last commit that touched the file is signed, with any key` deleted is reported as its table lacking that row
- PROOF-13 (RULE-5): A copy of the sign skill whose clause reads `whoever committed last` in place of `whoever last committed to the test file` is reported as not saying whose signature counts
- PROOF-38 (RULE-5): The sign skill's section on when a signature counts says `the signature counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it`
- PROOF-39 (RULE-5): A copy of the sign skill with a third row, `The signer is on a list`, added to its table `A signature counts when` is reported as that table having a third row
- PROOF-6 (RULE-6): The sign skill has a section whose heading names the `three answers`, and in it `**Sign.**`, `**Add a case.**`, `**Skip.**` and the sentence `A skipped rule waits again next time`
- PROOF-7 (RULE-7): The sign skill's table headed `Gate` has a row for each of `passed`, `strong` and `signed`; the `passed` and `strong` rows each say `The walk and --note work on the hand checks`, and the `signed` row says `Every rule waits for a signature once its tests pass and its audit is strong`
- PROOF-15 (RULE-7): A copy of the sign skill with the `passed` row removed from its gate table is reported as having no `passed` row
- PROOF-16 (RULE-7): A copy of the sign skill whose `signed` row reads `Rules wait once` in place of `Every rule waits for a signature once` is reported as that row lacking those words
- PROOF-8 (RULE-8): The sign skill's section on the tag carries "At the gate `signed`, when nothing is left but the tag", the path `.purlin/evidence/package/<version>.json`, and the words `commits it as a signed commit`, `writes a signed tag` and `on that commit`
- PROOF-17 (RULE-8): A copy of the sign skill with its printed package line and its printed tag line swapped is reported as printing the tag line before the package line
- PROOF-18 (RULE-8): A copy of the sign skill with "Below `signed` it writes no tag and no package." deleted is reported as its section on the tag lacking those words
- PROOF-40 (RULE-8): The sign skill's section on the tag shows the printed line `Evidence package committed: .purlin/evidence/package/1.4.0.json.` above the line `Tagged signed/1.4.0 at a1b2c3d.`
- PROOF-41 (RULE-8): The sign skill's section on the tag says "Below `signed` it writes no tag and no package"
- PROOF-42 (RULE-8): The sign skill's section on the tag says `this skill never pushes`
- PROOF-19 (RULE-9): The sign skill's section on the tag names `VERSION`, `package.json`, `pyproject.toml` and `*.csproj`, in that order
- PROOF-20 (RULE-9): A copy of the sign skill with `offer to write it to a` replaced by `then use` in its section on the tag is reported as not offering to write the version
- PROOF-43 (RULE-9): The sign skill's section on the tag says to `ask the person for the version, offer to write it to a VERSION file`, with the file name in code
- PROOF-21 (RULE-10): The sign skill's section on the key shows the lines `No key to sign with. These commands set one up:`, `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""`, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`, and says `offer to run them` and `carry on`
- PROOF-22 (RULE-10): A copy of the sign skill with `offer to run them` replaced by `tell them` in its section on the key is reported as lacking those words
