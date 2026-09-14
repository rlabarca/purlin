---
name: approve
description: Approve a rule, a feature or a batch as a signed commit
---

Attest that a rule, its proof and its test belong together. The attestation is a file, and the
commit that adds it is signed, so who approved what and when is in git history.

Use `purlin:review` when you want the list found for you and walked one brief at a time. Use
this skill when you already know what you are approving.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:approve <feature> RULE-N [RULE-M ...]   One rule, or several
purlin:approve <feature>                       Every reviewable rule of one feature
purlin:approve --batch                         Everything currently approvable
```

Plain language reaches the same place: "approve login rule 3", "sign off on billing".

## Step 1: check you may approve

`approvers` in `.purlin/config.json` is the list of emails that may approve. Read it and
compare your `git config user.email`. If your email is not on it, stop and print:

```
→ <your email> is not on the approver list. Add it by pull request, or ask someone on it.
```

If the gate is `approved` and the list is absent, print
`→ approver list missing: run purlin:init --gate approved` and stop.

## Step 2: read before you sign

For every rule you are about to approve, show the brief:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py" --feature <feature> --rule RULE-N
```

Approving a rule you have not read is the one thing this skill must not help with. Judge it
against `references/review_criteria.md`.

## Step 3: write the approval

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py" <feature> RULE-N [RULE-M ...]
```

The script writes one file per rule under `specs/<category>/<feature>.approvals/` and makes one
signed commit for all of them, with the message
`approve(<feature>): RULE-N ...` from `references/commit_conventions.md`.

Each file binds the hashes of the rule text, the proof text and the test body, plus the risk,
your email, the brief and the record it rests on. Change any of those and the approval goes
Stale, which is the whole point of binding them.

An approval also does not count when you are the author of the commit that last touched the
test. Write the test or approve it, not both.

## Step 4: reach the default branch

Under `tested` and `recorded` the commit can go straight to the branch you are on. Under
`approved` it reaches the default branch by pull request like any other change, and the gate
checks that the approval commit is an ancestor of the protected branch head before counting it.

## Step 5: name the next step

| What you left | The line to print |
|---------------|-------------------|
| Rules still unapproved | `→ Run: purlin:review` |
| Everything approved, gate `approved` | `→ Open the pull request.` |
| Everything approved, gate `recorded` | `→ Run: purlin:status` |
| The commit was not signed | `→ Set up signing: purlin:init --gate approved prints the four commands.` |
