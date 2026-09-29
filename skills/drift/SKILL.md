---
name: drift
description: Report what changed since your last pull, by role
---

Report what changed since you last brought someone else's changes into your checkout. Three
views, one per role: `pm`, `eng` and `qa`. Each is a list of facts read from git. This skill
writes nothing and judges nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:drift                    The view for your role, inferred from what you touched
purlin:drift pm                 Rules added, changed and removed
purlin:drift eng                Code changed, rules with no test, anchors behind, out of date
purlin:drift qa                 Tests changed, rules to test by hand and to sign
purlin:drift --since <N>        The last N commits instead of since your last pull
purlin:drift --since <date>     Every commit since a date, YYYY-MM-DD
```

Plain language reaches the same place: "what changed", "what did that pull bring in", "anything
waiting for QA". With no role, infer one from the files the session has touched: specs only is
`pm`, test files only is `qa`, anything else is `eng`. Say which you chose before the view.

## When to run it

Run it right after a pull, a merge, a rebase or a checkout of someone else's branch. A merge
that stopped on conflicts counts once you commit it, `commit (merge)` in git's log of HEAD. The
range starts where HEAD stood before that action, so it shows what the action brought in and what
you committed since.

## Step 1: get the data

```
drift(role="eng")
```

The tool returns the range and the view: `lines`, the sentences to print, beside the facts each
was built from. What each line means and which git facts it comes from live in
`references/drift_criteria.md`; do not restate them here and do not invent a line the tool does
not return.

## Step 2: print the view

Print `lines` as they come, one per line, the first naming the range. Do not reword a line, do
not drop one, and do not add a judgement of whether a change is right: drift reports facts.

**pm.** What happened to the rules.

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
3 rules added: login RULE-7, RULE-8; export RULE-2.
2 rules changed: login RULE-3, billing RULE-1.
1 rule removed: cart RULE-4.
```

With no rule moved, the second line reads `No rule was added, changed or removed since your
last pull.`

**eng.** What the code did, and what it leaves behind.

```
Since your last merge, 2 hours ago (9f8e7d6..4f5e6a7, 4 commits).
4 files changed under login's scope: RULE-1, RULE-2, RULE-5 are behind them.
2 changed files are under no spec's scope: src/x.py, src/y.py.
5 rules have no test: login RULE-6; export RULE-1, RULE-2, RULE-3, RULE-4.
anchor proof_common is behind its source (now 3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d). Run: purlin:anchor sync proof_common.
3 features are out of date: login, export, cart.
```

**qa.** What the tests did, and what waits for a person.

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
6 test files changed, covering export, login.
2 rules to test by hand: purlin:sign
3 rules to sign: purlin:sign
1 spec file has changes that are not committed.
```

The two middle lines are the ones `purlin:status` prints under `Left to do`, in the same words;
at the gate `passed` nothing is signed, so only the first of them can show.

## Step 3: what drift never does

It never edits a spec, a test or a signature, never advances an anchor pin, and never counts
`out of date` as work for a person: the code moved, and the next run clears the cell.

## Step 4: name the next step

One line per kind of thing the view showed, in the order below, then stop.

| What the view shows | The line to print |
|---------------------|-------------------|
| A rule added or changed | `→ Run: purlin:build <feature>` |
| A rule removed | `→ Run: purlin:status <feature>` |
| Code changed under a spec's scope | `→ Run: purlin:test <feature>` |
| A changed file under no spec's scope | `→ Run: purlin:spec-from-code <path>` |
| A rule with no test | `→ Run: purlin:build <feature>` |
| An anchor behind its source | `→ Run: purlin:anchor sync <name>` |
| A feature out of date | `→ Run: purlin:test <feature>; the next run clears it.` |
| A test file changed | `→ Run: purlin:test <feature>` |
| A rule to test by hand or to sign | `→ Run: purlin:sign` |
| Spec files not committed | `→ Commit the spec files, then run purlin:drift again.` |
| Only the first line, or only `No rule was added, ...` | `→ Nothing changed that the specs, the tests or the signatures need. Run: purlin:status` |
