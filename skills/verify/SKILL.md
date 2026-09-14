---
name: verify
description: Run the tests and the breaks, then write the record
---

Run every tagged test, break the code on purpose to measure how much the tests catch, and
write one record of what happened. The record is the evidence a gate reads.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:verify                   Run the tests and the breaks, write the record
purlin:verify <feature> [...]   One feature, or several
purlin:verify --remote          Push the branch, wait for CI, pull the records it wrote
purlin:verify --tag <name>      Pin this state as a validated release
```

Plain language reaches the same place: "verify this", "how strong are the tests", "pin 1.0".

## Step 1: run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --record --commit
```

`--record` runs the tests, then the breaks, then writes
`.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`. `--commit` commits it under
your own git identity, which is what the `tested` gate expects. Drop `--commit` to leave the
record uncommitted and read it yourself. Exit codes: `0` ok, `1` a test failed or the evidence
is missing, `2` the invocation was wrong.

CI runs the same script with `--ci`. You never pass `--ci` by hand.

## Step 2: read what came back

The script prints, per feature: each rule's state, the test strength as an integer percent
(`n/a` when no break engine is installed), and the record path it wrote.

Test strength is the share of the deliberate breaks the tests caught. `min_strength` in
`.purlin/config.json` is the floor the gate holds you to: 50 under `tested`, 70 under
`recorded`, 80 under `approved`, each overridable.

## Step 3: the record's label, and what counts

The last commit that touched a record decides its label, not anything inside the file:

| Label | How it got there | Counts under |
|-------|------------------|--------------|
| ci | Written through the git host's API by the CI identity | `tested`, `recorded`, `approved` |
| developer | A person committed it | `tested` only |
| local | Not committed yet | nothing |

So under `recorded` and `approved` your local run is a preflight: it tells you the push will
pass, and CI writes the record that counts. Under `tested` your own commit is the record.
`references/hard_gates.md` defines the three gates once; do not restate them elsewhere.

## Step 4: `--remote` and `--tag`

`--remote` pushes the current branch and waits for the workflow. On GitHub it watches the run
with `gh run watch`, pulls the records CI committed, and prints the table. On Azure DevOps it
prints the pipeline URL and returns. Use it when a proof is tagged `@env` for an operating
system this host is not.

`--tag <name>` writes an annotated tag `validated/<name>` whose message lists the records it
vouches for. Verify keeps the newest three records per feature per operating system and prunes
the rest; a record a validation tag names is kept for ever.

A forked pull request never gets a record commit. Verify still runs and the comment still
posts; the job says in one line that no record was written.

## Step 5: name the next step

| What the run shows | The line to print |
|--------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` |
| Test strength below `min_strength` | `→ Run: purlin:build <feature>` (add the case the break escaped) |
| A rule needs another operating system | `→ Run: purlin:verify --remote` |
| Every rule Recorded, gate `tested` | `→ Push.` |
| Every rule Recorded, gate `recorded` or `approved` | `→ Run: purlin:review` |
| A rule is Stale | `→ Run: purlin:review <feature>` |
