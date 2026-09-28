# Feature: skill_export

> Description: What `skills/export/SKILL.md` must say. Export writes the evidence package for a
>   version, says where the version stands, commits only when asked, checks a package against
>   its fingerprint, and says that Purlin makes no claim of compliance.
> Scope: skills/export/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:export`
- RULE-2: The skill runs `scripts/export/package.py` and names each form of the command: bare, `--release <name>`, `--commit` and `--check <file>`
- RULE-3: The skill says that Purlin makes no claim that the software is compliant and that the package is evidence for review in a regulated document and sign-off system
- RULE-4: The skill names the three states, `work in progress`, `gate <gate> met` and `signed`, and says that only `purlin:sign` writes a package whose state is `signed`
- RULE-5: The last section of `skills/export/SKILL.md` names the next step, giving a `→` directive for each outcome
- RULE-6: The whole of `skills/export/SKILL.md` is at most 90 lines [level: passed]

## Proof

- PROOF-1 (RULE-1): Read `skills/export/SKILL.md`; verify the file opens with `---`, that the frontmatter carries `name: export` and a `description:` whose value is one non-empty line, and that `references/purlin_commands.md` contains the literal `purlin:export`. Deleting the `name:` line fails naming the file
- PROOF-2 (RULE-2): Read `skills/export/SKILL.md` with its line wrapping collapsed; verify it carries `scripts/export/package.py`, `purlin:export --release <name>`, `purlin:export --commit` and `purlin:export --check <file>`, one assertion per literal. Deleting the `--check` line fails naming it
- PROOF-3 (RULE-3): Read `skills/export/SKILL.md` with its line wrapping collapsed; verify it carries `Purlin makes no claim that the software is compliant.` and `evidence for review in a regulated document and sign-off system`. Deleting the first sentence fails naming it
- PROOF-4 (RULE-4): Read `skills/export/SKILL.md` with its line wrapping collapsed; verify it carries `` `work in progress` ``, `` `gate <gate> met` ``, `` `signed` `` and `Only purlin:sign writes a package whose state is` with the command in backticks. Deleting the last sentence fails naming it
- PROOF-5 (RULE-5): Read `skills/export/SKILL.md` and split it on its `## ` headings; verify the last heading matches `next step` case-insensitively, that the text under it names at least two outcomes as table rows, and that at least one of its lines carries `→`. Deleting the closing section fails naming the heading it found instead
- PROOF-6 (RULE-6): Read `skills/export/SKILL.md` and count its lines; verify the count is at most 90. Appending prose until the file passes 90 lines fails, and the failure reports the count it found beside the ceiling
