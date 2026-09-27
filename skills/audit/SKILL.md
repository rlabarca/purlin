---
name: audit
description: Run the tests and the breaks, then write the record
---

Run every tagged test, break the code on purpose to measure how much the tests catch, run the
free checks and the model review, print what they found, and write the record. An audit is
level 2: it measures how good the tests are. Its record counts at `strong`, whoever ran it; at
`signed` only the run CI made on the protected branch counts.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run the tests and the breaks, and write the record
purlin:audit <feature> [...]    One feature, or several
```

Plain language reaches the same place: "audit this", "how strong are the tests", "pin 1.0".

There is no `--remote` here: a remote runner runs the tests, so that flag is
`purlin:test --remote`.

## Step 1: run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --audit
```

`--audit` runs the tests, then the breaks where the gate asks for them, then the free checks
and the model review. It writes one record per feature under
`.purlin/records/local/<feature>/` with its briefs under `.purlin/briefs/local/<feature>/`,
prints each feature's test strength beside the minimum and each rule's findings and
observations, and commits the record and the briefs under your own identity with the subject
`purlin: record for <sha7>`. It ends with `gate strong: <n> of <rules>` or
`gate not met: <n> of <rules>`, and it never pushes. Exit codes: `0` every rule met the gate, `1` a test failed, evidence is missing
or the gate is not met, `2` the command line was wrong.

The run script owns test execution for the whole plugin: `purlin:test` and `purlin:build` call
it too, so there is one answer to how a test is run. CI runs the same script in an arm of its
own, which writes the same files under `.purlin/records/ci/` and `.purlin/briefs/ci/`. That arm
belongs to the workflow and you never run it by hand. A CI run commits on the protected branch
and on a run branch only; `references/hard_gates.md` says where CI runs and what each run
writes.

## Step 2: read what came back

Test strength is the share of the deliberate breaks the tests caught. `min_strength` in
`.purlin/config.json` is the floor the gate holds you to: 70 under `strong`, 80 under `signed`,
each overridable. A finding is what a free check saw in the proof text or the test body; an
observation is what the model review saw. Both are build work: they name what the test does
not yet observe.

## Step 3: what the gate changes

| Gate | What this run does |
|------|--------------------|
| `passed` | Runs the tests only. No breaks, no bar, no brief; the run says `Strength n/a: the gate is passed.` |
| `strong` | Runs the breaks too, and prints the strength beside the minimum |
| `signed` | The same as `strong`. A record either source wrote counts here too; a project that wants CI's word before a signature sets `trust: remote`, which `purlin:sign` reads |

Raising the gate to `strong` turns the breaks on, locally and in CI.

## Step 4: the folder is the source

A record's source is the folder it sits in, and the file's own `source` field says the same
word. A file where the two disagree is ignored, with one warning naming it.

| Source | The folder | Counts under |
|--------|------------|--------------|
| ci | `.purlin/records/ci/<feature>/`, written by the CI identity through the git host's API | `passed`, `strong`, `signed` |
| local | `.purlin/records/local/<feature>/`, written by this command on anyone's machine | `passed`, `strong`, `signed` |

Under `passed` no record is written at all: the evidence there is the test results
`purlin:test` commits, under `.purlin/tests/`. `references/hard_gates.md` defines the three
gates once; do not restate them elsewhere.

## Step 5: retention

A feature keeps the newest three records per operating system per source, and a run prunes the
rest as it writes.

## Step 6: name the next step

| What the run shows | The line to print |
|--------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` |
| Test strength below `min_strength` | `→ Run: purlin:build <feature>` (add the case the break escaped) |
| A finding or an observation on a rule | `→ Run: purlin:build <feature>` (write the case it names) |
| A rule needs another operating system | `→ Run: purlin:test --remote` |
| Every rule met the gate `passed` | `→ Next: run git push.` |
| A `ci` record is missing under `signed` | `→ Next: run git push; the run on the protected branch writes the record a signature attaches to.` |
| A rule's tests pass on one operating system and not another | `→ Run: purlin:build <feature>` (the passed cell reads `partial` and names the platform) |
| A rule reads `manual test`, `unsettled` or `held`, or is signable | `→ Run: purlin:sign` |
