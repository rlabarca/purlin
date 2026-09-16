---
name: audit
description: Run the tests and the breaks, then write the record
---

Run every tagged test, break the code on purpose to measure how much the tests catch, and
write one record of what happened. An audit is level 2: it proves a rule strong or weak, and
the record is the evidence a gate reads.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run the tests and the breaks, write the record
purlin:audit <feature> [...]    One feature, or several
purlin:audit --remote           Push the branch, wait for CI, pull the records it wrote
purlin:audit --tag <name>       Pin this state as record/<name>
```

Plain language reaches the same place: "audit this", "how strong are the tests", "pin 1.0".

## Step 1: run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --record --commit
```

`--record` runs the tests, then the breaks, then writes
`.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`. `--commit` commits it under
your own git identity, which is what the `passed` gate expects. Drop `--commit` to leave the
record uncommitted and read it yourself. Exit codes: `0` ok, `1` a test failed or the evidence
is missing, `2` the invocation was wrong.

The run script owns test execution for the whole plugin: `purlin:test` and `purlin:build` call
it too, so there is one answer to how a test is run. CI runs the same script with `--ci`, which
also writes the briefs under `.purlin/briefs/<feature>/`. You never pass `--ci` by hand.

## Step 2: read what came back

The script prints, per feature: each rule's cells, the test strength as an integer percent,
and the record path it wrote.

Test strength is the share of the deliberate breaks the tests caught. `min_strength` in
`.purlin/config.json` is the floor the gate holds you to: 70 under `strong`, 80 under `signed`,
each overridable.

## Step 3: what the gate changes

| Gate | What this run does |
|------|--------------------|
| `passed` | Runs the tests only. No breaks, no risk, no brief, and the record carries test strength `n/a` |
| `strong` | Runs the breaks too. Your local run is a preview: it says in one line that it does not count and that CI writes the record that does |
| `signed` | The same as `strong`, and the record is what the review list and the signatures rest on |

Raising the gate to `strong` turns the breaks on, locally and in CI.

## Step 4: the record's source, and what counts

The last commit that touched a record decides its source, not anything inside the file:

| Source | How it got there | Counts under |
|--------|------------------|--------------|
| ci | Written through the git host's API by the CI identity | `passed`, `strong`, `signed` |
| developer | A person committed it | `passed` only |
| local | Not committed yet | `passed` only, and only in this checkout |

Under `strong` and `signed` only a `ci` record counts, so your local run tells you the push
will pass and CI writes the record that the gate reads. Under `passed` your own commit is the
record. `references/hard_gates.md` defines the three gates once; do not restate them elsewhere.

## Step 5: `--remote` and `--tag`

`--remote` pushes the current branch and waits for the workflow. On GitHub it watches the run
with `gh run watch`, pulls the records CI committed, and prints the table. On Azure DevOps it
prints the pipeline URL and returns. Use it when a proof is tagged `@env` for an operating
system this host is not.

`--tag <name>` writes an annotated tag `record/<name>` whose message lists the records it
vouches for. This skill keeps the newest three records per feature per operating system and
prunes the rest; a record a tag names is kept for ever.

A forked pull request never gets a record commit. The run still happens and the comment still
posts; the job says in one line that no record was written.

## Step 6: name the next step

| What the run shows | The line to print |
|--------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` |
| Test strength below `min_strength` | `→ Run: purlin:build <feature>` (add the case the break escaped) |
| A rule needs another operating system | `→ Run: purlin:audit --remote` |
| Every rule met the gate `passed` | `→ Push.` |
| A `ci` record is missing under `strong` or `signed` | `→ Push; CI writes the record.` |
| A rule needs a person, is unsigned or is stale | `→ Run: purlin:sign` |
