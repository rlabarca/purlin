# Feature: qa_report

> Description: What `tools/QA/purlin-qa-report.md` must say. A QA reader runs this packaged skill
>   against a repository URL from Claude Desktop and gets the review list back, so its text decides
>   how the repository is reached, which numbers the report repeats, and what it is forbidden to
>   claim. The `.skill` archive beside it is a zip of the same markdown, so the rules that cover the
>   text cover what installs.
> Scope: tools/QA/purlin-qa-report.md, tools/QA/purlin-qa-report.skill
> Stack: markdown, packaged Claude skill

## Rules

- RULE-1: The skill opens with a frontmatter block carrying `name: purlin-qa-report` and a `description` that names the words a request reaches it by, among them `review list`, `test strength` and `QA report` [risk: medium] [origin: eng]
- RULE-2: No instruction in the skill puts a credential in a URL, in any form, placeholder or literal, and a private repository is reached with `gh auth login` or a configured credential helper instead [risk: high] [origin: eng]
- RULE-3: The skill reaches a project by running `scripts/report/scan.py --repo <url>` from a checkout of the Purlin repository, and reads three things off the rollup: the gate, how many rules sit in each of the seven states, and how many commits the branch has moved past the newest record [risk: medium] [origin: eng]
- RULE-4: Every entry in the review list closes with exactly one of four verdicts, `ready`, `add a case`, `rewrite the proof` and `needs a human`, and the skill names no fifth [risk: medium] [origin: eng]
- RULE-5: The skill states its three limits: it does not run the project's tests, it cannot sign a commit, and a `@manual` proof has no test because its evidence is an approval a person wrote [risk: high] [origin: eng]
- RULE-6: `tools/QA/purlin-qa-report.skill` holds exactly one entry, `purlin-qa-report/SKILL.md`, whose bytes equal the sibling `.md` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `tools/QA/purlin-qa-report.md`; verify it opens with `---`, that the frontmatter carries `name: purlin-qa-report` and a non-empty `description`, and that the description names `review list`, `test strength` and `QA report`, one assertion per phrase. Deleting `test strength` from the description fails naming it
- PROOF-2 (RULE-2): Read `tools/QA/purlin-qa-report.md` and search it with two patterns, the placeholder form `://<[A-Z_]+>:<[A-Z_]+>@` and the general form `://[^/\s]+:[^/\s]+@`; verify both find zero matches. Then verify the file carries `gh auth login` and the words `credential helper`, so the proof cannot pass on a file that dropped the private-repository path instead of fixing it. Putting `https://<USERNAME>:<TOKEN>@host/repo.git` back fails on the first pattern, naming the line
- PROOF-3 (RULE-3): Read `tools/QA/purlin-qa-report.md`; verify a fenced block carries `scripts/report/scan.py` followed by `--repo` on the same line, and that the file carries `seven states`, the heading text `The gate.` and the phrase `commits the branch has moved past the newest record`, one assertion per literal. Deleting the commits-behind bullet fails naming that phrase
- PROOF-4 (RULE-4): Read `tools/QA/purlin-qa-report.md`; collect the bolded backticked verdict names in the section that lists them and verify the collected list is exactly `ready`, `add a case`, `rewrite the proof`, `needs a human`, in that order. Adding a fifth verdict `looks fine` fails on the comparison, printing both lists
- PROOF-5 (RULE-5): Read `tools/QA/purlin-qa-report.md`; verify the limits section carries `It does not run the project's tests.` and a line carrying both `@manual` and `no test`, and that the file carries the sentence `This skill cannot sign a commit.` Deleting the cannot-sign sentence fails naming it
- PROOF-6 (RULE-6): Open `tools/QA/purlin-qa-report.skill` as a zip; verify its namelist is exactly `['purlin-qa-report/SKILL.md']` and that the bytes of that entry equal the bytes of `tools/QA/purlin-qa-report.md`. Appending one byte to the `.md` without running `dev/pack_tools.sh` fails on the byte comparison
