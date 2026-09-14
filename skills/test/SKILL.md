---
name: test
description: Run the tagged tests and print the state of every rule
---

Run the tests that carry proof markers, write the proof files into `.purlin/runtime/proofs/`,
and print the state of every rule. This takes seconds: no breaks, no record, no approval.

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
The run script owns test execution for the whole plugin: `purlin:build` and `purlin:verify`
call it too, so there is one answer to how a test is run.

Exit codes: `0` everything ran and passed, `1` a test failed, `2` the invocation was wrong.

## Step 2: read the table

The script prints one line per rule with its state. This run moves a rule into one of three:

| State | What it means |
|-------|---------------|
| Drafted | The rule has no proof text yet |
| Proof ready | The proof text is written, but no passing test carries its marker |
| Tested | A test tagged with the proof ran here and passed |

A test that fails leaves its rule at Proof ready and the run exits 1. The script names the
test and the assertion; it never reports a rule as Tested on a failing run.

Records, reviews and approvals are not this skill's business; `purlin:verify` and
`purlin:status` report those. Print the table as the script returned it. Do not recount it.

## Step 3: operating systems

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating
system. On a host that does not match, the script skips the test and lists the rule as
`needs windows` rather than as a pass or a failure. An untagged proof runs anywhere.

Those three tags are the whole vocabulary. Nothing else is scoped this way.

## Step 4: name the next step

End with one line, computed from the table:

| What the table shows | The line to print |
|----------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` (fix the code or the test) |
| A rule is Proof ready with no test | `→ Run: purlin:build <feature>` |
| A rule is Drafted | `→ Run: purlin:spec <feature>` |
| Every rule is Tested | `→ Run: purlin:verify` |
| Only `needs <os>` rules remain | `→ Run: purlin:verify --remote` |

Diagnose a failure before changing anything: `references/spec_quality_guide.md` says which of
the rule, the proof and the code is usually at fault.
