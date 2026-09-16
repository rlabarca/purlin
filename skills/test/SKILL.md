---
name: test
description: Run the tagged tests and print each rule's passed cell
---

Run the tests that carry proof markers, write the proof files into `.purlin/runtime/proofs/`,
and print the passed cell of every rule. This is level 1 and it takes seconds: no breaks, no
record, no signature.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:test                     Run every feature's tagged tests, unit tier
purlin:test <feature> [...]     Run one feature, or several
purlin:test --all               Run every tier, not just unit
```

Plain language reaches the same place: "run the tests", "do the login tests pass", "test
everything". The documented syntax is canonical, never required.

## Step 1: run the tests

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --all --quick
```

One feature at a time is `--feature <name>`, repeated for each. Every tier is `--tier all`.
The run script owns test execution for the whole plugin: `purlin:build` and `purlin:audit`
call it too, so there is one answer to how a test is run.

Exit codes: `0` everything ran and passed, `1` a test failed, `2` the invocation was wrong.

## Step 2: read the table

The run prints `Ran <framework> on <n> feature(s) at tier <tier>.`, then the status table
`purlin:status` builds, so the counts come from one computation. The `Tests` column of that
table counts the words a passed cell can read:

| Word | What it means |
|------|---------------|
| `passed` | A test tagged with the rule's proof ran here and passed |
| `failed` | A tagged test ran and failed; the script names the test and the assertion |
| `no test` | The proof is written and no test carries its marker |
| `not run` | A test carries the marker and no counting run reached it |
| `code changed` | The last counting run covered a different tree |

A rule whose spec status is `drafted` has no proof text yet, so it has no passed cell to read.
Loud failures come first when they happen: `Evidence is missing: <what>.` means an arm ran and
wrote no proof entry, or a marker in the tree produced none. Read those before the table.

## Step 3: what the gate changes

This is the pattern every Purlin skill follows. Under `passed` the whole project is this one
cell: no strength, no risk, no review list, no signature, and no column for any of them. Under
`strong` the strong cell and the test strength appear beside it, and only a record CI wrote
counts. Under `signed` the signed cell and the signer list appear as well. Read the gate from
`.purlin/config.json` and print only what exists; `references/hard_gates.md` defines the three
gates once.

## Step 4: operating systems

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating
system. On a host that does not match, the run lists it under `Proofs another operating system
owns:` as `<feature> <PROOF-N>: needs <os>` rather than as a pass or a failure. An untagged
proof runs anywhere. Those three tags are the whole vocabulary.

## Step 5: name the next step

End with one line, computed from the table:

| What the table shows | The line to print |
|----------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` (fix the code or the test) |
| A rule reads `no test` | `→ Run: purlin:build <feature>` |
| A rule's spec status is `drafted` | `→ Run: purlin:spec <feature>` |
| Every rule reads `passed`, gate `passed` | `→ Push.` |
| Every rule reads `passed`, gate `strong` or `signed` | `→ Run: purlin:audit` |
| Only `needs <os>` proofs remain | `→ Run: purlin:audit --remote` |

Diagnose a failure before changing anything: `references/spec_quality_guide.md` says which of
the rule, the proof and the code is usually at fault.
