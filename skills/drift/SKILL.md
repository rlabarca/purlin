---
name: drift
description: Report what changed since the last record, by role
---

Report what changed in the tree that the specs, the tests and the signatures have not caught
up with. Four views, one per role: each shows the same underlying change from the angle of the
person who has to act on it. This skill writes nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:drift                    The view for your role, inferred from what you touched
purlin:drift eng                Files touched, tests missing, pins, out of date
purlin:drift pm                 Anchor pins behind their source
purlin:drift qa                 Signatures stale, how long the queue is, rules needing a person
purlin:drift --since <N>        The last N commits instead of since the last record
purlin:drift --since <date>     Since a date, YYYY-MM-DD
```

Plain language reaches the same place: "what changed", "what do I need to look at", "anything
stale for QA". With no role, infer one from the files the session has touched and say which
you chose in the first line.

## When to run it

Run it at the start of a session, after an anchor pin moved, before QA
walks the queue, and before a release. Those are the four moments where the tree has
moved ahead of the specs without anyone being told.

Under the gate `passed` the `qa` view has nothing to report: there is no strength, no review
list and no signature. Say the gate is `passed`, name what `purlin:init --gate strong` would
add, and stop, exactly as `purlin:sign` does.

## Step 1: get the data

```
drift(role="eng")
```

The tool classifies each changed file deterministically and returns the rules behind it. The
classification rules live in `references/drift_criteria.md`; do not restate them here and do
not invent a category the tool does not return.

## Step 2: read the diff before you report

The tool says which files changed and which rules they sit behind. It does not say whether the
change matters. Read the `git diff` and decide:

| Reading | What it means |
|---------|---------------|
| Behavioural | The software does something different: a rule may be wrong or missing |
| Structural | A rename, a move, a refactor: the rules still hold |
| Operational | How it runs changed: CI, environment, container |
| Documentation | Prose only |
| Trivial | Whitespace, formatting, generated files |

A feature whose rules all read `strong` after a behavioural change to the code still needs a
look: that audit was taken against the old behaviour.

## Step 3: the four views

**eng.** What you have to do before you push.

```
drift eng: 14 files since the last record (a1b2c3d)

  src/auth/login.js          RULE-2, RULE-5 behind this change
  src/auth/mfa.js            no spec covers this file
  login RULE-7               no test carries PROOF-7
  design_tokens (anchor)     pinned 4 commits behind
  export                     out of date: the code moved, the signatures stand
```

**pm.** What happened to what you asked for.

```
drift pm: 1 thing to look at

  design_tokens (anchor)     pinned 4 commits behind its source
```

**qa.** What is waiting for you.

```
drift qa: the queue is 12 rules

  login RULE-3               signature stale: the rule text changed after it
  billing RULE-2             unsettled: the AI audit could not settle
  export RULE-1              not audited: no audit has run on this code
```

## Step 4: what drift never does

It never edits a spec, a test or a signature, and it never counts `out of date` as work for a
person: the code moved, the signature stands, and the next run clears the cell. Say so in one
line rather than listing those rules one by one.

## Step 5: name the next step

| What the view shows | The line to print |
|---------------------|-------------------|
| A file no spec covers | `→ Run: purlin:spec-from-code <path>` |
| A rule behind a changed file | `→ Run: purlin:spec <feature>` |
| A rule with no test | `→ Run: purlin:build <feature>` |
| An anchor pin behind | `→ Run: purlin:anchor sync <name>` |
| Rules waiting on a person | `→ Run: purlin:sign` |
| Only `out of date` | `→ Next: run purlin:test; the next run clears it.` |
| Nothing at all | `→ Nothing has drifted.` |
