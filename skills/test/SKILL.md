---
name: test
description: Run the project's marked tests and record the results as evidence; with --all --commit, the hand-off before a sign-off
---

Run the project's own test suites, tie each result to the marker comment above its test, write
what they saw into `.purlin/evidence/local/`, and print every rule's passed cell. The hand-off to
a sign-off is `purlin:test --all --commit`, and the project's own run for the proofs tagged for
another operating system (Step 5).

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below is
relative to the plugin root; see `references/purlin_commands.md#path-resolution`. Pass
`project_root` on every Purlin tool call: the top folder of the git checkout you are working in.
**Pending migrations:** when the status opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

A line marked **Stop and ask** is a question for the person: print it, end your turn, and act
only on their answer. Never answer it yourself.

## Usage

```
purlin:test                     Run the features your change touched
purlin:test --all               Run every feature, slow proofs included
purlin:test <feature> [...]     Run one feature, or several
purlin:test --commit            Commit the work and the evidence the run wrote
purlin:test --all --commit      The hand-off: run every feature and commit the results
purlin:test --arm-timeout <seconds>  Give each suite longer than an hour
```

## Step 1: run the tests

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --test --project-root .
```

Add `--all` for `purlin:test --all` and `--feature <name>` for each feature named. Add
`--arm-timeout <seconds>` when the person gave it.

With neither `--all` nor a feature, the run selects a feature in any of these cases:

- it has no run on this operating system;
- its spec, code or tests changed since its evidence;
- an untracked file sits under its `> Scope:` or beside its tests;
- its spec names no files.

It runs only the test files carrying those features' markers: each suite of the `tests` setting
gets them as its `{files}`. It first prints `Selected <n> of <m> features: login (code changed
since a1b2c3d), ...`, the skipped ones ending `purlin:test --all runs them too.`, and a line per
untracked file. With nothing selected it prints `Nothing to run: every feature's spec, code and
tests match its evidence. purlin:test --all runs them anyway.` and exits 1 only where the
evidence holds a failing test. The status follows it, as after every run.

Without `--all` the run never starts a slow proof's test and prints `Left out <n> slow proofs`,
naming each; `references/purlin_commands.md` says what each run starts, and the status then
lists `<n> slow proofs to run: purlin:test --all`. A plain run keeps an earlier slow result
while nothing its spec covers changed. The status counts it. The sign-off does not: run
`purlin:test --all --commit` before `purlin:sign`.

The exit codes are in `references/purlin_commands.md`, "Exit codes". A test comment to correct
changes no exit code; it makes the tests read `not met`.

## Step 2: when the run stops before any test

It writes nothing and names what is missing:

| The run prints | What you do |
|----------------|-------------|
| `No .purlin/config.json here, so nothing ran.` | Run `purlin:init`, then this skill again |
| `This project was set up by an older Purlin and not upgraded` | Run `purlin:init --update`, then this skill again |
| `.purlin/config.json cannot be read:` | `→ Fix the settings file by hand, then run: purlin:test` |
| `Suggested tests setting: <the entries as one JSON array on one line>` | Show the person each suggested command, with the line after it that says what the tool needs added first, such as jest's `jest-junit`. Compare each suggested command with how the project runs its tests itself, in its CI files, its manifest's scripts, `tox.ini` or `Makefile`: the interpreter and its options; show the person each difference and offer the entry with the project's own. Run the line that says what a tool needs, as printed, once the person agrees. **Stop and ask** once. On yes, run Step 1 again with `--write-tests`: it writes the suggested entries and runs. Where the person chose a command of their own, write that array as the `tests` setting with the `purlin_config` tool, then run Step 1 again |
| `no test tool Purlin knows was found` | Read the project, its manifest, its test folder and its CI files, and propose one entry in the shape `references/formats/marker_format.md` gives. **Stop and ask**. On yes, write it as the `tests` setting with the `purlin_config` tool, and run Step 1 again |

## Step 3: the evidence, written and committed when asked

The run writes this operating system's section of `.purlin/evidence/local/<feature>.json`. The
section holds:

- the commit of the code it describes, and the time;
- who ran it, and on which machine;
- the fingerprint of the spec, code and tests it saw;
- each rule's word, and each proof's result and test.

It prints `Evidence written to .purlin/evidence/local/<feature>.json.`, or the folder and a count
for several features. It commits nothing.

With `--commit` it makes two commits under your own git identity: the work, then the evidence
that names it. It never pushes. `references/commit_conventions.md`, "The two commits of a run",
says what each commit holds. `references/formats/evidence_format.md` is the contract for the file
and for the lines the run prints.

The tests read `met` only on committed evidence. A sign-off counts only results taken on this
version of the code. So before a person signs, run `purlin:test --all --commit`. It runs every
feature on the code as committed, then commits the results.

## Step 4: read what the run found

The run prints, in this order:

1. `Markers: <n> tied to a test, <k> not tied.`
2. Each test comment to correct.
3. `Ran <suite> on <n> features.`
4. One line per rule that fails or has no test. It is one of:
   - `<feature> RULE-<n> fails: <file>::<test>. Run purlin:build <feature>.`
   - `<feature> RULE-<n> has no test. Run purlin:build <feature>.`
   - `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`
5. The status `purlin:status` builds.

For a failed test the run also prints the last 60 lines of the suite's own output.

The `Tests` column counts the words a passed cell can read: `passed`, `partial`, `failed`,
`no test`, `not run` and `out of date`. `references/spec_quality_guide.md`, "When a rule is
stuck", says what each word means, with its reasons, and what moves it.

A test comment to correct reads `<file>:<line> names <feature> <PROOF-N>, whose wording changed
after the test was last changed in <sha7>: ...`. It clears once the test itself changes: run
`purlin:build <feature>`.

Loud failures come first. `Evidence is missing: <what>.` means one of two things:

- a suite left no readable report;
- a marker has no pass or fail: its test was skipped, the report lacks it, or no test follows it.

A marker naming nothing a spec has reads `<file>:<line> names <feature> <ID>, which no spec has.`

## Step 5: another operating system

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating system.
On a machine that does not match, the run prints one line per system, `<n> proofs need <System>;
this machine is <System>. Run purlin:test on <System>.` That is an instruction, not a command
line: `purlin:test` on a machine of that system meets it, and so does the project's own run
there. An untagged proof runs anywhere. A system
that is neither Windows nor macOS is `linux`, shown as `Linux/Unix`. A rule reads `partial` where
two systems that each ran disagree.

Purlin runs the tests where you are and starts no run anywhere else. When the run prints that
line, look in the project for its own setup for that system: a workflow or pipeline file that
runs `scripts/run/purlin_run.py --ci`.

- **There is one.** Say how this project starts it, as its own files say, and **Stop and ask**
  whether to start it. Start it only on a yes. When it has finished, `git pull` brings the results back and
  `purlin:status` shows them.
- **There is none.** **Stop and ask**, in these words: `No setup in this project runs the tests on
  <System>. I can write one for <git host>: a file that runs the tagged tests there and returns
  the results through git, and a way to start it. Write it? [y/N]`. Read the git host from
  `origin`; where it names none, or the person wants another, ask which. On yes, write it as
  `references/evidence_and_signoff.md`, "A run on another system" says, show the files, and
  commit them only when the person says so. The files are the project's own: Purlin ships none
  and changes none later.

## Step 6: name the next step

The run ends on the summary sentence and `Left to do`, the lines of the status, counted over
every rule under `specs/`. Show the run's last lines as it printed them. The first line of `Left to do` is the next
step:

| What the run ends on | The line to print |
|----------------------|-------------------|
| `Left to do:` and its lines | `→ Run: <the command on its first line>` |
| A line `<feature> RULE-<n> fails: ...` above the status | `→ Run: purlin:build <feature>` (fix the code or the test) |
| `<n> features whose results are not committed: purlin:test --commit` | `→ Run: purlin:test --commit` |
| `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` | `→ Run: purlin:sign`, when a person chooses to sign |

Diagnose a failure first: `references/spec_quality_guide.md` says which part is at fault.
