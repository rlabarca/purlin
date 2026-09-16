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
purlin:drift eng                Files touched, tests missing, tags missing, pins, code changed
purlin:drift pm                 Criteria, pm-owned rules, rules engineers added, pins
purlin:drift design             Mocks changed, design rules gone stale
purlin:drift qa                 Signatures stale, how long the review list is, missing cases
purlin:drift --since <N>        The last N commits instead of since the last record
purlin:drift --since <date>     Since a date, YYYY-MM-DD
```

Plain language reaches the same place: "what changed", "what do I need to look at", "anything
stale for QA". With no role, infer one from the files the session has touched and say which
you chose in the first line.

## When to run it

Run it at the start of a session, after an anchor pin or a design export moved, before QA opens
the review list, and before a release. Those are the four moments where the tree has moved
ahead of the specs without anyone being told.

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

A feature whose rules all read `strong` after behavioural code changed still needs a look:
those records were taken against the old behaviour.

## Step 3: the four views

**eng.** What you have to do before you push.

```
drift eng: 14 files since the last record (a1b2c3d)

  src/auth/login.js          RULE-2, RULE-5 behind this change
  src/auth/mfa.js            no spec covers this file
  login RULE-7               no test carries PROOF-7
  billing RULE-3             no risk tag; the gate needs one
  design_tokens (anchor)     pinned 4 commits behind
  export                     code changed: the code moved, the signatures stand
```

**pm.** What happened to what you asked for.

```
drift pm: 3 things to look at

  criterion ACC-14           no rule carries it
  login RULE-3 (origin: pm)  text changed on this branch; signature stale
  login RULE-9               added by an engineer, origin: eng, derived from RULE-3
  design_tokens (anchor)     pinned 4 commits behind its source
```

**design.** What moved under the mocks.

```
drift design: 2 things to look at

  designs/checkout/cart.png  changed; the anchor pin is behind the files
  checkout RULE-4 (origin: design)  signature stale: the mock it names was re-exported
```

**qa.** What is waiting for you.

```
drift qa: review list is 12 rules (3 high, 6 medium, 3 low)

  login RULE-3               signature stale: the rule text changed after it
  billing RULE-2             unsigned
  export RULE-1              needs a person: every proof asserts a success path
```

## Step 4: what drift never does

It never edits a spec, a test or a signature, and it never counts `code changed` as work for a
person: the code moved, the signature stands, and CI clears it on the next run. Say so in one
line rather than listing those rules as findings.

## Step 5: name the next step

| What the view shows | The line to print |
|---------------------|-------------------|
| A file no spec covers | `→ Run: purlin:spec-from-code <path>` |
| A rule behind a changed file | `→ Run: purlin:spec <feature>` |
| A rule with no test | `→ Run: purlin:build <feature>` |
| A risk or origin tag missing under a gate that needs it | `→ Run: purlin:spec <feature>` |
| An anchor pin behind | `→ Run: purlin:anchor sync <name>` |
| Rules waiting on a person | `→ Run: purlin:sign` |
| Only `code changed` | `→ Push; CI clears it.` |
| Nothing at all | `→ Nothing has drifted.` |
