---
name: review
description: Walk the review list one brief at a time
---

Find every rule that needs a human look, order it by risk, and walk it one brief at a time.
At each stop you approve, add a case, or skip. QA runs this; an engineer acting as QA runs the
same thing. You need no arguments and no prior reading: the skill computes the list.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:review                   Walk everything that needs a look
purlin:review <feature>         Narrow to one feature
purlin:review <feature> RULE-N  Narrow to one rule
purlin:review --risk high       Narrow to one risk level
purlin:review --origin design   Narrow to one owner
```

Plain language reaches the same place: "what needs reviewing", "show me the high risk ones",
"review the login rules". A narrowing argument never adds a rule the full walk would skip.

## Step 1: get the list

```
sync_status()
```

`payload.review_list` is the list, already ordered. A rule is on it when any of these holds:

| Reason | What happened |
|--------|---------------|
| Stale | The rule text, the proof text or the test body changed after the approval |
| Reviewed, not approved | A brief exists for the current hashes and nobody has acted on it |
| Recorded, never reviewed | The rule has a counting record and no approval of any age |
| No negative case | Every proof for the rule asserts a success path |

Rules with only `re-verify pending` are **not** on the list: the code changed, the approval
stands, and CI clears it on the next run. Never ask a person to look at one. A rule whose
approval is current is not on the list either, whatever its risk, until that approval goes stale.

## Step 2: show the list before walking it

Print the count by risk, then the first five rows, then start. Do not print the whole list when
it runs past a screen: the point is the walk, not the inventory.

```
Review list: 12 rules across 4 features
  high 3   medium 6   low 3

  login       RULE-3   high     stale: rule text changed
  login       RULE-7   high     no negative case
  billing     RULE-2   high     recorded, never reviewed
```

High risk first, then medium, then low; within a level, oldest record first. Under the
`approved` gate, low risk is auto-approved by CI and appears only when auto-approval declined.

## Step 3: one brief at a time

For each rule in order:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py" --feature <feature> --rule RULE-N
```

The brief holds the rule text, the proof text, the test body, the record that last covered it,
the test strength, and for an `origin: design` rule the pinned mock beside the screenshot the
test captured. Show it, then ask for one of four answers. Judge it against
`references/review_criteria.md`, which is the one place the criteria live.

## Step 4: the four answers

**Approve.** The rule, the proof and the test belong together.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py" <feature> RULE-N
```

That writes the approval file and makes the signed commit. Collect several and pass them
together, or use `--batch` to approve everything you approved during the walk in one commit at
the end. `purlin:approve` is the same script outside the walk.

**Add a case.** The person says in plain language what is missing: "it should also reject an
expired token". Write the new proof line into the spec with the next free proof id, leave the
test for the next `purlin:build`, and move on. Do not write the test here: this skill writes
specs and approvals, never code.

**Hold.** The test does not prove the proof as written, and no new proof line would fix it.
Name the missing case in words and commit it, so CI does not approve the rule in the meantime:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py" <feature> RULE-N --hold "<the missing case>"
```

**Skip.** Move to the next rule and leave the state alone. A skipped rule is on the list again
next time, which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make a finding disappear. That lowers the claim instead of
strengthening the evidence, and on a rule that comes from an anchor it is not yours to change:
`purlin:anchor propose <name>` drafts that change where the rule lives.

## Step 5: close the walk

Print what happened and what is left:

```
Reviewed 12 rules: 8 approved, 1 case added, 3 skipped.
Approvals committed: 8 (signed, 1 commit)
Left on the list: 4
```

Under the `approved` gate the approval commits reach the default branch by pull request like
any other change. Say so in one line and name the branch you are on.

## Step 6: name the next step

| What the walk left | The line to print |
|--------------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| Rules still on the list | `→ Run: purlin:review` |
| Nothing left, gate `approved` | `→ Open the pull request.` |
| Nothing left, gate `recorded` | `→ Run: purlin:status` |
| A rule could not be approved by you | `→ Ask someone on the approver list.` |
