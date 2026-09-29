---
name: audit
description: Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence
---

Run the marked tests, break the code on purpose where mutation testing is on to measure how much the
tests catch, have a model read each rule's proof beside its test, and write what it found into the
evidence. An audit reports how good the tests are. What it writes counts at every gate, whoever ran
it: the strong cell reads the audit entry for each rule's current text, proof and test.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below is
relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and follow
`references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run what the change touched, audit, write the evidence
purlin:audit <feature> [...]    One feature, or several
purlin:audit --all              Run every feature, and read every rule again
purlin:audit --commit           Commit the evidence the run wrote
purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature
```

Plain language reaches the same place: "audit this", "how strong are the tests". `--remote` belongs
to `purlin:test --remote`.

## Step 1: run

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --audit
```

Add `--arm-timeout <seconds>` when the person gave it. Add `--all` for `purlin:audit --all` and
`--feature <name>` for each feature named; with neither, `--audit` runs the tests `purlin:test`
would select, then the breaks where mutation testing is on, then the AI audit: one `claude -p` call
per rule whose tests pass, that has a proof with a test, and whose text, proof or test changed since
its last audit, `audit_parallel` at once, announced by `AI audit: <n> rules to read, <k> at a time.`
The run writes each feature's section and its `audit` into `.purlin/evidence/local/<feature>.json`
and prints `Evidence written to .purlin/evidence/local/<feature>.json.`. It commits nothing unless
you add `--commit`, which commits under your own identity and ends on the evidence, with the subject
`purlin: evidence at <sha7>`, and it never pushes. It then prints one line of its own, `AI audit:
<n> rules read, <s> strong, <w> weak.`, and one line per cause for any rule the model could not be
reached for, and ends on the status table, the summary and `Left to do`, as every run does.

Exit codes: `0` everything asked happened; `1` a tied test failed or did not run, evidence is
missing, a marker names nothing a spec has, `.purlin/config.json` is missing, the settings file
cannot be read, the project was set up by 0.9.5 and not upgraded, no test command is set, or at
`strong` and `signed` a rule read is weak or could not be audited; `2` the command line was wrong.
An audit cannot make a signature appear, so a rule waiting on one does not set the code.

The run script owns test execution for the whole plugin: `purlin:test` and `purlin:build` call it
too. A remote runner runs the same script in an arm of its own (`references/hard_gates.md`, "Where a
runner runs"), which writes its section under `.purlin/evidence/ci/` and runs no audit; you never
run it by hand.

## Step 2: read what came back

Test strength is the share of the deliberate breaks the tests caught; what the strong cell reads
when nothing was measured is in `references/hard_gates.md`, under the gate table, and `rules to
measure: purlin:audit` is a line an audit clears. `min_strength` in `.purlin/config.json` is the
floor the gate holds you to where mutation testing is on: 70 under `strong`, 80 under `signed`, each
overridable. With it off, `min_strength` is null and the AI audit alone decides the strong cell.

The AI audit reads each proof beside the source of its test, against
`references/review_criteria.md`, and what comes back is what it observed, in its own words. A
finding is build work: it names what the test does not yet observe, and the rule reads `weak` with
that sentence as the reason. A proof longer than 60 words, or holding two cases, is noted: the audit
reader prints each note after the findings, starting `Note:`, with no heading, and a note does not
make the rule weak.

## Step 3: what the gate changes

| Gate | What this run does |
|------|--------------------|
| `passed` | Runs the tests and the AI audit, and no breaks: test strength is not measured, and what the audit finds holds nothing back |
| `strong` | Runs the breaks too where mutation testing is on; a rule whose feature's strength is under the minimum reads `weak` |
| `signed` | The same as `strong`. Evidence either source wrote counts here too |

## Step 4: the folder is the source

An evidence file's source is the folder it sits in, and the file's own `source` field says the same
word. A file where the two disagree is ignored, with one warning naming it.

| Source | The folder | Counts under |
|--------|------------|--------------|
| ci | `.purlin/evidence/ci/<feature>.json`, written by a remote runner | `passed`, `strong`, `signed` |
| local | `.purlin/evidence/local/<feature>.json`, written by this command and `purlin:test` on anyone's machine | `passed`, `strong`, `signed` |

## Step 5: retention

A file keeps the newest section per operating system and the newest audit entry per rule; the
history is the file's `git log`. Nothing pins the evidence: `purlin:sign` tags the commit, and the
tag holds the whole tree, every evidence file in it included.

## Step 6: name the next step

Show the ending as the run printed it; the first line of `Left to do` is the next step:

- `Left to do:` lists work: `→ Run:` the command its first line names, such as `purlin:build` after
  `2 rules to strengthen: purlin:build`.
- `Nothing left to do.`: say so and name no command. At the gate `signed` the line goes on to name
  the release step, `git push origin signed/<version>`.
