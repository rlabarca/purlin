# Feature: skill_anchor

> Description: What `skills/anchor/SKILL.md` must say. An anchor is a spec for something shared
>   across features, and the skill is what creates one, pulls one from another
>   repository and keeps its pin current.
> Scope: skills/anchor/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:anchor` [bar: strong]
- RULE-2: The skill runs `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` for `add` and `sync`, and names `sync --check` as the read-only form `purlin:drift` runs as well [bar: strong]
- RULE-3: The last section of `skills/anchor/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome [bar: strong]
- RULE-4: The whole of `skills/anchor/SKILL.md` is at most 160 lines [bar: passed]
- RULE-5: A pin is a commit and never a branch, and a pinned rule is never edited in the consuming project: the skill sends a change to a pull request against the source repository or to a separate local anchor that requires the pinned one [bar: strong]

## Proof

- PROOF-1 (RULE-1): Read `skills/anchor/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: anchor` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:anchor`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/anchor/SKILL.md`; verify the literal `"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"` appears at least twice, that `add` and `sync` each share a line with it, and that the file carries `--check` and names `purlin:drift`. Removing the sync fence fails, reporting one occurrence where two were expected
- PROOF-3 (RULE-3): Read `skills/anchor/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` or `when you are done` case-insensitively, that the text under it names at least two outcomes as list items or table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-4 (RULE-4): Read `skills/anchor/SKILL.md` and count its lines; verify the count is at most 160. Appending prose until the file passes 160 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): Read `skills/anchor/SKILL.md` with its line wrapping collapsed; verify it carries `A pin is always a commit, never a branch.`, `Never edit a pinned rule in place.`, the clause `a pull request against the source repository` and the local anchor line `> Requires: <the pinned one>`, one assertion per literal. Deleting the never-edit sentence fails naming it
