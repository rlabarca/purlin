# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must say. An anchor is a spec for something shared
>   across features, and the skill is what creates one, pulls one from another
>   repository and keeps its pin current.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:anchor`
- RULE-2: The skill runs `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` for `add` and `sync`, and names `sync --check` as the read-only form `purlin:drift` runs as well
- RULE-3: The last section of `skills/anchor/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome
- RULE-4: The whole of `skills/anchor/SKILL.md` is at most 160 lines [level: passed]
- RULE-5: A pin is a commit and never a branch, and a pinned rule is never edited in the consuming project: the skill sends a change to a pull request against the source repository or to a separate local anchor that requires the pinned one

## Proof

- PROOF-1 (RULE-1): The anchor skill opens with a frontmatter block set between two `---` lines; the block reads `name: anchor` and carries a `description:` whose text sits on that same line and is neither empty nor a lone `>` that folds it onto the lines below, and Purlin's command reference names `purlin:anchor`. A skill whose `name:` line is deleted fails, naming the skill's file and the expected name `anchor`; a `description:` left empty fails as carrying no one-line description
- PROOF-2 (RULE-2): The anchor skill gives the script `"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"`, quoted exactly so, at least twice: once on the same line as `add` and once on the same line as `sync`; the skill also names the flag `--check` and the command `purlin:drift`. With the `sync` command removed the skill fails, reporting the script named 1 time where at least 2 were expected and no line carrying the script together with `sync`
- PROOF-3 (RULE-3): The anchor skill's last section is headed with the words `next step` or `when you are done`, in any case; under that heading at least two outcomes stand as list items or table rows, and at least one line gives a `→` directive. With that section deleted the skill fails, naming `Changing a pinned rule`, the heading of the section that is then last; a closing section that lists one outcome fails with the count 1 beside the 2 expected
- PROOF-4 (RULE-4): Read `skills/anchor/SKILL.md` and count its lines; verify the count is at most 160. Appending prose until the file passes 160 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): The anchor skill carries the sentences `A pin is always a commit, never a branch.` and `Never edit a pinned rule in place.`, the words `a pull request against the source repository` and the line `> Requires: <the pinned one>`, each found even where the skill breaks it across two lines. With the sentence `Never edit a pinned rule in place.` deleted the skill fails, naming that sentence as missing
