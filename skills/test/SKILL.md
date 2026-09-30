---
name: test
description: Run the marked tests and print each rule's passed cell
---

Run the project's own test suites, tie each result to the marker comment above its test, write what
they saw into `.purlin/evidence/local/` and `.purlin/tests.md`, and print every rule's passed cell.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below is
relative to the plugin root; see `references/purlin_commands.md#path-resolution`. **Pending
migrations:** when `sync_status` with `project_root` set to the project root, the top folder of the
git checkout, opens with a pending-migrations advisory, stop and follow
`references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:test                     Run the features your change touched
purlin:test --all               Run every feature
purlin:test <feature> [...]     Run one feature, or several
purlin:test --commit            Commit the work and the evidence the run wrote
purlin:test --remote            Let the git host's runner do the run
purlin:test --arm-timeout <seconds>  Give each suite longer than an hour
purlin:test --release [<version>]  Run every test, commit the evidence and the package, and tag the release at the gate passed
```

## Step 1: run the tests

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --test
```

Add `--all` for `purlin:test --all` and `--feature <name>` for each feature named. With neither, the
run selects each feature with no run on this operating system, whose spec, code or tests changed
since its evidence, with an untracked file under its `> Scope:` or beside its tests, or whose spec
names no files, and runs only the test files carrying its markers: each suite of the `tests` setting
gets them as its `{files}`. It first prints `Selected <n> of <m> features: login (code changed since
a1b2c3d), ...`, the skipped ones ending `purlin:test --all runs them too.`, and a line per untracked
file. With nothing selected it prints `Nothing to run: every feature's spec, code and tests match
its evidence. purlin:test --all runs them anyway.` and exits 1 only where the evidence holds a
failing test. Add `--arm-timeout <seconds>` when the person gave it. `--remote` hands the run to the
git host's runner on a run branch it creates, waits on and deletes; the runner commits its section
under `.purlin/evidence/ci/` and the run pulls it back. It refuses a detached head and a tree with
changes that are not committed, and pushes nothing then. It waits through `gh` on GitHub and `az`
with `azure-devops` on Azure DevOps. With no gh on GitHub or no az on Azure DevOps it pushes nothing
and names the program to install; a failed run, no run found or the wait over exits 1.

Exit codes: `0` everything asked happened, `1` a tied test failed or did not run, evidence is missing, a marker names nothing a spec has, there is no settings file, the settings file cannot be read, an older Purlin set the project up, or no test command is set, `2` the invocation was wrong. A test run cannot make an audit or a signature appear, so the gate does not set the code. `purlin:test --release [<version>]` runs the script with `--release [<version>]`: every test, both commits of `--commit`, then the release, which commits `.purlin/evidence/package/<version>.json` and, at the gate `passed`, tags `passed/<version>`; at `signed` it prints `Run purlin:sign to sign it`. It never pushes. A refused release prints one line beginning `No release:` and exits 1.

## Step 2: when the run stops before any test

It writes nothing and names what is missing:

| The run prints | What you do |
|----------------|-------------|
| `No .purlin/config.json here, so nothing ran.` | Run `purlin:init`, then this skill again |
| `This project was set up by an older Purlin and not upgraded` | Run `purlin:init --update`, then this skill again |
| `.purlin/config.json cannot be read:` | `→ Fix the settings file by hand, then run: purlin:test` |
| `Suggested tests setting: <the entries as one JSON array on one line>` | Show the person each suggested command, with the line after it that says what the tool needs added first, such as jest's `jest-junit`. Compare each suggested command with how the project runs its tests itself, in its CI files, its manifest's scripts, `tox.ini` or `Makefile`: the interpreter, and options such as `--doctest-modules` or `--no-restore`; show the person each difference and offer the entry with the project's own. Run the line that says what a tool needs, as printed, once the person agrees. Ask once. On yes, write that array as the `tests` setting with the `purlin_config` tool, then run Step 1 again |
| `no test tool Purlin knows was found` | Read the project, its manifest, its test folder and its CI files, and propose one entry in the shape `references/formats/marker_format.md` gives. Ask, write it the same way, and run Step 1 again |

## Step 3: the evidence, written and committed when asked

The run writes this operating system's section of `.purlin/evidence/local/<feature>.json` (the
commit, the time, the machine, the fingerprint of the spec, code and tests it saw, each rule's word,
each proof's result and test) and `.purlin/tests.md`, one table for the whole project. It prints
`Evidence written to .purlin/evidence/local/<feature>.json.`, or the folder and a count for several
features, and commits nothing. With `--commit` it makes two commits under your own git identity. The
first, `purlin: specs, tests and settings for <feature>`, holds the specs of the features run, the
test files carrying their markers and `.purlin/config.json`, and the run prints `Committed <sha7>,
the work these results describe:` and each path. The second, `purlin: evidence at <sha7>`, holds the
evidence and names the first; the run prints `Evidence committed.`, or `Evidence unchanged.` when
nothing new was seen. It never pushes. `references/formats/evidence_format.md` is the contract.

## Step 4: read what the run found

The run prints `Markers: <n> tied to a test, <k> not tied.` and `Ran <suite> on <n> features.`,
then one line per rule that fails or has no test, `<feature> RULE-<n> fails: <file>::<test>. Run
purlin:build <feature>.`, `<feature> RULE-<n> has no test. Run purlin:build <feature>.` or
`<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`, then
the status table `purlin:status` builds. The `Tests` column counts the words a passed cell can read:

| Word | What it means |
|------|---------------|
| `passed` | Every test marked with the rule's proofs ran here and passed |
| `failed` | A marked test ran and failed; the run prints the last 60 lines of the suite's own output |
| `no test` | No test carries the proof's marker, or, with the reason `no proof written`, the rule has neither |
| `not run` | A test carries the marker and no counting run reached it |
| `out of date` | The spec, the code or the tests changed since the run; the reason names which |

Loud failures come first: `Evidence is missing: <what>.` means a suite left no readable report,
or a marker has no pass or fail: its test was skipped, the report lacks it, or no test follows it.
A marker naming nothing a spec has reads `<file>:<line> names <feature> <ID>, which no spec has.`

## Step 5: operating systems

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating system.
On a host that does not match, the run prints one line per system, `<n> proofs need <System>; this
machine is <System>. Run purlin:test --remote.` (for one, `1 proof needs <System>; this machine is
<System>. Run purlin:test --remote.`). An untagged proof runs anywhere (`references/hard_gates.md`,
"Where a runner runs"). A system that is neither Windows nor macOS is `linux`, shown as
`Linux/Unix`. Each system a counting run covered is one platform in the passed cell; a rule reads
`partial` where two systems that each ran disagree.

## Step 6: name the next step

The run ends on the summary sentence and `Left to do`, the lines `sync_status` returned, counted
over every rule under `specs/`. Print them as they are. The first line of `Left to do` is the next
step:

| What the run ends on | The line to print |
|----------------------|-------------------|
| `Left to do:` and its lines | `→ Run: <the command on its first line>` |
| A line `<feature> RULE-<n> fails: ...` above the status | `→ Run: purlin:build <feature>` (fix the code or the test) |
| `Nothing left to do. To release a version: purlin:test --release` (at `signed`, `, then purlin:sign`) | `→ Run: purlin:test --release` |
| A line beginning `No release:` | `→ Run: <the command it names>`, or say what git refused |
| `Nothing left to do. Push the tag to release it: git push origin <tag>` | `→ Run: git push origin <tag>` |

Diagnose a failure first: `references/spec_quality_guide.md` says which part is at fault.
