---
name: test
description: Run the tagged tests and print each rule's passed cell
---

Run the tests that carry proof markers, write what they saw into `.purlin/evidence/local/`
and `.purlin/tests.md`, and print the passed cell of every rule. This is level 1 and it takes
seconds: no breaks, no audit, no signature. `purlin:audit` adds the audit.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:test                     Run every feature's tagged tests
purlin:test <feature> [...]     Run one feature, or several
purlin:test --commit            Commit the evidence the run wrote
purlin:test --remote            Let the git host's runner do the run
```

Plain language reaches the same place: "run the tests", "do the login tests pass", "test
everything". The documented syntax is canonical, never required.

## Step 1: run the tests

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --test
```

One feature at a time is `--feature <name>`, repeated for each; `--commit` commits the run.
The run script owns test execution for the whole plugin: `purlin:build` and `purlin:audit`
call it too, so there is one answer to how a test is run. `--remote` hands the run to the git
host's runner instead, on a run branch it creates, waits on and deletes; the runner writes its
own section under `.purlin/evidence/ci/` and always commits it, and the run pulls it back. Use
it for two reasons and no other: a proof is tagged `@env` for an operating system this machine
is not, or `trust` is `remote`, so a signature rests on a run this machine did not make.
It waits through `gh` on GitHub and through `az` with its `azure-devops` extension on Azure
DevOps. A red run is pulled home and exits 1; with no CLI, no run found or the wait over, it
says so and exits 1. The live Azure DevOps behaviour is confirmed by a hand-run check.

Exit codes: `0` the tests ran and the level is met, `1` a test failed or it is not, `2` the invocation was wrong.

## Step 2: the evidence, written and committed when asked

The run writes this operating system's section of `.purlin/evidence/local/<feature>.json`
(the commit, the time, the fingerprint of the spec, code and tests it saw, each rule's word,
each proof's result and test) and `.purlin/tests.md`, one table for the whole project:
`Feature`, `Rules`, `Passed`, `Failing`, `No test`, `Last run`. It prints `Evidence written to
.purlin/evidence/local/<feature>.json.` and commits nothing. With `--commit` it commits both
under your own git identity, with the subject `purlin: evidence at <sha7>`, and prints
`Evidence committed.`, or `Evidence unchanged.` when nothing new was seen. It never pushes. A
`--feature` run writes what it ran and leaves the rest of the table as it was. The folder is
the source: yours are `local`, and a remote run's, under `.purlin/evidence/ci/`, are `ci`.
`references/formats/evidence_format.md` is the contract, and its `> Format-Version:` line says
which version this release ships.

## Step 3: read the table

The run prints `Ran <framework> on <n> feature(s).`, then the status table
`purlin:status` builds. The `Tests` column counts the words a passed cell can read:

| Word | What it means |
|------|---------------|
| `passed` | A test tagged with the rule's proof ran here and passed |
| `failed` | A tagged test ran and failed; the script names the test and the assertion |
| `no test` | No test carries the proof's marker, or, with the reason `no proof written`, no proof line names the rule |
| `not run` | A test carries the marker and no counting run reached it |
| `out of date` | The spec, the code or the tests changed since the run; the reason names which |

A rule no proof line names reads `no test` with the reason `no proof written`. Loud failures
come first: `Evidence is missing: <what>.` means an arm ran and wrote no proof entry,
or a marker in the tree produced none. Read those before the table.

## Step 4: what the gate changes

This is the pattern every Purlin skill follows. Under `passed` the whole project is this one
cell: no strength, no level, no queue, no signature. Under `strong` the strong cell and
the test strength appear beside it; under `signed` the signed cell appears too. Evidence from either source counts at every gate; what `trust: remote` changes is that
`purlin:sign` asks for a `ci` run first. Read the gate from `.purlin/config.json` and print
only what exists; `references/hard_gates.md` defines the three gates once.

## Step 5: operating systems

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating
system. On a host that does not match, the run prints `<feature> PROOF-N needs <os>; this
machine is <os>. A remote runner runs it: purlin:init adds one.` An untagged proof runs
anywhere, and those three tags are the whole vocabulary.

Each operating system a counting run covered is one **platform** in the passed cell, with its
own word, and the cell merges the two sources per platform. A rule that passes on one and fails
on another reads `partial`, which is not met. `--remote` pulls the runner's results home at
every gate, so a proof tagged for a system this machine is not reads `passed` with that
platform beside it rather than `not run`.

## Step 6: the gate line

The last line is `gate passed: <n> of <rules>` or `gate not met: <n> of <rules>`, and the run
exits 1 on the second. At `passed` that line is the check: nobody runs a script.
`scripts/ci/gate_check.py --check` is the CI step, not yours.

## Step 7: name the next step

End with one line, computed from the table:

| What the table shows | The line to print |
|----------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` (fix the code or the test) |
| A rule reads `partial` | `→ Run: purlin:build <feature>` (the cell names the platform that failed) |
| A rule reads `no test` | `→ Run: purlin:build <feature>` |
| A rule reads `no test` with the reason `no proof written` | `→ Run: purlin:spec <feature>` |
| Every rule reads `passed`, gate `passed` | `→ Push.` |
| Every rule reads `passed`, gate `strong` or `signed` | `→ Run: purlin:audit` |
| Only `needs <os>` proofs remain | `→ Run: purlin:test --remote` |

Diagnose a failure first: `references/spec_quality_guide.md` says which of the rule, the proof
and the code is usually at fault.
