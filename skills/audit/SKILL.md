---
name: audit
description: Run the tests, the heuristic spot tests, one model call per rule and one planted bug per proof, then write what it found into the evidence
---

Show how much the tests are worth. The audit runs the marked tests, then for each rule that
passes: the heuristic spot tests, which read each test as text; one model call, which writes a
small bug for each proof and explains the tests; and each bug planted in a copy of the project, to
see whether the proof's own test catches it.
It writes what it found into the evidence and reports the share of rules it found strong. A person
runs it by hand, when they choose; nothing waits on it, and a weak rule stops no sign-off.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below is
relative to the plugin root; see `references/purlin_commands.md#path-resolution`. Pass
`project_root` on every Purlin tool call: the top folder of the git checkout you are working in.
**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run what the change touched, audit, write the evidence
purlin:audit <feature> [...]    One feature, or several
purlin:audit --all              Run every feature, and read every passing rule again
purlin:audit --commit           Commit the work and the evidence the run wrote
purlin:audit --arm-timeout <seconds>  Give each suite, and each planted bug's test run, longer
```

Plain language reaches the same place: "audit this", "how strong are the tests". A team may set
itself a target, such as building and auditing until 80% of rules read strong; the audit's last
line is the number to hold against it.

## Step 1: run

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --audit --project-root .
```

Add `--arm-timeout <seconds>` when the person gave it. Add `--all` for `purlin:audit --all` and
`--feature <name>` for each feature named; with neither, the run covers the features `purlin:test`
would select. It runs the tests, then reads each rule whose tests pass, that has a proof with a
test, and whose text, proofs, tests or covered code changed since its last audit. It takes three
steps for each rule:

1. The heuristic spot tests, with no model.
2. One model call for the rule: a bug for each proof, and the model's reading.
3. Each bug planted in a copy of the project, and that proof's own test run.

A rule reads:

- `weak` when a spot test fires on one of its tests or a planted bug survived;
- `strong` when none did and a planted bug was caught by its proof's test;
- `spot-checked` when none did and no bug was planted and caught. The audit says why.

One caught bug makes a rule `strong`. Each of its proofs with no caught bug is named under it,
with the reason. A test that is skipped, is not collected or runs past its limit with the bug in
place is not a caught bug. An anchor's rule reads `spot-checked`: no bug is planted for one. No
bug is planted on this machine for a proof tagged for another system.

The model is started with no tools, no plugins and none of your settings, in an empty folder.
Before the first call the audit prints how many model calls it will make, one for each rule
it reads. After the last it prints what the run cost.

`references/review_criteria.md` is the one home of each step: its checks, the research behind
them and what the model is sent.

The run writes each feature's section and its `audit` into `.purlin/evidence/local/<feature>.json`
and prints `Evidence written to .purlin/evidence/local/<feature>.json.` It commits nothing unless
you add `--commit`, which commits under your own identity, and it never pushes.

The exit codes are in `references/purlin_commands.md`, "Exit codes": those of a test run, and
`1` where a file of the project changed while the audit ran. What the audit found never sets
the code: a weak rule is listed, not failed.

## Step 2: read what came back

The audit prints its calls, then one block per rule it read, then its cost, then the share, and
the run ends on the status, as every run does:

```
The audit reads 12 rules: 12 model calls.
login RULE-2   weak
  tests/test_login.py::test_wrong_password: the test checks nothing.
  PROOF-2: the test still passes when src/auth.py:12 reads "return 200"
login RULE-3   spot-checked
  The spot tests found nothing. No bug was planted: PROOF-3 needs Windows, and this machine is macOS.
The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.
The audit found 4 of 6 rules strong (66%): 4 strong, 1 weak, 1 spot-checked.
```

- A line `<file>::<test>: ...` is a spot test's finding: fix the test.
- A line `PROOF-N: the test still passes when <file>:<line> reads "<line>"` is a planted bug the
  test did not catch: add the case that tells the right behaviour from that change.
- A line `No bug was planted: <why>.` is not a finding and does not make the rule weak. A rule
  with no finding and no caught bug reads `spot-checked`.
- `<check> is not read in <language> tests.` says a spot test does not read that language.
- `The model could not be reached: <why>. <n> rules are spot-checked alone. Run purlin:audit
  again.` means `claude` gave no usable answer. A rule a spot test fired on is still written
  `weak`. Any other rule is written `spot-checked`, and the next `purlin:audit` reads it again.
- `The audit stopped: <file> changed while the audit ran. Nothing in the project was written by
  the audit.` means a file changed under the run: leave the project alone while the audit runs,
  then run it again.
- `<file>::<test>: its source was not found, so the spot tests did not read it.` means the
  evidence names a test the file no longer holds: run `purlin:test`, then `purlin:audit`.

A finding is build work. `purlin:build <feature>` fixes the test, and the rule is read again by
the next `purlin:audit`. Never narrow a rule or a proof to make a finding disappear. What the
model cost is also written to `.purlin/runtime/audit_run.json`, which git ignores.

## Step 3: name the next step

Show the ending as the run printed it, then name the next step:

- A rule reads `weak`: `→ Run: purlin:build <feature>`, then `purlin:audit` again.
- A rule reads `spot-checked`: say why, in the audit's own sentence. Where the reason is another
  system or an anchor's rule, there is nothing to run.
- `Left to do:` lists other work: `→ Run:` the command its first line names.
- Every rule read is strong and nothing else is left: say so, and name `purlin:audit --commit` to
  commit what the audit found where the person wants it kept.
