---
name: purlin-qa-report
description: >
  Read a Purlin project from a git repository URL and produce the QA triage report: the review
  list ordered by risk, what each rule needs, and what to do about it. Use when the user gives
  a repository URL and asks what needs reviewing, what needs a test, what is stale, whether a
  release is ready, or how a project's rules stand. Also opens pull requests carrying proof
  edits and approval files. Mentions of "Purlin", "QA report", "review list", "test strength",
  "what needs approving" or "verification status" all reach this skill.
---

# Purlin QA report

This skill reads a repository's specs and records, prints the review list, and turns what QA
decides into a pull request. QA works the review list, never the whole rule list: the list
holds only the rules that are stale or that need a person to look, ordered by risk.

## Step 1: run the scan

`scan.py` fetches `specs/` and `.purlin/records/` alone, reads them, and prints the rollup. It
lives in the Purlin repository, so fetch that first, then point it at the project.

```bash
git clone --depth 1 --filter=blob:none --sparse <PURLIN_REPO_URL> /tmp/purlin
git -C /tmp/purlin sparse-checkout set scripts
python3 /tmp/purlin/scripts/report/scan.py --repo <PROJECT_URL> [--ref <branch-or-tag>]
```

`PURLIN_REPO_URL` is the Purlin repository. Ask for it once and offer to remember it; the
project URL is asked every session. With no `--ref`, the project's default branch is read.

Both clones are read-only and need read access. If either fails, read the error before
retrying:

| Error | Cause | What to do |
|---|---|---|
| `could not read Username` | HTTPS with no stored credential | `gh auth login`, or set a credential helper |
| `Permission denied (publickey)` | No SSH key on this machine | Ask the user to add `~/.ssh/id_ed25519.pub` to their git host |
| `Repository not found` | Wrong URL, or no read access | Confirm the URL, then confirm access |

Never put a token in a URL: it is written into shell history, into the clone's config file and
into the process table. Hand it to `gh auth login` or to a credential helper instead.

## Step 2: read the rollup

`scan.py` prints the project name, its gate, the count of features and rules, how many rules
sit in each of the seven states, and how many commits the branch has moved past the newest
record. After that it prints the review list, one line per rule: the risk, the feature and rule
id, the state, and why the rule is on the list. Read three things off the rollup:

- **Stale rules.** The rule, its proof or its test changed after it was approved. A person has
  to look at every one.
- **Commits behind the latest record.** A large number means the evidence describes older code
  than the branch holds. Say the number; do not soften it.
- **The gate.** `tested`, `recorded` or `approved`. It decides what counts as evidence, and the
  next two sections change with it.

## Step 3: print the review list

Work from the review list `scan.py` printed; it is already ordered by risk, `high` first, then
`medium`, then `low`, and inside each Stale first. Keep that order. For every entry give the feature, the rule id, the risk, why it is on the list,
and one of the four verdicts a review ends with:

- **`ready`**: every check is clear and the test proves what the proof text claims.
- **`add a case`**: the test is right as far as it goes and a case is missing, usually the
  rejection the rule implies. The proof text stays.
- **`rewrite the proof`**: no test written against this proof text could prove the rule.
- **`needs a human`**: the checks disagree, the proof is `@manual`, or the evidence is a
  screenshot a model should not settle. Nothing is approved from this verdict.

Print it as plain text in the chat. The full board, with every rule and its history, is the
dashboard CI publishes as a build artifact on each pull request; link to that rather than
rebuilding it here.

Close the report with the counts: how many rules are on the list, how many are `high`, how many
are stale, and the project's test strength as an integer percent, or `n/a` when no engine ran.
Test strength is the share of the deliberate breaks made to the code that the tests caught. It
says the tests noticed when the behaviour changed. It does not say the tests prove the right
rule. Read it beside the verdicts, never instead of them.

## Step 4: open a pull request for proof edits

When a verdict is `add a case` or `rewrite the proof`, write the change into the spec and open
a pull request. Through the connector, or in a clone of the project:

1. Branch `review/<feature>`.
2. Edit only the `## Proof` lines, and only for the rules on the review list. Leave rule text
   alone: changing a rule is the product manager's call, and a proposal belongs in a pull
   request comment.
3. Commit as `spec(<feature>): <what changed>`.
4. Open the pull request, listing each rule id and its verdict in the body.

A new or changed proof line is a request to the engineer. The next `purlin:build` writes the
test for it.

## Step 5: approvals, and what counts

An approval is one file, `specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<slug>.json`,
binding the hashes of the rule text, the proof text and the test body. If any of the three
change, it no longer counts.

| Gate | What CI requires before a change can merge | Approvals |
|---|---|---|
| `tested` | Every rule has a passing tagged test | None |
| `recorded` | Every rule has a CI-written record at this commit, at or above `min_strength` | Advisory |
| `approved` | `recorded`, plus a current approval on every high and medium rule | Required |

Under `approved`, an approval counts only when the commit that added the file is signed, its
author's email is on the approver list in `.purlin/config.json` as of that commit, and that
author is not the author of the commit that last touched the test. CI auto-approves low-risk
rules; nobody signs those.

This skill cannot sign a commit. It can write the approval files and open the pull request, and
you should say plainly that the approver has to run `purlin:approve` in a checkout, or sign the
merge themselves, for the approval to count under `approved`. Under `recorded` the pull request
is enough.

## Limits, stated plainly

- This skill reads specs and records. It does not run the project's tests.
- The rollup is only as current as the newest record. Say how many commits the branch has moved
  past it every time.
- A `@manual` proof has no test. Its evidence is an approval carrying a one-line note, always
  written by a person.
