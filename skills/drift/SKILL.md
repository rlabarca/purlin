---
name: drift
description: Report what a pull, a merge, a rebase or a checkout changed in the rules, the proofs and the tests, and name a number two branches both took
---

Report what changed since you last brought someone else's changes into your checkout, in one
view: a list of facts read from git. This skill writes nothing and judges nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when the status opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:drift                    What changed since your last pull
purlin:drift --since <N>        The last N commits instead of since your last pull
purlin:drift --since <date>     Every commit since a date, YYYY-MM-DD
```

Plain language reaches the same place: "what changed", "what did that pull bring in".

## When to run it

Run it right after a pull, a merge, a rebase or a checkout of someone else's branch. A merge
that stopped on conflicts counts once you commit it, `commit (merge)` in git's log of HEAD. The
range starts where HEAD stood before that action, so it shows what the action brought in and what
you committed since. Run mid-merge, drift says `MERGE_HEAD: merge in progress.`: its
range stops before the merge.

Drift reads only this checkout: it never fetches, pulls or reaches the host, and it never pulls
an anchor. When it names a number written twice it also says how old this checkout's copy of the
default branch is. If that copy is old, run `git fetch`, then run drift again.

## Step 1: get the data

Call the tool `mcp__plugin_purlin_purlin__drift` with `project_root`, and `since` where the
person gave `--since`. Where the session lists it as a deferred tool, load it with ToolSearch
first. Where the session does not have it, run the script, which prints the view's lines:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_drift.py" --project-root . [--since <N or date>]
```

`project_root` is the top folder of the git checkout you are working in. The tool returns the range, `since`, and the one
view: `lines`, the sentences to print, beside the facts each was built from: the rules added,
changed and removed, the proofs added, changed and moved, the numbers written twice, the test
comments whose proof's wording changed, and the anchors behind their source. What each line means
and which git facts it comes from live in `references/drift_criteria.md`; do not restate them
here and do not invent a line the tool does not return.

## Step 2: print the view

Print `lines` as they come, one per line, the first naming the range. Do not reword a line, do
not drop one, and do not add a judgement of whether a change is right: drift reports facts.

## A number written twice

The line already on the default branch keeps the number; the other line moves to the number
drift names. To renumber it and move the test comments that name it, follow `Renumbering` in
`purlin:spec`: it shows the plan and asks before anything changes.
`<feature>: PROOF-n will name RULE-m.` names a proof that follows a moved rule.

## Step 3: what drift never does

It never edits a spec or a test, never advances an anchor pin, and repeats nothing the status
already prints: what is left to do is `purlin:status`'s to say.

## Step 4: name the next step

One line per kind of thing the view showed, in the order below, then stop.

| What the view shows | The line to print |
|---------------------|-------------------|
| A rule added or changed | `→ Run: purlin:build <feature>` |
| A rule removed | `→ Run: purlin:status <feature>` |
| A proof added, changed or moved | `→ Run: purlin:build <feature>` |
| A number written twice | `→ Run: purlin:spec <feature>` |
| A test comment whose proof's wording changed | `→ Run: purlin:spec <feature>` where its old wording is now another id, else `→ Run: purlin:build <feature>` |
| An anchor behind its source | `→ Run: purlin:anchor sync <name>` |
| How old the copy of the default branch is | `→ Run git fetch, then purlin:drift again.` |
| Only the first line, or only `No rule was added, ...` | `→ Nothing changed that the specs or the tests need. Run: purlin:status` |
