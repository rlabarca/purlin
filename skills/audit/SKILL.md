---
name: audit
description: Run the tests and the breaks, then report how good the tests are
---

Run every tagged test, break the code on purpose to measure how much the tests catch, run the
free checks and the model review, and print what they found. An audit is level 2: it measures
how good the tests are. It writes no record, because the record is CI's.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run the tests and the breaks, and report
purlin:audit <feature> [...]    One feature, or several
purlin:audit --tag <name>       Pin the records in the tree as record/<name>
```

Plain language reaches the same place: "audit this", "how strong are the tests", "pin 1.0".

There is no `--remote` here: a remote runner runs the tests, so that flag is
`purlin:test --remote`. Nothing on your machine writes a record.

## Step 1: run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --audit
```

`--audit` runs the tests, then the breaks where the gate asks for them, then the free checks
and the model review. It prints each feature's test strength beside the minimum, then each
rule's findings and observations, and ends with `This audit counts only when CI runs it.` It
writes nothing to the tree. Exit codes: `0` everything asked for happened, `1` a test failed
or evidence is missing, `2` the command line was wrong.

The run script owns test execution for the whole plugin: `purlin:test` and `purlin:build` call
it too, so there is one answer to how a test is run. CI runs the same script in an arm of its
own, which runs the tests, then the audit at `strong` and above, then writes the record and the
briefs under `.purlin/briefs/<feature>/`. That arm belongs to the workflow and you never run it
by hand. A CI run commits on the protected branch and on a run branch only;
`references/hard_gates.md` says where CI runs and what each run writes.

## Step 2: read what came back

Test strength is the share of the deliberate breaks the tests caught. `min_strength` in
`.purlin/config.json` is the floor the gate holds you to: 70 under `strong`, 80 under `signed`,
each overridable. A finding is what a free check saw in the proof text or the test body; an
observation is what the model review saw. Both are build work: they name what the test does
not yet observe.

## Step 3: what the gate changes

| Gate | What this run does |
|------|--------------------|
| `passed` | Runs the tests only. No breaks, no risk, no brief; the run says `Strength n/a: the gate is passed.` |
| `strong` | Runs the breaks too, and prints the strength beside the minimum |
| `signed` | The same as `strong`, and CI's record is what the review list and the signatures rest on |

Raising the gate to `strong` turns the breaks on, locally and in CI.

## Step 4: the record is CI's

Nothing here writes a record. The CI job runs the tagged tests, then this audit at `strong`
and above, and commits one record per feature on the protected branch and on a run branch. The
last commit that touched a record decides its source, not anything inside the file:

| Source | How it got there | Counts under |
|--------|------------------|--------------|
| ci | Written through the git host's API by the CI identity | `passed`, `strong`, `signed` |
| local | Anything else: not committed, or committed by somebody other than the git host | `passed` only |

Under `passed` the evidence is the test results `purlin:test` commits, under `.purlin/tests/`.
`references/hard_gates.md` defines the three gates once; do not restate them elsewhere.

## Step 5: `--tag`

`--tag <name>` writes an annotated tag `record/<name>` over the records already in the tree,
whose message lists the records it vouches for, and prints `Record tag written: record/<name>`.
With no record in the tree it says so and writes nothing. A feature keeps the newest three
records per operating system and the rest are pruned; a record a tag names is kept for ever.

## Step 6: name the next step

| What the run shows | The line to print |
|--------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` |
| Test strength below `min_strength` | `→ Run: purlin:build <feature>` (add the case the break escaped) |
| A finding or an observation on a rule | `→ Run: purlin:build <feature>` (write the case it names) |
| A rule needs another operating system | `→ Run: purlin:test --remote` |
| Every rule met the gate `passed` | `→ Next: run git push.` |
| A `ci` record is missing under `strong` or `signed` | `→ Next: run git push; the run on the protected branch writes the record.` |
| A rule reads `manual test`, `manual audit` or `held`, or is unsigned or stale | `→ Run: purlin:sign` |
