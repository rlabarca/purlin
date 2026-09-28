---
name: audit
description: Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence
---

Run the marked tests, break the code on purpose where mutation testing is on to measure how much
the tests catch, have a model read each rule's proof beside its test, and write what it found
into the evidence. An audit is level 2: it reports how good the tests are. What it writes counts
at every gate, whoever ran it: the strong cell reads the audit entry for each rule's current
text, proof and test.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run what the change touched, audit, write the evidence
purlin:audit <feature> [...]    One feature, or several
purlin:audit --all              Run every feature, and read every rule again
purlin:audit --commit           Commit the evidence the run wrote
```

Plain language reaches the same place: "audit this", "how strong are the tests". A remote
runner runs the tests, so `--remote` belongs to `purlin:test --remote`.

## Step 1: run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --audit
```

Add `--all` for `purlin:audit --all` and `--feature <name>` for each feature named. With neither,
`--audit` runs the tests `purlin:test` would select, then the breaks where mutation testing is
on, then the AI audit: one `claude -p` call per rule whose tests pass, that has a proof with a
test, and whose text, proof or test changed since its last audit, `audit_parallel` at once,
announced by `AI audit: <n> rules to read, <k> at a time.` The answer names the model that gave
it. The run writes each feature's section and its `audit` into
`.purlin/evidence/local/<feature>.json`, prints the status table, `AI audit: <n> rules read, <n>
strong, <n> weak.` and a `Test strength:` line, one line per cause for any rule the model could
not be reached for, and `Evidence written to .purlin/evidence/local/<feature>.json.`. It commits
nothing unless you add `--commit`, which commits the evidence under your own identity with the
subject `purlin: evidence at <sha7>`. It ends with `gate strong: <n> of <rules>` or
`gate not met: <n> of <rules>`, and it never pushes.

Exit codes: `0` every rule met the gate, `1` a test failed, evidence is missing, a rule could not be audited or the gate is not met, `2` the command line was wrong.

The run script owns test execution for the whole plugin: `purlin:test` and `purlin:build` call
it too. A remote runner runs the same script in an arm of its own, which writes its section
under `.purlin/evidence/ci/` and runs no audit; you never run it by hand. A project has a runner
for two reasons only, and `references/hard_gates.md` says which.

## Step 2: read what came back

Test strength is the share of the deliberate breaks the tests caught. `min_strength` in
`.purlin/config.json` is the floor the gate holds you to where mutation testing is on: 70 under
`strong`, 80 under `signed`, each overridable. With it off, `min_strength` is null and the AI
audit alone decides the strong cell.

The AI audit reads each proof beside the source of its test, against
`references/review_criteria.md`, and what comes back is what it observed, in its own words. A
finding is build work: it names what the test does not yet observe, and the rule reads `weak`
with that sentence as the reason.

## Step 3: what the gate changes

| Gate | What this run does |
|------|--------------------|
| `passed` | Runs the tests and the AI audit, and no breaks: `Test strength: not measured; the gate is passed.` Nothing blocks: `Audit: <n> strong, <n> weak. Nothing blocks at the gate passed.` |
| `strong` | Runs the breaks too where mutation testing is on, and prints the strength beside the minimum |
| `signed` | The same as `strong`. Evidence either source wrote counts here too; a project that wants CI's word before a signature sets `trust: remote`, which `purlin:sign` reads |

## Step 4: the folder is the source

An evidence file's source is the folder it sits in, and the file's own `source` field says
the same word. A file where the two disagree is ignored, with one warning naming it.

| Source | The folder | Counts under |
|--------|------------|--------------|
| ci | `.purlin/evidence/ci/<feature>.json`, written by the CI identity through the git host's API | `passed`, `strong`, `signed` |
| local | `.purlin/evidence/local/<feature>.json`, written by this command and `purlin:test` on anyone's machine | `passed`, `strong`, `signed` |

## Step 5: retention

A file keeps the newest section per operating system and the newest audit entry per rule; the
history is the file's `git log`. Nothing pins the evidence: `purlin:sign` tags the commit, and
the tag holds the whole tree, every evidence file in it included.

## Step 6: name the next step

| What the run shows | The line to print |
|--------------------|-------------------|
| A test failed | `→ Run: purlin:build <feature>` |
| Test strength below `min_strength` | `→ Run: purlin:build <feature>` (add the case the break escaped) |
| A finding on a rule | `→ Run: purlin:build <feature>` (write the case it names) |
| A rule needs another operating system | `→ Run: purlin:test --remote` |
| Every rule met the gate | `→ Run: git push` |
| A current `ci` run is missing under `trust: remote` | `→ Run: purlin:test --remote` |
| A rule could not be audited: the model could not be reached | `→ Run: purlin:audit` |
| A rule's tests pass on one operating system and not another | `→ Run: purlin:build <feature>` (the passed cell reads `partial` and names the platform) |
| A rule is in the queue: it reads `manual test`, or waits for a signature | `→ Run: purlin:sign` |
