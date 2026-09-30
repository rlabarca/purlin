# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign walks a release's evidence package with
>   a person, one stop at a time where there is something to look at, and adds their sign-off
>   over the package in a signed commit, so the text has to say how the agent runs the walk in
>   two calls, what each stop takes as an answer, when a sign-off counts and what the first
>   sign-off writes.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 31
> Highest-Proof: 62

## Rules

- RULE-1: `skills/sign/SKILL.md` tells the agent the skill's name, `sign`, and its purpose in one non-empty line, in a frontmatter block at its top
- RULE-3: The last section of the skill tells the agent the next step for each way the walk can end, pairing what it ended on with a `→` directive
- RULE-4: The skill gives the agent its instructions in at most 185 lines, the whole of `skills/sign/SKILL.md`
- RULE-5: The skill tells the agent the two things that make a sign-off count: a last commit signed with any key whose signature verifies, and a `package_hash` that is the fingerprint of the package committed for its version
- RULE-10: The skill shows the agent the commands the script prints when there is no key to sign with, and tells it to offer to run them and carry on
- RULE-11: The table of commands in `references/purlin_commands.md` tells the agent that `purlin:sign` exists, in a row carrying its purpose
- RULE-13: The skill tells the agent that a sign-off counts whoever wrote it and on whatever branch carries it
- RULE-15: The skill tells the agent that it never pushes
- RULE-16: The skill tells the agent that with no version stated it asks the person for the version and offers to write it to a `VERSION` file
- RULE-20: The skill tells the agent the line the script prints when no version is stated, `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.`
- RULE-23: The skill tells the agent never to narrow a rule or a proof to make an observation disappear
- RULE-25: The skill tells the agent that each stop shows, under each proof that is not `@manual`, the test tied to it, or that no test is
- RULE-29: The skill tells the agent to run `--show` first, to ask the person about each stop in the order printed, to write their answers to `.purlin/runtime/signoff-answers.json`, and then to run `--answers` with that file
- RULE-30: The skill tells the agent that at the gate `passed` nothing is signed, quoting the line the script prints
- RULE-31: The skill tells the agent that the first sign-off of a version writes `signed/<version>` on its commit and that a later one leaves the tag where it is

## Proof

- PROOF-1 (RULE-1): The sign skill opens with a frontmatter block between two `---` lines that carries `name: sign` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-23 (RULE-11): The command reference carries a row in its command table whose first cell is the `purlin:sign` command and whose second cell gives its purpose
- PROOF-3 (RULE-3): The sign skill's last section has a heading naming the `next step` and a table of at least 2 outcomes below its header and divider, and every outcome carries its own `→` directive
- PROOF-4 (RULE-4): The sign skill, counted line by line, is at most 185 lines long
- PROOF-5 (RULE-5): The sign skill's table headed `A sign-off counts when` has exactly two rows: `The last commit that touched the file is signed, with any key, and that signature verifies` and `Its package_hash is the fingerprint of the package committed for its version`, with the field in code
- PROOF-38 (RULE-13): The sign skill says `a sign-off counts whoever wrote it and on whatever branch carries it`
- PROOF-21 (RULE-10): The sign skill's section on the key shows the lines `No key to sign with. These commands set one up:`, `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""`, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`, and says `offer to run them` and `carry on`
- PROOF-42 (RULE-15): The sign skill says `this skill never pushes`
- PROOF-43 (RULE-16): The sign skill's section on the refusals says to `ask the person for the version, offer to write it to a VERSION file`, with the file name in code
- PROOF-48 (RULE-20): The sign skill's section on the refusals, its line breaks read as spaces, quotes `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` word for word
- PROOF-51 (RULE-23): The sign skill, read across its line breaks, carries the sentence `Never narrow a rule or a proof to make an observation disappear.`
- PROOF-54 (RULE-25): The sign skill's section on the stops shows, in code, `    tied to tests/test_login.py::test_valid_credentials_return_200` and `    tied to no test`, and names a proof that is not `@manual`
- PROOF-59 (RULE-29): In the sign skill, the first `scripts/review/sign.py` command carries `--show`, and the section after it says to ask the person about each stop in the order printed
- PROOF-60 (RULE-29): The sign skill names `.purlin/runtime/signoff-answers.json` as where the answers are written, then shows the `scripts/review/sign.py` command carrying `--answers .purlin/runtime/signoff-answers.json`, in that order
- PROOF-61 (RULE-30): The sign skill's gate table has a `passed` row quoting `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`
- PROOF-62 (RULE-31): The sign skill says the first sign-off of the version writes `signed/<version>` on that commit, and quotes `signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push`
