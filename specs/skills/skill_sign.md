# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks the rules that wait for a person
>   and attests that a rule, its proof, its test, its code and what the audit found belong
>   together, and the attestation is a signed commit, so the text has to say what the walk asks,
>   when the signature counts, and where the version for the tag comes from.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 21

## Rules

- RULE-1: `skills/sign/SKILL.md` tells the agent the skill's name, `sign`, and its purpose in one non-empty line, in a frontmatter block at its top
- RULE-2: The skill tells the agent to read what waits for a person from `sync_status`, as each rule's `left`, `to_test_by_hand` or `to_sign`
- RULE-3: The last section of the skill tells the agent the next step for each way the walk can end, pairing what it ended on with a `→` directive, except `Nothing left to do.`, which at the gates `passed` and `strong` names no command
- RULE-4: The skill gives the agent its instructions in at most 185 lines, the whole of `skills/sign/SKILL.md`
- RULE-5: The skill tells the agent the two things that make a signature count: a last commit signed with any key, and a signature still made over the rule, the proof, the test, the code, what the audit found and the machine each system's tests ran on
- RULE-6: The skill tells the agent the walk's three answers, sign, add a case and skip, and that a skipped rule waits again next time
- RULE-7: The skill tells the agent what each of the three gates leaves it able to do: under `passed` and `strong` the walk and `--note` work on the hand checks, and under `signed` every rule waits for a signature once its tests pass and its audit is strong
- RULE-8: The skill tells the agent that at the gate `signed`, when nothing is left but the tag, the script writes the evidence package `.purlin/evidence/package/<version>.json`, commits it as a signed commit and writes the signed tag `signed/<version>` on that commit
- RULE-9: The skill tells the agent that the version is read from the `VERSION` file, then `package.json`, then `pyproject.toml`, then the first `*.csproj` at the root
- RULE-10: The skill shows the agent the commands the script prints when there is no key to sign with, and tells it to offer to run them and carry on
- RULE-11: The table of commands in `references/purlin_commands.md` tells the agent that `purlin:sign` exists, in a row carrying its purpose
- RULE-12: The skill tells the agent to read what the audit read and found for a rule before anything is written, naming `scripts/review/ai_audit.py`, which shows it, ahead of `scripts/review/sign.py`, which writes the signature, both inside `${CLAUDE_PLUGIN_ROOT}`
- RULE-13: The skill tells the agent that a signature counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it
- RULE-14: The skill tells the agent that below the gate `signed` the script writes no tag and no evidence package
- RULE-15: The skill tells the agent that it never pushes
- RULE-16: The skill tells the agent that with no version stated it asks the person for the version and offers to write it to a `VERSION` file
- RULE-17: The skill tells the agent that the script exits 1 when the tag was refused for a reason to fix, uncommitted work or results, no version, a package not committed or git failing to write the tag, and 0 when the tag already exists
- RULE-18: The skill tells the agent to call `sync_status` with `project_root` set to the project root, the top folder of the git checkout
- RULE-19: The skill tells the agent that at the gate `signed` a rule of a spec that names no files is signed, and that its line reads `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>`
- RULE-20: The skill tells the agent the line the script prints when no version is stated, `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.`
- RULE-21: The skill tells the agent the line the script prints when the tag is already written, `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.`

## Proof

- PROOF-1 (RULE-1): The sign skill opens with a frontmatter block between two `---` lines that carries `name: sign` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-23 (RULE-11): The command reference carries a row in its command table whose first cell is the `purlin:sign` command and whose second cell gives its purpose
- PROOF-2 (RULE-2): In the sign skill's section on what waits, `sync_status` comes first, then each rule's `left`, then `to_test_by_hand` and `to_sign`, in that order
- PROOF-46 (RULE-18): The sign skill's section on what waits, its line breaks read as spaces, says to call `sync_status` with `project_root` set to the project root, the top folder of the git checkout
- PROOF-30 (RULE-12): The sign skill's section on what waits says `Read what the audit read and found for a rule before anything is written`
- PROOF-31 (RULE-12): In the sign skill, the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"` comes before the first mention of `"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"`
- PROOF-3 (RULE-3): The sign skill's last section has a heading naming the `next step` and a table of at least 2 outcomes below its header and divider, and every outcome but `Nothing left to do.` carries its own `→` directive
- PROOF-44 (RULE-3): The sign skill's closing table gives the outcome `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` the line `→ Run: purlin:status <feature>`
- PROOF-4 (RULE-4): The sign skill, counted line by line, is at most 185 lines long
- PROOF-5 (RULE-5): The sign skill's table headed `A signature counts when` has exactly two rows: `The last commit that touched the file is signed, with any key` and `It is still made over the rule, the proof, the test, the code its feature lists, what the audit found and the machine each system's tests ran on`
- PROOF-38 (RULE-13): The sign skill's section on when a signature counts says `the signature counts whoever wrote it, whoever last committed to the test file, and on whatever branch carries it`
- PROOF-47 (RULE-19): The sign skill's section on when a signature counts says that at the gate `signed` a rule of a spec that names no files is signed, and shows, on a line of its own, `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>`
- PROOF-6 (RULE-6): The sign skill has a section whose heading names the `three answers`, and in it `**Sign.**`, `**Add a case.**`, `**Skip.**` and the sentence `A skipped rule waits again next time`
- PROOF-7 (RULE-7): The sign skill's table headed `Gate` has a row for each of `passed`, `strong` and `signed`; the `passed` and `strong` rows each say `The walk and --note work on the hand checks`, and the `signed` row says `Every rule waits for a signature once its tests pass and its audit is strong`
- PROOF-8 (RULE-8): The sign skill's section on the tag carries "At the gate `signed`, when nothing is left but the tag", the path `.purlin/evidence/package/<version>.json`, and the words `commits it as a signed commit`, `writes a signed tag` and `on that commit`
- PROOF-40 (RULE-8): The sign skill's section on the tag shows the printed line `Evidence package committed: .purlin/evidence/package/1.4.0.json.` above the line `Tagged signed/1.4.0 at a1b2c3d.`
- PROOF-41 (RULE-14): The sign skill's section on the tag says "Below `signed` it writes no tag and no package"
- PROOF-42 (RULE-15): The sign skill's section on the tag says `this skill never pushes`
- PROOF-19 (RULE-9): The sign skill's section on the tag names `VERSION`, `package.json`, `pyproject.toml` and `*.csproj`, in that order
- PROOF-43 (RULE-16): The sign skill's section on the tag says to `ask the person for the version, offer to write it to a VERSION file`, with the file name in code
- PROOF-48 (RULE-20): The sign skill's section on the tag, its line breaks read as spaces, quotes `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` word for word
- PROOF-49 (RULE-21): The sign skill's section on the tag, its line breaks read as spaces, quotes `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.` word for word
- PROOF-21 (RULE-10): The sign skill's section on the key shows the lines `No key to sign with. These commands set one up:`, `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""`, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`, and says `offer to run them` and `carry on`
- PROOF-45 (RULE-17): The sign skill's section on the tag says the script exits 1 when the tag was refused for a reason to fix, naming uncommitted work or results, no version, a package not committed and git failing to write the tag, and 0 when the tag already exists
