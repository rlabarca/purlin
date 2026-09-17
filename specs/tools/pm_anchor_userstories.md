# Feature: pm_anchor_userstories

> Description: What `tools/PM/purlin-anchor-userstories.md` must say. A product manager runs this
>   packaged skill in Claude Desktop, with no checkout and no git, so its text is the only thing
>   standing between a requirement and a spec the project's tooling can read. The `.skill` archive
>   beside it is a zip of the same markdown, so the rules that cover the text cover what installs.
> Scope: tools/PM/purlin-anchor-userstories.md, tools/PM/purlin-anchor-userstories.skill
> Stack: markdown, packaged Claude skill

## Rules

- RULE-1: The skill opens with a frontmatter block carrying `name: purlin-anchor-userstories` and a `description` that names the words a request reaches it by, among them `spec`, `anchor` and `acceptance criteria` [risk: medium] [origin: eng]
- RULE-2: Every change the skill makes reaches the repository as a pull request and never as a commit to the default branch, and the only paths it writes are `specs/<category>/<name>.md`, `specs/_anchors/<name>.md` and `designs/<feature>/` [risk: high] [origin: eng]
- RULE-3: A rule tagged `[origin: eng]` or `[origin: qa]` is never edited and never deleted, whoever asks: the proposed replacement goes in a pull request comment naming the rule id [risk: high] [origin: eng]
- RULE-4: The skill names the three rule tags `[risk: ...]`, `[origin: ...]` and `[criterion: ...]` with their values, says risk and origin are both required under the `signed` gate, and names the four proof tiers and the three `@env` values [risk: medium] [origin: eng]
- RULE-5: `tools/PM/purlin-anchor-userstories.skill` holds exactly one entry, `purlin-anchor-userstories/SKILL.md`, whose bytes equal the sibling `.md` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `tools/PM/purlin-anchor-userstories.md`; verify it opens with `---`, that the frontmatter carries `name: purlin-anchor-userstories` and a non-empty `description`, and that the description names `spec`, `anchor` and `acceptance criteria`, one assertion per word. Deleting `acceptance criteria` from the description fails naming it
- PROOF-2 (RULE-2): Read `tools/PM/purlin-anchor-userstories.md`; verify it carries the sentence `Never commit to the default branch.`, that `specs/<category>/<name>.md`, `specs/_anchors/<name>.md` and `designs/<feature>/` each appear, and that the sentence `Create no other folder.` appears, one assertion per literal so the failure names the missing one. Deleting `Create no other folder.` fails naming it
- PROOF-3 (RULE-3): Read `tools/PM/purlin-anchor-userstories.md`; verify the owner-comment section names `[origin: eng]` and `[origin: qa]`, carries `Never edit its text` and `never delete it`, and shows a pull request comment carrying a `RULE-` id. Deleting the section fails naming `[origin: qa]`
- PROOF-4 (RULE-4): Read `tools/PM/purlin-anchor-userstories.md`; verify `[risk:`, `[origin:` and `[criterion:` each appear, that `[risk: high]`, `[risk: medium]` and `[risk: low]` each appear, that the file carries the sentence "Under the `signed` gate risk and origin are both required", that `@integration`, `@e2e` and `@manual` each appear, and that `@env(windows)`, `@env(macos)` and `@env(linux)` each appear. Dropping the `@env` sentence fails naming `@env(macos)`
- PROOF-5 (RULE-5): Open `tools/PM/purlin-anchor-userstories.skill` as a zip; verify its namelist is exactly `['purlin-anchor-userstories/SKILL.md']` and that the bytes of that entry equal the bytes of `tools/PM/purlin-anchor-userstories.md`. Appending one byte to the `.md` without running `dev/pack_tools.sh` fails on the byte comparison
